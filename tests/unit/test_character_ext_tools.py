"""Unit tests for character_play_animation_variant / character_load_crowd (Phase G)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.scenario.action_registry import build_request
from omniverse_kit_mcp.types.character import (
    CharacterLoadCrowdRequest,
    CharacterLoadCrowdResult,
    CharacterPlayAnimationVariantRequest,
    CharacterPlayAnimationVariantResult,
)
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta


def _meta() -> OperationMeta:
    return OperationMeta(request_id="t", module=ModuleName.CHARACTER, started_at_epoch_ms=0)


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_character_ext_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "character_play_animation_variant" in names
    assert "character_load_crowd" in names


@pytest.mark.asyncio
async def test_play_animation_variant_sit_reading():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    result = await module.play_animation_variant(
        _meta(),
        CharacterPlayAnimationVariantRequest(
            prim_path="/World/Characters/Biped",
            variant="SitReading",
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, CharacterPlayAnimationVariantResult)
    assert result.data.variant == "SitReading"
    assert result.data.base_action == "Sit"
    assert "sit_style" in result.data.variables_set or "Action" in result.data.variables_set


@pytest.mark.asyncio
async def test_play_animation_variant_walk_fast_with_target():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    result = await module.play_animation_variant(
        _meta(),
        CharacterPlayAnimationVariantRequest(
            prim_path="/World/Characters/Biped",
            variant="WalkFast",
            speed=1.5,
            target_position=(3.0, 2.0, 0.0),
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert result.data.base_action == "Walk"
    assert result.data.speed == pytest.approx(1.5)


@pytest.mark.asyncio
async def test_load_crowd_grid_layout():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = CharacterModule(client)
    result = await module.load_crowd(
        _meta(),
        CharacterLoadCrowdRequest(
            count=4, layout="grid", spacing=2.0, base_name="Shopper",
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, CharacterLoadCrowdResult)
    assert result.data.count == 4
    assert result.data.layout == "grid"
    assert len(result.data.loaded) == 4
    # Grid positions should differ (not all colocated at origin)
    xs = {m.position[0] for m in result.data.loaded}
    ys = {m.position[1] for m in result.data.loaded}
    assert len(xs) >= 2 or len(ys) >= 2


def test_action_registry_phase_g_character_builders():
    req = build_request(
        ModuleName.CHARACTER, "play_animation_variant",
        {"prim_path": "/W/C", "variant": "SitIdle"},
    )
    assert isinstance(req, CharacterPlayAnimationVariantRequest)
    req2 = build_request(
        ModuleName.CHARACTER, "load_crowd",
        {"count": 3, "layout": "line", "spacing": 1.5},
    )
    assert isinstance(req2, CharacterLoadCrowdRequest)
    assert req2.layout == "line"


def test_action_registry_character_errors():
    with pytest.raises(ValueError, match="variant"):
        build_request(
            ModuleName.CHARACTER, "play_animation_variant", {"prim_path": "/x"},
        )
    with pytest.raises(ValueError, match="count"):
        build_request(ModuleName.CHARACTER, "load_crowd", {"count": 0})
    with pytest.raises(ValueError, match="layout"):
        build_request(
            ModuleName.CHARACTER, "load_crowd",
            {"count": 3, "layout": "chaos"},
        )
