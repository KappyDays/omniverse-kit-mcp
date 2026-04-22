"""Tests for TutorialState + stage-based recovery."""

from __future__ import annotations

from unittest.mock import MagicMock

from omni.mycompany.isaac_tutorial.actions.state import (
    TutorialState, recover_state_from_stage,
)


def test_default_state_all_false():
    s = TutorialState()
    assert s.office_loaded is False
    assert s.nova_carter_loaded is False
    assert s.navigated is False
    assert s.people_loaded is False
    assert s.ceiling_hidden is False
    assert s.ceiling_cache == []
    assert s.wasd_graph_path is None
    assert s.active_job_ids == {}
    assert s.navmesh_viz_mode == "off"
    assert s.camera_speed == 0.1
    assert s.sensor_writer_id is None
    assert s.sensor_output_dir is None
    assert s.chair_anchor_path is None


def _mock_stage(prim_paths):
    stage = MagicMock()

    def _get_prim(path):
        prim = MagicMock()
        prim.IsValid.return_value = path in prim_paths
        return prim
    stage.GetPrimAtPath.side_effect = _get_prim

    def _traverse():
        for path in prim_paths:
            p = MagicMock()
            p.GetPath.return_value = path
            p.GetName.return_value = path.rsplit("/", 1)[-1]
            yield p
    stage.Traverse.side_effect = _traverse
    return stage


def test_recover_from_stage_with_office_and_nova():
    stage = _mock_stage([
        "/World/office",
        "/World/nova_carter",
    ])
    state = recover_state_from_stage(stage)
    assert state.office_loaded is True
    assert state.nova_carter_loaded is True
    assert state.people_loaded is False


def test_recover_from_stage_empty():
    stage = _mock_stage([])
    state = recover_state_from_stage(stage)
    assert state.office_loaded is False
    assert state.nova_carter_loaded is False
    assert state.people_loaded is False


def test_recover_detects_people_under_Characters():
    stage = _mock_stage([
        "/World/Characters/Biped_01",
    ])
    state = recover_state_from_stage(stage)
    assert state.people_loaded is True
