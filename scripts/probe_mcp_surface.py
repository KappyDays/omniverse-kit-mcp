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
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")
PLAN_REQUIRED_FIELDS = (
    "simulation_state_summary",
    "simulation_state_steps",
    "timeline_control_steps",
    "live_validation_checklist",
)


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
    }


def _runtime_info_mismatches(
    summary: dict[str, Any],
    *,
    expect_tool_profile: str | None = None,
    expect_app_profile: str | None = None,
    expect_tool_count: int | None = None,
    require_runtime_fresh: bool = False,
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
    return {
        "scenario_id": plan.get("scenario_id"),
        "total_steps": plan.get("total_steps"),
        "required_fields_present": {
            field: field in plan for field in field_names
        },
        "play_state_missing_count": simulation_state_summary.get(
            "play_state_missing_count"
        ),
        "requires_play_count": simulation_state_summary.get("requires_play_count"),
        "simulation_state_step_count": len(simulation_state_steps),
        "timeline_control_step_count": len(timeline_control_steps),
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


async def probe(
    *,
    workspace: Path | None = None,
    runtime_info: bool = False,
    expect_tool_profile: str | None = None,
    expect_app_profile: str | None = None,
    expect_tool_count: int | None = None,
    require_runtime_fresh: bool = False,
    scenario_plan: str | None = None,
    scenario_validate_dry_run: bool = False,
    input_overrides: dict[str, Any] | None = None,
    required_plan_fields: tuple[str, ...] = (),
    required_live_validation_tools: tuple[str, ...] = (),
    expected_retry_key_args: tuple[tuple[str, str, Any], ...] = (),
    expect_scratch_stage_required: bool | None = None,
    expect_log_capture_recommended: bool | None = None,
) -> int:
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

    async def recv() -> dict[str, Any]:
        line = await proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed stdout early")
        return json.loads(line.decode("utf-8"))

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
    init_resp = await recv()
    server_info = init_resp.get("result", {}).get("serverInfo", {})
    caps = init_resp.get("result", {}).get("capabilities", {})
    print(f"server: {server_info.get('name')} v{server_info.get('version')}")
    print(f"capabilities: {list(caps.keys())}")

    await send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools_resp = await recv()
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
    res_resp = await recv()
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
        retry_mismatches = _retry_key_arg_mismatches(
            plan_summary,
            expected_retry_key_args,
        )
        if retry_mismatches:
            print(f"{label} retry key-arg expectation mismatch:")
            for mismatch in retry_mismatches:
                print(f"  - {mismatch}")
            passed = False
        return passed

    if runtime_info:
        await send({
            "jsonrpc": "2.0",
            "id": next_id,
            "method": "tools/call",
            "params": {
                "name": "mcp_runtime_info",
                "arguments": {},
            },
        })
        next_id += 1
        runtime_resp = await recv()
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
        )
        if runtime_mismatches:
            print("runtime expectation mismatch:")
            for mismatch in runtime_mismatches:
                print(f"  - {mismatch}")
            exit_status = 1

    if scenario_plan is not None:
        await send({
            "jsonrpc": "2.0",
            "id": next_id,
            "method": "tools/call",
            "params": {
                "name": "scenario_plan",
                "arguments": {
                    "scenario_path": scenario_plan,
                    **(
                        {"input_overrides": input_overrides}
                        if input_overrides is not None
                        else {}
                    ),
                },
            },
        })
        next_id += 1
        plan_resp = await recv()
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
            await send({
                "jsonrpc": "2.0",
                "id": next_id,
                "method": "tools/call",
                "params": {
                    "name": "scenario_validate",
                    "arguments": {
                        "scenario_path": scenario_plan,
                        "dry_run": True,
                        **(
                            {"input_overrides": input_overrides}
                            if input_overrides is not None
                            else {}
                        ),
                    },
                },
            })
            next_id += 1
            dry_run_resp = await recv()
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
    elif (
        required_live_validation_tools
        or expected_retry_key_args
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
        "--input-overrides-json",
        help="JSON object passed as scenario_plan input_overrides.",
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
        "--expect-retry-key-arg",
        action="append",
        default=[],
        help=(
            "Require a scenario_plan retry_steps entry key arg, formatted "
            "as step_id:key=value. Value is JSON-decoded when possible; "
            "repeat for multiple expectations."
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
    expect_scratch_stage_required = _parse_expected_bool(
        args.expect_scratch_stage_required,
    )
    expect_log_capture_recommended = _parse_expected_bool(
        args.expect_log_capture_recommended,
    )
    has_plan_expectations = (
        bool(required_live_validation_tools)
        or bool(expected_retry_key_args)
        or expect_scratch_stage_required is not None
        or expect_log_capture_recommended is not None
    )
    if has_plan_expectations and args.scenario_plan is None:
        print("scenario plan expectations require --scenario-plan")
        return 2
    if args.scenario_validate_dry_run and args.scenario_plan is None:
        print("--scenario-validate-dry-run requires --scenario-plan")
        return 2
    runtime_info = (
        args.runtime_info
        or args.expect_tool_profile is not None
        or args.expect_app_profile is not None
        or args.expect_tool_count is not None
        or args.require_runtime_fresh
    )
    return asyncio.run(
        probe(
            workspace=args.workspace,
            runtime_info=runtime_info,
            expect_tool_profile=args.expect_tool_profile,
            expect_app_profile=args.expect_app_profile,
            expect_tool_count=args.expect_tool_count,
            require_runtime_fresh=args.require_runtime_fresh,
            scenario_plan=args.scenario_plan,
            scenario_validate_dry_run=args.scenario_validate_dry_run,
            input_overrides=input_overrides,
            required_plan_fields=required_plan_fields,
            required_live_validation_tools=required_live_validation_tools,
            expected_retry_key_args=expected_retry_key_args,
            expect_scratch_stage_required=expect_scratch_stage_required,
            expect_log_capture_recommended=expect_log_capture_recommended,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
