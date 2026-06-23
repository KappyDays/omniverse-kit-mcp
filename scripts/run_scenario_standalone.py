"""Standalone scenario runner.

Bypasses the cached MCP-server import graph so updates to action_registry /
runner / schema take effect without restarting the Claude Code session.

Usage:
    .venv/Scripts/python.exe scripts/run_scenario_standalone.py <scenario_path>
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.clients.lakehouse_client import LakehouseClient
from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.modules.asset_module import AssetModule
from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.modules.content_module import ContentModule
from omniverse_kit_mcp.modules.extension_module import ExtensionModule
from omniverse_kit_mcp.modules.job_module import JobModule
from omniverse_kit_mcp.modules.lakehouse_module import LakehouseModule
from omniverse_kit_mcp.modules.lighting_module import LightingModule
from omniverse_kit_mcp.modules.material_module import MaterialModule
from omniverse_kit_mcp.modules.navigation_module import NavigationModule
from omniverse_kit_mcp.modules.omnigraph_module import OmnigraphModule
from omniverse_kit_mcp.modules.physics_module import PhysicsModule
from omniverse_kit_mcp.modules.replicator_module import ReplicatorModule
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.modules.sensor_module import SensorModule
from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.modules.stage_module import StageModule
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.modules.window_module import WindowModule
from omniverse_kit_mcp.scenario.compiler import compile_scenario
from omniverse_kit_mcp.scenario.loader import load_scenario
from omniverse_kit_mcp.scenario.reporters import to_json, to_markdown
from omniverse_kit_mcp.scenario.runner import ScenarioRunner


async def run(scenario_path: str) -> int:
    os.chdir(PROJECT_ROOT)
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
        window = WindowModule(isaac_client)
        navigation = NavigationModule(isaac_client)
        sensor = SensorModule(isaac_client)
        physics = PhysicsModule(isaac_client)
        lighting = LightingModule(isaac_client)
        material = MaterialModule(isaac_client)
        replicator = ReplicatorModule(isaac_client)
        omnigraph = OmnigraphModule(isaac_client)
        content = ContentModule(isaac_client)

        runner = ScenarioRunner(
            stage, viewport, lakehouse, extension, simulation,
            robot, job, asset, character,
            window, navigation, sensor, physics, lighting,
            material, replicator, omnigraph, content,
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
