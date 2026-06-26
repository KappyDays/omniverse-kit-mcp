"""Probe the MCP server via stdio JSON-RPC.

By default this lists tools/resources from a fresh local server. Pass
``--workspace workspaces/isaac/instance-1`` to spawn the same workspace-local
stdio entry used by Codex/Claude Code, ``--runtime-info`` to confirm the active
tool/app profile and import freshness, and ``--scenario-plan`` to verify that a
scenario plan payload exposes the expected preflight fields without mutating a
live stage.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)


REPO_ROOT = Path(__file__).resolve().parent.parent
PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")
PLAN_REQUIRED_FIELDS = (
    "preflight_requirements",
    "simulation_state_summary",
    "simulation_state_steps",
    "timeline_control_steps",
    "live_validation_checklist",
)
ROBOT_PROBE_UNKNOWN_PROFILE_FALLBACK_TOOL_ORDER = (
    "robot_list_arm_profiles",
    "robot_probe_arm_profiles",
    "official_asset_search",
    "asset_search",
    "robot_load",
)
LIVE_EVIDENCE_SUMMARY_FIELDS = (
    "step_id",
    "phase",
    "status",
    "attempts",
    "max_attempts",
    "retry_failure_count",
    "evidence_kind",
    "kind",
    "name",
    "app_profile",
    "verification_status",
    "load_quality",
    "attempt",
    "timeout_s",
    "retry_count",
    "error",
    "error_code",
    "num_points",
    "backend",
    "frames_waited",
    "empty_reason",
    "warning",
    "truncated",
    "viewport_name",
    "distance",
    "prim_count",
    "bbox_empty",
    "sha256",
    "width",
    "height",
    "warmup_frames_used",
    "passed",
    "pixel_mean_average",
    "pixel_variance_average",
    "failure_codes",
    "diagnostics.reason",
    "diagnostics.target_status",
    "diagnostics.current_catalog_status",
    "diagnostics.stale_warning",
    "diagnostics.error_type",
    "diagnostics.min_points",
    "diagnostics.fallback_tool_order",
    "diagnostics.readback_paths_attempted",
    "diagnostics.cached_lidar_instance",
    "diagnostics.suggested_next",
    "diagnostics.asset_checks",
    "diagnostics.material_checks",
)
LIVE_DIAGNOSTIC_NEXT_ACTION_FIELDS = (
    "step_id",
    "phase",
    "source",
    "status",
    "error_code",
    "final_step_status",
    "attempt",
    "diagnostics.reason",
    "diagnostics.target_status",
    "diagnostics.current_catalog_status",
    "diagnostics.error_type",
    "diagnostics.num_points",
    "diagnostics.min_points",
    "diagnostics.fallback_tool_order",
    "diagnostics.readback_paths_attempted",
    "diagnostics.cached_lidar_instance",
    "diagnostics.failure_codes",
    "diagnostics.upstream_error_code",
    "diagnostics.timeout_s",
    "diagnostics.pixel_mean_average",
    "diagnostics.pixel_variance_average",
    "diagnostics.min_mean",
    "diagnostics.min_variance",
    "diagnostics.asset_checks",
    "diagnostics.material_checks",
    "suggested_next",
)
_MISSING = object()


def _summary_field_value(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row[field]
    current: Any = row
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _load_workspace_stdio_entry(workspace: Path) -> tuple[list[str], Path, dict[str, str]]:
    if not workspace.is_absolute():
        workspace = REPO_ROOT / workspace
    mcp_path = workspace / ".mcp.json"
    config = json.loads(mcp_path.read_text(encoding="utf-8"))
    servers = config.get("mcpServers")
    if not isinstance(servers, dict) or len(servers) != 1:
        raise ValueError(f"{mcp_path} must contain exactly one mcpServers entry")
    _server_name, server_config = next(iter(servers.items()))
    if server_config.get("type") != "stdio":
        raise ValueError(f"{mcp_path} server must use type='stdio'")
    command = server_config.get("command")
    args = server_config.get("args", [])
    if not isinstance(command, str) or not isinstance(args, list):
        raise ValueError(f"{mcp_path} server command/args are invalid")
    env = server_config.get("env", {})
    if not isinstance(env, dict):
        raise ValueError(f"{mcp_path} server env must be an object")
    return [command, *(str(arg) for arg in args)], workspace, {
        str(key): str(value) for key, value in env.items()
    }


def _default_stdio_entry() -> tuple[list[str], Path, dict[str, str]]:
    return [PY, "-m", "omniverse_kit_mcp.main"], REPO_ROOT, {}


def _parse_json_object(raw_json: str | None, *, label: str) -> dict[str, Any] | None:
    if raw_json is None:
        return None
    parsed = json.loads(raw_json)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must decode to a JSON object")
    return parsed


def _merge_required_plan_fields(
    require_default_fields: bool,
    custom_fields: list[str] | None,
) -> tuple[str, ...]:
    fields: list[str] = []
    if require_default_fields:
        fields.extend(PLAN_REQUIRED_FIELDS)
    fields.extend(custom_fields or [])
    return tuple(dict.fromkeys(field.strip() for field in fields if field.strip()))


def _parse_required_tool_sequence(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _parse_expected_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    return raw == "true"


def _tool_text_response(response: dict[str, Any]) -> str:
    if "error" in response:
        raise RuntimeError(json.dumps(response["error"], ensure_ascii=False))
    content = response.get("result", {}).get("content", [])
    if not isinstance(content, list):
        raise RuntimeError("tools/call response result.content must be a list")
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if isinstance(text, str):
                return text
    raise RuntimeError("tools/call response did not include text content")


def _tool_json_response(response: dict[str, Any]) -> dict[str, Any]:
    text = _tool_text_response(response)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise RuntimeError("tools/call text content did not decode to an object")
    return parsed


def _runtime_info_probe_summary(payload: dict[str, Any]) -> dict[str, Any]:
    included_groups = payload.get("included_groups")
    omitted_tools = payload.get("omitted_tools")
    return {
        "tool_profile": payload.get("tool_profile"),
        "app_profile": payload.get("app_profile"),
        "tool_count": payload.get("tool_count"),
        "registered_tool_count": payload.get("registered_tool_count"),
        "omitted_tool_count": payload.get("omitted_tool_count"),
        "included_group_count": len(included_groups)
        if isinstance(included_groups, dict)
        else None,
        "omitted_tool_list_count": len(omitted_tools)
        if isinstance(omitted_tools, list)
        else None,
        "custom_include_tokens": payload.get("custom_include_tokens"),
        "custom_exclude_tokens": payload.get("custom_exclude_tokens"),
        "source_newer_than_import": payload.get("source_newer_than_import"),
        "restart_required_for_latest_mcp_code": payload.get(
            "restart_required_for_latest_mcp_code"
        ),
        "has_mcp_runtime_info_tool": payload.get("has_mcp_runtime_info_tool"),
        "robot_probe_result_has_checks": payload.get(
            "robot_probe_result_has_checks"
        ),
        "robot_probe_unknown_profile_error_code": payload.get(
            "robot_probe_unknown_profile_error_code"
        ),
        "robot_probe_unknown_profile_error_data_path": payload.get(
            "robot_probe_unknown_profile_error_data_path"
        ),
        "robot_probe_unknown_profile_fallback_tool_order": payload.get(
            "robot_probe_unknown_profile_fallback_tool_order"
        ),
    }


def _runtime_info_mismatches(
    summary: dict[str, Any],
    *,
    expect_tool_profile: str | None = None,
    expect_app_profile: str | None = None,
    expect_tool_count: int | None = None,
    require_runtime_fresh: bool = False,
    require_robot_probe_error_contract: bool = False,
) -> list[str]:
    mismatches: list[str] = []
    if (
        expect_tool_profile is not None
        and summary.get("tool_profile") != expect_tool_profile
    ):
        mismatches.append(
            f"tool_profile expected {expect_tool_profile!r}, "
            f"got {summary.get('tool_profile')!r}"
        )
    if (
        expect_app_profile is not None
        and summary.get("app_profile") != expect_app_profile
    ):
        mismatches.append(
            f"app_profile expected {expect_app_profile!r}, "
            f"got {summary.get('app_profile')!r}"
        )
    if (
        expect_tool_count is not None
        and summary.get("tool_count") != expect_tool_count
    ):
        mismatches.append(
            f"tool_count expected {expect_tool_count}, "
            f"got {summary.get('tool_count')!r}"
        )
    if require_runtime_fresh:
        if summary.get("source_newer_than_import") is True:
            mismatches.append("source_newer_than_import is true")
        if summary.get("restart_required_for_latest_mcp_code") is True:
            mismatches.append("restart_required_for_latest_mcp_code is true")
    if require_robot_probe_error_contract:
        if summary.get("robot_probe_result_has_checks") is not True:
            mismatches.append("robot_probe_result_has_checks is not true")
        if summary.get("robot_probe_unknown_profile_error_code") != (
            "ROBOT_PROBE_UNKNOWN_PROFILE"
        ):
            mismatches.append(
                "robot_probe_unknown_profile_error_code expected "
                "'ROBOT_PROBE_UNKNOWN_PROFILE', got "
                f"{summary.get('robot_probe_unknown_profile_error_code')!r}"
            )
        if summary.get("robot_probe_unknown_profile_error_data_path") != (
            "data.checks.probe.evidence"
        ):
            mismatches.append(
                "robot_probe_unknown_profile_error_data_path expected "
                "'data.checks.probe.evidence', got "
                f"{summary.get('robot_probe_unknown_profile_error_data_path')!r}"
            )
        if tuple(summary.get(
            "robot_probe_unknown_profile_fallback_tool_order"
        ) or ()) != ROBOT_PROBE_UNKNOWN_PROFILE_FALLBACK_TOOL_ORDER:
            mismatches.append(
                "robot_probe_unknown_profile_fallback_tool_order expected "
                f"{list(ROBOT_PROBE_UNKNOWN_PROFILE_FALLBACK_TOOL_ORDER)!r}, "
                "got "
                f"{summary.get('robot_probe_unknown_profile_fallback_tool_order')!r}"
            )
    return mismatches


def _live_validation_tool_mismatches(
    summary: dict[str, Any],
    expected_tools: tuple[str, ...],
) -> list[str]:
    if not expected_tools:
        return []
    actual_tools = summary.get("live_validation_tools")
    if not isinstance(actual_tools, list):
        return ["live_validation_tools summary is missing or malformed"]
    actual = tuple(str(tool) for tool in actual_tools)
    if actual == expected_tools:
        return []
    return [
        "live_validation_tools expected "
        f"{list(expected_tools)!r}, got {list(actual)!r}"
    ]


def _plan_flag_mismatches(
    summary: dict[str, Any],
    *,
    expect_scratch_stage_required: bool | None = None,
    expect_log_capture_recommended: bool | None = None,
) -> list[str]:
    mismatches: list[str] = []
    expectations = {
        "scratch_stage_required": expect_scratch_stage_required,
        "log_capture_recommended": expect_log_capture_recommended,
    }
    for field, expected in expectations.items():
        if expected is not None and summary.get(field) != expected:
            mismatches.append(
                f"{field} expected {expected}, got {summary.get(field)!r}"
            )
    return mismatches


def _parse_expected_retry_key_args(
    raw_values: list[str],
) -> tuple[tuple[str, str, Any], ...]:
    expectations: list[tuple[str, str, Any]] = []
    for raw in raw_values:
        if ":" not in raw or "=" not in raw:
            raise ValueError(
                "--expect-retry-key-arg entries must look like step_id:key=value"
            )
        step_id, rest = raw.split(":", 1)
        key, raw_value = rest.split("=", 1)
        step_id = step_id.strip()
        key = key.strip()
        if not step_id or not key:
            raise ValueError(
                "--expect-retry-key-arg requires non-empty step_id and key"
            )
        try:
            value: Any = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        expectations.append((step_id, key, value))
    return tuple(expectations)


def _retry_key_arg_mismatches(
    summary: dict[str, Any],
    expectations: tuple[tuple[str, str, Any], ...],
) -> list[str]:
    if not expectations:
        return []
    retry_steps = summary.get("retry_steps")
    if not isinstance(retry_steps, list):
        return ["retry_steps summary is missing or malformed"]
    by_id = {
        str(step.get("step_id")): step
        for step in retry_steps
        if isinstance(step, dict) and step.get("step_id") is not None
    }
    mismatches: list[str] = []
    for step_id, key, expected in expectations:
        step = by_id.get(step_id)
        if step is None:
            mismatches.append(f"retry step {step_id!r} was not found")
            continue
        key_args = step.get("key_args")
        if not isinstance(key_args, dict):
            mismatches.append(f"retry step {step_id!r} key_args missing or malformed")
            continue
        if key not in key_args:
            mismatches.append(f"retry step {step_id!r} key_args[{key!r}] was not found")
            continue
        actual = key_args.get(key)
        if actual != expected:
            mismatches.append(
                f"retry step {step_id!r} key_args[{key!r}] expected "
                f"{expected!r}, got {actual!r}"
            )
    return mismatches


def _parse_expected_automatic_cleanup_timeouts(
    raw_values: list[str],
) -> tuple[tuple[str, float], ...]:
    expectations: list[tuple[str, float]] = []
    for raw in raw_values:
        if "=" not in raw:
            raise ValueError(
                "--expect-automatic-cleanup-timeout entries must look like "
                "step_id=seconds"
            )
        step_id, raw_value = raw.split("=", 1)
        step_id = step_id.strip()
        if not step_id:
            raise ValueError(
                "--expect-automatic-cleanup-timeout requires non-empty step_id"
            )
        try:
            timeout_s = float(raw_value)
        except ValueError as exc:
            raise ValueError(
                "--expect-automatic-cleanup-timeout seconds must be numeric"
            ) from exc
        expectations.append((step_id, timeout_s))
    return tuple(expectations)


def _automatic_cleanup_timeout_mismatches(
    summary: dict[str, Any],
    expectations: tuple[tuple[str, float], ...],
) -> list[str]:
    if not expectations:
        return []
    cleanup_steps = summary.get("automatic_cleanup_steps")
    if not isinstance(cleanup_steps, list):
        return ["automatic_cleanup_steps summary is missing or malformed"]
    by_id = {
        str(step.get("step_id")): step
        for step in cleanup_steps
        if isinstance(step, dict) and step.get("step_id") is not None
    }
    mismatches: list[str] = []
    for step_id, expected in expectations:
        step = by_id.get(step_id)
        if step is None:
            mismatches.append(f"automatic cleanup step {step_id!r} was not found")
            continue
        actual = step.get("timeoutSeconds")
        try:
            actual_s = float(actual)
        except (TypeError, ValueError):
            mismatches.append(
                f"automatic cleanup step {step_id!r} timeoutSeconds "
                f"is missing or non-numeric: {actual!r}"
            )
            continue
        if actual_s != expected:
            mismatches.append(
                f"automatic cleanup step {step_id!r} timeoutSeconds expected "
                f"{expected!r}, got {actual!r}"
            )
    return mismatches


def _live_evidence_kind_mismatches(
    summary: dict[str, Any],
    expected_kinds: tuple[str, ...],
) -> list[str]:
    if not expected_kinds:
        return []
    evidence_kinds = summary.get("evidence_kinds")
    if not isinstance(evidence_kinds, list):
        return ["evidence_kinds summary is missing or malformed"]
    actual = {str(kind) for kind in evidence_kinds}
    return [
        f"live evidence kind {expected!r} was not found"
        for expected in expected_kinds
        if expected not in actual
    ]


def _parse_expected_live_evidence_fields(
    raw_values: list[str],
) -> tuple[tuple[str, str, Any], ...]:
    expectations: list[tuple[str, str, Any]] = []
    for raw in raw_values:
        if ":" not in raw:
            raise ValueError(
                "--expect-live-evidence-field entries must look like "
                "selector:key=value"
            )
        selector, rest = raw.split(":", 1)
        if "=" not in rest:
            raise ValueError(
                "--expect-live-evidence-field entries must look like "
                "selector:key=value"
            )
        key, raw_value = rest.split("=", 1)
        selector = selector.strip()
        key = key.strip()
        raw_value = raw_value.strip()
        if not selector or not key:
            raise ValueError(
                "--expect-live-evidence-field requires non-empty selector and key"
            )
        try:
            value: Any = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        expectations.append((selector, key, value))
    return tuple(expectations)


def _live_evidence_field_mismatches(
    summary: dict[str, Any],
    expectations: tuple[tuple[str, str, Any], ...],
) -> list[str]:
    if not expectations:
        return []
    evidence_rows = summary.get("evidence")
    if not isinstance(evidence_rows, list):
        return ["evidence summary is missing or malformed"]
    mismatches: list[str] = []
    for selector, key, expected in expectations:
        matching_rows = [
            row
            for row in evidence_rows
            if isinstance(row, dict)
            and (
                row.get("evidence_kind") == selector
                or row.get("step_id") == selector
            )
        ]
        if not matching_rows:
            mismatches.append(f"live evidence row {selector!r} was not found")
            continue
        actual_values = [row.get(key) for row in matching_rows if key in row]
        if not actual_values:
            mismatches.append(
                f"live evidence row {selector!r} field {key!r} was not found"
            )
            continue
        if any(actual == expected for actual in actual_values):
            continue
        mismatches.append(
            f"live evidence row {selector!r} field {key!r} expected "
            f"{expected!r}, got {actual_values!r}"
        )
    return mismatches


def _parse_expected_live_evidence_field_minimums(
    raw_values: list[str],
) -> tuple[tuple[str, str, float], ...]:
    expectations: list[tuple[str, str, float]] = []
    for raw in raw_values:
        if ":" not in raw:
            raise ValueError(
                "--expect-live-evidence-field-min entries must look like "
                "selector:key=minimum"
            )
        selector, rest = raw.split(":", 1)
        if "=" not in rest:
            raise ValueError(
                "--expect-live-evidence-field-min entries must look like "
                "selector:key=minimum"
            )
        key, raw_value = rest.split("=", 1)
        selector = selector.strip()
        key = key.strip()
        if not selector or not key:
            raise ValueError(
                "--expect-live-evidence-field-min requires non-empty selector "
                "and key"
            )
        try:
            minimum = float(raw_value)
        except ValueError as exc:
            raise ValueError(
                "--expect-live-evidence-field-min minimum must be numeric"
            ) from exc
        expectations.append((selector, key, minimum))
    return tuple(expectations)


def _live_evidence_field_minimum_mismatches(
    summary: dict[str, Any],
    expectations: tuple[tuple[str, str, float], ...],
) -> list[str]:
    if not expectations:
        return []
    evidence_rows = summary.get("evidence")
    if not isinstance(evidence_rows, list):
        return ["evidence summary is missing or malformed"]
    mismatches: list[str] = []
    for selector, key, expected_minimum in expectations:
        matching_rows = [
            row
            for row in evidence_rows
            if isinstance(row, dict)
            and (
                row.get("evidence_kind") == selector
                or row.get("step_id") == selector
            )
        ]
        if not matching_rows:
            mismatches.append(f"live evidence row {selector!r} was not found")
            continue
        actual_values = [row.get(key) for row in matching_rows if key in row]
        if not actual_values:
            mismatches.append(
                f"live evidence row {selector!r} field {key!r} was not found"
            )
            continue
        actual_numbers: list[float] = []
        for actual in actual_values:
            try:
                actual_numbers.append(float(actual))
            except (TypeError, ValueError):
                continue
        if any(actual >= expected_minimum for actual in actual_numbers):
            continue
        mismatches.append(
            f"live evidence row {selector!r} field {key!r} expected at least "
            f"{expected_minimum!r}, got {actual_values!r}"
        )
    return mismatches


def _live_cleanup_failure_mismatches(
    summary: dict[str, Any],
    expected_count: int | None,
) -> list[str]:
    if expected_count is None:
        return []
    actual = summary.get("cleanup_failed_steps")
    try:
        actual_count = int(actual)
    except (TypeError, ValueError):
        return [
            "cleanup_failed_steps expected "
            f"{expected_count}, got {actual!r}"
        ]
    if actual_count == expected_count:
        return []
    return [
        "cleanup_failed_steps expected "
        f"{expected_count}, got {actual!r}"
    ]


def _parse_expected_live_failure_step_errors(
    raw_values: list[str],
) -> tuple[tuple[str, str], ...]:
    expectations: list[tuple[str, str]] = []
    for raw in raw_values:
        if "=" not in raw:
            raise ValueError(
                "--expect-live-failure-step-error entries must look like "
                "step_id=ERROR_CODE"
            )
        step_id, error_code = raw.split("=", 1)
        step_id = step_id.strip()
        error_code = error_code.strip()
        if not step_id or not error_code:
            raise ValueError(
                "--expect-live-failure-step-error requires non-empty "
                "step_id and ERROR_CODE"
            )
        expectations.append((step_id, error_code))
    return tuple(expectations)


def _live_failure_step_error_mismatches(
    summary: dict[str, Any],
    expectations: tuple[tuple[str, str], ...],
) -> list[str]:
    if not expectations:
        return []
    failure_steps = summary.get("failure_steps")
    if not isinstance(failure_steps, list):
        return ["failure_steps summary is missing or malformed"]
    by_id = {
        str(step.get("step_id")): step
        for step in failure_steps
        if isinstance(step, dict) and step.get("step_id") is not None
    }
    mismatches: list[str] = []
    for step_id, expected in expectations:
        step = by_id.get(step_id)
        if step is None:
            mismatches.append(f"live failure step {step_id!r} was not found")
            continue
        actual = step.get("error_code")
        if actual != expected:
            mismatches.append(
                f"live failure step {step_id!r} error_code expected "
                f"{expected!r}, got {actual!r}"
            )
    return mismatches


def _live_diagnostic_next_action_mismatches(
    summary: dict[str, Any],
    expected_min_count: int | None,
) -> list[str]:
    if expected_min_count is None:
        return []
    actual = summary.get("diagnostic_next_action_count")
    try:
        actual_count = int(actual)
    except (TypeError, ValueError):
        return [
            "diagnostic_next_action_count expected at least "
            f"{expected_min_count}, got {actual!r}"
        ]
    if actual_count >= expected_min_count:
        return []
    return [
        "diagnostic_next_action_count expected at least "
        f"{expected_min_count}, got {actual!r}"
    ]


def _parse_expected_live_diagnostic_fields(
    raw_values: list[str],
) -> tuple[tuple[str, str, Any], ...]:
    expectations: list[tuple[str, str, Any]] = []
    for raw in raw_values:
        if ":" not in raw:
            raise ValueError(
                "--expect-live-diagnostic-field entries must look like "
                "step_id:key=value"
            )
        step_id, rest = raw.split(":", 1)
        if "=" not in rest:
            raise ValueError(
                "--expect-live-diagnostic-field entries must look like "
                "step_id:key=value"
            )
        key, raw_value = rest.split("=", 1)
        step_id = step_id.strip()
        key = key.strip()
        raw_value = raw_value.strip()
        if not step_id or not key:
            raise ValueError(
                "--expect-live-diagnostic-field requires non-empty step_id "
                "and key"
            )
        try:
            value: Any = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        expectations.append((step_id, key, value))
    return tuple(expectations)


def _live_diagnostic_field_mismatches(
    summary: dict[str, Any],
    expectations: tuple[tuple[str, str, Any], ...],
) -> list[str]:
    if not expectations:
        return []
    diagnostic_rows = summary.get("diagnostic_next_actions")
    if not isinstance(diagnostic_rows, list):
        return ["diagnostic_next_actions summary is missing or malformed"]
    mismatches: list[str] = []
    for step_id, key, expected in expectations:
        matching_rows = [
            row
            for row in diagnostic_rows
            if isinstance(row, dict) and row.get("step_id") == step_id
        ]
        if not matching_rows:
            mismatches.append(f"live diagnostic row {step_id!r} was not found")
            continue
        actual_values = [row.get(key) for row in matching_rows if key in row]
        if not actual_values:
            mismatches.append(
                f"live diagnostic row {step_id!r} field {key!r} was not found"
            )
            continue
        if any(actual == expected for actual in actual_values):
            continue
        mismatches.append(
            f"live diagnostic row {step_id!r} field {key!r} expected "
            f"{expected!r}, got {actual_values!r}"
        )
    return mismatches


def _preflight_runtime_check_mismatches(
    summary: dict[str, Any],
    expected_checks: tuple[str, ...],
) -> list[str]:
    if not expected_checks:
        return []
    checks = summary.get("preflight_runtime_info_checks")
    if not isinstance(checks, list):
        return ["preflight_runtime_info_checks summary is missing or malformed"]
    actual = {str(check) for check in checks}
    return [
        f"preflight runtime check {expected!r} was not found"
        for expected in expected_checks
        if expected not in actual
    ]


def _retry_step_max_attempts(step: dict[str, Any]) -> Any:
    if step.get("max_attempts") is not None:
        return step.get("max_attempts")
    retries = step.get("retries")
    if isinstance(retries, dict):
        return retries.get("maxAttempts")
    return None


def _scenario_validate_dry_run_mismatches(payload: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    if payload.get("dry_run") is not True:
        mismatches.append(f"dry_run expected True, got {payload.get('dry_run')!r}")
    if payload.get("compiled") is not True:
        mismatches.append(f"compiled expected True, got {payload.get('compiled')!r}")
    if payload.get("steps") != payload.get("total_steps"):
        mismatches.append(
            f"steps expected total_steps {payload.get('total_steps')!r}, "
            f"got {payload.get('steps')!r}"
        )
    return mismatches


def _module_result_probe_summary(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}
    summary: dict[str, Any] = {
        "ok": payload.get("ok"),
        "status": payload.get("status"),
        "message": payload.get("message"),
        "error_code": payload.get("error_code"),
        "duration_ms": payload.get("duration_ms"),
    }
    for key in (
        "status",
        "is_playing",
        "current_time",
        "timeline_settled",
        "timeline_settle_updates",
        "capture_running",
        "capture_stop_requested",
        "capture_stop_completed",
        "capture_stop_timed_out",
        "capture_stop_timeout_s",
    ):
        if key in data:
            summary[f"data.{key}"] = data.get(key)
    diagnostics = data.get("diagnostics")
    if isinstance(diagnostics, dict):
        for key in (
            "reason",
            "error_type",
            "retryable",
            "fallback_tool_order",
        ):
            if key in diagnostics:
                summary[f"data.diagnostics.{key}"] = diagnostics.get(key)
    return {key: value for key, value in summary.items() if value is not None}


def _module_result_failed(payload: dict[str, Any]) -> bool:
    if payload.get("ok") is False:
        return True
    return payload.get("status") in {"error", "failed", "timeout"}


def _log_capture_close_mismatches(summary: dict[str, Any]) -> list[str]:
    expected = {
        "data.capture_stop_requested": True,
        "data.capture_stop_completed": True,
        "data.capture_stop_timed_out": False,
        "data.capture_running": False,
    }
    return [
        f"{key} expected {expected_value!r}, got {summary.get(key)!r}"
        for key, expected_value in expected.items()
        if summary.get(key) != expected_value
    ]


def _scenario_live_report_summary(payload: dict[str, Any]) -> dict[str, Any]:
    failure_summary = payload.get("failure_summary")
    if not isinstance(failure_summary, list):
        failure_summary = []
    evidence_summary = payload.get("evidence_summary")
    if not isinstance(evidence_summary, list):
        evidence_summary = []
    diagnostic_next_actions = payload.get("diagnostic_next_actions")
    if not isinstance(diagnostic_next_actions, list):
        diagnostic_next_actions = []
    return {
        "scenario_id": payload.get("scenario_id"),
        "status": payload.get("status"),
        "passed_steps": payload.get("passed_steps"),
        "failed_steps": payload.get("failed_steps"),
        "skipped_steps": payload.get("skipped_steps"),
        "continued_steps": payload.get("continued_steps"),
        "fatal_failed_steps": payload.get("fatal_failed_steps"),
        "cleanup_failed_steps": payload.get("cleanup_failed_steps"),
        "failure_summary_count": len(failure_summary),
        "failure_steps": [
            {
                "step_id": row.get("step_id"),
                "error_code": row.get("error_code"),
            }
            for row in failure_summary
            if isinstance(row, dict) and row.get("step_id") is not None
        ],
        "failure_step_ids": [
            row.get("step_id")
            for row in failure_summary
            if isinstance(row, dict) and row.get("step_id") is not None
        ],
        "diagnostic_next_action_count": len(diagnostic_next_actions),
        "diagnostic_next_actions": [
            {
                field: row.get(field)
                for field in LIVE_DIAGNOSTIC_NEXT_ACTION_FIELDS
                if field in row
            }
            for row in diagnostic_next_actions
            if isinstance(row, dict) and row.get("step_id") is not None
        ],
        "evidence_kinds": [
            row.get("evidence_kind")
            for row in evidence_summary
            if isinstance(row, dict) and row.get("evidence_kind") is not None
        ],
        "evidence": [
            {
                field: value
                for field in LIVE_EVIDENCE_SUMMARY_FIELDS
                if (value := _summary_field_value(row, field)) is not _MISSING
            }
            for row in evidence_summary
            if isinstance(row, dict)
            and (
                row.get("evidence_kind") is not None
                or row.get("step_id") is not None
            )
        ],
    }


def _scenario_plan_probe_summary(
    plan: dict[str, Any],
    field_names: tuple[str, ...] = PLAN_REQUIRED_FIELDS,
) -> dict[str, Any]:
    simulation_state_summary = plan.get("simulation_state_summary")
    if not isinstance(simulation_state_summary, dict):
        simulation_state_summary = {}
    simulation_state_steps = plan.get("simulation_state_steps")
    if not isinstance(simulation_state_steps, list):
        simulation_state_steps = []
    timeline_control_steps = plan.get("timeline_control_steps")
    if not isinstance(timeline_control_steps, list):
        timeline_control_steps = []
    live_validation_checklist = plan.get("live_validation_checklist")
    live_validation_steps = (
        live_validation_checklist.get("steps")
        if isinstance(live_validation_checklist, dict)
        else []
    )
    if not isinstance(live_validation_steps, list):
        live_validation_steps = []
    live_validation_tools = [
        step.get("tool")
        for step in live_validation_steps
        if isinstance(step, dict) and isinstance(step.get("tool"), str)
    ]
    retry_steps = plan.get("retry_steps")
    if not isinstance(retry_steps, list):
        retry_steps = []
    retry_step_summaries = [
        {
            "step_id": step.get("step_id") or step.get("id"),
            "phase": step.get("phase"),
            "action": step.get("action"),
            "max_attempts": _retry_step_max_attempts(step),
            "key_args": step.get("key_args"),
        }
        for step in retry_steps
        if isinstance(step, dict)
    ]
    preflight_requirements = plan.get("preflight_requirements")
    if not isinstance(preflight_requirements, dict):
        preflight_requirements = {}
    runtime_info_requirements = preflight_requirements.get("runtime_info")
    if not isinstance(runtime_info_requirements, dict):
        runtime_info_requirements = {}
    runtime_info_checks = runtime_info_requirements.get("checks")
    if not isinstance(runtime_info_checks, list):
        runtime_info_checks = []
    automatic_cleanup_steps = _automatic_cleanup_step_summaries(plan)
    return {
        "scenario_id": plan.get("scenario_id"),
        "total_steps": plan.get("total_steps"),
        "required_fields_present": {
            field: field in plan for field in field_names
        },
        "preflight_requirement_keys": sorted(preflight_requirements),
        "preflight_runtime_info_checks": runtime_info_checks,
        "play_state_missing_count": simulation_state_summary.get(
            "play_state_missing_count"
        ),
        "requires_play_count": simulation_state_summary.get("requires_play_count"),
        "simulation_state_step_count": len(simulation_state_steps),
        "timeline_control_step_count": len(timeline_control_steps),
        "automatic_cleanup_steps": automatic_cleanup_steps,
        "retry_step_count": len(retry_step_summaries),
        "retry_steps": retry_step_summaries,
        "live_validation_step_count": len(live_validation_steps),
        "live_validation_tools": live_validation_tools,
        "scratch_stage_required": (
            live_validation_checklist.get("scratch_stage_required")
            if isinstance(live_validation_checklist, dict)
            else None
        ),
        "log_capture_recommended": (
            live_validation_checklist.get("log_capture_recommended")
            if isinstance(live_validation_checklist, dict)
            else None
        ),
    }


def _automatic_cleanup_step_summaries(
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    phases = plan.get("phases")
    cleanup_steps = phases.get("cleanup") if isinstance(phases, dict) else []
    if not isinstance(cleanup_steps, list):
        return []
    return [
        {
            "step_id": step.get("id"),
            "action": step.get("action"),
            "timeoutSeconds": step.get("timeoutSeconds"),
        }
        for step in cleanup_steps
        if isinstance(step, dict) and step.get("automatic") is True
    ]


async def probe(
    *,
    workspace: Path | None = None,
    runtime_info: bool = False,
    expect_tool_profile: str | None = None,
    expect_app_profile: str | None = None,
    expect_tool_count: int | None = None,
    require_runtime_fresh: bool = False,
    require_robot_probe_error_contract: bool = False,
    live_preflight: bool = False,
    scenario_plan: str | None = None,
    scenario_validate_dry_run: bool = False,
    scenario_validate_live: bool = False,
    input_overrides: dict[str, Any] | None = None,
    required_plan_fields: tuple[str, ...] = (),
    required_live_validation_tools: tuple[str, ...] = (),
    expected_preflight_runtime_checks: tuple[str, ...] = (),
    expected_retry_key_args: tuple[tuple[str, str, Any], ...] = (),
    expected_automatic_cleanup_timeouts: tuple[tuple[str, float], ...] = (),
    expected_live_evidence_kinds: tuple[str, ...] = (),
    expected_live_evidence_fields: tuple[tuple[str, str, Any], ...] = (),
    expected_live_evidence_field_minimums: tuple[tuple[str, str, float], ...] = (),
    expect_live_cleanup_failures: int | None = None,
    expected_live_failure_step_errors: tuple[tuple[str, str], ...] = (),
    expect_live_diagnostic_next_actions_min: int | None = None,
    expected_live_diagnostic_fields: tuple[tuple[str, str, Any], ...] = (),
    expect_live_status: str = "passed",
    expect_scratch_stage_required: bool | None = None,
    expect_log_capture_recommended: bool | None = None,
    mcp_response_timeout_s: float = 30.0,
    mcp_tool_call_timeout_s: float = 900.0,
) -> int:
    runtime_info = runtime_info or live_preflight or scenario_validate_live
    if workspace is None:
        command, cwd, extra_env = _default_stdio_entry()
    else:
        command, cwd, extra_env = _load_workspace_stdio_entry(workspace)
    env = os.environ.copy()
    env.update(extra_env)
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=8 * 1024 * 1024,
    )
    assert proc.stdin is not None and proc.stdout is not None

    async def send(payload: dict[str, Any]) -> None:
        proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        await proc.stdin.drain()

    async def recv(timeout_s: float) -> dict[str, Any]:
        try:
            line = await asyncio.wait_for(
                proc.stdout.readline(),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise TimeoutError(
                "timed out waiting for MCP stdio response after "
                f"{timeout_s:g}s"
            ) from exc
        if not line:
            raise RuntimeError("server closed stdout early")
        return json.loads(line.decode("utf-8"))

    async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal next_id
        await send({
            "jsonrpc": "2.0",
            "id": next_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
            },
        })
        next_id += 1
        return await recv(mcp_tool_call_timeout_s)

    await send({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "probe", "version": "0.1"},
        },
    })
    init_resp = await recv(mcp_response_timeout_s)
    server_info = init_resp.get("result", {}).get("serverInfo", {})
    caps = init_resp.get("result", {}).get("capabilities", {})
    print(f"server: {server_info.get('name')} v{server_info.get('version')}")
    print(f"capabilities: {list(caps.keys())}")

    await send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools_resp = await recv(mcp_response_timeout_s)
    tools = tools_resp.get("result", {}).get("tools", [])
    tool_names = sorted(t["name"] for t in tools)
    print(f"\n=== tools/list: {len(tool_names)} tools ===")
    for target in (
        "scenario_validate",
        "scenario_plan",
        "scenario_last_report",
        "asset_list",
        "content_browse",
        "extension_list_all",
    ):
        mark = "+" if target in tool_names else "-"
        print(f"  {mark} {target}")

    await send({"jsonrpc": "2.0", "id": 3, "method": "resources/list"})
    res_resp = await recv(mcp_response_timeout_s)
    resources = res_resp.get("result", {}).get("resources", [])
    res_uris = sorted(r["uri"] for r in resources)
    print(f"\n=== resources/list: {len(res_uris)} resources ===")
    for uri in res_uris:
        print(f"  - {uri}")
    for uri in ("isaacsim://scenarios", "isaacsim://scenario-schema"):
        mark = "+" if uri in res_uris else "-"
        print(f"  {mark} {uri}")

    exit_status = 0
    next_id = 4

    def check_plan_expectations(
        *,
        label: str,
        plan_payload: dict[str, Any],
        plan_summary: dict[str, Any],
    ) -> bool:
        passed = True
        missing_fields = [
            field
            for field in required_plan_fields
            if field not in plan_payload
        ]
        if missing_fields:
            print(f"{label} missing required fields: " + ", ".join(missing_fields))
            passed = False
        tool_mismatches = _live_validation_tool_mismatches(
            plan_summary,
            required_live_validation_tools,
        )
        if tool_mismatches:
            print(f"{label} live validation tool order mismatch:")
            for mismatch in tool_mismatches:
                print(f"  - {mismatch}")
            passed = False
        flag_mismatches = _plan_flag_mismatches(
            plan_summary,
            expect_scratch_stage_required=expect_scratch_stage_required,
            expect_log_capture_recommended=expect_log_capture_recommended,
        )
        if flag_mismatches:
            print(f"{label} flag expectation mismatch:")
            for mismatch in flag_mismatches:
                print(f"  - {mismatch}")
            passed = False
        preflight_mismatches = _preflight_runtime_check_mismatches(
            plan_summary,
            expected_preflight_runtime_checks,
        )
        if preflight_mismatches:
            print(f"{label} preflight runtime-check expectation mismatch:")
            for mismatch in preflight_mismatches:
                print(f"  - {mismatch}")
            passed = False
        retry_mismatches = _retry_key_arg_mismatches(
            plan_summary,
            expected_retry_key_args,
        )
        if retry_mismatches:
            print(f"{label} retry key-arg expectation mismatch:")
            for mismatch in retry_mismatches:
                print(f"  - {mismatch}")
            passed = False
        cleanup_timeout_mismatches = _automatic_cleanup_timeout_mismatches(
            plan_summary,
            expected_automatic_cleanup_timeouts,
        )
        if cleanup_timeout_mismatches:
            print(f"{label} automatic cleanup timeout expectation mismatch:")
            for mismatch in cleanup_timeout_mismatches:
                print(f"  - {mismatch}")
            passed = False
        return passed

    if runtime_info:
        runtime_resp = await call_tool("mcp_runtime_info")
        runtime_text = _tool_text_response(runtime_resp)
        runtime_payload = json.loads(runtime_text)
        runtime_summary = _runtime_info_probe_summary(runtime_payload)
        print("\n=== mcp_runtime_info smoke ===")
        print(json.dumps(runtime_summary, indent=2, ensure_ascii=False))
        runtime_mismatches = _runtime_info_mismatches(
            runtime_summary,
            expect_tool_profile=expect_tool_profile,
            expect_app_profile=expect_app_profile,
            expect_tool_count=expect_tool_count,
            require_runtime_fresh=require_runtime_fresh,
            require_robot_probe_error_contract=require_robot_probe_error_contract,
        )
        if runtime_mismatches:
            print("runtime expectation mismatch:")
            for mismatch in runtime_mismatches:
                print(f"  - {mismatch}")
            exit_status = 1

    if live_preflight or scenario_validate_live:
        kit_start_payload = _tool_json_response(await call_tool("kit_app_start"))
        print("\n=== kit_app_start ===")
        print(json.dumps(
            _module_result_probe_summary(kit_start_payload),
            indent=2,
            ensure_ascii=False,
        ))
        if _module_result_failed(kit_start_payload):
            exit_status = 1
        sim_status_payload = _tool_json_response(await call_tool("simulation_get_status"))
        print("\n=== simulation_get_status preflight ===")
        print(json.dumps(
            _module_result_probe_summary(sim_status_payload),
            indent=2,
            ensure_ascii=False,
        ))
        if _module_result_failed(sim_status_payload):
            exit_status = 1
        if live_preflight:
            clear_logs_payload = _tool_json_response(
                await call_tool("extension_clear_logs")
            )
            print("\n=== extension_clear_logs preflight ===")
            print(json.dumps(
                _module_result_probe_summary(clear_logs_payload),
                indent=2,
                ensure_ascii=False,
            ))
            if _module_result_failed(clear_logs_payload):
                exit_status = 1
            log_payload = _tool_json_response(
                await call_tool(
                    "extension_capture_logs",
                    {
                        "level": "WARN",
                        "stop_after_capture": True,
                    },
                )
            )
            log_summary = _module_result_probe_summary(log_payload)
            print("\n=== extension_capture_logs WARN+ preflight ===")
            print(json.dumps(log_summary, indent=2, ensure_ascii=False))
            if _module_result_failed(log_payload):
                exit_status = 1
            log_close_mismatches = _log_capture_close_mismatches(log_summary)
            if log_close_mismatches:
                print("extension_capture_logs close expectation mismatch:")
                for mismatch in log_close_mismatches:
                    print(f"  - {mismatch}")
                exit_status = 1

    if scenario_plan is not None:
        plan_resp = await call_tool(
            "scenario_plan",
            {
                "scenario_path": scenario_plan,
                **(
                    {"input_overrides": input_overrides}
                    if input_overrides is not None
                    else {}
                ),
            },
        )
        plan_text = _tool_text_response(plan_resp)
        plan = json.loads(plan_text)
        summary_fields = required_plan_fields or PLAN_REQUIRED_FIELDS
        plan_summary = _scenario_plan_probe_summary(plan, summary_fields)
        print("\n=== scenario_plan smoke ===")
        print(json.dumps(plan_summary, indent=2, ensure_ascii=False))
        if not check_plan_expectations(
            label="scenario_plan",
            plan_payload=plan,
            plan_summary=plan_summary,
        ):
            exit_status = 1
        if scenario_validate_dry_run:
            dry_run_resp = await call_tool(
                "scenario_validate",
                {
                    "scenario_path": scenario_plan,
                    "dry_run": True,
                    **(
                        {"input_overrides": input_overrides}
                        if input_overrides is not None
                        else {}
                    ),
                },
            )
            dry_run_text = _tool_text_response(dry_run_resp)
            dry_run_payload = json.loads(dry_run_text)
            dry_run_summary = _scenario_plan_probe_summary(
                dry_run_payload,
                summary_fields,
            )
            print("\n=== scenario_validate dry-run smoke ===")
            print(json.dumps(dry_run_summary, indent=2, ensure_ascii=False))
            dry_run_mismatches = _scenario_validate_dry_run_mismatches(
                dry_run_payload
            )
            if dry_run_mismatches:
                print("scenario_validate dry-run expectation mismatch:")
                for mismatch in dry_run_mismatches:
                    print(f"  - {mismatch}")
                exit_status = 1
            if not check_plan_expectations(
                label="scenario_validate dry-run",
                plan_payload=dry_run_payload,
                plan_summary=dry_run_summary,
            ):
                exit_status = 1
        if scenario_validate_live:
            if exit_status != 0:
                print("\nskipping live scenario_validate because preflight failed")
            else:
                clear_logs_payload = _tool_json_response(
                    await call_tool("extension_clear_logs")
                )
                print("\n=== extension_clear_logs ===")
                print(json.dumps(
                    _module_result_probe_summary(clear_logs_payload),
                    indent=2,
                    ensure_ascii=False,
                ))
                if _module_result_failed(clear_logs_payload):
                    exit_status = 1
                live_report_payload = _tool_json_response(
                    await call_tool(
                        "scenario_validate",
                        {
                            "scenario_path": scenario_plan,
                            "report_format": "json",
                            "redact_local_paths": True,
                            **(
                                {"input_overrides": input_overrides}
                                if input_overrides is not None
                                else {}
                            ),
                        },
                    )
                )
                live_summary = _scenario_live_report_summary(live_report_payload)
                print("\n=== scenario_validate live summary ===")
                print(json.dumps(live_summary, indent=2, ensure_ascii=False))
                if live_report_payload.get("status") != expect_live_status:
                    print(
                        "scenario_validate live status expected "
                        f"{expect_live_status!r}, got "
                        f"{live_report_payload.get('status')!r}"
                    )
                    exit_status = 1
                evidence_mismatches = _live_evidence_kind_mismatches(
                    live_summary,
                    expected_live_evidence_kinds,
                )
                if evidence_mismatches:
                    print("scenario_validate live evidence expectation mismatch:")
                    for mismatch in evidence_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
                evidence_field_mismatches = _live_evidence_field_mismatches(
                    live_summary,
                    expected_live_evidence_fields,
                )
                if evidence_field_mismatches:
                    print(
                        "scenario_validate live evidence field expectation "
                        "mismatch:"
                    )
                    for mismatch in evidence_field_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
                evidence_field_minimum_mismatches = (
                    _live_evidence_field_minimum_mismatches(
                        live_summary,
                        expected_live_evidence_field_minimums,
                    )
                )
                if evidence_field_minimum_mismatches:
                    print(
                        "scenario_validate live evidence field minimum "
                        "expectation mismatch:"
                    )
                    for mismatch in evidence_field_minimum_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
                cleanup_mismatches = _live_cleanup_failure_mismatches(
                    live_summary,
                    expect_live_cleanup_failures,
                )
                if cleanup_mismatches:
                    print("scenario_validate live cleanup expectation mismatch:")
                    for mismatch in cleanup_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
                failure_step_mismatches = _live_failure_step_error_mismatches(
                    live_summary,
                    expected_live_failure_step_errors,
                )
                if failure_step_mismatches:
                    print("scenario_validate live failure-step expectation mismatch:")
                    for mismatch in failure_step_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
                diagnostic_mismatches = _live_diagnostic_next_action_mismatches(
                    live_summary,
                    expect_live_diagnostic_next_actions_min,
                )
                if diagnostic_mismatches:
                    print("scenario_validate live diagnostic expectation mismatch:")
                    for mismatch in diagnostic_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
                diagnostic_field_mismatches = _live_diagnostic_field_mismatches(
                    live_summary,
                    expected_live_diagnostic_fields,
                )
                if diagnostic_field_mismatches:
                    print(
                        "scenario_validate live diagnostic field expectation "
                        "mismatch:"
                    )
                    for mismatch in diagnostic_field_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
                markdown_report = _tool_text_response(
                    await call_tool(
                        "scenario_last_report",
                        {
                            "report_format": "markdown",
                            "redact_local_paths": True,
                        },
                    )
                )
                print("\n=== scenario_last_report markdown redacted ===")
                print(markdown_report)
                log_payload = _tool_json_response(
                    await call_tool(
                        "extension_capture_logs",
                        {
                            "level": "WARN",
                            "stop_after_capture": True,
                        },
                    )
                )
                log_summary = _module_result_probe_summary(log_payload)
                print("\n=== extension_capture_logs WARN+ ===")
                print(json.dumps(log_summary, indent=2, ensure_ascii=False))
                if _module_result_failed(log_payload):
                    exit_status = 1
                log_close_mismatches = _log_capture_close_mismatches(log_summary)
                if log_close_mismatches:
                    print("extension_capture_logs close expectation mismatch:")
                    for mismatch in log_close_mismatches:
                        print(f"  - {mismatch}")
                    exit_status = 1
    elif (
        required_live_validation_tools
        or expected_preflight_runtime_checks
        or expected_retry_key_args
        or expected_automatic_cleanup_timeouts
        or expect_scratch_stage_required is not None
        or expect_log_capture_recommended is not None
    ):
        print("scenario plan expectations require --scenario-plan")
        exit_status = 2

    proc.stdin.close()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    snapshot = {
        "tool_count": len(tool_names),
        "tools": tool_names,
        "resource_count": len(res_uris),
        "resources": res_uris,
    }
    snap_path = REPO_ROOT / "tmp_mcp_surface.json"
    snap_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"\nsnapshot: {snap_path.relative_to(REPO_ROOT).as_posix()}")
    return exit_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace",
        type=Path,
        help=(
            "Workspace instance folder containing .mcp.json, "
            "e.g. workspaces/isaac/instance-1."
        ),
    )
    parser.add_argument(
        "--runtime-info",
        action="store_true",
        help="Call mcp_runtime_info and print a compact profile/freshness summary.",
    )
    parser.add_argument(
        "--expect-tool-profile",
        help="Require mcp_runtime_info.tool_profile to match this value.",
    )
    parser.add_argument(
        "--expect-app-profile",
        help="Require mcp_runtime_info.app_profile to match this value.",
    )
    parser.add_argument(
        "--expect-tool-count",
        type=int,
        help="Require mcp_runtime_info.tool_count to match this value.",
    )
    parser.add_argument(
        "--require-runtime-fresh",
        action="store_true",
        help=(
            "Fail when mcp_runtime_info reports source_newer_than_import or "
            "restart_required_for_latest_mcp_code."
        ),
    )
    parser.add_argument(
        "--require-robot-probe-error-contract",
        action="store_true",
        help=(
            "Fail unless mcp_runtime_info exposes the robot_probe_arm_profile "
            "unknown-profile typed error data path and fallback tool order."
        ),
    )
    parser.add_argument(
        "--live-preflight",
        action="store_true",
        help=(
            "Workspace-only non-stage preflight: call kit_app_start, "
            "simulation_get_status, extension_clear_logs, and "
            "extension_capture_logs(level=WARN, stop_after_capture=true)."
        ),
    )
    parser.add_argument(
        "--scenario-plan",
        help="Call scenario_plan for this scenario path after tools/resources smoke.",
    )
    parser.add_argument(
        "--scenario-validate-dry-run",
        action="store_true",
        help=(
            "After --scenario-plan, also call scenario_validate with dry_run=true "
            "and apply the same plan-shape expectations without mutating a stage."
        ),
    )
    parser.add_argument(
        "--scenario-validate-live",
        action="store_true",
        help=(
            "Mutating smoke: require a workspace entry, call kit_app_start, "
            "simulation_get_status, extension_clear_logs, "
            "scenario_validate(report_format=json, redact_local_paths=true), "
            "scenario_last_report(report_format=markdown, redact_local_paths=true), and "
            "extension_capture_logs(stop_after_capture=true). "
            "Requires --scenario-plan and --scenario-validate-dry-run."
        ),
    )
    parser.add_argument(
        "--expect-live-status",
        default="passed",
        choices=("passed", "failed", "timeout", "error", "canceled"),
        help=(
            "Expected status for --scenario-validate-live; use 'failed' for "
            "controlled-failure diagnostics."
        ),
    )
    parser.add_argument(
        "--expect-live-evidence-kind",
        action="append",
        default=[],
        help=(
            "Require scenario_validate live evidence_summary to include this "
            "evidence_kind; repeat for multiple kinds."
        ),
    )
    parser.add_argument(
        "--expect-live-evidence-field",
        action="append",
        default=[],
        help=(
            "Require a scenario_validate live evidence_summary field, formatted "
            "as selector:key=value where selector matches evidence_kind or "
            "step_id and key may be dotted, for example diagnostics.error_type. "
            "Value is JSON-decoded when possible; repeat for multiple "
            "expectations. Use step_id for row-specific failure fields such as "
            "error_code or diagnostics.error_type when multiple rows share an "
            "evidence_kind."
        ),
    )
    parser.add_argument(
        "--expect-live-evidence-field-min",
        action="append",
        default=[],
        help=(
            "Require a numeric scenario_validate live evidence_summary field "
            "to be at least a value, formatted as selector:key=minimum where "
            "selector matches evidence_kind or step_id; repeat for multiple "
            "expectations."
        ),
    )
    parser.add_argument(
        "--expect-live-cleanup-failures",
        type=int,
        help="Require scenario_validate live cleanup_failed_steps to match.",
    )
    parser.add_argument(
        "--expect-live-failure-step-error",
        action="append",
        default=[],
        help=(
            "Require a scenario_validate live failure_summary step error, "
            "formatted as step_id=ERROR_CODE; repeat for multiple steps."
        ),
    )
    parser.add_argument(
        "--expect-live-diagnostic-next-actions-min",
        type=int,
        help=(
            "Require scenario_validate live diagnostic_next_actions to contain "
            "at least this many entries."
        ),
    )
    parser.add_argument(
        "--expect-live-diagnostic-field",
        action="append",
        default=[],
        help=(
            "Require a scenario_validate live diagnostic_next_actions field, "
            "formatted as step_id:key=value. Value is JSON-decoded when "
            "possible; repeat for multiple expectations."
        ),
    )
    parser.add_argument(
        "--input-overrides-json",
        help="JSON object passed as scenario_plan input_overrides.",
    )
    parser.add_argument(
        "--mcp-response-timeout-s",
        type=float,
        default=30.0,
        help="Seconds to wait for MCP initialize/list/resource responses.",
    )
    parser.add_argument(
        "--mcp-tool-call-timeout-s",
        type=float,
        default=900.0,
        help="Seconds to wait for each MCP tools/call response.",
    )
    parser.add_argument(
        "--require-plan-fields",
        action="store_true",
        help="Exit non-zero if scenario_plan is missing simulation-state plan fields.",
    )
    parser.add_argument(
        "--require-plan-field",
        action="append",
        default=[],
        help=(
            "Additional top-level scenario_plan field required for success; "
            "can be repeated."
        ),
    )
    parser.add_argument(
        "--require-live-validation-tools",
        help=(
            "Comma-separated exact live_validation_checklist tool order required "
            "for success, e.g. 'mcp_runtime_info,kit_app_start,...'."
        ),
    )
    parser.add_argument(
        "--expect-scratch-stage-required",
        choices=("true", "false"),
        help="Require scenario_plan.live_validation_checklist.scratch_stage_required.",
    )
    parser.add_argument(
        "--expect-log-capture-recommended",
        choices=("true", "false"),
        help="Require scenario_plan.live_validation_checklist.log_capture_recommended.",
    )
    parser.add_argument(
        "--expect-preflight-runtime-check",
        action="append",
        default=[],
        help=(
            "Require a scenario_plan preflight_requirements.runtime_info.checks "
            "entry; repeat for multiple checks."
        ),
    )
    parser.add_argument(
        "--expect-retry-key-arg",
        action="append",
        default=[],
        help=(
            "Require a scenario_plan retry_steps entry key arg, formatted "
            "as step_id:key=value. Value is JSON-decoded when possible; "
            "repeat for multiple expectations."
        ),
    )
    parser.add_argument(
        "--expect-automatic-cleanup-timeout",
        action="append",
        default=[],
        help=(
            "Require a runner-added automatic cleanup timeout, formatted as "
            "step_id=seconds; repeat for multiple expectations."
        ),
    )
    args = parser.parse_args(argv)
    try:
        input_overrides = _parse_json_object(
            args.input_overrides_json,
            label="--input-overrides-json",
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    required_plan_fields = _merge_required_plan_fields(
        args.require_plan_fields,
        args.require_plan_field,
    )
    required_live_validation_tools = _parse_required_tool_sequence(
        args.require_live_validation_tools,
    )
    try:
        expected_retry_key_args = _parse_expected_retry_key_args(
            args.expect_retry_key_arg,
        )
    except ValueError as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    try:
        expected_automatic_cleanup_timeouts = (
            _parse_expected_automatic_cleanup_timeouts(
                args.expect_automatic_cleanup_timeout,
            )
        )
    except ValueError as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    try:
        expected_live_evidence_fields = _parse_expected_live_evidence_fields(
            args.expect_live_evidence_field,
        )
    except ValueError as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    try:
        expected_live_evidence_field_minimums = (
            _parse_expected_live_evidence_field_minimums(
                args.expect_live_evidence_field_min,
            )
        )
    except ValueError as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    try:
        expected_live_diagnostic_fields = _parse_expected_live_diagnostic_fields(
            args.expect_live_diagnostic_field,
        )
    except ValueError as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    try:
        expected_live_failure_step_errors = (
            _parse_expected_live_failure_step_errors(
                args.expect_live_failure_step_error,
            )
        )
    except ValueError as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    expect_scratch_stage_required = _parse_expected_bool(
        args.expect_scratch_stage_required,
    )
    expect_log_capture_recommended = _parse_expected_bool(
        args.expect_log_capture_recommended,
    )
    has_plan_expectations = (
        bool(required_live_validation_tools)
        or bool(args.expect_preflight_runtime_check)
        or bool(expected_retry_key_args)
        or bool(expected_automatic_cleanup_timeouts)
        or expect_scratch_stage_required is not None
        or expect_log_capture_recommended is not None
    )
    if has_plan_expectations and args.scenario_plan is None:
        print("scenario plan expectations require --scenario-plan")
        return 2
    if args.scenario_validate_dry_run and args.scenario_plan is None:
        print("--scenario-validate-dry-run requires --scenario-plan")
        return 2
    if args.live_preflight and args.workspace is None:
        print("--live-preflight requires --workspace")
        return 2
    if args.scenario_validate_live:
        if args.workspace is None:
            print("--scenario-validate-live requires --workspace")
            return 2
        if args.scenario_plan is None:
            print("--scenario-validate-live requires --scenario-plan")
            return 2
        if not args.scenario_validate_dry_run:
            print("--scenario-validate-live requires --scenario-validate-dry-run")
            return 2
    elif args.expect_live_status != "passed":
        print("--expect-live-status requires --scenario-validate-live")
        return 2
    elif args.expect_live_evidence_kind:
        print("--expect-live-evidence-kind requires --scenario-validate-live")
        return 2
    elif expected_live_evidence_fields:
        print("--expect-live-evidence-field requires --scenario-validate-live")
        return 2
    elif expected_live_evidence_field_minimums:
        print("--expect-live-evidence-field-min requires --scenario-validate-live")
        return 2
    elif args.expect_live_cleanup_failures is not None:
        print("--expect-live-cleanup-failures requires --scenario-validate-live")
        return 2
    elif expected_live_failure_step_errors:
        print("--expect-live-failure-step-error requires --scenario-validate-live")
        return 2
    elif args.expect_live_diagnostic_next_actions_min is not None:
        print(
            "--expect-live-diagnostic-next-actions-min requires "
            "--scenario-validate-live"
        )
        return 2
    elif expected_live_diagnostic_fields:
        print("--expect-live-diagnostic-field requires --scenario-validate-live")
        return 2
    if (
        args.expect_live_cleanup_failures is not None
        and args.expect_live_cleanup_failures < 0
    ):
        print("--expect-live-cleanup-failures must be >= 0")
        return 2
    if (
        args.expect_live_diagnostic_next_actions_min is not None
        and args.expect_live_diagnostic_next_actions_min < 0
    ):
        print("--expect-live-diagnostic-next-actions-min must be >= 0")
        return 2
    runtime_info = (
        args.runtime_info
        or args.expect_tool_profile is not None
        or args.expect_app_profile is not None
        or args.expect_tool_count is not None
        or args.require_runtime_fresh
        or args.require_robot_probe_error_contract
        or args.live_preflight
        or args.scenario_validate_live
    )
    return asyncio.run(
        probe(
            workspace=args.workspace,
            runtime_info=runtime_info,
            expect_tool_profile=args.expect_tool_profile,
            expect_app_profile=args.expect_app_profile,
            expect_tool_count=args.expect_tool_count,
            require_runtime_fresh=args.require_runtime_fresh,
            require_robot_probe_error_contract=(
                args.require_robot_probe_error_contract
            ),
            live_preflight=args.live_preflight,
            scenario_plan=args.scenario_plan,
            scenario_validate_dry_run=args.scenario_validate_dry_run,
            scenario_validate_live=args.scenario_validate_live,
            input_overrides=input_overrides,
            required_plan_fields=required_plan_fields,
            required_live_validation_tools=required_live_validation_tools,
            expected_preflight_runtime_checks=tuple(
                args.expect_preflight_runtime_check
            ),
            expected_retry_key_args=expected_retry_key_args,
            expected_automatic_cleanup_timeouts=(
                expected_automatic_cleanup_timeouts
            ),
            expected_live_evidence_kinds=tuple(args.expect_live_evidence_kind),
            expected_live_evidence_fields=expected_live_evidence_fields,
            expected_live_evidence_field_minimums=(
                expected_live_evidence_field_minimums
            ),
            expect_live_cleanup_failures=args.expect_live_cleanup_failures,
            expected_live_failure_step_errors=(
                expected_live_failure_step_errors
            ),
            expect_live_diagnostic_next_actions_min=(
                args.expect_live_diagnostic_next_actions_min
            ),
            expected_live_diagnostic_fields=expected_live_diagnostic_fields,
            expect_live_status=args.expect_live_status,
            expect_scratch_stage_required=expect_scratch_stage_required,
            expect_log_capture_recommended=expect_log_capture_recommended,
            mcp_response_timeout_s=args.mcp_response_timeout_s,
            mcp_tool_call_timeout_s=args.mcp_tool_call_timeout_s,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
