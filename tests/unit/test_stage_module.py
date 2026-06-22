"""Unit tests for StageModule."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.stage_module import StageModule, _compute_diff, _parse_snapshot
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.stage import (
    DiffKind,
    PrimExistenceAssertion,
    PrimSpec,
    PropertyAssertion,
    StageCaptureFilter,
    StagePlacementValidationRequest,
    StageSnapshot,
    StageVisualAlignmentRequest,
    StageWorldBboxRequest,
    UsdPropertyValue,
)
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def stage_module(mock_client):
    return StageModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(request_id="test", module=ModuleName.STAGE, started_at_epoch_ms=1000)


@pytest.mark.asyncio
async def test_capture_snapshot_success(stage_module, meta, snapshot_after_raw):
    stage_module._client.responses["stage_snapshot"] = snapshot_after_raw
    result = await stage_module.capture_snapshot(meta, StageCaptureFilter())
    assert result.ok is True
    assert result.status == ExecutionStatus.PASSED
    assert result.data is not None
    assert "/World/Cube" in result.data.prims


@pytest.mark.asyncio
async def test_assert_prim_exists_pass(stage_module, meta):
    result = await stage_module.assert_prim_exists(
        meta, PrimExistenceAssertion(prim_path="/World/Cube")
    )
    assert result.ok is True


@pytest.mark.asyncio
async def test_assert_prim_exists_fail(stage_module, meta):
    stage_module._client.responses["stage_assert_prim_exists"] = {
        "passed": False,
        "failures": [{"code": "PRIM_NOT_FOUND", "message": "Prim not found", "prim_path": "/World/Missing"}],
        "checked_count": 1,
    }
    result = await stage_module.assert_prim_exists(
        meta, PrimExistenceAssertion(prim_path="/World/Missing")
    )
    assert result.ok is False
    assert result.data is not None
    assert result.data.passed is False
    assert len(result.data.failures) == 1


@pytest.mark.asyncio
async def test_assert_property_approx(stage_module, meta):
    result = await stage_module.assert_property(
        meta,
        PropertyAssertion(
            prim_path="/World/Cube",
            property_name="xformOp:translate",
            comparator="approx",
            expected=UsdPropertyValue(type_name="double3", value=[0, 0, 0]),
            tolerance=0.001,
        ),
    )
    assert result.ok is True


def test_compute_diff_detects_prim_added(snapshot_before_raw, snapshot_after_raw):
    before = _parse_snapshot(snapshot_before_raw, StageCaptureFilter())
    after = _parse_snapshot(snapshot_after_raw, StageCaptureFilter())
    entries = _compute_diff(before, after)
    prim_added = [e for e in entries if e.kind == DiffKind.PRIM_ADDED]
    assert len(prim_added) == 1
    assert prim_added[0].prim_path == "/World/Cube"


def test_compute_diff_detects_prim_changed():
    """M-4: Detect PRIM_CHANGED when active/type_name changes."""
    before_prim = PrimSpec(
        path="/World/Obj", type_name="Cube", active=True, defined=True,
        instanceable=False, properties={}, relationships={}, metadata={},
    )
    after_prim = PrimSpec(
        path="/World/Obj", type_name="Sphere", active=False, defined=True,
        instanceable=False, properties={}, relationships={}, metadata={},
    )
    before = StageSnapshot(
        root_layer_identifier="", stage_identifier="", default_prim=None,
        prims={"/World/Obj": before_prim}, captured_at_epoch_ms=0,
        capture_filter=StageCaptureFilter(),
    )
    after = StageSnapshot(
        root_layer_identifier="", stage_identifier="", default_prim=None,
        prims={"/World/Obj": after_prim}, captured_at_epoch_ms=0,
        capture_filter=StageCaptureFilter(),
    )
    entries = _compute_diff(before, after)
    prim_changed = [e for e in entries if e.kind == DiffKind.PRIM_CHANGED]
    assert len(prim_changed) == 1
    assert "type_name" in prim_changed[0].details
    assert "active" in prim_changed[0].details


def test_parse_snapshot_converts_properties(snapshot_after_raw):
    snapshot = _parse_snapshot(snapshot_after_raw, StageCaptureFilter())
    cube = snapshot.prims["/World/Cube"]
    assert "size" in cube.properties
    assert cube.properties["size"].type_name == "double"
    assert cube.properties["size"].value == 1.0


@pytest.mark.asyncio
async def test_compute_world_bbox(stage_module, meta):
    stage_module._client.responses["stage_compute_world_bbox"] = {
        "ok": True,
        "prim_path": "/World/Cube",
        "min": [0.0, 0.0, 0.0],
        "max": [1.0, 2.0, 3.0],
        "center": [0.5, 1.0, 1.5],
        "size": [1.0, 2.0, 3.0],
        "world_translate": [0.0, 0.0, 0.0],
        "world_orient_wxyz": [1.0, 0.0, 0.0, 0.0],
        "is_empty": False,
    }

    result = await stage_module.compute_world_bbox(
        meta, StageWorldBboxRequest(prim_path="/World/Cube")
    )

    assert result.ok is True
    assert result.data is not None
    assert result.data.center == (0.5, 1.0, 1.5)
    assert stage_module._client.calls[-1] == (
        "stage_compute_world_bbox",
        {"prim_path": "/World/Cube", "include_purposes": ["default", "render"]},
    )


@pytest.mark.asyncio
async def test_visual_alignment_report_flags_xy_iou_failure(stage_module, meta):
    stage_module._client.responses["stage_compute_world_bbox_sequence"] = [
        {
            "ok": True,
            "prim_path": "/World/Reference",
            "min": [0.0, 0.0, 0.0],
            "max": [1.0, 1.0, 1.0],
            "center": [0.5, 0.5, 0.5],
            "size": [1.0, 1.0, 1.0],
            "world_translate": [0.0, 0.0, 0.0],
            "world_orient_wxyz": [1.0, 0.0, 0.0, 0.0],
            "is_empty": False,
        },
        {
            "ok": True,
            "prim_path": "/World/Candidate",
            "min": [2.0, 2.0, 0.0],
            "max": [3.0, 3.0, 1.0],
            "center": [2.5, 2.5, 0.5],
            "size": [1.0, 1.0, 1.0],
            "world_translate": [0.0, 0.0, 0.0],
            "world_orient_wxyz": [1.0, 0.0, 0.0, 0.0],
            "is_empty": False,
        },
    ]

    result = await stage_module.visual_alignment_report(
        meta,
        StageVisualAlignmentRequest(
            reference_prim_path="/World/Reference",
            candidate_prim_paths=("/World/Candidate",),
            min_iou_xy=0.1,
            max_center_delta_m=0.25,
        ),
    )

    assert result.ok is False
    assert result.data is not None
    assert result.data.passed is False
    assert result.data.entries[0].iou_xy == 0.0
    assert "IOU_XY_BELOW_THRESHOLD" in result.data.entries[0].failure_codes


@pytest.mark.asyncio
async def test_placement_validation_report_flags_outside_container(stage_module, meta):
    stage_module._client.responses["stage_placement_validate"] = {
        "ok": True,
        "passed": False,
        "checked_count": 1,
        "approximation": "world_aabb",
        "container_bbox": {
            "ok": True,
            "prim_path": "/World/Validation/WarehouseInterior",
            "min": [0.0, 0.0, 0.0],
            "max": [5.0, 5.0, 3.0],
            "center": [2.5, 2.5, 1.5],
            "size": [5.0, 5.0, 3.0],
            "world_translate": [0.0, 0.0, 0.0],
            "world_orient_wxyz": [1.0, 0.0, 0.0, 0.0],
            "is_empty": False,
        },
        "support_bbox": None,
        "obstacle_bboxes": [],
        "settings": {
            "checks": ["containment"],
            "containment_axes": ["x", "y"],
            "margin_m": 0.1,
        },
        "entries": [{
            "subject_prim_path": "/World/Forklift",
            "passed": False,
            "failure_codes": ["OUTSIDE_CONTAINER"],
            "bbox": {
                "ok": True,
                "prim_path": "/World/Forklift",
                "min": [4.8, 1.0, 0.0],
                "max": [5.8, 2.0, 1.5],
                "center": [5.3, 1.5, 0.75],
                "size": [1.0, 1.0, 1.5],
                "world_translate": [5.3, 1.5, 0.75],
                "world_orient_wxyz": [1.0, 0.0, 0.0, 0.0],
                "is_empty": False,
            },
            "prim": {
                "prim_path": "/World/Forklift",
                "valid": True,
                "type_name": "Xform",
                "active": True,
                "defined": True,
                "loaded": True,
                "instanceable": True,
                "variant_selections": {},
            },
            "checks": {
                "containment": {
                    "passed": False,
                    "axes": ["x", "y"],
                    "margin_m": 0.1,
                    "overruns_m": {
                        "x": {"below_min_m": 0.0, "above_max_m": 0.9},
                        "y": {"below_min_m": 0.0, "above_max_m": 0.0},
                    },
                },
            },
        }],
    }

    result = await stage_module.placement_validation_report(
        meta,
        StagePlacementValidationRequest(
            subject_prim_paths=("/World/Forklift",),
            container_prim_path="/World/Validation/WarehouseInterior",
            checks=("containment",),
            containment_axes=("x", "y"),
            margin_m=0.1,
        ),
    )

    assert result.ok is False
    assert result.error_code == "STAGE_PLACEMENT_VALIDATION_FAILED"
    assert result.data is not None
    assert result.data.approximation == "world_aabb"
    assert result.data.container_bbox is not None
    assert result.data.entries[0].bbox is not None
    assert "OUTSIDE_CONTAINER" in result.data.entries[0].failure_codes
    assert stage_module._client.calls[-1] == (
        "stage_placement_validate",
        {
            "subject_prim_paths": ["/World/Forklift"],
            "container_prim_path": "/World/Validation/WarehouseInterior",
            "support_prim_path": None,
            "obstacle_prim_paths": [],
            "checks": ["containment"],
            "include_purposes": ["default", "render"],
            "containment_axes": ["x", "y"],
            "margin_m": 0.1,
            "min_clearance_m": 0.0,
            "floor_tolerance_m": 0.01,
            "floor_axis": "z",
        },
    )
