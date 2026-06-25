"""Unit tests for SimulationModule stage play-guard."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.simulation import (
    SimulationEESpec,
    SimulationStepObserveRequest,
    SimulationStepObserveResult,
    SimulationStepRequest,
    SimulationStepResult,
)
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
    assert result.data.diagnostics == {}


@pytest.mark.asyncio
async def test_simulation_status_error_returns_typed_diagnostics(meta):
    class FailingStatusClient(MockIsaacRestClient):
        async def simulation_status(self):  # type: ignore[override]
            raise RuntimeError("timeline unavailable")

    mod = SimulationModule(FailingStatusClient())

    result = await mod.get_status(meta)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "SIMULATION_STATUS_ERROR"
    assert "timeline unavailable" in (result.message or "")
    assert result.data is not None
    assert result.data.is_playing is False
    assert result.data.is_stopped is False
    assert result.data.diagnostics["reason"] == "simulation_status_error"
    assert result.data.diagnostics["upstream_error_code"] == (
        "SIMULATION_STATUS_ERROR"
    )
    assert result.data.diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "extension_capture_logs",
    ]
    assert any(
        "mcp_runtime_info" in item
        for item in result.data.diagnostics["suggested_next"]
    )


@pytest.mark.asyncio
async def test_simulation_step_error_returns_typed_diagnostics(meta):
    class FailingStepClient(MockIsaacRestClient):
        async def simulation_step(self, request):  # type: ignore[override]
            raise RuntimeError("timeline step unavailable")

    mod = SimulationModule(FailingStepClient())
    result = await mod.step(meta, SimulationStepRequest(frames=8))

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "SIMULATION_STEP_ERROR"
    assert isinstance(result.data, SimulationStepResult)
    assert result.data.frames == 8
    assert result.data.status.diagnostics["reason"] == "simulation_step_error"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "simulation_step_error"
    assert diagnostics["upstream_error_code"] == "SIMULATION_STEP_ERROR"
    assert diagnostics["upstream_message"] == "timeline step unavailable"
    assert diagnostics["frames"] == 8
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "simulation_step",
        "extension_capture_logs",
    ]
    assert any("simulation_get_status" in item for item in diagnostics["suggested_next"])


@pytest.mark.asyncio
async def test_simulation_step_observe_error_returns_typed_diagnostics(meta):
    class FailingStepObserveClient(MockIsaacRestClient):
        async def simulation_step_observe(self, request):  # type: ignore[override]
            raise RuntimeError("observation failed")

    mod = SimulationModule(FailingStepObserveClient())
    request = SimulationStepObserveRequest(
        frames=4,
        observe_prims=("/World/Robot",),
        observe_joints=("/World/Robot",),
        observe_ee=(SimulationEESpec("/World/Robot", "panda_hand"),),
    )
    result = await mod.step_observe(meta, request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "SIMULATION_STEP_OBSERVE_ERROR"
    assert isinstance(result.data, SimulationStepObserveResult)
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "simulation_step_observe_error"
    assert diagnostics["upstream_error_code"] == "SIMULATION_STEP_OBSERVE_ERROR"
    assert diagnostics["upstream_message"] == "observation failed"
    assert diagnostics["frames"] == 4
    assert diagnostics["observe_prims"] == ["/World/Robot"]
    assert diagnostics["observe_joints"] == ["/World/Robot"]
    assert diagnostics["observe_ee"] == [
        {"prim_path": "/World/Robot", "end_effector_frame": "panda_hand"}
    ]
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "simulation_step_observe",
        "extension_capture_logs",
    ]


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
