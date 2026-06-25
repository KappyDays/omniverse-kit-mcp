"""Unit tests for Viewport render extension (Phase F)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.viewport import (
    ImageArtifact,
    ViewportCaptureAssertRequest,
    ViewportCaptureAssertResult,
    ViewportCaptureRequest,
    ViewportFocusPrimRequest,
    ViewportFocusPrimResult,
    ViewportFramePrimsRequest,
    ViewportFramePrimsResult,
    ViewportProjectPointsRequest,
    ViewportProjectPointsResult,
    ViewportSetCameraLookatRequest,
    ViewportSetCameraLookatResult,
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
async def test_project_points_error_returns_typed_diagnostics():
    class BrokenProjectClient:
        async def viewport_project_points(self, _req):
            raise RuntimeError("projection unavailable")

    module = ViewportModule(BrokenProjectClient())  # type: ignore[arg-type]
    request = ViewportProjectPointsRequest(
        points=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        viewport_name="Viewport",
        camera_path="/World/Camera",
        width=640,
        height=480,
    )
    result = await module.project_points(_meta(), request)

    assert result.ok is False
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_PROJECT_POINTS_ERROR"
    assert isinstance(result.data, ViewportProjectPointsResult)
    assert result.data.ok is False
    assert result.data.points == ()
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_project_points_error"
    assert diagnostics["point_count"] == 2
    assert diagnostics["camera_path"] == "/World/Camera"
    assert diagnostics["fallback_tool_order"] == [
        "stage_capture_snapshot",
        "viewport_frame_prims",
        "viewport_project_points",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_frame_prims_returns_camera_pose():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["viewport_frame_prims"] = {
        "ok": True,
        "viewport_name": "Viewport",
        "camera_path": "/OmniverseKit_Persp",
        "prim_paths": ["/World/Cube"],
        "eye": [2.0, -1.0, 1.5],
        "target": [0.5, 0.5, 0.5],
        "up": [0.0, 0.0, 1.0],
        "fov_deg": 60.0,
        "distance": 2.0,
        "combined_bbox": {
            "min": [0.0, 0.0, 0.0],
            "max": [1.0, 1.0, 1.0],
            "center": [0.5, 0.5, 0.5],
            "size": [1.0, 1.0, 1.0],
            "is_empty": False,
        },
        "prim_bboxes": [],
        "diagnostics": {"source": "mock"},
    }
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
    assert result.data.diagnostics == {"source": "mock"}
    assert client.calls[-1][0] == "viewport_frame_prims"


@pytest.mark.asyncio
async def test_frame_prims_error_returns_typed_diagnostics():
    class BrokenFrameClient:
        async def viewport_frame_prims(self, _req):
            raise RuntimeError("camera framing unavailable")

    module = ViewportModule(BrokenFrameClient())  # type: ignore[arg-type]
    request = ViewportFramePrimsRequest(
        prim_paths=("/World/Robot", "/World/Lidar"),
        viewport_name="Viewport",
        camera_path="/World/Camera",
        set_camera=True,
    )
    result = await module.frame_prims(_meta(), request)

    assert result.ok is False
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_FRAME_PRIMS_ERROR"
    assert isinstance(result.data, ViewportFramePrimsResult)
    assert result.data.ok is False
    assert result.data.viewport_name == "Viewport"
    assert result.data.camera_path == "/World/Camera"
    assert result.data.prim_paths == ("/World/Robot", "/World/Lidar")
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_frame_prims_error"
    assert diagnostics["upstream_error_code"] == "VIEWPORT_FRAME_PRIMS_ERROR"
    assert diagnostics["upstream_message"] == "camera framing unavailable"
    assert diagnostics["prim_paths"] == ["/World/Robot", "/World/Lidar"]
    assert diagnostics["fallback_tool_order"] == [
        "stage_capture_snapshot",
        "simulation_get_status",
        "viewport_frame_prims",
        "extension_capture_logs",
    ]
    assert any("stage_capture_snapshot" in item for item in diagnostics["suggested_next"])


@pytest.mark.asyncio
async def test_set_camera_lookat_error_returns_typed_diagnostics():
    class BrokenLookatClient:
        async def viewport_set_camera_lookat(self, _req):
            raise RuntimeError("lookat failed")

    module = ViewportModule(BrokenLookatClient())  # type: ignore[arg-type]
    request = ViewportSetCameraLookatRequest(
        eye=(1.0, -2.0, 3.0),
        target=(0.0, 0.0, 0.5),
        up=(0.0, 0.0, 1.0),
        viewport_name="Viewport",
        camera_path="/World/Camera",
    )
    result = await module.set_camera_lookat(_meta(), request)

    assert result.ok is False
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_SET_CAMERA_LOOKAT_ERROR"
    assert isinstance(result.data, ViewportSetCameraLookatResult)
    assert result.data.ok is False
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_set_camera_lookat_error"
    assert diagnostics["eye"] == [1.0, -2.0, 3.0]
    assert diagnostics["target"] == [0.0, 0.0, 0.5]
    assert diagnostics["fallback_tool_order"] == [
        "stage_capture_snapshot",
        "simulation_get_status",
        "viewport_set_camera_lookat",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_focus_prim_error_returns_typed_diagnostics():
    class BrokenFocusClient:
        async def viewport_focus_prim(self, _req):
            raise RuntimeError("focus failed")

    module = ViewportModule(BrokenFocusClient())  # type: ignore[arg-type]
    request = ViewportFocusPrimRequest(
        prim_path="/World/Robot",
        viewport_name="Viewport",
        camera_path="/World/Camera",
        padding=1.5,
        select=True,
    )
    result = await module.focus_prim(_meta(), request)

    assert result.ok is False
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_FOCUS_PRIM_ERROR"
    assert isinstance(result.data, ViewportFocusPrimResult)
    assert result.data.ok is False
    assert result.data.prim_path == "/World/Robot"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_focus_prim_error"
    assert diagnostics["prim_path"] == "/World/Robot"
    assert diagnostics["padding"] == 1.5
    assert diagnostics["fallback_tool_order"] == [
        "stage_capture_snapshot",
        "stage_compute_world_bbox",
        "simulation_get_status",
        "viewport_focus_prim",
        "viewport_frame_prims",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_capture_error_returns_typed_diagnostics():
    class BrokenCaptureClient:
        async def viewport_capture(self, _req):
            raise RuntimeError("viewport unavailable")

    module = ViewportModule(BrokenCaptureClient())  # type: ignore[arg-type]
    request = ViewportCaptureRequest(
        viewport_name="Viewport",
        camera_prim_path="/World/Camera",
        renderer="rtx",
        width=640,
        height=480,
        warmup_frames=2,
        return_stats=True,
    )
    result = await module.capture(_meta(), request)

    assert result.ok is False
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_CAPTURE_ERROR"
    assert isinstance(result.data, ImageArtifact)
    assert result.data.path == ""
    assert result.data.width == 640
    assert result.data.height == 480
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_capture_error"
    assert diagnostics["upstream_error_code"] == "VIEWPORT_CAPTURE_ERROR"
    assert diagnostics["upstream_message"] == "viewport unavailable"
    assert diagnostics["camera_prim_path"] == "/World/Camera"
    assert diagnostics["warmup_frames"] == 2
    assert diagnostics["return_stats"] is True
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "viewport_frame_prims",
        "viewport_capture",
        "extension_capture_logs",
    ]


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
async def test_capture_assert_surfaces_capture_error_diagnostics():
    class BrokenCaptureClient:
        async def viewport_capture(self, _req):
            raise RuntimeError("viewport unavailable")

    module = ViewportModule(BrokenCaptureClient())  # type: ignore[arg-type]
    request = ViewportCaptureAssertRequest(min_mean=8.0, min_variance=1.0)
    result = await module.capture_assert(_meta(), request)

    assert result.ok is False
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_CAPTURE_ERROR"
    assert isinstance(result.data, ViewportCaptureAssertResult)
    assert result.data.passed is False
    assert result.data.artifact is None
    assert result.data.failure_codes == ("VIEWPORT_CAPTURE_ERROR",)
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "capture_error"
    assert diagnostics["failure_codes"] == ["VIEWPORT_CAPTURE_ERROR"]
    assert diagnostics["upstream_error_code"] == "VIEWPORT_CAPTURE_ERROR"
    assert diagnostics["upstream_message"] == "viewport unavailable"
    assert diagnostics["pixel_mean_average"] is None
    assert diagnostics["pixel_variance_average"] is None
    assert diagnostics["min_mean"] == 8.0
    assert diagnostics["min_variance"] == 1.0
    assert diagnostics["fallback_tool_order"] == [
        "simulation_get_status",
        "viewport_frame_prims",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]
    assert any(
        "simulation_get_status" in item
        for item in diagnostics["suggested_next"]
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
    assert isinstance(result.data, ViewportSetRenderModeResult)
    assert result.data.ok is False
    assert result.data.mode == "RealTime"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_set_render_mode_error"
    assert diagnostics["tool_name"] == "viewport_set_render_mode"
    assert diagnostics["upstream_error_code"] == "VIEWPORT_SET_RENDER_MODE_ERROR"
    assert diagnostics["upstream_message"] == "rtx offline"
    assert diagnostics["request"] == {"viewport_name": "Viewport", "mode": "RealTime"}
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "viewport_set_render_mode",
        "viewport_set_render_quality",
        "viewport_toggle_overlay",
        "viewport_set_fov",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_set_render_quality_error_returns_typed_diagnostics():
    class BrokenClient:
        async def viewport_set_render_quality(self, _req):
            raise RuntimeError("quality rejected")

    module = ViewportModule(BrokenClient())  # type: ignore[arg-type]
    request = ViewportSetRenderQualityRequest(samples=32, denoiser="DLSS")
    result = await module.set_render_quality(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_SET_RENDER_QUALITY_ERROR"
    assert isinstance(result.data, ViewportSetRenderQualityResult)
    assert result.data.samples == 32
    assert result.data.denoiser == "DLSS"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_set_render_quality_error"
    assert diagnostics["request"] == {"samples": 32, "denoiser": "DLSS"}
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "viewport_set_render_mode",
        "viewport_set_render_quality",
        "viewport_toggle_overlay",
        "viewport_set_fov",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_toggle_overlay_error_returns_typed_diagnostics():
    class BrokenClient:
        async def viewport_toggle_overlay(self, _req):
            raise RuntimeError("overlay setting unavailable")

    module = ViewportModule(BrokenClient())  # type: ignore[arg-type]
    request = ViewportToggleOverlayRequest(
        viewport_name="Viewport", overlay="stats", visible=False,
    )
    result = await module.toggle_overlay(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_TOGGLE_OVERLAY_ERROR"
    assert isinstance(result.data, ViewportToggleOverlayResult)
    assert result.data.overlay == "stats"
    assert result.data.visible is False
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_toggle_overlay_error"
    assert diagnostics["request"] == {
        "viewport_name": "Viewport",
        "overlay": "stats",
        "visible": False,
    }
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "viewport_set_render_mode",
        "viewport_set_render_quality",
        "viewport_toggle_overlay",
        "viewport_set_fov",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_set_fov_error_returns_typed_diagnostics():
    class BrokenClient:
        async def viewport_set_fov(self, _req):
            raise RuntimeError("camera unavailable")

    module = ViewportModule(BrokenClient())  # type: ignore[arg-type]
    request = ViewportSetFovRequest(viewport_name="Viewport", fov_deg=42.0)
    result = await module.set_fov(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_SET_FOV_ERROR"
    assert isinstance(result.data, ViewportSetFovResult)
    assert result.data.fov_deg == pytest.approx(42.0)
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_set_fov_error"
    assert diagnostics["upstream_message"] == "camera unavailable"
    assert diagnostics["request"] == {"viewport_name": "Viewport", "fov_deg": 42.0}
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "viewport_set_render_mode",
        "viewport_set_render_quality",
        "viewport_toggle_overlay",
        "viewport_set_fov",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]
