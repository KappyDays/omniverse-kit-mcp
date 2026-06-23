"""Unit tests for sensor_attach_contact / sensor_attach_imu / sensor_set_annotator (Phase G)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

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

PROJECT = Path(__file__).resolve().parents[2]


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
    assert result.data.backend == "isaacsim.sensors.experimental.physics.Contact.create"


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
    assert result.data.backend == "isaacsim.sensors.experimental.physics.IMU.create"


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


def test_lidar_gmo_extractor_converts_spherical_points():
    service = _load_validation_sensor_service()

    class Coord:
        name = "SPHERICAL"

    class Elements:
        x = [0.0, 90.0]
        y = [0.0, 0.0]
        z = [2.0, 3.0]
        scalar = [0.25, 0.75]

    class Gmo:
        numElements = 2
        elementsCoordsType = Coord()
        elements = Elements()

    points, intensities, raw_keys, truncated = service._extract_gmo_points(Gmo(), 10)

    assert truncated is False
    assert raw_keys == [
        "generic-model-output",
        "coords_type:SPHERICAL",
        "num_elements:2",
    ]
    assert points[0] == pytest.approx([2.0, 0.0, 0.0])
    assert points[1] == pytest.approx([0.0, 3.0, 0.0], abs=1e-6)
    assert intensities == [0.25, 0.75]


def test_lidar_gmo_extractor_truncates_cartesian_points():
    service = _load_validation_sensor_service()

    class Coord:
        name = "CARTESIAN"

    class Elements:
        x = [1.0, 4.0]
        y = [2.0, 5.0]
        z = [3.0, 6.0]
        scalar = []

    class Gmo:
        numElements = 2
        elementsCoordsType = Coord()
        elements = Elements()

    points, intensities, _raw_keys, truncated = service._extract_gmo_points(Gmo(), 1)

    assert truncated is True
    assert points == [[1.0, 2.0, 3.0]]
    assert intensities == []


def test_lidar_scan_dict_extractor_converts_degrees_to_cartesian():
    service = _load_validation_sensor_service()

    points, intensities, raw_keys, truncated, warning = service._extract_scan_dict_points(
        {
            "azimuth": [0.0, 90.0],
            "elevation": [0.0, 0.0],
            "distance": [2.0, 3.0],
            "intensity": [0.25, 0.75],
        },
        10,
    )

    assert warning is None
    assert truncated is False
    assert raw_keys == ["azimuth", "distance", "elevation", "intensity"]
    assert points[0] == pytest.approx([2.0, 0.0, 0.0])
    assert points[1] == pytest.approx([0.0, 3.0, 0.0], abs=1e-6)
    assert intensities == [0.25, 0.75]


def test_lidar_scan_dict_extractor_reports_empty_polar_arrays():
    service = _load_validation_sensor_service()

    points, intensities, raw_keys, truncated, warning = service._extract_scan_dict_points(
        {
            "azimuth": [],
            "elevation": [],
            "distance": [],
            "channelId": [],
        },
        10,
    )

    assert points == []
    assert intensities == []
    assert truncated is False
    assert raw_keys == ["azimuth", "channelId", "distance", "elevation"]
    assert warning == "polar arrays contained 0 elements"


def test_lidar_empty_reason_classifies_zero_gmo_buffer():
    service = _load_validation_sensor_service()

    reason = service._lidar_empty_reason(
        points=[],
        warning="parsed generic-model-output contained 0 elements but no usable point data",
        raw_keys=["generic-model-output", "coords_type:CARTESIAN", "num_elements:0"],
        backend="isaacsim.sensors.experimental.rtx.LidarSensor",
    )

    assert reason == "empty_scan_buffer"


def test_lidar_readback_diagnostics_suggests_retry_for_empty_scan_buffer():
    service = _load_validation_sensor_service()

    diagnostics = service._lidar_readback_diagnostics(
        empty_reason="empty_scan_buffer",
        warning="polar arrays contained 0 elements",
        raw_keys=["azimuth", "distance", "elevation"],
        frames_waited=60,
        cached_lidar_instance=True,
        readback_paths_attempted=["cached_lidar_sensor", "replicator_annotator"],
    )

    assert diagnostics["empty_reason"] == "empty_scan_buffer"
    assert diagnostics["frames_waited"] == 60
    assert diagnostics["cached_lidar_instance"] is True
    assert diagnostics["raw_key_count"] == 3
    assert diagnostics["readback_paths_attempted"] == [
        "cached_lidar_sensor",
        "replicator_annotator",
    ]
    assert "retry an idempotent read" in diagnostics["suggested_next"]


def _load_validation_sensor_service():
    path = (
        PROJECT / "kkr-extensions" / "omni.mycompany.validation_api"
        / "omni" / "mycompany" / "validation_api" / "services"
        / "sensor_service.py"
    )
    spec = importlib.util.spec_from_file_location("_validation_sensor_service", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
