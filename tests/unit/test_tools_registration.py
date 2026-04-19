"""Unit tests verifying all MCP tools are registered.

Expected tool names are a **single source of truth** (below) — Phase C/D
additions only need to update these lists, no count literal to chase.
"""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server


EXPECTED_MODULE_TOOLS: frozenset[str] = frozenset({
    # Process
    "isaac_sim_start",
    "isaac_sim_stop",
    "isaac_sim_restart",
    # Stage READ/ASSERT
    "stage_capture_snapshot",
    "stage_diff_snapshots",
    "stage_assert_prim_exists",
    "stage_assert_property",
    # Stage WRITE (→ SimulationModule)
    "stage_load_usd",
    "stage_set_property",
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
    "robot_set_joint_positions",
    "robot_navigate_to",
    # Phase B — Job
    "job_status",
    "job_cancel",
    # Phase B+ — Asset catalog (GUI Asset Browser equivalent)
    "asset_list",
    # Phase B+ — File / Selection / Camera (GUI File menu + Stage panel)
    "stage_save",
    "stage_open",
    "stage_new",
    "stage_get_selection",
    "stage_set_selection",
    "viewport_set_active_camera",
    # Phase C — Character
    "character_load",
    "character_play_animation",
    "character_set_position",
    "character_stop_animation",
    "character_navigate_to",
    "character_get_state",
    # Phase D — Extension UI automation + carb log capture
    "extension_activate",
    "extension_get_ui_tree",
    "extension_ui_invoke",
    "extension_capture_logs",
    # Phase E — log ring buffer management
    "extension_clear_logs",
    # Phase E — Window (Kit GUI / menu / omni.ui.Window)
    "window_capture",
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
    "sensor_attach_rtx_depth_camera",
    "sensor_set_visualization",
    # Phase E — Viewport multi (create / destroy)
    "viewport_create",
    "viewport_destroy",
    # Phase E — NavMesh visualization overlay
    "navigation_set_visualization",
})

EXPECTED_SCENARIO_TOOLS: frozenset[str] = frozenset({
    "scenario_validate",
    "scenario_plan",
    "scenario_list",
    "scenario_schema",
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
