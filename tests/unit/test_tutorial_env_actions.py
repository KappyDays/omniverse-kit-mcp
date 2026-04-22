"""Tests for env_actions — scale / camera_speed / ceiling_toggle."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from omni.mycompany.isaac_tutorial.actions.state import TutorialState


# ---------- T6: scale_selected ----------

def _stage_with_scale(scales: dict) -> MagicMock:
    stage = MagicMock()

    def _get_prim(path):
        prim = MagicMock()
        prim.IsValid.return_value = path in scales
        attr = MagicMock()
        attr.IsValid.return_value = True
        attr.Get.return_value = scales.get(path, (1.0, 1.0, 1.0))
        prim.GetAttribute.return_value = attr
        return prim
    stage.GetPrimAtPath.side_effect = _get_prim
    return stage


@patch("omni.mycompany.isaac_tutorial.actions.env_actions.omni.kit.commands.execute")
@patch("omni.mycompany.isaac_tutorial.actions.env_actions.omni.usd.get_context")
def test_scale_selected_multiplies(mock_ctx, mock_exec):
    mock_sel = MagicMock()
    mock_sel.get_selected_prim_paths.return_value = ["/World/foo", "/World/bar"]
    mock_ctx.return_value.get_selection.return_value = mock_sel
    mock_ctx.return_value.get_stage.return_value = _stage_with_scale({
        "/World/foo": (1.0, 1.0, 1.0),
        "/World/bar": (2.0, 2.0, 2.0),
    })

    from omni.mycompany.isaac_tutorial.actions.env_actions import scale_selected
    msg = scale_selected(factor=10.0)

    assert mock_exec.call_count == 2
    assert "Scaled 2 prim(s) by 10" in msg


@patch("omni.mycompany.isaac_tutorial.actions.env_actions.omni.usd.get_context")
def test_scale_selected_raises_when_nothing_selected(mock_ctx):
    mock_sel = MagicMock()
    mock_sel.get_selected_prim_paths.return_value = []
    mock_ctx.return_value.get_selection.return_value = mock_sel

    from omni.mycompany.isaac_tutorial.actions.env_actions import scale_selected
    with pytest.raises(ValueError, match="선택"):
        scale_selected(factor=10.0)


# ---------- T7: set_camera_speed ----------

@patch("omni.mycompany.isaac_tutorial.actions.env_actions.carb.settings.get_settings")
def test_set_camera_speed_writes_carb_setting(mock_get_settings):
    settings = MagicMock()
    mock_get_settings.return_value = settings

    from omni.mycompany.isaac_tutorial.actions.env_actions import set_camera_speed
    msg = set_camera_speed(0.5)

    settings.set.assert_called_once()
    key, value = settings.set.call_args[0]
    assert "navigation" in key.lower() or "cam" in key.lower() or "viewport" in key.lower()
    assert value == 0.5
    assert "0.5" in msg


def test_set_camera_speed_rejects_out_of_range():
    from omni.mycompany.isaac_tutorial.actions.env_actions import set_camera_speed
    with pytest.raises(ValueError):
        set_camera_speed(-1.0)
    with pytest.raises(ValueError):
        set_camera_speed(100.0)


# ---------- T8: toggle_ceiling_visibility ----------

def _make_prim(path: str, name: str):
    p = MagicMock()
    p.GetPath.return_value = path
    p.GetName.return_value = name
    return p


@patch("omni.mycompany.isaac_tutorial.actions.env_actions.UsdGeom.Imageable")
@patch("omni.mycompany.isaac_tutorial.actions.env_actions.omni.usd.get_context")
def test_toggle_ceiling_hides_and_caches(mock_ctx, mock_imageable):
    stage = MagicMock()
    stage.Traverse.return_value = [
        _make_prim("/World/office/Ceiling_01", "Ceiling_01"),
        _make_prim("/World/office/Wall_01", "Wall_01"),
        _make_prim("/World/office/ceiling_tile_03", "ceiling_tile_03"),
    ]
    # GetPrimAtPath returns a valid prim
    stage.GetPrimAtPath.return_value = MagicMock(IsValid=lambda: True)
    mock_ctx.return_value.get_stage.return_value = stage
    # Imageable(prim) returns a truthy object with MakeInvisible/MakeVisible
    mock_imageable.return_value = MagicMock()

    state = TutorialState()
    from omni.mycompany.isaac_tutorial.actions.env_actions import toggle_ceiling_visibility
    msg = toggle_ceiling_visibility(state)

    assert state.ceiling_hidden is True
    assert len(state.ceiling_cache) == 2
    assert sorted(state.ceiling_cache) == [
        "/World/office/Ceiling_01", "/World/office/ceiling_tile_03",
    ]
    assert "Hid 2" in msg


@patch("omni.mycompany.isaac_tutorial.actions.env_actions.UsdGeom.Imageable")
@patch("omni.mycompany.isaac_tutorial.actions.env_actions.omni.usd.get_context")
def test_toggle_ceiling_restores_on_second_call(mock_ctx, mock_imageable):
    stage = MagicMock()
    stage.GetPrimAtPath.return_value = MagicMock(IsValid=lambda: True)
    mock_ctx.return_value.get_stage.return_value = stage
    mock_imageable.return_value = MagicMock()

    state = TutorialState(
        ceiling_hidden=True,
        ceiling_cache=["/World/office/Ceiling_01", "/World/office/ceiling_tile_03"],
    )
    from omni.mycompany.isaac_tutorial.actions.env_actions import toggle_ceiling_visibility
    msg = toggle_ceiling_visibility(state)

    assert state.ceiling_hidden is False
    assert state.ceiling_cache == []
    assert "Restored 2" in msg
