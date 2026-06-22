"""Unit tests verifying all MCP tools are registered.

Expected tool names are a **single source of truth** (below) — Phase C/D
additions only need to update these lists, no count literal to chase.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

from omniverse_kit_mcp.config import AppConfig, MCPServerConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.tools.module_tools import register_module_tools
from omniverse_kit_mcp.tools.tool_profiles import (
    PROFILE_APP,
    PROFILE_CORE,
    PROFILE_CUSTOM,
    PROFILE_FULL,
    TOOL_METADATA,
    build_tool_selection,
)


EXPECTED_MODULE_TOOLS: frozenset[str] = frozenset({
    # Process
    "mcp_runtime_info",
    "kit_app_start",
    "kit_app_stop",
    "kit_app_restart",
    "process_list_kit_instances",
    # Stage READ/ASSERT
    "stage_capture_snapshot",
    "stage_diff_snapshots",
    "stage_compute_world_bbox",
    "stage_visual_alignment_report",
    "stage_placement_validation_report",
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
    "robot_list_arm_profiles",
    "robot_probe_arm_profile",
    "robot_probe_arm_profiles",
    "robot_get_joint_positions",
    "robot_get_joint_config",
    "robot_get_joint_config_static",
    "robot_set_joint_positions",
    "robot_navigate_to",
    # Phase B — Job
    "job_status",
    "job_cancel",
    # Phase B+ — Asset catalog (GUI Asset Browser equivalent)
    "asset_list",
    # Asset discovery — offline curated-catalog semantic search (no REST)
    "asset_search",
    # Generated NVIDIA official browser-extension catalog (offline + on-demand verify)
    "official_asset_search",
    "official_asset_resolve",
    "official_asset_get",
    "official_asset_sync_status",
    "official_asset_verify",
    # External free asset prepare-only ingest (download + convert, no stage placement)
    "external_asset_search",
    "external_asset_download",
    "external_asset_convert",
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
    "viewport_project_points",
    "viewport_frame_prims",
    "viewport_capture_assert",
    # Phase G — Robot extensions (navigate_path / gripper_control / set_ee_target)
    "robot_navigate_path",
    "robot_gripper_control",
    "robot_set_ee_target",
    "robot_get_ee_pose",
    "robot_run_franka_pick_place",
    "robot_install_franka_pick_place_playback_demo",
    "robot_install_pick_place_playback_demo",
    "robot_reset_pick_place_demo",
    "robot_get_pick_place_demo_status",
    # Phase G — Character extensions (animation variant / crowd load)
    "character_play_animation_variant",
    "character_load_crowd",
    # Phase G — Sensor extensions (contact / imu / annotator)
    "sensor_attach_contact",
    "sensor_attach_imu",
    "sensor_set_annotator",
    # Phase G — Simulation timeline extensions (step / set_time)
    "simulation_step",
    "simulation_step_observe",
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
    "omnigraph_create_script_controller",
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
FULL_PROFILE_CONTRACT_TOOL_COUNT = 152
APP_PROFILE_CONTRACT_TOOL_COUNT = 148


@pytest.fixture(autouse=True)
def _isolate_tool_profile_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in (
        "MCP_SERVER_TOOL_PROFILE",
        "MCP_SERVER_TOOL_INCLUDE",
        "MCP_SERVER_TOOL_EXCLUDE",
        "ISAAC_MCP_APP_PROFILE",
    ):
        monkeypatch.delenv(key, raising=False)


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


def test_full_tool_profile_matches_expected_set():
    """Explicit full profile is the compatibility surface."""
    config = AppConfig(mcp_server=MCPServerConfig(tool_profile=PROFILE_FULL))
    mcp = create_mcp_server(config)
    registered = frozenset(mcp._tool_manager._tools)
    assert registered == EXPECTED_ALL_TOOLS
    assert len(registered) == FULL_PROFILE_CONTRACT_TOOL_COUNT


def test_core_tool_profile_is_strict_subset():
    config = AppConfig(mcp_server=MCPServerConfig(tool_profile=PROFILE_CORE))
    mcp = create_mcp_server(config)
    registered = frozenset(mcp._tool_manager._tools)

    assert registered < EXPECTED_ALL_TOOLS
    assert "mcp_runtime_info" in registered
    assert "stage_load_usd" in registered
    assert "robot_load" not in registered


def test_app_tool_profile_is_strict_subset_for_isaac():
    config = AppConfig(mcp_server=MCPServerConfig(tool_profile=PROFILE_APP))
    mcp = create_mcp_server(config)
    registered = frozenset(mcp._tool_manager._tools)

    assert registered < EXPECTED_ALL_TOOLS
    assert len(registered) == APP_PROFILE_CONTRACT_TOOL_COUNT
    assert "mcp_runtime_info" in registered
    assert "robot_load" in registered
    assert "external_asset_download" not in registered
    assert "kit_python_run" not in registered


def test_app_tool_profile_is_invariant_across_app_profiles(monkeypatch):
    default_config = AppConfig(mcp_server=MCPServerConfig(tool_profile=PROFILE_APP))
    default_mcp = create_mcp_server(default_config)
    default_registered = frozenset(default_mcp._tool_manager._tools)

    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    config = AppConfig(mcp_server=MCPServerConfig(tool_profile=PROFILE_APP))
    mcp = create_mcp_server(config)
    registered = frozenset(mcp._tool_manager._tools)

    assert registered == default_registered
    assert registered < EXPECTED_ALL_TOOLS
    assert len(registered) == APP_PROFILE_CONTRACT_TOOL_COUNT
    assert "mcp_runtime_info" in registered
    assert "material_assign_mdl" in registered
    assert "content_browse" in registered
    assert "robot_load" in registered
    assert "robot_probe_arm_profiles" in registered
    assert "sensor_attach_rtx_camera" in registered
    assert "sensor_lidar_get_point_cloud" in registered
    assert "sensor_set_annotator" in registered
    assert "omnigraph_create_ros2_publisher" in registered
    assert "external_asset_download" not in registered
    assert "kit_python_run" not in registered


def test_mcp_runtime_info_present_in_every_tool_profile():
    for profile in (PROFILE_FULL, PROFILE_CORE, PROFILE_APP, PROFILE_CUSTOM):
        config = AppConfig(mcp_server=MCPServerConfig(tool_profile=profile))
        mcp = create_mcp_server(config)
        assert "mcp_runtime_info" in mcp._tool_manager._tools


def test_every_expected_tool_has_metadata_classification():
    assert frozenset(TOOL_METADATA) == EXPECTED_ALL_TOOLS
    for name, meta in TOOL_METADATA.items():
        assert meta.name == name
        assert meta.group
        assert meta.group != "Unclassified"
        assert meta.domain
        assert PROFILE_FULL in meta.default_profiles
        assert meta.workflow_tags
        assert meta.risk_level


def test_custom_profile_applies_include_exclude_tokens():
    selection = build_tool_selection(
        profile=PROFILE_CUSTOM,
        include="robot_load,material",
        exclude="lakehouse",
    )

    assert "mcp_runtime_info" in selection.included_tools
    assert "robot_load" in selection.included_tools
    assert "material_assign_mdl" in selection.included_tools
    assert "lakehouse_query" not in selection.included_tools


def test_tool_count_matches_expected_list(mcp_server):
    """Count is derived from the SoT list — no literal to update per Phase."""
    registered = mcp_server._tool_manager._tools
    assert len(EXPECTED_ALL_TOOLS) == FULL_PROFILE_CONTRACT_TOOL_COUNT
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


@pytest.mark.asyncio
async def test_mcp_runtime_info_reports_probe_result_freshness(mcp_server):
    tool = mcp_server._tool_manager._tools["mcp_runtime_info"]

    payload = json.loads(await tool.fn())

    assert payload["ok"] is True
    assert payload["has_mcp_runtime_info_tool"] is True
    assert payload["tool_count"] == FULL_PROFILE_CONTRACT_TOOL_COUNT
    assert payload["tool_profile"] == PROFILE_FULL
    assert payload["app_profile"] == "isaac-sim"
    assert payload["registered_tool_count"] == FULL_PROFILE_CONTRACT_TOOL_COUNT
    assert payload["omitted_tool_count"] == 0
    assert payload["included_groups"]["Process - MCP / Kit app lifecycle"] == 5
    assert payload["omitted_groups"] == {}
    assert payload["omitted_tools"] == []
    assert payload["custom_include_tokens"] == []
    assert payload["custom_exclude_tokens"] == []
    assert payload["robot_probe_result_has_mcp_controllability"] is True
    assert payload["robot_probe_result_has_probe_capability_level"] is True
    assert payload["robot_probe_result_has_pick_place_validation_boundary"] is True
    assert payload["robot_probe_batch_result_has_summary"] is True
    assert payload["robot_probe_arm_profile_timeout_default_s"] == pytest.approx(90.0)
    assert payload["robot_probe_arm_profiles_per_profile_timeout_default_s"] == (
        pytest.approx(90.0)
    )
    assert payload["robot_probe_arm_profiles_batch_timeout_default_s"] == (
        pytest.approx(105.0)
    )
    assert "mcp_controllability" in payload["robot_probe_result_fields"]
    assert "mcp_controllability_reason" in payload["robot_probe_result_fields"]
    assert "probe_capability_level" in payload["robot_probe_result_fields"]
    assert "probe_capability_level_name" in payload["robot_probe_result_fields"]
    assert "probe_capability_level_reason" in payload["robot_probe_result_fields"]
    assert "probe_proves_pick_place" in payload["robot_probe_result_fields"]
    assert "pick_place_validation_status" in payload["robot_probe_result_fields"]
    assert "pick_place_validation_reason" in payload["robot_probe_result_fields"]
    assert "mcp_controllability_counts" in payload["robot_probe_batch_result_fields"]
    assert "mcp_controllability_profiles" in payload["robot_probe_batch_result_fields"]
    assert "probe_capability_level_name_counts" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "probe_capability_level_name_profiles" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "pick_place_validation_status_counts" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "pick_place_validation_status_profiles" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "unsupported_capability_counts" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "timed_out_profiles" in payload["robot_probe_batch_result_fields"]
    assert "batch_timeout_profiles" in payload["robot_probe_batch_result_fields"]
    assert "batch_aborted_profiles" in payload["robot_probe_batch_result_fields"]
    assert "blocked_profiles" in payload["robot_probe_batch_result_fields"]
    assert "hard_failure_profiles" in payload["robot_probe_batch_result_fields"]
    assert "lifecycle_recovery_profiles" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "unsupported_capability_profiles" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "ik_target_failure_profiles" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "static_metadata_profiles" in payload["robot_probe_batch_result_fields"]
    assert "known_dynamic_timeout_routed_profiles" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "dynamic_joint_control_profiles" in payload[
        "robot_probe_batch_result_fields"
    ]
    assert "dynamic_probe_recommended_profiles" in payload[
        "robot_arm_profiles_result_fields"
    ]
    assert "static_only_probe_recommended_profiles" in payload[
        "robot_arm_profiles_result_fields"
    ]
    assert "recommended_probe_mode_by_profile" in payload[
        "robot_arm_profiles_result_fields"
    ]
    assert "recommended_probe_mode_reasons" in payload[
        "robot_arm_profiles_result_fields"
    ]
    assert "profile_names" in payload["robot_probe_batch_request_fields"]
    assert "profile_names" in payload["robot_probe_batch_result_fields"]
    assert payload["source_modules"]
    source_module_names = {entry["module"] for entry in payload["source_modules"]}
    assert "omniverse_kit_mcp.robot_arm_profiles" in source_module_names
    assert "process_id" not in payload
    assert "cwd" not in payload
    assert "python_executable" not in payload
    assert all("file" not in entry for entry in payload["source_modules"])
    assert all(
        entry["source"] is None or not Path(entry["source"]).is_absolute()
        for entry in payload["source_modules"]
    )
    assert isinstance(payload["restart_required_for_latest_mcp_code"], bool)


@pytest.mark.asyncio
async def test_mcp_runtime_info_reports_app_profile_payload(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    config = AppConfig(mcp_server=MCPServerConfig(tool_profile=PROFILE_APP))
    mcp = create_mcp_server(config)
    tool = mcp._tool_manager._tools["mcp_runtime_info"]

    payload = json.loads(await tool.fn())

    assert payload["tool_profile"] == PROFILE_APP
    assert payload["app_profile"] == "usd-composer"
    assert payload["tool_count"] == APP_PROFILE_CONTRACT_TOOL_COUNT
    assert payload["registered_tool_count"] == APP_PROFILE_CONTRACT_TOOL_COUNT
    assert payload["omitted_tool_count"] == (
        FULL_PROFILE_CONTRACT_TOOL_COUNT - APP_PROFILE_CONTRACT_TOOL_COUNT
    )
    assert payload["custom_include_tokens"] == []
    assert payload["custom_exclude_tokens"] == []
    assert sorted(payload["omitted_tools"]) == [
        "external_asset_convert",
        "external_asset_download",
        "external_asset_search",
        "kit_python_run",
    ]
    assert payload["omitted_groups"] == {
        "Asset - catalog browsing / official assets": 3,
        "Kit commands - command registry / Python runner": 1,
    }
    assert "robot_load" in mcp._tool_manager._tools
    assert "sensor_attach_rtx_camera" in mcp._tool_manager._tools
    assert "omnigraph_create_ros2_publisher" in mcp._tool_manager._tools


@pytest.mark.asyncio
async def test_mcp_runtime_info_reports_custom_include_exclude_tokens():
    config = AppConfig(
        mcp_server=MCPServerConfig(
            tool_profile=PROFILE_CUSTOM,
            tool_include="robot_load,material",
            tool_exclude="lakehouse",
        )
    )
    mcp = create_mcp_server(config)
    tool = mcp._tool_manager._tools["mcp_runtime_info"]

    payload = json.loads(await tool.fn())

    assert payload["tool_profile"] == PROFILE_CUSTOM
    assert payload["custom_include_tokens"] == ["material", "robot_load"]
    assert payload["custom_exclude_tokens"] == ["lakehouse"]
    assert "robot_load" in mcp._tool_manager._tools
    assert "material_assign_mdl" in mcp._tool_manager._tools
    assert "lakehouse_query" not in mcp._tool_manager._tools


@pytest.mark.asyncio
async def test_robot_list_arm_profiles_tool_serializes_pick_place_blockers():
    from tests.conftest import MockIsaacRestClient

    mcp = FastMCP(name="test")
    dummy = SimpleNamespace()
    robot = RobotModule(MockIsaacRestClient())
    register_module_tools(
        mcp,
        *[dummy] * 6,
        robot,
        *[dummy] * 14,
    )
    tool = mcp._tool_manager._tools["robot_list_arm_profiles"]

    payload = json.loads(await tool.fn())

    assert payload["ok"] is True
    data = payload["data"]
    assert data["known_pick_place_blocker_profiles"] == [
        "franka_panda",
        "factory_franka",
    ]
    assert "insufficient lift" in (
        data["known_pick_place_blocker_profile_reasons"]["franka_panda"]
    )
    assert "deeper combined-Z offset trial" in (
        data["known_pick_place_blocker_profile_reasons"]["factory_franka"]
    )
    assert data["static_only_probe_recommended_profiles"] == (
        data["known_dynamic_timeout_profiles"]
    )
    assert "ur20" in data["static_only_probe_recommended_profiles"]
    assert "ur30" in data["dynamic_probe_recommended_profiles"]
    assert not set(data["dynamic_probe_recommended_profiles"]) & set(
        data["static_only_probe_recommended_profiles"]
    )
    assert data["recommended_probe_mode_by_profile"]["ur20"] == (
        "static_only_known_dynamic_timeout"
    )
    assert data["recommended_probe_mode_by_profile"]["ur30"] == (
        "dynamic_with_bounded_timeouts"
    )
    assert "timed out" in data["recommended_probe_mode_reasons"]["ur20"]
    assert "factory_franka" in {
        profile["profile_name"] for profile in data["profiles"]
    }


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_tool_serializes_batch_summary_fields():
    from tests.conftest import MockIsaacRestClient

    class UnsupportedCapabilityClient(MockIsaacRestClient):
        async def robot_gripper_control(self, request):  # type: ignore[override]
            self.calls.append(("robot_gripper_control", request))
            raise ValueError("No gripper joints found")

        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            raise ValueError("End-effector frame panda_hand not found")

    mcp = FastMCP(name="test")
    dummy = SimpleNamespace()
    robot = RobotModule(UnsupportedCapabilityClient())
    register_module_tools(
        mcp,
        *[dummy] * 6,
        robot,
        *[dummy] * 14,
    )
    tool = mcp._tool_manager._tools["robot_probe_arm_profiles"]

    payload = json.loads(
        await tool.fn(
            profile_names=["franka_panda"],
            family_filter=["franka"],
            limit=1,
            safe_nudge=False,
        )
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["profile_names"] == ["franka_panda"]
    assert data["mcp_controllability_counts"] == {"dynamic_joint_read_only": 1}
    assert data["mcp_controllability_profiles"] == {
        "dynamic_joint_read_only": ["franka_panda"]
    }
    assert data["probe_capability_level_name_counts"] == {
        "dynamic_joint_read": 1
    }
    assert data["probe_capability_level_name_profiles"] == {
        "dynamic_joint_read": ["franka_panda"]
    }
    assert data["pick_place_validation_status_counts"] == {
        "known_pick_place_blocker": 1
    }
    assert data["pick_place_validation_status_profiles"] == {
        "known_pick_place_blocker": ["franka_panda"]
    }
    assert data["unsupported_capability_counts"] == {
        "gripper": 1,
        "ee_pose": 1,
    }
    assert data["unsupported_capability_profiles"] == ["franka_panda"]
    assert data["ik_target_failure_profiles"] == []
    assert data["timed_out_profiles"] == []
    assert data["batch_timeout_profiles"] == []
    assert data["batch_aborted_profiles"] == []
    assert data["blocked_profiles"] == []
    assert data["hard_failure_profiles"] == []
    assert data["lifecycle_recovery_profiles"] == []
    assert data["known_dynamic_timeout_routed_profiles"] == []
    assert data["results"][0]["mcp_controllability"] == "dynamic_joint_read_only"
    assert data["results"][0]["probe_proves_pick_place"] is False
    assert (
        data["results"][0]["pick_place_validation_status"]
        == "known_pick_place_blocker"
    )


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_tool_preserves_empty_profile_names():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    mcp = FastMCP(name="test")
    dummy = SimpleNamespace()
    robot = RobotModule(client)
    register_module_tools(
        mcp,
        *[dummy] * 6,
        robot,
        *[dummy] * 14,
    )
    tool = mcp._tool_manager._tools["robot_probe_arm_profiles"]

    payload = json.loads(await tool.fn(profile_names=[]))

    assert payload["ok"] is True
    data = payload["data"]
    assert data["profile_names"] == []
    assert data["requested_count"] == 0
    assert data["count"] == 0
    assert data["results"] == []
    assert data["mcp_controllability_counts"] == {}
    assert client.calls == []
