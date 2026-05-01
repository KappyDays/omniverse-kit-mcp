"""Unit tests for RobotModule — load / joint positions / navigate (Phase B)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.robot_module import RobotModule
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.robot import (
    JointConfig,
    JointPositions,
    JointPositionsSetRequest,
    JointPositionsSetResult,
    RobotDrivePhysicsRequest,
    RobotDrivePhysicsResult,
    RobotLoadRequest,
    RobotLoadResult,
    RobotNavigateRequest,
    RobotNavigateResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(request_id="test", module=ModuleName.ROBOT, started_at_epoch_ms=0)


@pytest.mark.asyncio
async def test_robot_load_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotLoadRequest(
        usd_url="file:///tmp/franka.usd",
        prim_path="/World/Franka",
        position=(1.0, 2.0, 3.0),
    )
    result = await module.load(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, RobotLoadResult)
    assert result.data.prim_path == "/World/Franka"
    assert result.data.has_articulation is True
    load_calls = [c for c in client.calls if c[0] == "robot_load"]
    assert len(load_calls) == 1
    assert load_calls[0][1]["position"] == [1.0, 2.0, 3.0]


@pytest.mark.asyncio
async def test_robot_get_joint_positions():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_get_joint_positions"] = {
        "ok": True,
        "prim_path": "/World/Franka",
        "positions": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
    }
    module = RobotModule(client)
    result = await module.get_joint_positions(_meta(), "/World/Franka")

    assert result.ok
    assert isinstance(result.data, JointPositions)
    assert result.data.positions == (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)


@pytest.mark.asyncio
async def test_robot_get_joint_config_default_franka():
    """Default mock returns Franka 7-DOF config from dof_properties source."""
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    result = await module.get_joint_config(_meta(), "/World/Franka")

    assert result.ok
    assert isinstance(result.data, JointConfig)
    assert result.data.dof_count == 7
    assert result.data.source == "dof_properties"
    assert len(result.data.stiffness) == 7
    assert result.data.stiffness[0] == 400.0
    assert result.data.upper_limits[5] == 3.7
    cfg_calls = [c for c in client.calls if c[0] == "robot_get_joint_config"]
    assert len(cfg_calls) == 1
    assert cfg_calls[0][1]["prim_path"] == "/World/Franka"


@pytest.mark.asyncio
async def test_robot_get_joint_config_usd_fallback_source():
    """Custom mock simulates UsdPhysics.DriveAPI fallback path."""
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_get_joint_config"] = {
        "ok": True,
        "prim_path": "/World/UR10",
        "source": "usd_drive_api",
        "dof_count": 6,
        "dof_names": [f"j{i}" for i in range(6)],
        "joint_types": ["RevoluteJoint"] * 6,
        "stiffness": [0.0] * 6,
        "damping": [0.0] * 6,
        "max_force": [0.0] * 6,
        "lower_limits": [-3.14] * 6,
        "upper_limits": [3.14] * 6,
        "max_velocity": [0.0] * 6,
    }
    module = RobotModule(client)
    result = await module.get_joint_config(_meta(), "/World/UR10")

    assert result.ok
    assert result.data.source == "usd_drive_api"
    assert result.data.dof_count == 6
    assert all(v == 0.0 for v in result.data.stiffness)


@pytest.mark.asyncio
async def test_robot_get_joint_config_propagates_400():
    """Extension raises ValueError when prim has no articulation → wrapped error."""
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_get_joint_config(self, prim_path):  # type: ignore[override]
            raise ValueError("Prim at /X has no PhysX articulation API")

    module = RobotModule(FailingClient())
    result = await module.get_joint_config(_meta(), "/X")

    assert not result.ok
    assert result.error_code == "ROBOT_GET_JOINT_CONFIG_ERROR"
    assert "articulation" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_robot_set_joint_positions():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    positions = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    request = JointPositionsSetRequest(
        prim_path="/World/Franka",
        positions=tuple(positions),
    )
    result = await module.set_joint_positions(_meta(), request)

    assert result.ok
    assert isinstance(result.data, JointPositionsSetResult)
    assert result.data.positions_count == 7
    set_calls = [c for c in client.calls if c[0] == "robot_set_joint_positions"]
    assert len(set_calls) == 1
    assert set_calls[0][1]["positions"] == positions


@pytest.mark.asyncio
async def test_robot_set_joint_positions_surfaces_http_400():
    """Extension raises ValueError on missing articulation → HTTP 400 →
    RemoteServiceError propagates as ROBOT_SET_JOINTS_ERROR."""
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_set_joint_positions(self, request):  # type: ignore[override]
            raise ValueError("Prim at /X has no PhysX articulation API")

    module = RobotModule(FailingClient())
    request = JointPositionsSetRequest(prim_path="/X", positions=(0.0,))
    result = await module.set_joint_positions(_meta(), request)

    assert not result.ok
    assert result.error_code == "ROBOT_SET_JOINTS_ERROR"
    assert "articulation" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_robot_navigate_returns_job_id():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotNavigateRequest(
        prim_path="/World/Franka",
        target=(5.0, 0.0, 0.0),
        duration_s=2.0,
    )
    result = await module.navigate_to(_meta(), request)

    assert result.ok
    assert isinstance(result.data, RobotNavigateResult)
    assert result.data.job_id == "job_test_0001"
    nav_calls = [c for c in client.calls if c[0] == "robot_navigate"]
    assert nav_calls[0][1]["duration_s"] == 2.0


@pytest.mark.asyncio
async def test_robot_load_propagates_error():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_load(self, request):  # type: ignore[override]
            raise RuntimeError("CreateReferenceCommand failed")

    module = RobotModule(FailingClient())
    request = RobotLoadRequest(usd_url="bogus", prim_path="/World/X")
    result = await module.load(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_LOAD_ERROR"
    assert "CreateReferenceCommand failed" in (result.message or "")


# Phase J — drive_physics


@pytest.mark.asyncio
async def test_robot_drive_physics_returns_job_id():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    waypoints = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 2.0, 0.0))
    request = RobotDrivePhysicsRequest(
        prim_path="/World/Robot",
        waypoints=waypoints,
        wheel_radius=0.14, wheel_base=0.413,
    )
    result = await module.drive_physics(_meta(), request)

    assert result.ok
    assert isinstance(result.data, RobotDrivePhysicsResult)
    assert result.data.job_id == "drive_test_0001"
    drive_calls = [c for c in client.calls if c[0] == "robot_drive_physics"]
    assert len(drive_calls) == 1
    assert drive_calls[0][1]["waypoints"] == [list(p) for p in waypoints]
    assert drive_calls[0][1]["wheel_radius"] == 0.14


@pytest.mark.asyncio
async def test_robot_drive_physics_server_error_maps():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_drive_physics"] = {"ok": False, "reason": "wheel DOF unresolvable"}
    module = RobotModule(client)
    request = RobotDrivePhysicsRequest(
        prim_path="/World/X",
        waypoints=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
    )
    result = await module.drive_physics(_meta(), request)

    assert not result.ok
    assert result.error_code == "ROBOT_DRIVE_PHYSICS_ERROR"
    assert "DOF" in (result.message or "")
