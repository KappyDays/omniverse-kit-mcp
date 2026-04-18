"""Unit tests for NavigationModule (Phase E)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.navigation_module import NavigationModule
from isaacsim_mcp.types.common import ModuleName, OperationMeta
from isaacsim_mcp.types.navigation import NavPathQueryRequest
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def nav_module(mock_client):
    return NavigationModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(
        request_id="test", module=ModuleName.NAVIGATION, started_at_epoch_ms=1,
    )


@pytest.mark.asyncio
async def test_bake_default(nav_module, mock_client, meta):
    result = await nav_module.bake(meta)
    assert result.ok is True
    assert result.data.ok is True
    assert result.data.volume_prim_path == "/World/NavMeshVolume"
    assert result.data.agent_max_radius == 0.25

    _, payload = mock_client.calls[-1]
    assert payload == {"volume_scale": 40.0, "timeout_s": 300.0}


@pytest.mark.asyncio
async def test_bake_custom_scale(nav_module, mock_client, meta):
    await nav_module.bake(meta, volume_scale=12.5, timeout_s=45.0)
    _, payload = mock_client.calls[-1]
    assert payload == {"volume_scale": 12.5, "timeout_s": 45.0}


@pytest.mark.asyncio
async def test_query_path(nav_module, mock_client, meta):
    request = NavPathQueryRequest(
        start=(0.0, 0.0, 0.0), end=(3.0, 4.0, 0.0), straighten=True,
    )
    result = await nav_module.query_path(meta, request)
    assert result.ok is True
    assert result.data.points == (
        (0.0, 0.0, 0.0), (3.0, 4.0, 0.0),
    )
    assert result.data.auto_baked is False

    _, payload = mock_client.calls[-1]
    assert payload == {
        "start": [0.0, 0.0, 0.0],
        "end": [3.0, 4.0, 0.0],
        "agent_radius": 0.25,
        "agent_height": 1.8,
        "straighten": True,
    }


@pytest.mark.asyncio
async def test_add_exclude_volume(nav_module, mock_client, meta):
    result = await nav_module.add_exclude_volume(
        meta, prim_path="/World/Chair", padding=0.2,
    )
    assert result.ok is True
    assert result.data.volume_prim_path == "/World/NavMeshExclude_1"
    assert result.data.source_prim_path == "/World/Chair"
    assert result.data.padding == 0.2


@pytest.mark.asyncio
async def test_query_path_error_maps(nav_module, mock_client, meta):
    async def _boom(*a, **kw):
        raise RuntimeError("navmesh not built")
    mock_client.navigation_query_path = _boom
    result = await nav_module.query_path(
        meta,
        NavPathQueryRequest(start=(0, 0, 0), end=(1, 1, 1)),
    )
    assert result.ok is False
    assert result.error_code == "NAVIGATION_QUERY_PATH_ERROR"
