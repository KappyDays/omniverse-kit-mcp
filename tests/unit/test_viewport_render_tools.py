"""Unit tests for Viewport render extension (Phase F)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.viewport import (
    ViewportCaptureAssertRequest,
    ViewportCaptureAssertResult,
    ViewportFramePrimsRequest,
    ViewportFramePrimsResult,
    ViewportProjectPointsRequest,
    ViewportProjectPointsResult,
    ViewportSetFovRequest,
    ViewportSetFovResult,
    ViewportSetRenderModeRequest,
    ViewportSetRenderModeResult,
    ViewportSetRenderQualityRequest,
    ViewportSetRenderQualityResult,
    ViewportToggleOverlayRequest,
    ViewportToggleOverlayResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="test", module=ModuleName.VIEWPORT, started_at_epoch_ms=0,
    )


# --- Tool registration -----------------------------------------------------


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_viewport_render_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    for tool in (
        "viewport_set_render_mode",
        "viewport_set_render_quality",
        "viewport_toggle_overlay",
        "viewport_set_fov",
        "viewport_project_points",
        "viewport_frame_prims",
        "viewport_capture_assert",
    ):
        assert tool in names, f"{tool} not registered"


# --- Module unit tests -----------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["RealTime", "PathTracing"])
async def test_set_render_mode(mode):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportSetRenderModeRequest(viewport_name="Viewport", mode=mode)
    result = await module.set_render_mode(_meta(), request)

    assert result.ok
    assert isinstance(result.data, ViewportSetRenderModeResult)
    assert result.data.mode == mode


@pytest.mark.asyncio
@pytest.mark.parametrize("denoiser,expected_op", [
    ("auto", 3), ("DLSS", 4), ("NRD", 5), ("off", 0),
])
async def test_set_render_quality(denoiser, expected_op):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportSetRenderQualityRequest(samples=16, denoiser=denoiser)
    result = await module.set_render_quality(_meta(), request)

    assert result.ok
    assert isinstance(result.data, ViewportSetRenderQualityResult)
    assert result.data.samples == 16
    assert result.data.denoiser == denoiser
    assert result.data.aa_op == expected_op


@pytest.mark.asyncio
@pytest.mark.parametrize("overlay", ["gridlines", "axis", "stats"])
async def test_toggle_overlay(overlay):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportToggleOverlayRequest(
        viewport_name="Viewport", overlay=overlay, visible=True,
    )
    result = await module.toggle_overlay(_meta(), request)

    assert result.ok
    assert isinstance(result.data, ViewportToggleOverlayResult)
    assert result.data.overlay == overlay
    assert result.data.visible is True
    assert result.data.setting_path


@pytest.mark.asyncio
async def test_set_fov_returns_focal_length():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportSetFovRequest(viewport_name="Viewport", fov_deg=60.0)
    result = await module.set_fov(_meta(), request)

    assert result.ok
    assert isinstance(result.data, ViewportSetFovResult)
    assert result.data.fov_deg == 60.0
    assert result.data.focal_length > 0
    assert result.data.camera_path == "/OmniverseKit_Persp"


@pytest.mark.asyncio
async def test_project_points_returns_screen_coordinates():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportProjectPointsRequest(
        points=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        viewport_name="Viewport",
        width=640,
        height=480,
    )
    result = await module.project_points(_meta(), request)

    assert result.ok
    assert isinstance(result.data, ViewportProjectPointsResult)
    assert result.data.width == 640
    assert result.data.points[0].pixel_xy == (320.0, 240.0)
    assert client.calls[-1][0] == "viewport_project_points"


@pytest.mark.asyncio
async def test_frame_prims_returns_camera_pose():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportFramePrimsRequest(
        prim_paths=("/World/Cube",),
        viewport_name="Viewport",
        margin=0.2,
        set_camera=True,
    )
    result = await module.frame_prims(_meta(), request)

    assert result.ok
    assert isinstance(result.data, ViewportFramePrimsResult)
    assert result.data.prim_paths == ("/World/Cube",)
    assert result.data.eye[2] > result.data.target[2]
    assert client.calls[-1][0] == "viewport_frame_prims"


@pytest.mark.asyncio
async def test_capture_assert_fails_blank_frame():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["viewport_capture"] = {
        "artifact_id": "blank",
        "path": "/tmp/blank.png",
        "width": 1280,
        "height": 720,
        "sha256": "abc",
        "created_at_epoch_ms": 0,
        "pixel_mean": [0.0, 0.0, 0.0],
        "pixel_variance": [0.0, 0.0, 0.0],
    }
    module = ViewportModule(client)
    request = ViewportCaptureAssertRequest(min_mean=8.0, min_variance=1.0)
    result = await module.capture_assert(_meta(), request)

    assert result.ok is False
    assert isinstance(result.data, ViewportCaptureAssertResult)
    assert result.data.passed is False
    assert result.error_code == "VIEWPORT_CAPTURE_ASSERT_FAILED"
    assert result.data.failure_codes == (
        "PIXEL_MEAN_BELOW_THRESHOLD",
        "PIXEL_VARIANCE_BELOW_THRESHOLD",
    )
    assert result.data.diagnostics["reason"] == "capture_blank_or_flat"
    assert result.data.diagnostics["failure_codes"] == [
        "PIXEL_MEAN_BELOW_THRESHOLD",
        "PIXEL_VARIANCE_BELOW_THRESHOLD",
    ]
    assert result.data.diagnostics["pixel_mean_average"] == 0.0
    assert result.data.diagnostics["pixel_variance_average"] == 0.0
    assert result.data.diagnostics["min_mean"] == 8.0
    assert result.data.diagnostics["min_variance"] == 1.0
    assert result.data.diagnostics["fallback_tool_order"] == [
        "simulation_get_status",
        "viewport_frame_prims",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]
    assert any(
        "viewport_frame_prims" in item
        for item in result.data.diagnostics["suggested_next"]
    )


@pytest.mark.asyncio
async def test_set_render_mode_propagates_client_error():
    class BrokenClient:
        async def viewport_set_render_mode(self, _req):
            raise RuntimeError("rtx offline")

    module = ViewportModule(BrokenClient())  # type: ignore[arg-type]
    request = ViewportSetRenderModeRequest(
        viewport_name="Viewport", mode="RealTime",
    )
    result = await module.set_render_mode(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_SET_RENDER_MODE_ERROR"
