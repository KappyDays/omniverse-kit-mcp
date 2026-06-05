"""Unit tests for ViewportModule."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.types.common import ModuleName, OperationMeta
from omniverse_kit_mcp.types.viewport import (
    SSIMComparisonRequest,
    ViewportCaptureRequest,
    ViewportFocusPrimRequest,
)
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def viewport_module(mock_client):
    return ViewportModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(request_id="test", module=ModuleName.VIEWPORT, started_at_epoch_ms=1000)


@pytest.mark.asyncio
async def test_capture_success(viewport_module, meta):
    result = await viewport_module.capture(meta, ViewportCaptureRequest())
    assert result.ok is True
    assert result.data is not None
    assert result.data.artifact_id == "test_img"
    assert "image" in result.artifacts


@pytest.mark.asyncio
async def test_ssim_pass(viewport_module, meta):
    result = await viewport_module.compare_ssim(
        meta,
        SSIMComparisonRequest(
            baseline_artifact_path="/tmp/a.png",
            candidate_artifact_path="/tmp/b.png",
            min_ssim=0.95,
        ),
    )
    assert result.ok is True
    assert result.data is not None
    assert result.data.score == 0.99


@pytest.mark.asyncio
async def test_ssim_fail(viewport_module, meta):
    viewport_module._client.responses["viewport_compare_ssim"] = {
        "score": 0.50,
        "passed": False,
    }
    result = await viewport_module.compare_ssim(
        meta,
        SSIMComparisonRequest(
            baseline_artifact_path="/tmp/a.png",
            candidate_artifact_path="/tmp/b.png",
            min_ssim=0.95,
        ),
    )
    assert result.ok is False
    assert result.data is not None
    assert result.data.score == 0.50


@pytest.mark.asyncio
async def test_capture_with_stats(viewport_module, meta):
    viewport_module._client.responses["viewport_capture"] = {
        "artifact_id": "img2", "path": "/tmp/x.png", "width": 1280, "height": 720,
        "sha256": "abc", "created_at_epoch_ms": 0,
        "pixel_mean": [3.1, 3.0, 3.2], "pixel_variance": [0.0, 0.0, 0.0],
        "warmup_frames_used": 8,
    }
    result = await viewport_module.capture(meta, ViewportCaptureRequest(warmup_frames=8, return_stats=True))
    assert result.ok is True
    assert result.data.pixel_mean == (3.1, 3.0, 3.2)
    assert result.data.warmup_frames_used == 8
    sent = dict(viewport_module._client.calls)["viewport_capture"]
    assert sent["warmup_frames"] == 8 and sent["return_stats"] is True


@pytest.mark.asyncio
async def test_set_camera_lookat(viewport_module, meta):
    from omniverse_kit_mcp.types.viewport import ViewportSetCameraLookatRequest
    result = await viewport_module.set_camera_lookat(
        meta,
        ViewportSetCameraLookatRequest(eye=(5, 5, 5), target=(0, 0, 0)),
    )
    assert result.ok is True
    assert result.data.camera_path == "/OmniverseKit_Persp"
    sent = dict(viewport_module._client.calls)["viewport_set_camera_lookat"]
    assert sent["eye"] == [5, 5, 5] and sent["up"] == [0.0, 0.0, 1.0]


@pytest.mark.asyncio
async def test_focus_prim(viewport_module, meta):
    result = await viewport_module.focus_prim(
        meta,
        ViewportFocusPrimRequest(
            prim_path="/World/Cube",
            viewport_name="Viewport",
            padding=1.5,
            select=True,
        ),
    )

    assert result.ok is True
    assert result.data is not None
    assert result.data.prim_path == "/World/Cube"
    assert result.data.camera_path == "/OmniverseKit_Persp"
    assert result.data.method == "frame_viewport_prims"
    sent = dict(viewport_module._client.calls)["viewport_focus_prim"]
    assert sent == {
        "prim_path": "/World/Cube",
        "viewport_name": "Viewport",
        "camera_path": None,
        "padding": 1.5,
        "select": True,
    }
