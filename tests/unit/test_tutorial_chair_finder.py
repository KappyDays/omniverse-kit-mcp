"""Tests for _find_nearest_chair helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_prim(path: str, name: str):
    p = MagicMock()
    p.GetPath.return_value = path
    p.GetName.return_value = name
    return p


@pytest.mark.asyncio
@patch("omni.mycompany.isaac_tutorial.actions.step_actions.omni.usd.get_context")
async def test_find_nearest_chair_picks_closest(mock_ctx):
    stage = MagicMock()
    stage.Traverse.return_value = [
        _make_prim("/World/office/Armchair_far", "Armchair_far"),
        _make_prim("/World/office/Chair_near", "Chair_near"),
        _make_prim("/World/office/Desk_01", "Desk_01"),
    ]
    mock_ctx.return_value.get_stage.return_value = stage

    services = MagicMock()

    async def _bbox(path):
        # compute_world_bbox returns a dict with 'center' key (not an object attr)
        if "far" in path:
            return {"center": [20.0, 0.0, 0.0]}
        return {"center": [1.0, 0.0, 0.0]}

    services.stage.compute_world_bbox = AsyncMock(side_effect=_bbox)

    from omni.mycompany.isaac_tutorial.actions.step_actions import _find_nearest_chair
    path, center = await _find_nearest_chair(services, start=(0.0, 0.0, 0.0))
    assert path == "/World/office/Chair_near"
    # Converted from list to tuple by _find_nearest_chair
    assert tuple(center) == (1.0, 0.0, 0.0)


@pytest.mark.asyncio
@patch("omni.mycompany.isaac_tutorial.actions.step_actions.omni.usd.get_context")
async def test_find_nearest_chair_fallback_when_none(mock_ctx):
    stage = MagicMock()
    stage.Traverse.return_value = [
        _make_prim("/World/office/Desk_01", "Desk_01"),
    ]
    mock_ctx.return_value.get_stage.return_value = stage
    services = MagicMock()

    from omni.mycompany.isaac_tutorial.actions.step_actions import _find_nearest_chair
    path, center = await _find_nearest_chair(services, start=(0.0, 0.0, 0.0))
    assert path == ""
    assert center == (-10.0, -15.0, 0.0)
