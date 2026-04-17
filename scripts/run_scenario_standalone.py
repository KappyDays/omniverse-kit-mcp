"""Standalone scenario runner.

Bypasses the cached MCP-server import graph so updates to action_registry /
runner / schema take effect without restarting the Claude Code session.

Usage:
    .venv/Scripts/python.exe scripts/run_scenario_standalone.py <scenario_path>
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from isaacsim_mcp.clients.isaac_rest_client import IsaacRestClient
from isaacsim_mcp.clients.lakehouse_client import LakehouseClient
from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.modules.extension_module import ExtensionModule
from isaacsim_mcp.modules.lakehouse_module import LakehouseModule
from isaacsim_mcp.modules.simulation_module import SimulationModule
from isaacsim_mcp.modules.stage_module import StageModule
from isaacsim_mcp.modules.viewport_module import ViewportModule
from isaacsim_mcp.scenario.compiler import compile_scenario
from isaacsim_mcp.scenario.loader import load_scenario
from isaacsim_mcp.scenario.reporters import to_json, to_markdown
from isaacsim_mcp.scenario.runner import ScenarioRunner


async def run(scenario_path: str) -> int:
    config = AppConfig()
    isaac_client = IsaacRestClient(config.isaac_sim)
    lakehouse_client = LakehouseClient(config.lakehouse)
    try:
        stage = StageModule(isaac_client)
        viewport = ViewportModule(isaac_client)
        lakehouse = LakehouseModule(lakehouse_client)
        extension = ExtensionModule(isaac_client)
        simulation = SimulationModule(isaac_client)

        runner = ScenarioRunner(stage, viewport, lakehouse, extension, simulation)

        raw = load_scenario(scenario_path)
        scenario = compile_scenario(raw)
        summary = await runner.run(scenario)

        print("===== JSON REPORT =====")
        print(to_json(summary))
        print("===== MARKDOWN REPORT =====")
        print(to_markdown(summary))

        return 0 if summary.status.value == "passed" else 1
    finally:
        await isaac_client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_scenario_standalone.py <scenario_path>")
        sys.exit(2)
    sys.exit(asyncio.run(run(sys.argv[1])))
