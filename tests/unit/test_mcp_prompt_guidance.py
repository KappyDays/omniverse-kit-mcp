from __future__ import annotations

from omniverse_kit_mcp.mcp.prompts import build_system_prompt


def test_isaac_prompt_guides_robot_control_to_scriptnode_loop():
    prompt = build_system_prompt("isaac-sim")

    assert "MCP tools operate between frames" in prompt
    assert "ScriptNode" in prompt
    assert "omnigraph_create_script_controller" in prompt
    assert "simulation_step_observe" in prompt
