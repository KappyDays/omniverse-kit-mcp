"""Unit tests for sensor_attach_contact / sensor_attach_imu / sensor_set_annotator (Phase G)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.sensor_module import SensorModule
from omniverse_kit_mcp.scenario.action_registry import build_request
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.sensor import (
    SensorAttachContactRequest,
    SensorAttachContactResult,
    SensorAttachImuRequest,
    SensorAttachImuResult,
    SensorSetAnnotatorRequest,
    SensorSetAnnotatorResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(request_id="t", module=ModuleName.SENSOR, started_at_epoch_ms=0)


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_sensor_ext_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "sensor_attach_contact" in names
    assert "sensor_attach_imu" in names
    assert "sensor_set_annotator" in names


@pytest.mark.asyncio
async def test_attach_contact_returns_prim_path():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SensorModule(client)
    result = await module.attach_contact(
        _meta(),
        SensorAttachContactRequest(
            prim_path="/World/Robot/chassis",
            sensor_name="FrontBumper",
            frequency=120,
            translation=(0.3, 0.0, 0.1),
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, SensorAttachContactResult)
    assert result.data.sensor_prim_path.endswith("/FrontBumper")
    assert result.data.sensor_type == "contact"
    assert result.data.frequency == 120


@pytest.mark.asyncio
async def test_attach_imu_returns_prim_path():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SensorModule(client)
    result = await module.attach_imu(
        _meta(),
        SensorAttachImuRequest(
            prim_path="/World/Robot/chassis",
            sensor_name="MainIMU",
            frequency=500,
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, SensorAttachImuResult)
    assert result.data.sensor_type == "imu"
    assert result.data.frequency == 500


@pytest.mark.asyncio
async def test_set_annotator_attaches_multiple():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SensorModule(client)
    result = await module.set_annotator(
        _meta(),
        SensorSetAnnotatorRequest(
            sensor_prim="/World/Robot/chassis/FrontCam",
            annotators=("rgb", "depth", "semantic_segmentation"),
            resolution=(640, 480),
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, SensorSetAnnotatorResult)
    assert set(result.data.annotators) == {"rgb", "depth", "semantic_segmentation"}
    assert result.data.resolution == (640, 480)


def test_action_registry_phase_g_sensor_builders():
    req = build_request(
        ModuleName.SENSOR, "attach_contact",
        {"prim_path": "/W/R", "sensor_name": "Foot"},
    )
    assert isinstance(req, SensorAttachContactRequest)
    req2 = build_request(
        ModuleName.SENSOR, "attach_imu",
        {"prim_path": "/W/R", "mount_offset": [0.1, 0.0, 0.2]},
    )
    assert isinstance(req2, SensorAttachImuRequest)
    req3 = build_request(
        ModuleName.SENSOR, "set_annotator",
        {"sensor_prim": "/W/R/Cam", "annotators": ["rgb", "depth"]},
    )
    assert isinstance(req3, SensorSetAnnotatorRequest)


def test_action_registry_sensor_errors():
    with pytest.raises(ValueError, match="annotators"):
        build_request(
            ModuleName.SENSOR, "set_annotator",
            {"sensor_prim": "/x", "annotators": []},
        )
    with pytest.raises(ValueError, match="translation"):
        build_request(
            ModuleName.SENSOR, "attach_contact",
            {"prim_path": "/x", "translation": [0, 0]},
        )
    with pytest.raises(ValueError, match="mount_orientation"):
        build_request(
            ModuleName.SENSOR, "attach_imu",
            {"prim_path": "/x", "mount_orientation": [1, 0, 0]},
        )
