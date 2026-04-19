"""Unit tests for SensorModule + sensor_* MCP tool registration (Phase E)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server
from isaacsim_mcp.modules.sensor_module import SensorModule
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.sensor import (
    SensorAttachRtxCameraRequest,
    SensorAttachRtxCameraResult,
    SensorAttachRtxDepthCameraRequest,
    SensorAttachRtxDepthCameraResult,
    SensorAttachRtxLidarRequest,
    SensorAttachRtxLidarResult,
    SensorSetVisualizationRequest,
    SensorSetVisualizationResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(request_id="test", module=ModuleName.SENSOR, started_at_epoch_ms=0)


# --- Tool registration ------------------------------------------------------


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_sensor_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "sensor_attach_rtx_camera" in names
    assert "sensor_attach_rtx_lidar" in names
    assert "sensor_attach_rtx_depth_camera" in names
    assert "sensor_set_visualization" in names


def test_sensor_enum_registered():
    assert ModuleName.SENSOR.value == "sensor"


# --- Module unit tests ------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_rtx_camera_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SensorModule(client)
    request = SensorAttachRtxCameraRequest(
        robot_prim="/World/Robot/NovaCarter",
        mount_offset=(0.0, 0.3, 0.8),
        mount_rotation=(0.0, 0.0, 0.0),
        resolution=(1920, 1080),
        sensor_name="FrontRGB",
    )
    result = await module.attach_rtx_camera(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, SensorAttachRtxCameraResult)
    assert result.data.sensor_prim_path == "/World/Robot/NovaCarter/FrontRGB"
    assert result.data.sensor_type == "rtx_camera"
    assert result.data.resolution == (1920, 1080)

    calls = [c for c in client.calls if c[0] == "sensor_attach_rtx_camera"]
    assert len(calls) == 1
    assert calls[0][1]["mount_offset"] == [0.0, 0.3, 0.8]
    assert calls[0][1]["resolution"] == [1920, 1080]


@pytest.mark.asyncio
async def test_attach_rtx_lidar_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SensorModule(client)
    request = SensorAttachRtxLidarRequest(
        robot_prim="/World/Robot/NovaCarter",
        mount_offset=(0.0, 0.0, 1.2),
        mount_rotation=(0.0, 0.0, 0.0),
        config_preset="Example_Rotary",
        sensor_name="TopLidar",
    )
    result = await module.attach_rtx_lidar(_meta(), request)

    assert result.ok
    assert isinstance(result.data, SensorAttachRtxLidarResult)
    assert result.data.sensor_type == "rtx_lidar"
    assert result.data.config_preset == "Example_Rotary"
    assert result.data.annotator is not None
    assert result.data.sensor_prim_path.endswith("/TopLidar")


@pytest.mark.asyncio
async def test_attach_rtx_depth_camera_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SensorModule(client)
    request = SensorAttachRtxDepthCameraRequest(
        robot_prim="/World/Robot/NovaCarter",
        mount_offset=(0.3, 0.0, 0.7),
        mount_rotation=(0.0, 0.0, 0.0),
        resolution=(1280, 720),
        sensor_name="DepthSide",
    )
    result = await module.attach_rtx_depth_camera(_meta(), request)

    assert result.ok
    assert isinstance(result.data, SensorAttachRtxDepthCameraResult)
    assert result.data.sensor_type == "rtx_depth_camera"
    assert result.data.resolution == (1280, 720)
    assert result.data.annotator == "distance_to_camera"


@pytest.mark.asyncio
async def test_set_visualization_toggle():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SensorModule(client)

    for mode in ("on", "off"):
        request = SensorSetVisualizationRequest(
            sensor_prim="/World/Robot/NovaCarter/TopLidar",
            mode=mode,
        )
        result = await module.set_visualization(_meta(), request)
        assert result.ok
        assert isinstance(result.data, SensorSetVisualizationResult)
        assert result.data.mode == mode


@pytest.mark.asyncio
async def test_attach_rtx_camera_propagates_client_error():
    class BrokenClient:
        async def sensor_attach_rtx_camera(self, _req):
            raise RuntimeError("extension offline")

    module = SensorModule(BrokenClient())  # type: ignore[arg-type]
    request = SensorAttachRtxCameraRequest(
        robot_prim="/World/Robot",
        mount_offset=(0.0, 0.0, 0.0),
        mount_rotation=(0.0, 0.0, 0.0),
    )
    result = await module.attach_rtx_camera(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "SENSOR_ATTACH_RTX_CAMERA_ERROR"
    assert "extension offline" in (result.message or "")
