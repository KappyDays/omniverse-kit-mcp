"""Unit tests verifying all 22 tools are registered and no inject/cleanup tools exist."""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server


@pytest.fixture
def mcp_server():
    config = AppConfig()
    return create_mcp_server(config)


def test_22_tools_registered(mcp_server):
    """Verify exactly 22 tools are registered (14 original + 8 WRITE)."""
    tools = mcp_server._tool_manager._tools
    assert len(tools) == 22, f"Expected 22 tools, got {len(tools)}: {list(tools.keys())}"


def test_module_tools_present(mcp_server):
    """Verify all 17 module tools are registered (9 READ/ASSERT + 8 WRITE)."""
    tools = mcp_server._tool_manager._tools
    expected_module_tools = [
        "stage_capture_snapshot",
        "stage_diff_snapshots",
        "stage_assert_prim_exists",
        "stage_assert_property",
        "viewport_capture",
        "viewport_compare_ssim",
        "lakehouse_query",
        "extension_trigger",
        "extension_get_state",
        "stage_load_usd",
        "stage_set_property",
        "stage_create_prim",
        "stage_delete_prim",
        "simulation_play",
        "simulation_pause",
        "simulation_stop",
        "simulation_get_status",
    ]
    for tool_name in expected_module_tools:
        assert tool_name in tools, f"Missing module tool: {tool_name}"


def test_scenario_tools_present(mcp_server):
    """Verify all 5 scenario tools are registered."""
    tools = mcp_server._tool_manager._tools
    expected_scenario_tools = [
        "scenario_validate",
        "scenario_plan",
        "scenario_list",
        "scenario_schema",
        "scenario_last_report",
    ]
    for tool_name in expected_scenario_tools:
        assert tool_name in tools, f"Missing scenario tool: {tool_name}"


def test_no_inject_cleanup_tools(mcp_server):
    """Verify lakehouse_inject and lakehouse_cleanup are NOT registered."""
    tools = mcp_server._tool_manager._tools
    assert "lakehouse_inject" not in tools
    assert "lakehouse_cleanup" not in tools
    assert "extension_reset" not in tools  # reset is internal only
