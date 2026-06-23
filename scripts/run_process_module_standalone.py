"""Exercise ProcessModule directly (bypasses cached MCP server).

Usage:
    .venv/Scripts/python.exe scripts/run_process_module_standalone.py <start|stop|restart> \
        [--profile isaac-sim|usd-composer] [--instance N]

Defaults: profile=isaac-sim, instance=1 (mirrors legacy single-instance behavior).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from omniverse_kit_mcp.config import AppConfig  # noqa: E402
from omniverse_kit_mcp.modules.process_module import ProcessModule  # noqa: E402


async def run(action: str, profile: str, instance: int) -> int:
    os.chdir(PROJECT_ROOT)
    os.environ["ISAAC_MCP_APP_PROFILE"] = profile
    os.environ["ISAAC_MCP_INSTANCE_ID"] = str(instance)

    config = AppConfig()
    pm = ProcessModule(config.isaac_sim_process)

    print(f"[standalone] profile={profile} instance_id={instance} "
          f"ext_port={config.isaac_sim_process.ext_port} action={action}")
    print(f"[standalone] kit_exe={config.isaac_sim_process.effective_kit_exe}")

    if action == "start":
        result = await pm.start()
    elif action == "stop":
        result = await pm.stop()
    elif action == "restart":
        result = await pm.restart()
    else:
        print(f"Unknown action: {action}")
        return 2

    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["start", "stop", "restart"])
    p.add_argument("--profile", choices=["isaac-sim", "usd-composer"], default="isaac-sim")
    p.add_argument("--instance", type=int, default=1)
    args = p.parse_args()
    return asyncio.run(run(args.action, args.profile, args.instance))


if __name__ == "__main__":
    sys.exit(main())
