"""Live verification: 2 Isaac Sim instances on ports 8011 + 8012.

Success criteria:
  1. Both kits spawn to healthy state
  2. PIDs differ
  3. Health endpoints respond on their respective ports
  4. Stopping instance 2 leaves instance 1 alive (PID scoping)
  5. Stopping instance 1 completes cleanly (last instance → hub cleanup)

Assumes no kit.exe is running beforehand. If one exists, Phase 0 should
have killed it; this script does NOT auto-cleanup to avoid masking bugs.
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


async def _health(port: int) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"http://localhost:{port}/validation/v1/health")
            return r.status_code == 200
    except Exception:
        return False


async def main() -> int:
    print("=== Isaac Sim multi-instance verification ===\n")

    pm1 = _module_for("isaac-sim", 1)
    pm2 = _module_for("isaac-sim", 2)

    print("[1/5] Start instance 1 (port 8011)")
    r1 = await pm1.start()
    print(json.dumps(r1, indent=2, default=str))
    assert r1.get("ok"), "instance 1 failed to start"
    pid1 = r1["pid"]

    print("\n[2/5] Start instance 2 (port 8012)")
    r2 = await pm2.start()
    print(json.dumps(r2, indent=2, default=str))
    assert r2.get("ok"), "instance 2 failed to start"
    pid2 = r2["pid"]

    print(f"\n[3/5] PIDs differ? pid1={pid1} pid2={pid2}")
    assert pid1 != pid2

    print("\n[4/5] Health check both ports")
    h1, h2 = await _health(8011), await _health(8012)
    print(f"  8011: {'OK' if h1 else 'FAIL'}   8012: {'OK' if h2 else 'FAIL'}")
    assert h1 and h2

    print("\n[5a/5] Stop instance 2; instance 1 must stay alive")
    r_stop2 = await pm2.stop()
    print(json.dumps(r_stop2, indent=2, default=str))
    assert await _health(8011), "instance 1 died when instance 2 stopped (PID scoping broken)"

    print("\n[5b/5] Stop instance 1")
    r_stop1 = await pm1.stop()
    print(json.dumps(r_stop1, indent=2, default=str))
    assert r_stop1.get("ok")

    print("\n=== PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
