"""Unit tests for Viewport render extension (Phase F)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.viewport import (
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
