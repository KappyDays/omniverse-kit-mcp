"""Probe the MCP server via stdio JSON-RPC.

By default this lists tools/resources from a fresh local server. Pass
``--workspace workspaces/isaac/instance-1`` to spawn the same workspace-local
stdio entry used by Codex/Claude Code, and ``--scenario-plan`` to verify that a
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


def _scenario_plan_probe_summary(plan: dict[str, Any]) -> dict[str, Any]:
    simulation_state_summary = plan.get("simulation_state_summary")
    if not isinstance(simulation_state_summary, dict):
        simulation_state_summary = {}
    simulation_state_steps = plan.get("simulation_state_steps")
    if not isinstance(simulation_state_steps, list):
        simulation_state_steps = []
    timeline_control_steps = plan.get("timeline_control_steps")
    if not isinstance(timeline_control_steps, list):
        timeline_control_steps = []
    return {
        "scenario_id": plan.get("scenario_id"),
        "total_steps": plan.get("total_steps"),
        "required_fields_present": {
            field: field in plan for field in PLAN_REQUIRED_FIELDS
        },
        "play_state_missing_count": simulation_state_summary.get(
            "play_state_missing_count"
        ),
        "requires_play_count": simulation_state_summary.get("requires_play_count"),
        "simulation_state_step_count": len(simulation_state_steps),
        "timeline_control_step_count": len(timeline_control_steps),
    }


async def probe(
    *,
    workspace: Path | None = None,
    scenario_plan: str | None = None,
    input_overrides: dict[str, Any] | None = None,
    require_plan_fields: bool = False,
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
    if scenario_plan is not None:
        await send({
            "jsonrpc": "2.0",
            "id": 4,
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
        plan_resp = await recv()
        plan_text = _tool_text_response(plan_resp)
        plan = json.loads(plan_text)
        plan_summary = _scenario_plan_probe_summary(plan)
        print("\n=== scenario_plan smoke ===")
        print(json.dumps(plan_summary, indent=2, ensure_ascii=False))
        missing_fields = [
            field
            for field, present in plan_summary["required_fields_present"].items()
            if not present
        ]
        if missing_fields:
            print("missing required plan fields: " + ", ".join(missing_fields))
            if require_plan_fields:
                exit_status = 1

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
    print(f"\nsnapshot: {snap_path}")
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
        "--scenario-plan",
        help="Call scenario_plan for this scenario path after tools/resources smoke.",
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
    args = parser.parse_args(argv)
    try:
        input_overrides = _parse_json_object(
            args.input_overrides_json,
            label="--input-overrides-json",
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid probe option: {exc}")
        return 2
    return asyncio.run(
        probe(
            workspace=args.workspace,
            scenario_plan=args.scenario_plan,
            input_overrides=input_overrides,
            require_plan_fields=args.require_plan_fields,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
