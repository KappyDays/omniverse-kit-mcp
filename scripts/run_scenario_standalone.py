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
from isaacsim_mcp.modules.asset_module import AssetModule
from isaacsim_mcp.modules.character_module import CharacterModule
from isaacsim_mcp.modules.extension_module import ExtensionModule
from isaacsim_mcp.modules.job_module import JobModule
from isaacsim_mcp.modules.lakehouse_module import LakehouseModule
from isaacsim_mcp.modules.robot_module import RobotModule
from isaacsim_mcp.modules.simulation_module import SimulationModule
from isaacsim_mcp.modules.stage_module import StageModule
from isaacsim_mcp.modules.viewport_module import ViewportModule
from isaacsim_mcp.scenario.compiler import compile_scenario
from isaacsim_mcp.scenario.loader import load_scenario
from isaacsim_mcp.scenario.reporters import to_json, to_markdown
from isaacsim_mcp.scenario.runner import ScenarioRunner


async def run(scenario_path: str) -> int:
    config = AppConfig()
    resolved_path = _resolve_scenario_path(scenario_path, config)
    isaac_client = IsaacRestClient(config.isaac_sim)
    lakehouse_client = LakehouseClient(config.lakehouse)
    try:
        stage = StageModule(isaac_client)
        viewport = ViewportModule(isaac_client)
        lakehouse = LakehouseModule(lakehouse_client)
        extension = ExtensionModule(isaac_client)
        simulation = SimulationModule(isaac_client)
        robot = RobotModule(isaac_client)
        job = JobModule(isaac_client)
        asset = AssetModule(isaac_client)
        character = CharacterModule(isaac_client)

        runner = ScenarioRunner(
            stage, viewport, lakehouse, extension, simulation,
            robot, job, asset, character,
        )

        raw = load_scenario(resolved_path)
        scenario = compile_scenario(raw)
        summary = await runner.run(scenario)

        print("===== JSON REPORT =====")
        print(to_json(summary))
        print("===== MARKDOWN REPORT =====")
        print(to_markdown(summary))

        return 0 if summary.status.value == "passed" else 1
    finally:
        await isaac_client.close()


def _resolve_scenario_path(user_path: str, config) -> str:
    """Resolve *user_path* against config.scenario.scenarios_dir / project root.

    Absolute paths pass through unchanged; relative paths are looked up
    first under the configured scenarios_dir, then under the project root
    (so both ``smoke/foo.yaml`` and ``scenarios/smoke/foo.yaml`` work).
    """
    p = Path(user_path)
    if p.is_absolute():
        return str(p)
    scenarios_dir = Path(config.scenario.scenarios_dir)
    if not scenarios_dir.is_absolute():
        scenarios_dir = PROJECT_ROOT / scenarios_dir
    candidate = scenarios_dir / p
    if candidate.exists():
        return str(candidate)
    root_candidate = PROJECT_ROOT / p
    if root_candidate.exists():
        return str(root_candidate)
    return str(candidate)  # let loader raise with a sensible path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_scenario_standalone.py <scenario_path>")
        sys.exit(2)
    sys.exit(asyncio.run(run(sys.argv[1])))
