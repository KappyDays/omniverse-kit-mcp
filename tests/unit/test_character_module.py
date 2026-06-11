"""Unit tests for CharacterModule — load / animation / position / navigate / state (Phase C)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.types.character import (
    CharacterLoadRequest,
    CharacterLoadResult,
    CharacterNavigateRequest,
    CharacterNavigateResult,
    CharacterPlayAnimationRequest,
    CharacterPlayAnimationResult,
    CharacterSetPositionRequest,
    CharacterSetPositionResult,
    CharacterState,
    CharacterStopAnimationRequest,
    CharacterStopAnimationResult,
)
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta


def _meta() -> OperationMeta:
    return OperationMeta(request_id="test", module=ModuleName.CHARACTER, started_at_epoch_ms=0)


@pytest.mark.asyncio
async def test_character_load_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    request = CharacterLoadRequest(
        usd_url="https://example/biped.usd",
        prim_path="/World/Characters/c_1",
        position=(1.0, 2.0, 3.0),
        yaw=90.0,
    )
    result = await module.load(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, CharacterLoadResult)
    assert result.data.prim_path == "/World/Characters/c_1"
    assert result.data.sanitized_prim_path == "/World/Characters/c_1"
    assert result.data.skel_root_path == "/World/Characters/c_1/SkelRoot"
    assert result.data.has_skeleton is True
    assert result.data.anim_graph_bound is True
    load_calls = [c for c in client.calls if c[0] == "character_load"]
    assert len(load_calls) == 1
    assert load_calls[0][1]["position"] == [1.0, 2.0, 3.0]
    assert load_calls[0][1]["yaw"] == 90.0


@pytest.mark.asyncio
async def test_character_play_animation_walk_with_target():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    request = CharacterPlayAnimationRequest(
        prim_path="/World/Characters/c_1",
        animation_name="Walk",
        speed=1.5,
        target_position=(5.0, 0.0, 0.0),
    )
    result = await module.play_animation(_meta(), request)

    assert result.ok
    assert isinstance(result.data, CharacterPlayAnimationResult)
    assert result.data.action == "Walk"
    assert result.data.speed == 1.5
    assert result.data.prim_path == "/World/Characters/c_1"
    play_calls = [c for c in client.calls if c[0] == "character_play_animation"]
    assert len(play_calls) == 1
    assert play_calls[0][1]["animation_name"] == "Walk"
    assert play_calls[0][1]["target_position"] == [5.0, 0.0, 0.0]


@pytest.mark.asyncio
async def test_character_set_position_round_trip():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    request = CharacterSetPositionRequest(
        prim_path="/World/Characters/c_1",
        position=(1.0, 2.0, 3.0),
        orientation=(0.707, 0.0, 0.707, 0.0),
    )
    result = await module.set_position(_meta(), request)

    assert result.ok
    assert isinstance(result.data, CharacterSetPositionResult)
    assert result.data.position == (1.0, 2.0, 3.0)
    assert result.data.orientation == (0.707, 0.0, 0.707, 0.0)
    set_calls = [c for c in client.calls if c[0] == "character_set_position"]
    assert len(set_calls) == 1
    assert set_calls[0][1]["position"] == [1.0, 2.0, 3.0]
    assert set_calls[0][1]["orientation"] == [0.707, 0.0, 0.707, 0.0]


@pytest.mark.asyncio
async def test_character_set_position_raises_on_missing_orientation_field():
    """Task 2 review fix — KeyError propagation when Extension omits orientation."""
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def character_set_position(self, request):  # type: ignore[override]
            return {"ok": True, "prim_path": "/X", "position": [0.0, 0.0, 0.0]}

    module = CharacterModule(FailingClient())
    request = CharacterSetPositionRequest(
        prim_path="/X",
        position=(0.0, 0.0, 0.0),
    )
    result = await module.set_position(_meta(), request)

    assert not result.ok
    assert result.error_code == "CHARACTER_SET_POSITION_ERROR"
    assert "orientation" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_character_stop_animation_returns_idle():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    request = CharacterStopAnimationRequest(prim_path="/World/Characters/c_1")
    result = await module.stop_animation(_meta(), request)

    assert result.ok
    assert isinstance(result.data, CharacterStopAnimationResult)
    assert result.data.action == "Idle"
    assert result.data.speed == 0.0
    assert result.data.prim_path == "/World/Characters/c_1"
    stop_calls = [c for c in client.calls if c[0] == "character_stop_animation"]
    assert len(stop_calls) == 1


@pytest.mark.asyncio
async def test_character_navigate_returns_job_id():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    request = CharacterNavigateRequest(
        prim_path="/World/Characters/c_1",
        target=(5.0, 0.0, 0.0),
        speed=1.0,
    )
    result = await module.navigate_to(_meta(), request)

    assert result.ok
    assert isinstance(result.data, CharacterNavigateResult)
    assert result.data.job_id == "job_char_0001"
    assert result.data.prim_path == "/World/Characters/c_1"
    assert result.data.target == (5.0, 0.0, 0.0)
    nav_calls = [c for c in client.calls if c[0] == "character_navigate"]
    assert len(nav_calls) == 1
    assert nav_calls[0][1]["target"] == [5.0, 0.0, 0.0]
    assert nav_calls[0][1]["speed"] == 1.0


@pytest.mark.asyncio
async def test_character_get_state_returns_typed_state():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["character_get_state"] = {
        "ok": True,
        "prim_path": "/World/Characters/c_1",
        "position": [1.0, 2.0, 3.0],
        "rotation": [0.707, 0.0, 0.707, 0.0],
        "action": "Walk",
        "is_navigating": True,
    }
    module = CharacterModule(client)
    result = await module.get_state(_meta(), "/World/Characters/c_1")

    assert result.ok
    assert isinstance(result.data, CharacterState)
    assert result.data.prim_path == "/World/Characters/c_1"
    assert result.data.position == (1.0, 2.0, 3.0)
    assert result.data.rotation == (0.707, 0.0, 0.707, 0.0)
    assert result.data.action == "Walk"
    assert result.data.is_navigating is True
    state_calls = [c for c in client.calls if c[0] == "character_get_state"]
    assert len(state_calls) == 1
    assert state_calls[0][1]["prim_path"] == "/World/Characters/c_1"


@pytest.mark.asyncio
async def test_character_get_state_raises_on_missing_required_fields():
    """Task 2 review fix — Extension response missing action/is_navigating must error."""
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def character_get_state(self, prim_path):  # type: ignore[override]
            return {
                "ok": True,
                "prim_path": prim_path,
                "position": [0.0, 0.0, 0.0],
                "rotation": [1.0, 0.0, 0.0, 0.0],
                # action and is_navigating intentionally omitted
            }

    module = CharacterModule(FailingClient())
    result = await module.get_state(_meta(), "/World/Characters/c_1")

    assert not result.ok
    assert result.error_code == "CHARACTER_GET_STATE_ERROR"
    msg = (result.message or "").lower()
    assert "action" in msg or "is_navigating" in msg or "missing" in msg


@pytest.mark.asyncio
async def test_character_load_propagates_error():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def character_load(self, request):  # type: ignore[override]
            raise RuntimeError("CreatePayloadCommand failed for character.usd")

    module = CharacterModule(FailingClient())
    request = CharacterLoadRequest(usd_url="bogus", prim_path="/World/Characters/c_1")
    result = await module.load(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "CHARACTER_LOAD_ERROR"
    assert "CreatePayloadCommand failed" in (result.message or "")
