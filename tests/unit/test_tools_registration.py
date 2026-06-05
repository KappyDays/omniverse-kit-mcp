"""Unit tests verifying all MCP tools are registered.

Expected tool names are a **single source of truth** (below) — Phase C/D
additions only need to update these lists, no count literal to chase.
"""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server


EXPECTED_MODULE_TOOLS: frozenset[str] = frozenset({
    # Process
    "kit_app_start",
    "kit_app_stop",
    "kit_app_restart",
    "process_list_kit_instances",
    # Stage READ/ASSERT
    "stage_capture_snapshot",
    "stage_diff_snapshots",
    "stage_assert_prim_exists",
    "stage_assert_property",
    # Stage WRITE (→ SimulationModule)
    "stage_load_usd",
    "stage_set_property",
    "stage_set_semantic_label",
    "stage_create_prim",
    "stage_delete_prim",
    # Simulation
    "simulation_play",
    "simulation_pause",
    "simulation_stop",
    "simulation_get_status",
    # Viewport
    "viewport_capture",
    "viewport_compare_ssim",
    # Extension
    "extension_trigger",
    "extension_get_state",
    # Lakehouse
    "lakehouse_query",
    # Phase B — Robot
    "robot_load",
    "robot_get_joint_positions",
    "robot_get_joint_config",
    "robot_set_joint_positions",
    "robot_navigate_to",
    # Phase B — Job
    "job_status",
    "job_cancel",
    # Phase B+ — Asset catalog (GUI Asset Browser equivalent)
    "asset_list",
    # Asset discovery — offline curated-catalog semantic search (no REST)
    "asset_search",
    # Phase B+ — File / Selection / Camera (GUI File menu + Stage panel)
    "stage_save",
    "stage_open",
    "stage_new",
    "stage_get_selection",
    "stage_set_selection",
    "viewport_set_active_camera",
    "viewport_set_camera_lookat",
    "viewport_focus_prim",
    # Phase C — Character
    "character_load",
    "character_play_animation",
    "character_set_position",
    "character_stop_animation",
    "character_navigate_to",
    "character_get_state",
    # Phase D — Extension UI automation + carb log capture
    "extension_activate",
    "extension_reload",
    "extension_get_ui_tree",
    "extension_ui_invoke",
    "extension_ui_run_and_wait",
    "extension_capture_logs",
    # Phase E — log ring buffer management
    "extension_clear_logs",
    # Phase E — Window (Kit GUI / menu / omni.ui.Window)
    "window_capture",
    "window_capture_sequence",
    "window_list",
    "window_ui_list",
    "window_ui_show",
    "window_menu_list",
    "window_menu_trigger",
    # Phase E — NavMesh
    "navigation_bake",
    "navigation_query_path",
    "navigation_add_exclude_volume",
    # Phase E — Sensor (RTX Camera / Lidar / Depth) + visualization
    "sensor_attach_rtx_camera",
    "sensor_attach_rtx_lidar",
    "sensor_lidar_get_point_cloud",
    "sensor_attach_rtx_depth_camera",
    "sensor_set_visualization",
    # Phase E — Viewport multi (create / destroy)
    "viewport_create",
    "viewport_destroy",
    # Phase E — NavMesh visualization overlay
    "navigation_set_visualization",
    # Phase F — Physics (rigid body / collider / material / joint / scene / viz)
    "physics_apply_rigid_body",
    "physics_get_rigid_body_state",
    "physics_apply_collider",
    "physics_apply_material",
    "physics_create_joint",
    "physics_set_joint_drive",
    "physics_set_scene",
    "physics_visualize",
    # Phase F — Lighting (UsdLux Dome/Distant/Disk/Rect/Sphere + exposure)
    "lighting_create_dome",
    "lighting_create_distant",
    "lighting_create_disk",
    "lighting_create_rect",
    "lighting_create_sphere",
    "lighting_set_exposure",
    # Phase F — Material (MDL list / assign / bound)
    "material_list_mdl",
    "material_assign_mdl",
    "material_get_bound",
    # Phase F — Viewport render extension (mode / quality / overlay / fov)
    "viewport_set_render_mode",
    "viewport_set_render_quality",
    "viewport_toggle_overlay",
    "viewport_set_fov",
    # Phase G — Robot extensions (navigate_path / gripper_control / set_ee_target)
    "robot_navigate_path",
    "robot_gripper_control",
    "robot_set_ee_target",
    # Phase G — Character extensions (animation variant / crowd load)
    "character_play_animation_variant",
    "character_load_crowd",
    # Phase G — Sensor extensions (contact / imu / annotator)
    "sensor_attach_contact",
    "sensor_attach_imu",
    "sensor_set_annotator",
    # Phase G — Simulation timeline extensions (step / set_time)
    "simulation_step",
    "simulation_wait_until",
    "simulation_set_time",
    # Phase H — Replicator (writer / randomizer / trigger)
    "replicator_create_writer",
    "replicator_register_randomizer",
    "replicator_trigger_once",
    "replicator_trigger_on_time",
    # Phase H — OmniGraph (node / connect / execute + ROS2 publisher)
    "omnigraph_create_node",
    "omnigraph_connect",
    "omnigraph_execute",
    "omnigraph_create_ros2_publisher",
    # Phase H — Content browser (browse / preview / resolve)
    "content_browse",
    "content_preview",
    "content_inspect",
    "content_resolve",
    # Phase H — Extension management (deactivate / list_all / get_info)
    "extension_deactivate",
    "extension_list_all",
    "extension_get_info",
    # Phase J — NavMesh Playground (sample_walkable_points + drive_physics)
    "navigation_sample_walkable_points",
    "robot_drive_physics",
    # D25 — Kit commands (common profile)
    "kit_command_execute",
    "kit_python_run",
    # Phase E — Extension catalog search (local JSON query, no REST)
    "extension_search",
})

EXPECTED_SCENARIO_TOOLS: frozenset[str] = frozenset({
    "scenario_validate",
    "scenario_plan",
    # scenario_list demoted to MCP resource isaacsim://scenarios
    # scenario_schema demoted to MCP resource isaacsim://scenario-schema
    "scenario_last_report",
})

EXPECTED_ALL_TOOLS: frozenset[str] = EXPECTED_MODULE_TOOLS | EXPECTED_SCENARIO_TOOLS


@pytest.fixture
def mcp_server():
    config = AppConfig()
    return create_mcp_server(config)


def test_registered_tools_match_expected_set(mcp_server):
    """Every tool in EXPECTED_ALL_TOOLS is registered, nothing extra."""
    registered = frozenset(mcp_server._tool_manager._tools)
    missing = EXPECTED_ALL_TOOLS - registered
    unexpected = registered - EXPECTED_ALL_TOOLS
    assert not missing, f"Missing tools: {sorted(missing)}"
    assert not unexpected, f"Unexpected tools: {sorted(unexpected)}"


def test_tool_count_matches_expected_list(mcp_server):
    """Count is derived from the SoT list — no literal to update per Phase."""
    registered = mcp_server._tool_manager._tools
    assert len(registered) == len(EXPECTED_ALL_TOOLS)


def test_module_tools_present(mcp_server):
    tools = mcp_server._tool_manager._tools
    for name in EXPECTED_MODULE_TOOLS:
        assert name in tools, f"Missing module tool: {name}"


def test_scenario_tools_present(mcp_server):
    tools = mcp_server._tool_manager._tools
    for name in EXPECTED_SCENARIO_TOOLS:
        assert name in tools, f"Missing scenario tool: {name}"


def test_no_inject_cleanup_tools(mcp_server):
    """Verify lakehouse_inject and lakehouse_cleanup are NOT registered."""
    tools = mcp_server._tool_manager._tools
    assert "lakehouse_inject" not in tools
    assert "lakehouse_cleanup" not in tools
    assert "extension_reset" not in tools  # reset is internal only
