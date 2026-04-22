"""Tests for reset_all action."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_reset_all_clears_state_and_calls_new_stage():
    services = MagicMock()
    services.stage.new_stage = AsyncMock()

    from omni.mycompany.isaac_tutorial.actions.state import TutorialState
    from omni.mycompany.isaac_tutorial.actions.env_actions import reset_all

    state = TutorialState(
        office_loaded=True, nova_carter_loaded=True,
        navigated=True, people_loaded=True,
        ceiling_hidden=True, ceiling_cache=["/a", "/b"],
        wasd_graph_path="/World/nova_carter/WASDGraph",
        sensor_writer_id="tutorial_writer",
        sensor_output_dir="/tmp/out",
        navmesh_viz_mode="walkable",
        chair_anchor_path="/World/office/Chair_01",
    )
    msg = await reset_all(services, state)

    services.stage.new_stage.assert_awaited_once()
    assert state.office_loaded is False
    assert state.nova_carter_loaded is False
    assert state.navigated is False
    assert state.people_loaded is False
    assert state.ceiling_hidden is False
    assert state.ceiling_cache == []
    assert state.wasd_graph_path is None
    assert state.sensor_writer_id is None
    assert state.sensor_output_dir is None
    assert state.navmesh_viz_mode == "off"
    assert state.chair_anchor_path is None
    assert "reset" in msg.lower()
