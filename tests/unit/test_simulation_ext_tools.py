"""Unit tests for simulation_step / simulation_set_time (Phase G)."""

from __future__ import annotations

import inspect

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.scenario.action_registry import build_request
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.simulation import (
    ObservedEETarget,
    ObservedPrimState,
    SimulationEESpec,
    SimulationSetTimeRequest,
    SimulationSetTimeResult,
    SimulationStepObserveRequest,
    SimulationStepObserveResult,
    SimulationStepRequest,
    SimulationStepResult,
)
from omni.mycompany.validation_api.services.simulation_service import SimulationService


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="t", module=ModuleName.SIMULATION, started_at_epoch_ms=0,
    )


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_simulation_ext_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "simulation_step" in names
    assert "simulation_step_observe" in names
    assert "simulation_set_time" in names


def test_simulation_service_step_uses_play_burst_by_default():
    source = inspect.getsource(SimulationService.step)

    assert 'advance_mode = "play_burst"' in source
    assert "timeline.forward_one_frame" not in source


@pytest.mark.asyncio
async def test_simulation_step_advances_time():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SimulationModule(client)
    result = await module.step(_meta(), SimulationStepRequest(frames=60))
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, SimulationStepResult)
    assert result.data.frames == 60
    assert result.data.advance_mode in {
        "forward_one_frame",
        "play_burst",
        "set_time_fallback",
    }
    assert result.data.status.current_time == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_simulation_step_observe_returns_runtime_evidence():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SimulationModule(client)
    result = await module.step_observe(
        _meta(),
        SimulationStepObserveRequest(
            frames=2,
            observe_prims=("/World/Cube",),
            observe_joints=("/World/Franka",),
            observe_ee=(SimulationEESpec("/World/Franka", "panda_hand"),),
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, SimulationStepObserveResult)
    assert result.data.frames == 2
    assert isinstance(result.data.prim_states[0], ObservedPrimState)
    assert result.data.prim_states[0].prim_path == "/World/Cube"
    assert result.data.prim_states[0].position == pytest.approx((0.1, 0.2, 0.3))
    assert result.data.joint_states[0].prim_path == "/World/Franka"
    assert isinstance(result.data.ee_states[0], ObservedEETarget)
    assert result.data.ee_states[0].position == pytest.approx((0.5, 0.0, 0.4))


@pytest.mark.asyncio
async def test_simulation_set_time_seeks():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SimulationModule(client)
    result = await module.set_time(_meta(), SimulationSetTimeRequest(time_seconds=3.5))
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, SimulationSetTimeResult)
    assert result.data.requested_time == pytest.approx(3.5)
    assert result.data.status.current_time == pytest.approx(3.5)


def test_action_registry_phase_g_simulation_builders():
    req = build_request(ModuleName.SIMULATION, "step", {"frames": 5})
    assert isinstance(req, SimulationStepRequest)
    assert req.frames == 5
    req2 = build_request(
        ModuleName.SIMULATION, "set_time", {"time_seconds": 2.0},
    )
    assert isinstance(req2, SimulationSetTimeRequest)
    assert req2.time_seconds == pytest.approx(2.0)


def test_action_registry_simulation_errors():
    with pytest.raises(ValueError, match="frames"):
        build_request(ModuleName.SIMULATION, "step", {"frames": 0})
    with pytest.raises(ValueError, match="time_seconds"):
        build_request(ModuleName.SIMULATION, "set_time", {"time_seconds": -1.0})
