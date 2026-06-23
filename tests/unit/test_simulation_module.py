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
async def test_simulation_play_preserves_settle_diagnostics(meta):
    client = MockIsaacRestClient()
    client.responses["simulation_play"] = {
        "is_playing": True,
        "is_stopped": False,
        "current_time": 0.1,
        "start_time": 0.0,
        "end_time": 10.0,
        "time_codes_per_second": 60.0,
        "timeline_settled": True,
        "timeline_settle_updates": 2,
    }
    mod = SimulationModule(client)
    result = await mod.play(meta)

    assert result.ok is True
    assert result.data is not None
    assert result.data.timeline_settled is True
    assert result.data.timeline_settle_updates == 2


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
async def test_wait_until_reached(meta):
    from omniverse_kit_mcp.types.simulation import SimulationWaitUntilRequest

    client = MockIsaacRestClient()
    mod = SimulationModule(client)
    result = await mod.wait_until(meta, SimulationWaitUntilRequest(until_time=12.0, timeout_s=30.0))
    assert result.ok is True
    assert result.data is not None
    assert result.data.until_time == 12.0
    assert result.data.reached is True
    assert result.data.timed_out is False
    assert result.data.status.current_time == 12.0
    sent = dict(client.calls)["simulation_wait_until"]
    assert sent["until_time"] == 12.0 and sent["timeout_s"] == 30.0


@pytest.mark.asyncio
async def test_wait_until_timeout(meta):
    from omniverse_kit_mcp.types.simulation import SimulationWaitUntilRequest

    client = MockIsaacRestClient()
    client.responses["simulation_wait_until"] = {
        "ok": True, "is_playing": False, "is_stopped": True, "current_time": 3.0,
        "start_time": 0.0, "end_time": 100.0, "time_codes_per_second": 60.0,
        "until_time": 12.0, "reached": False, "timed_out": True,
        "elapsed_s": 30.0, "frames_waited": 1800,
    }
    mod = SimulationModule(client)
    from omniverse_kit_mcp.types.simulation import SimulationWaitUntilRequest as _R
    result = await mod.wait_until(meta, _R(until_time=12.0, timeout_s=30.0))
    assert result.ok is True
    assert result.data.reached is False
    assert result.data.timed_out is True


@pytest.mark.asyncio
async def test_stage_set_semantic_label(meta):
    client = MockIsaacRestClient()
    mod = SimulationModule(client)
    result = await mod.stage_set_semantic_label(
        meta,
        {"prim_path": "/World/Props/Forklift", "label_class": "forklift", "label_type": "class"},
    )
    assert result.ok is True
    assert result.data is not None
    assert result.data.prim_path == "/World/Props/Forklift"
    assert "forklift" in result.data.detail
    sent = dict(client.calls)["stage_set_semantic_label"]
    assert sent["label_class"] == "forklift"


@pytest.mark.asyncio
async def test_stage_set_semantic_label_propagates_error(meta):
    class FailingClient(MockIsaacRestClient):
        async def stage_set_semantic_label(self, request):  # type: ignore[override]
            raise ValueError("Prim not found at /World/Nope")

    mod = SimulationModule(FailingClient())
    result = await mod.stage_set_semantic_label(meta, {"prim_path": "/World/Nope", "label_class": "x"})
    assert not result.ok
    assert result.error_code == "STAGE_SEMANTIC_LABEL_ERROR"


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
