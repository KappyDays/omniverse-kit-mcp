"""Unit tests for RobotModule — load / joint positions / navigate (Phase B)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.robot_module import RobotModule
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.robot import (
    JointPositions,
    JointPositionsSetRequest,
    JointPositionsSetResult,
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
