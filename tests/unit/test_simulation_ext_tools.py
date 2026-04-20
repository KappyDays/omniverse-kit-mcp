"""Unit tests for simulation_step / simulation_set_time (Phase G)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server
from isaacsim_mcp.modules.simulation_module import SimulationModule
from isaacsim_mcp.scenario.action_registry import build_request
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.simulation import (
    SimulationSetTimeRequest,
    SimulationSetTimeResult,
    SimulationStepRequest,
    SimulationStepResult,
)


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
    assert "simulation_set_time" in names


@pytest.mark.asyncio
async def test_simulation_step_advances_time():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = SimulationModule(client)
    result = await module.step(_meta(), SimulationStepRequest(frames=60))
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, SimulationStepResult)
    assert result.data.frames == 60
    assert result.data.advance_mode in {"forward_one_frame", "play_burst"}
    assert result.data.status.current_time == pytest.approx(1.0)


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
