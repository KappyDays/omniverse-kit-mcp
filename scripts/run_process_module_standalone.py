"""Exercise the updated ProcessModule directly (bypasses cached MCP server).

Usage:
    .venv/Scripts/python.exe scripts/run_process_module_standalone.py <start|stop|restart>
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from isaacsim_mcp.config import AppConfig  # noqa: E402
from isaacsim_mcp.modules.process_module import ProcessModule  # noqa: E402


async def run(action: str) -> int:
    config = AppConfig()
    pm = ProcessModule(config.isaac_sim_process)

    if action == "start":
        result = await pm.start()
    elif action == "stop":
        result = await pm.stop()
    elif action == "restart":
        result = await pm.restart()
    else:
        print(f"Unknown action: {action}")
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_process_module_standalone.py <start|stop|restart>")
        sys.exit(2)
    sys.exit(asyncio.run(run(sys.argv[1])))
