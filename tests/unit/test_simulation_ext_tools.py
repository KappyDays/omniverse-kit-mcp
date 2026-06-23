"""Unit tests for simulation_step / simulation_set_time (Phase G)."""

from __future__ import annotations

import inspect
import sys
import types

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


class _FakeTimeline:
    def __init__(self) -> None:
        self._is_playing = False
        self._is_stopped = True
        self._pending_state: tuple[bool, bool] | None = None

    def play(self) -> None:
        self._pending_state = (True, False)

    def pause(self) -> None:
        self._pending_state = (False, False)

    def stop(self) -> None:
        self._pending_state = (False, True)

    def apply_pending(self) -> None:
        if self._pending_state is None:
            return
        self._is_playing, self._is_stopped = self._pending_state
        self._pending_state = None

    def is_playing(self) -> bool:
        return self._is_playing

    def is_stopped(self) -> bool:
        return self._is_stopped

    def get_current_time(self) -> float:
        return 0.0

    def get_start_time(self) -> float:
        return 0.0

    def get_end_time(self) -> float:
        return 10.0

    def get_time_codes_per_seconds(self) -> float:
        return 60.0


class _FakeApp:
    def __init__(self, timeline: _FakeTimeline) -> None:
        self.timeline = timeline
        self.updates = 0

    async def next_update_async(self) -> None:
        self.updates += 1
        self.timeline.apply_pending()


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="t", module=ModuleName.SIMULATION, started_at_epoch_ms=0,
    )


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


@pytest.fixture
def fake_timeline_runtime(monkeypatch):
    import omni

    timeline = _FakeTimeline()
    app = _FakeApp(timeline)

    timeline_module = types.ModuleType("omni.timeline")
    timeline_module.get_timeline_interface = lambda: timeline

    kit_module = types.ModuleType("omni.kit")
    app_module = types.ModuleType("omni.kit.app")
    app_module.get_app = lambda: app
    kit_module.app = app_module

    monkeypatch.setitem(sys.modules, "omni.timeline", timeline_module)
    monkeypatch.setitem(sys.modules, "omni.kit", kit_module)
    monkeypatch.setitem(sys.modules, "omni.kit.app", app_module)
    monkeypatch.setattr(omni, "timeline", timeline_module, raising=False)
    monkeypatch.setattr(omni, "kit", kit_module, raising=False)

    return timeline, app


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
async def test_simulation_service_controls_return_settled_timeline_status(
    fake_timeline_runtime,
):
    _, app = fake_timeline_runtime
    service = SimulationService()

    play = await service.play()
    assert play["is_playing"] is True
    assert play["is_stopped"] is False
    assert play["timeline_settled"] is True
    assert play["timeline_settle_updates"] == 1

    pause = await service.pause()
    assert pause["is_playing"] is False
    assert pause["is_stopped"] is False
    assert pause["timeline_settled"] is True
    assert pause["timeline_settle_updates"] == 1

    stop = await service.stop()
    assert stop["is_playing"] is False
    assert stop["is_stopped"] is True
    assert stop["timeline_settled"] is True
    assert stop["timeline_settle_updates"] == 1
    assert app.updates == 3


@pytest.mark.asyncio
async def test_simulation_service_reports_unsettled_timeline_state(
    fake_timeline_runtime,
):
    timeline, app = fake_timeline_runtime
    timeline.apply_pending = lambda: None
    service = SimulationService()

    play = await service.play()

    assert play["is_playing"] is False
    assert play["is_stopped"] is True
    assert play["timeline_settled"] is False
    assert play["timeline_settle_updates"] == 5
    assert app.updates == 5


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
