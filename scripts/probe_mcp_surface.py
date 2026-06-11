"""Probe the MCP server via stdio JSON-RPC - list tools and resources."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")


async def probe() -> None:
    proc = await asyncio.create_subprocess_exec(
        PY,
        "-m",
        "omniverse_kit_mcp.main",
        cwd=str(REPO_ROOT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None

    async def send(payload: dict) -> None:
        proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        await proc.stdin.drain()

    async def recv() -> dict:
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
    for target in ("scenario_validate", "scenario_plan", "scenario_last_report",
                   "asset_list", "content_browse", "extension_list_all"):
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


if __name__ == "__main__":
    asyncio.run(probe())
