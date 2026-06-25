"""Unit tests for viewport_create / viewport_destroy (Phase E multi-viewport)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.viewport import (
    ViewportCreateRequest,
    ViewportCreateResult,
    ViewportDestroyRequest,
    ViewportDestroyResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(request_id="test", module=ModuleName.VIEWPORT, started_at_epoch_ms=0)


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_viewport_multi_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "viewport_create" in names
    assert "viewport_destroy" in names


@pytest.mark.asyncio
async def test_viewport_create_binds_camera():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportCreateRequest(
        viewport_name="Viewport_Lidar",
        camera_path="/World/Robot/NovaCarter/TopLidar",
        width=960,
        height=540,
        docked=False,
    )
    result = await module.create(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, ViewportCreateResult)
    assert result.data.viewport_name == "Viewport_Lidar"
    assert result.data.camera_path == "/World/Robot/NovaCarter/TopLidar"
    assert result.data.width == 960
    assert result.data.height == 540
    assert result.data.docked is False

    calls = [c for c in client.calls if c[0] == "viewport_create"]
    assert len(calls) == 1
    assert calls[0][1]["viewport_name"] == "Viewport_Lidar"
    assert calls[0][1]["camera_path"] == "/World/Robot/NovaCarter/TopLidar"


@pytest.mark.asyncio
async def test_viewport_destroy_idempotent():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ViewportModule(client)
    request = ViewportDestroyRequest(viewport_name="Viewport_Lidar")
    result = await module.destroy(_meta(), request)

    assert result.ok
    assert isinstance(result.data, ViewportDestroyResult)
    assert result.data.viewport_name == "Viewport_Lidar"
    assert result.data.destroyed is True


@pytest.mark.asyncio
async def test_viewport_create_error_propagation():
    class BrokenClient:
        async def viewport_create(self, _req):
            raise RuntimeError("kit not responding")

    module = ViewportModule(BrokenClient())  # type: ignore[arg-type]
    request = ViewportCreateRequest(viewport_name="Viewport_Err")
    result = await module.create(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_CREATE_ERROR"
    assert isinstance(result.data, ViewportCreateResult)
    assert result.data.ok is False
    assert result.data.viewport_name == "Viewport_Err"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_create_error"
    assert diagnostics["tool_name"] == "viewport_create"
    assert diagnostics["upstream_error_code"] == "VIEWPORT_CREATE_ERROR"
    assert diagnostics["upstream_message"] == "kit not responding"
    assert diagnostics["request"] == {
        "viewport_name": "Viewport_Err",
        "camera_path": None,
        "width": 1280,
        "height": 720,
        "docked": False,
    }
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "window_list",
        "viewport_create",
        "viewport_destroy",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_viewport_destroy_error_returns_typed_diagnostics():
    class BrokenClient:
        async def viewport_destroy(self, _req):
            raise RuntimeError("destroy failed")

    module = ViewportModule(BrokenClient())  # type: ignore[arg-type]
    request = ViewportDestroyRequest(viewport_name="Viewport_Err")
    result = await module.destroy(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "VIEWPORT_DESTROY_ERROR"
    assert isinstance(result.data, ViewportDestroyResult)
    assert result.data.ok is False
    assert result.data.viewport_name == "Viewport_Err"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "viewport_destroy_error"
    assert diagnostics["tool_name"] == "viewport_destroy"
    assert diagnostics["upstream_message"] == "destroy failed"
    assert diagnostics["request"] == {"viewport_name": "Viewport_Err"}
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "window_list",
        "viewport_create",
        "viewport_destroy",
        "extension_capture_logs",
    ]
