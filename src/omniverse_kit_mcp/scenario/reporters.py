"""Scenario result reporters (JSON / Markdown)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any

from omniverse_kit_mcp.types.scenario import ScenarioRunSummary, StepResult

_MAX_HIGHLIGHT_PARTS = 16
_FAILED_STATUS_VALUES = {"failed", "error", "timeout"}
_DIAGNOSTIC_SUMMARY_PATHS = (
    ("num_points", (("num_points",),)),
    ("backend", (("backend",),)),
    ("frames_waited", (("frames_waited",),)),
    ("empty_reason", (("empty_reason",), ("diagnostics", "empty_reason"))),
    ("diagnostics.reason", (("diagnostics", "reason"),)),
    ("diagnostics.requested_app_profile", (("diagnostics", "requested_app_profile"),)),
    ("diagnostics.available_profiles", (("diagnostics", "available_profiles"),)),
    ("diagnostics.available_providers", (("diagnostics", "available_providers"),)),
    ("diagnostics.matching_item_count", (("diagnostics", "matching_item_count"),)),
    (
        "diagnostics.candidate_counts.total_entries",
        (("diagnostics", "candidate_counts", "total_entries"),),
    ),
    (
        "diagnostics.candidate_counts.after_app_profile",
        (("diagnostics", "candidate_counts", "after_app_profile"),),
    ),
    (
        "diagnostics.candidate_counts.query_matches",
        (("diagnostics", "candidate_counts", "query_matches"),),
    ),
    ("suggested_next", (("diagnostics", "suggested_next"),)),
    ("diagnostics.fallback_tool_order", (("diagnostics", "fallback_tool_order"),)),
    ("diagnostics.cached_lidar_instance", (("diagnostics", "cached_lidar_instance"),)),
    ("diagnostics.readback_paths_attempted", (("diagnostics", "readback_paths_attempted"),)),
    ("raw_keys", (("raw_keys",),)),
    ("warning", (("warning",),)),
    ("truncated", (("truncated",),)),
    ("timeline_settled", (("timeline_settled",), ("status", "timeline_settled"))),
    (
        "timeline_settle_updates",
        (("timeline_settle_updates",), ("status", "timeline_settle_updates")),
    ),
    ("is_playing", (("is_playing",), ("status", "is_playing"))),
    ("is_stopped", (("is_stopped",), ("status", "is_stopped"))),
    ("capture_path", (("capture_path",), ("artifact", "path"), ("path",))),
    ("sha256", (("sha256",), ("artifact", "sha256"))),
    ("non_empty", (("non_empty",),)),
    ("passed", (("passed",),)),
)
_VALIDATION_CAPTURE_RE = re.compile(
    r"\b[A-Za-z]:[\\/]+Users[\\/]+[^\\/]+[\\/]+AppData[\\/]+Local[\\/]+"
    r"Temp[\\/]+validation_api_captures[\\/]+([^\\/`\"'\s]+)",
    re.IGNORECASE,
)
_KIT_TEMP_LOG_RE = re.compile(
    r"\b[A-Za-z]:[\\/]+Users[\\/]+[^\\/]+[\\/]+AppData[\\/]+Local[\\/]+"
    r"Temp[\\/]+omniverse_kit_mcp[\\/]+(kit_[^\\/`\"'\s]+\.log)",
    re.IGNORECASE,
)
_WINDOWS_USER_PATH_RE = re.compile(
    r"\b[A-Za-z]:[\\/]+Users[\\/]+[^\\/`\"'\s]+(?:[\\/][^`\"'\s]*)?",
    re.IGNORECASE,
)
_MSYS_USER_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])/[A-Za-z]/Users/[^/`\"'\s]+(?:/[^`\"'\s]*)?",
    re.IGNORECASE,
)
_SANITIZED_WINDOWS_USER_PATH_RE = re.compile(
    r"\b[A-Za-z]--Users-[A-Za-z0-9._-]+(?:-[A-Za-z0-9._-]+)*\b"
)
_PY_OBJECT_REPR_RE = re.compile(r"<([^<>]*\bobject) at 0x[0-9A-Fa-f]+>")


def to_json(
    summary: ScenarioRunSummary, *, redact_local_paths: bool = False
) -> str:
    """Serialize summary to JSON string."""
    data = _to_dict(summary)
    if redact_local_paths:
        data = _redact_local_paths(data)
    return json.dumps(data, indent=2, ensure_ascii=False)


def to_markdown(
    summary: ScenarioRunSummary, *, redact_local_paths: bool = False
) -> str:
    """Render summary as Markdown report."""
    cleanup_failures = _summary_cleanup_failed_steps(summary)
    continued_failures = _summary_continued_steps(summary)
    fatal_main_failures = _summary_fatal_failed_steps(
        summary,
        cleanup_failures=cleanup_failures,
        continued_failures=continued_failures,
    )
    if continued_failures:
        steps_text = (
            f"**Steps**: {summary.passed_steps} passed, "
            f"{fatal_main_failures} failed, {continued_failures} continued, "
            f"{summary.skipped_steps} skipped"
        )
    else:
        steps_text = (
            f"**Steps**: {summary.passed_steps} passed, {fatal_main_failures} failed, "
            f"{summary.skipped_steps} skipped"
        )
    lines = [
        f"# Scenario Report: {summary.scenario_id}",
        "",
        f"**Status**: {summary.status.value.upper()}",
        f"**Duration**: {summary.ended_at_epoch_ms - summary.started_at_epoch_ms}ms",
        steps_text,
    ]
    if cleanup_failures:
        lines.append(f"**Cleanup**: {cleanup_failures} non-fatal failure(s)")
    lines.extend([
        "",
        "## Step Results",
        "",
        "| Step | Phase | Status | Attempts | Duration | Message |",
        "|------|-------|--------|----------|----------|---------|",
    ])
    for sr in summary.step_results:
        dur = f"{sr.duration_ms}ms" if sr.duration_ms is not None else "-"
        attempts = f"{sr.attempts}/{sr.max_attempts}"
        message = sr.message or ""
        if redact_local_paths:
            message = _redact_local_path_string(message)
        lines.append(
            f"| {_markdown_table_cell(sr.step_id)} | "
            f"{_markdown_table_cell(sr.phase)} | "
            f"{_markdown_table_cell(_display_step_status(sr))} | "
            f"{_markdown_table_cell(attempts)} | "
            f"{_markdown_table_cell(dur)} | "
            f"{_markdown_table_cell(message)} |"
        )

    data_rows = [
        (
            sr.step_id,
            _format_data_summary_highlight(
                _redact_local_paths(sr.data_summary)
                if redact_local_paths
                else sr.data_summary
            ),
        )
        for sr in summary.step_results
        if sr.data_summary and _has_diagnostic_summary(sr.data_summary)
    ]
    if data_rows:
        lines.extend(["", "## Data Summary Highlights", ""])
        for step_id, detail in data_rows:
            lines.append(
                f"- {_markdown_code_span(step_id)}: {_markdown_inline(detail)}"
            )

    retry_rows = [
        (sr.step_id, failure)
        for sr in summary.step_results
        for failure in sr.retry_failures
    ]
    if retry_rows:
        lines.extend(["", "## Retry Failures", ""])
        for step_id, failure in retry_rows:
            failure_message = failure.get("message") or ""
            if redact_local_paths:
                failure_message = _redact_local_path_string(str(failure_message))
            failure_detail = ""
            data_summary = failure.get("data_summary")
            if isinstance(data_summary, dict) and _has_diagnostic_summary(data_summary):
                data_summary = (
                    _redact_local_paths(data_summary)
                    if redact_local_paths
                    else data_summary
                )
                failure_detail = (
                    f" [{_format_data_summary_highlight(data_summary)}]"
                )
            lines.append(
                f"- {_markdown_code_span(step_id)} attempt {failure.get('attempt')}: "
                f"{failure.get('status')} {failure.get('error_code')} - "
                f"{_markdown_inline(failure_message)}{_markdown_inline(failure_detail)}"
            )

    action_rows = _diagnostic_next_action_rows(summary, redact_local_paths=redact_local_paths)
    if action_rows:
        lines.extend(["", "## Diagnostic Next Actions", ""])
        for source, detail in action_rows:
            lines.append(
                f"- {_markdown_code_span(source)}: {_markdown_inline(detail)}"
            )

    if summary.artifact_paths:
        lines.extend(["", "## Artifacts", ""])
        for path in summary.artifact_paths:
            if redact_local_paths:
                path = _redact_local_path_string(path)
            lines.append(f"- {_markdown_code_span(path)}")

    return "\n".join(lines)


def _to_dict(summary: ScenarioRunSummary) -> dict[str, Any]:
    d = asdict(summary)  # type: ignore[arg-type]
    # Convert enum values to strings
    d["status"] = summary.status.value
    step_results: list[dict[str, Any]] = []
    diagnostic_next_actions: list[dict[str, Any]] = []
    for sr in summary.step_results:
        step_result = {**asdict(sr), "status": sr.status.value}  # type: ignore[arg-type]
        action = _diagnostic_next_action_payload(sr.data_summary)
        if action:
            step_result["diagnostic_next_actions"] = action
            diagnostic_next_actions.append({
                "step_id": sr.step_id,
                "source": "step",
                **action,
            })

        retry_failures: list[dict[str, Any]] = []
        for failure in sr.retry_failures:
            retry_failure = dict(failure)
            data_summary = retry_failure.get("data_summary")
            if isinstance(data_summary, dict):
                retry_action = _diagnostic_next_action_payload(data_summary)
                if retry_action:
                    retry_failure["diagnostic_next_actions"] = retry_action
                    summary_action = {
                        "step_id": sr.step_id,
                        "source": "retry_failure",
                        **retry_action,
                    }
                    if retry_failure.get("attempt") is not None:
                        summary_action["attempt"] = retry_failure["attempt"]
                    diagnostic_next_actions.append(summary_action)
            retry_failures.append(retry_failure)
        step_result["retry_failures"] = retry_failures
        step_results.append(step_result)
    d["step_results"] = step_results
    d["diagnostic_next_actions"] = diagnostic_next_actions
    return d


def _redact_local_paths(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_local_path_string(value)
    if isinstance(value, list):
        return [_redact_local_paths(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_local_paths(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _redact_local_paths(item)
            for key, item in value.items()
        }
    return value


def _redact_local_path_string(value: str) -> str:
    redacted = _VALIDATION_CAPTURE_RE.sub(
        r"<validation-api-capture>/\1", value
    )
    redacted = _KIT_TEMP_LOG_RE.sub(r"<local-kit-log>/\1", redacted)
    redacted = _WINDOWS_USER_PATH_RE.sub("<local-user-path>", redacted)
    redacted = _MSYS_USER_PATH_RE.sub("<local-user-path>", redacted)
    return _SANITIZED_WINDOWS_USER_PATH_RE.sub(
        "<local-user-path>", redacted
    )


def _summary_cleanup_failed_steps(summary: ScenarioRunSummary) -> int:
    return summary.cleanup_failed_steps or sum(
        1
        for step in summary.step_results
        if step.phase == "cleanup" and step.status.value in _FAILED_STATUS_VALUES
    )


def _summary_continued_steps(summary: ScenarioRunSummary) -> int:
    return summary.continued_steps or sum(
        1
        for step in summary.step_results
        if step.phase != "cleanup"
        and step.continue_on_failure
        and step.status.value in _FAILED_STATUS_VALUES
    )


def _summary_fatal_failed_steps(
    summary: ScenarioRunSummary,
    *,
    cleanup_failures: int,
    continued_failures: int,
) -> int:
    if summary.fatal_failed_steps:
        return summary.fatal_failed_steps
    return max(0, summary.failed_steps - cleanup_failures - continued_failures)


def _display_step_status(step: StepResult) -> str:
    if step.continue_on_failure and step.status.value in _FAILED_STATUS_VALUES:
        return f"{step.status.value} (continued)"
    return step.status.value


def _markdown_table_cell(value: Any) -> str:
    return _markdown_inline(value).replace("|", r"\|")


def _markdown_inline(value: Any) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _markdown_code_span(value: Any) -> str:
    text = _markdown_inline(value)
    longest_run = 0
    current_run = 0
    for char in text:
        if char == "`":
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0
    delimiter = "`" * (longest_run + 1)
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{delimiter}{padding}{text}{padding}{delimiter}"


def _has_diagnostic_summary(data_summary: dict[str, Any]) -> bool:
    return bool(_diagnostic_summary_parts(data_summary))


def _format_data_summary_highlight(data_summary: dict[str, Any]) -> str:
    parts = _diagnostic_summary_parts(data_summary)
    emitted = _emitted_summary_roots(data_summary)
    for key, value in data_summary.items():
        if len(parts) >= _MAX_HIGHLIGHT_PARTS:
            break
        if value is None and key in {"empty_reason"}:
            continue
        if key not in emitted and _is_compact_scalar(value):
            parts.extend(_format_summary_pair(key, value))
    return "; ".join(parts[:_MAX_HIGHLIGHT_PARTS])


def _diagnostic_next_action_rows(
    summary: ScenarioRunSummary,
    *,
    redact_local_paths: bool,
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for step in summary.step_results:
        if step.data_summary:
            data_summary = (
                _redact_local_paths(step.data_summary)
                if redact_local_paths
                else step.data_summary
            )
            detail = _format_diagnostic_next_action(data_summary)
            if detail:
                rows.append((step.step_id, detail))
        for failure in step.retry_failures:
            data_summary = failure.get("data_summary")
            if not isinstance(data_summary, dict):
                continue
            data_summary = (
                _redact_local_paths(data_summary)
                if redact_local_paths
                else data_summary
            )
            detail = _format_diagnostic_next_action(data_summary)
            if not detail:
                continue
            attempt = failure.get("attempt")
            source = f"{step.step_id} attempt {attempt}" if attempt else step.step_id
            rows.append((source, detail))
    return rows


def _format_diagnostic_next_action(data_summary: dict[str, Any]) -> str:
    payload = _diagnostic_next_action_payload(data_summary)
    if not payload:
        return ""
    parts = [
        part
        for key, value in payload.items()
        for part in _format_summary_pair(key, value)
    ]
    return "; ".join(parts[:_MAX_HIGHLIGHT_PARTS])


def _diagnostic_next_action_payload(data_summary: dict[str, Any]) -> dict[str, Any]:
    diagnostics = data_summary.get("diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}

    payload: dict[str, Any] = {}
    for key, value in (
        ("diagnostics.reason", diagnostics.get("reason")),
        (
            "empty_reason",
            data_summary.get("empty_reason", diagnostics.get("empty_reason")),
        ),
        (
            "suggested_next",
            data_summary.get("suggested_next", diagnostics.get("suggested_next")),
        ),
        ("diagnostics.fallback_tool_order", diagnostics.get("fallback_tool_order")),
        (
            "diagnostics.readback_paths_attempted",
            diagnostics.get("readback_paths_attempted"),
        ),
    ):
        if value is None:
            continue
        payload[key] = value

    if not any(
        key in payload
        for key in ("suggested_next", "diagnostics.fallback_tool_order")
    ):
        return {}
    return payload


def _emitted_summary_roots(data_summary: dict[str, Any]) -> set[str]:
    emitted: set[str] = set()
    for key, paths in _DIAGNOSTIC_SUMMARY_PATHS:
        for path in paths:
            found, _value = _lookup_diagnostic_summary_path(data_summary, key, path)
            if found:
                emitted.add(path[0])
                break
    return emitted


def _diagnostic_summary_parts(data_summary: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for key, paths in _DIAGNOSTIC_SUMMARY_PATHS:
        for path in paths:
            found, value = _lookup_diagnostic_summary_path(data_summary, key, path)
            if found:
                if value is None and key in {
                    "empty_reason",
                    "suggested_next",
                    "timeline_settled",
                    "timeline_settle_updates",
                }:
                    continue
                parts.extend(_format_summary_pair(key, value))
                break
    return parts


def _lookup_diagnostic_summary_path(
    data_summary: dict[str, Any],
    key: str,
    path: tuple[str, ...],
) -> tuple[bool, Any]:
    found, value = _lookup_summary_path(data_summary, path)
    if not found:
        return False, None
    if (
        key == "capture_path"
        and path == ("path",)
        and not _is_top_level_image_artifact(data_summary)
    ):
        return False, None
    return True, value


def _is_top_level_image_artifact(data_summary: dict[str, Any]) -> bool:
    return (
        isinstance(data_summary.get("path"), str)
        and isinstance(data_summary.get("sha256"), str)
        and isinstance(data_summary.get("artifact_id"), str)
        and isinstance(data_summary.get("width"), int)
        and isinstance(data_summary.get("height"), int)
    )


def _lookup_summary_path(
    data_summary: dict[str, Any], path: tuple[str, ...],
) -> tuple[bool, Any]:
    current: Any = data_summary
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def _format_summary_pair(key: str, value: Any) -> list[str]:
    if isinstance(value, dict) and "count" in value:
        parts = [f"{key}.count={_format_summary_value(value['count'])}"]
        if "sample" in value:
            parts.append(f"{key}.sample={_format_summary_value(value['sample'])}")
        return parts
    return [f"{key}={_format_summary_value(value)}"]


def _format_summary_value(value: Any) -> str:
    if isinstance(value, list):
        formatted = ", ".join(_format_summary_value(v) for v in value[:6])
        if len(value) > 6:
            formatted += ", ..."
        return f"[{formatted}]"
    if isinstance(value, tuple):
        return _format_summary_value(list(value))
    if isinstance(value, dict):
        compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        stable = _stable_summary_text(compact)
        return stable[:117] + "..." if len(stable) > 120 else stable
    if value is None:
        return "null"
    return _stable_summary_text(value)


def _stable_summary_text(value: Any) -> str:
    return _PY_OBJECT_REPR_RE.sub(r"<\1>", _markdown_inline(value))


def _is_compact_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None
