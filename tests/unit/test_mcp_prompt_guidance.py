from __future__ import annotations

from omniverse_kit_mcp.mcp.prompts import build_system_prompt


def test_isaac_prompt_guides_robot_control_to_scriptnode_loop():
    prompt = build_system_prompt("isaac-sim")

    assert "MCP tools operate between frames" in prompt
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
