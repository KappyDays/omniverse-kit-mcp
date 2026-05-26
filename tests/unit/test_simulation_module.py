"""Unit tests for SimulationModule stage play-guard."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.types.common import ModuleName, OperationMeta
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def meta():
    return OperationMeta(request_id="t", module=ModuleName.STAGE, started_at_epoch_ms=1000)


@pytest.mark.asyncio
async def test_stage_new_stops_when_playing(meta):
    client = MockIsaacRestClient()
    client.responses["simulation_status"] = {
        "is_playing": True, "is_stopped": False, "current_time": 1.0,
        "start_time": 0.0, "end_time": 10.0, "time_codes_per_second": 24.0,
    }
    mod = SimulationModule(client)
    result = await mod.stage_new(meta)
    assert result.ok is True
    called = [name for name, _ in client.calls]
    # status checked, stop issued BEFORE stage_new
    assert called.index("simulation_stop") < called.index("stage_new")


@pytest.mark.asyncio
async def test_stage_new_no_stop_when_idle(meta):
    client = MockIsaacRestClient()  # default simulation_status is_playing=False
    mod = SimulationModule(client)
    result = await mod.stage_new(meta)
    assert result.ok is True
    called = [name for name, _ in client.calls]
    assert "simulation_stop" not in called


@pytest.mark.asyncio
async def test_stage_open_stops_when_playing(meta):
    client = MockIsaacRestClient()
    client.responses["simulation_status"] = {
        "is_playing": True, "is_stopped": False, "current_time": 1.0,
        "start_time": 0.0, "end_time": 10.0, "time_codes_per_second": 24.0,
    }
    mod = SimulationModule(client)
    result = await mod.stage_open(meta, "file:///x.usd")
    assert result.ok is True
    called = [name for name, _ in client.calls]
    assert called.index("simulation_stop") < called.index("stage_open")
