"""Live smoke for kit_command_execute across profiles.

Hard check: the /commands/execute route exists (non-404) on both profiles.
Soft check: invoking a Kit command may stall the Kit main thread depending
on command type (CreatePrim triggers USD notices that can deadlock when
called from a FastAPI threadpool). This script intentionally uses a
nonexistent command name to exercise the dispatch path without waiting
for a real USD operation to complete.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from omniverse_kit_mcp.config import AppConfig  # noqa: E402
from omniverse_kit_mcp.modules.process_module import ProcessModule  # noqa: E402


def _module_for(profile: str, instance: int) -> ProcessModule:
    os.environ["ISAAC_MCP_APP_PROFILE"] = profile
    os.environ["ISAAC_MCP_INSTANCE_ID"] = str(instance)
    return ProcessModule(AppConfig().isaac_sim_process)


async def _call(port: int, name: str, payload: dict | None = None) -> tuple[int, dict | str]:
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(
            f"http://localhost:{port}/validation/v1/commands/execute",
            json={"name": name, "payload": payload or {}, "expect_undo": False},
        )
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text


async def main() -> int:
    print("=== kit_command_execute live smoke ===\n")

    pm_isaac = _module_for("isaac-sim", 1)
    pm_composer = _module_for("usd-composer", 1)

    print("[1] Start Isaac + USD Composer")
    r1 = await pm_isaac.start()
    r2 = await pm_composer.start()
    assert r1.get("ok") and r2.get("ok"), (
        f"start failed: isaac={r1}, composer={r2}"
    )

    # Use a nonexistent command — omni.kit.commands.execute raises KeyError
    # or similar quickly, and commands_service catches it and returns
    # {"ok": false, "error": "command_exception"}. This confirms the route
    # is live and the dispatch path works without waiting for a heavy USD
    # operation on the main thread.
    print("\n[2] Dispatch nonexistent command on Isaac (8011)")
    status_isaac, isaac_result = await _call(8011, "NonExistentCommand_Smoke")
    print(f"  HTTP {status_isaac}")
    print(json.dumps(isaac_result, indent=2, default=str) if isinstance(isaac_result, dict) else isaac_result)

    print("\n[3] Dispatch nonexistent command on USD Composer (8014)")
    status_composer, composer_result = await _call(8014, "NonExistentCommand_Smoke")
    print(f"  HTTP {status_composer}")
    print(json.dumps(composer_result, indent=2, default=str) if isinstance(composer_result, dict) else composer_result)

    print("\n[4] Stop both")
    await pm_composer.stop()
    await pm_isaac.stop()

    # Hard assertions: route exists (not 404) and returns structured JSON.
    assert status_isaac != 404, f"Isaac /commands/execute not registered (404)"
    assert status_composer != 404, f"USD Composer /commands/execute not registered (404)"
    assert isinstance(isaac_result, dict), f"Isaac response not JSON: {isaac_result!r}"
    assert isinstance(composer_result, dict), f"Composer response not JSON: {composer_result!r}"

    print("\n=== PASS (soft) ===")
    print("Hard check: /commands/execute route is live on both profiles.")
    print("Soft check: actual Kit command execution depends on Kit version")
    print("and threading model — a nonexistent command confirms the error")
    print("path returns structured JSON without hanging.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
