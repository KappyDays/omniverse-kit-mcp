"""Live verification: Isaac Sim + USD Composer concurrent on separate ports.

Success criteria:
  1. Isaac instance 1 spawns on 8011
  2. USD Composer instance 1 spawns on 8014
  3. Both healthy simultaneously
  4. Common route (/health) works on BOTH ports
  5. Isaac-specific route (/robot/load) works on 8011, returns 503 on 8014
  6. Both stop cleanly

GPU budget: RTX 4070 12GB. Both apps empty-scene ~4-5GB each. Keep scene
content at minimum during verification.
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


async def _get(port: int, path: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=10.0) as c:
        return await c.get(f"http://localhost:{port}{path}")


async def _post(port: int, path: str, body: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=15.0) as c:
        return await c.post(f"http://localhost:{port}{path}", json=body)


async def main() -> int:
    print("=== Multi-app (Isaac + USD Composer) verification ===\n")

    pm_isaac = _module_for("isaac-sim", 1)
    pm_composer = _module_for("usd-composer", 1)

    print("[1/6] Start Isaac Sim (port 8011)")
    r_isaac = await pm_isaac.start()
    print(json.dumps(r_isaac, indent=2, default=str))
    assert r_isaac.get("ok"), "Isaac Sim failed to start"

    print("\n[2/6] Start USD Composer (port 8014)")
    r_composer = await pm_composer.start()
    print(json.dumps(r_composer, indent=2, default=str))
    assert r_composer.get("ok"), "USD Composer failed to start"

    print(f"\n[3/6] PIDs differ? isaac={r_isaac['pid']} composer={r_composer['pid']}")
    assert r_isaac["pid"] != r_composer["pid"]

    print("\n[4/6] Common route /health on both ports")
    h_isaac = await _get(8011, "/validation/v1/health")
    h_composer = await _get(8014, "/validation/v1/health")
    print(f"  8011: {h_isaac.status_code}   8014: {h_composer.status_code}")
    assert h_isaac.status_code == 200 and h_composer.status_code == 200

    print("\n[5/6] Isaac-only route /robot/load")
    body = {"prim_path": "/World/Robot", "usd_url": "/nonexistent"}
    r_isaac_robot = await _post(8011, "/validation/v1/robot/load", body)
    r_composer_robot = await _post(8014, "/validation/v1/robot/load", body)
    print(f"  isaac 8011: {r_isaac_robot.status_code}  "
          f"composer 8014: {r_composer_robot.status_code}")
    assert r_isaac_robot.status_code != 503, (
        "Isaac Sim should NOT return 503 for /robot/load"
    )
    assert r_composer_robot.status_code == 503, (
        f"USD Composer should return 503 for /robot/load, got {r_composer_robot.status_code}"
    )
    detail = r_composer_robot.json().get("detail", {})
    assert detail.get("error") == "robot_stack_unavailable", (
        f"Expected robot_stack_unavailable, got {detail}"
    )

    print("\n[6/6] Stop both instances")
    r_stop_c = await pm_composer.stop()
    r_stop_i = await pm_isaac.stop()
    print(json.dumps({"composer_stop": r_stop_c, "isaac_stop": r_stop_i}, indent=2, default=str))
    assert r_stop_c.get("ok") and r_stop_i.get("ok")

    print("\n=== PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
