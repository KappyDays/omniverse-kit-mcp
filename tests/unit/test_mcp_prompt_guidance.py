from __future__ import annotations

from omniverse_kit_mcp.mcp.prompts import build_system_prompt


def test_isaac_prompt_guides_robot_control_to_scriptnode_loop():
    prompt = build_system_prompt("isaac-sim")

    assert "MCP tools operate between frames" in prompt
    assert "robot_list_arm_profiles" in prompt
    assert "robot_probe_arm_profile" in prompt
    assert "robot_probe_arm_profiles" in prompt
    assert "dynamic_probe_recommended_profiles" in prompt
    assert "static_only_probe_recommended_profiles" in prompt
    assert "recommended_probe_mode_by_profile" in prompt
    assert "recommended_probe_mode_reasons" in prompt
    assert "known_dynamic_timeout_profiles" in prompt
    assert "known_dynamic_timeout_profile_reasons" in prompt
    assert "known_pick_place_blocker_profiles" in prompt
    assert "known_pick_place_blocker_profile_reasons" in prompt
    assert "static-only hazard rows" in prompt
    assert "does not promote" in prompt
    assert "mcp_controllability" in prompt
    assert "probe_capability_level" in prompt
    assert "capped below durable" in prompt
    assert "probe_proves_pick_place=false" in prompt
    assert "pick_place_validation_status" in prompt
    assert "pick_place_validation_reason" in prompt
    assert "dynamic_joint_control" in prompt
    assert "blocked_*" in prompt
    assert "dynamic_checks=false" in prompt
    assert "static_only_for_known_dynamic_timeouts=true" in prompt
    assert "mcp_controllability_counts" in prompt
    assert "mcp_controllability_profiles" in prompt
    assert "probe_capability_level_name_counts" in prompt
    assert "probe_capability_level_name_profiles" in prompt
    assert "unsupported_capability_counts" in prompt
    assert "timed_out_profiles" in prompt
    assert "batch_timeout_profiles" in prompt
    assert "batch_aborted_profiles" in prompt
    assert "blocked_profiles" in prompt
    assert "hard_failure_profiles" in prompt
    assert "lifecycle_recovery_profiles" in prompt
    assert "ik_target_failure_profiles" in prompt
    assert "pick_place_validation_status_counts" in prompt
    assert "pick_place_validation_status_profiles" in prompt
    assert "known_dynamic_timeout_routed_profiles" in prompt
    assert "profile_names=[...]" in prompt
    assert "exact ordered small-batch reruns" in prompt
    assert "explicit empty list selects no profiles" in prompt
    assert "not a shorthand for the full catalog" in prompt
    assert "partial evidence" in prompt
    assert "validated_pick_place" in prompt
    assert "robot_install_pick_place_playback_demo" in prompt
    assert "`franka_fr3` is the current validated" in prompt
    assert "`franka_panda` is a candidate with a known repeatability blocker" in prompt
    assert "Candidate, IK-only, and profile-only" in prompt
    assert "arms return an explicit" in prompt
    assert "known-unvalidated playback paths" in prompt
    assert "diagnostics.known_pick_place_blocker" in prompt
    assert "diagnostics.known_pick_place_blocker_reason" in prompt
    assert "unsupported" in prompt
    assert "robot_get_pick_place_demo_status" in prompt
    assert "timeout_s" in prompt
    assert "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT" in prompt
    assert "host-degrading" in prompt
    assert "offset recommendations" in prompt
    assert "mcp_runtime_info" in prompt
    assert "restart the MCP host" in prompt
    assert "source_newer_than_import=true" in prompt
    assert "restart_required_for_latest_mcp_code=true" in prompt
    assert "stale-MCP blocker" in prompt
    assert "object_fit_ok" in prompt
    assert "object_fit_limit_m" in prompt
    assert "stop before Play cycles" in prompt
    assert "robot_run_franka_pick_place" in prompt
    assert "PickPlaceController" in prompt
    assert "RMPFlowController" in prompt
    assert "ParallelGripper" in prompt
    assert "does not kinematically carry" in prompt
    assert "bbox-based lift" in prompt
    assert "hover height is absolute world Z" in prompt
    assert "end_effector_initial_height_source" in prompt
    assert "picking_position" in prompt
    assert "end_effector_orientation" in prompt
    assert "ScriptNode" in prompt
    assert "omnigraph_create_script_controller" in prompt
    assert "telemetry alone" in prompt
    assert "viewport images" in prompt
    assert "stage_compute_world_bbox" in prompt
    assert "simulation_step_observe" in prompt


def test_prompt_points_to_scenario_resources_not_removed_tools():
    prompt = build_system_prompt("isaac-sim")

    assert "isaacsim://scenarios" in prompt
    assert "isaacsim://scenario-schema" in prompt
    assert "Use `scenario_list`" not in prompt
    assert "Use `scenario_schema`" not in prompt
