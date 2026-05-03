"""FastMCP server setup — wires every domain module into the MCP tool surface."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.clients.lakehouse_client import LakehouseClient
from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.prompts import SYSTEM_PROMPT
from omniverse_kit_mcp.modules.asset_module import AssetModule
from omniverse_kit_mcp.modules.catalog_module import CatalogModule
from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.modules.content_module import ContentModule
from omniverse_kit_mcp.modules.extension_module import ExtensionModule
from omniverse_kit_mcp.modules.job_module import JobModule
from omniverse_kit_mcp.modules.kit_command_module import KitCommandModule
from omniverse_kit_mcp.modules.lakehouse_module import LakehouseModule
from omniverse_kit_mcp.modules.lighting_module import LightingModule
from omniverse_kit_mcp.modules.material_module import MaterialModule
from omniverse_kit_mcp.modules.navigation_module import NavigationModule
from omniverse_kit_mcp.modules.omnigraph_module import OmnigraphModule
from omniverse_kit_mcp.modules.physics_module import PhysicsModule
from omniverse_kit_mcp.modules.process_module import ProcessModule
from omniverse_kit_mcp.modules.replicator_module import ReplicatorModule
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.modules.sensor_module import SensorModule
from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.modules.stage_module import StageModule
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.modules.window_module import WindowModule
from omniverse_kit_mcp.mcp.resources import register_resources
from omniverse_kit_mcp.tools.module_tools import register_module_tools
from omniverse_kit_mcp.tools.scenario_tools import register_scenario_tools


def create_mcp_server(config: AppConfig) -> FastMCP:
    """Create and configure the MCP server with all tools."""
    mcp = FastMCP(
        name=config.mcp_server.name,
        instructions=SYSTEM_PROMPT,
    )

    # Create clients
    isaac_client = IsaacRestClient(config.isaac_sim)
    lakehouse_client = LakehouseClient(config.lakehouse)

    # Create modules
    stage_module = StageModule(isaac_client)
    viewport_module = ViewportModule(isaac_client)
    lakehouse_module = LakehouseModule(lakehouse_client)
    extension_module = ExtensionModule(isaac_client)
    simulation_module = SimulationModule(isaac_client)
    process_module = ProcessModule(config.isaac_sim_process)
    robot_module = RobotModule(isaac_client)
    job_module = JobModule(isaac_client)
    asset_module = AssetModule(isaac_client)
    character_module = CharacterModule(isaac_client)
    window_module = WindowModule(isaac_client)
    navigation_module = NavigationModule(isaac_client)
    sensor_module = SensorModule(isaac_client)
    physics_module = PhysicsModule(isaac_client)
    lighting_module = LightingModule(isaac_client)
    material_module = MaterialModule(isaac_client)
    replicator_module = ReplicatorModule(isaac_client)
    omnigraph_module = OmnigraphModule(isaac_client)
    content_module = ContentModule(isaac_client)
    kit_command_module = KitCommandModule(isaac_client)
    catalog_path = Path(__file__).resolve().parents[3] / "docs" / "references" / "extensions.json"
    catalog_module = CatalogModule(catalog_path)

    # Register tools
    register_module_tools(
        mcp, stage_module, viewport_module, lakehouse_module,
        extension_module, simulation_module, process_module,
        robot_module, job_module, asset_module, character_module,
        window_module, navigation_module, sensor_module,
        physics_module, lighting_module, material_module,
        replicator_module, omnigraph_module, content_module,
        kit_command_module, catalog_module,
    )
    register_scenario_tools(
        mcp, config, stage_module, viewport_module, lakehouse_module,
        extension_module, simulation_module, robot_module, job_module,
        asset_module, character_module, window_module, navigation_module,
        sensor_module, physics_module, lighting_module, material_module,
        replicator_module, omnigraph_module, content_module,
    )
    register_resources(mcp, config)

    return mcp
