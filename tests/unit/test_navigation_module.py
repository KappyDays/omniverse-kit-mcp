"""Unit tests for NavigationModule (Phase E)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from omniverse_kit_mcp.modules.navigation_module import NavigationModule
from omniverse_kit_mcp.types.common import ModuleName, OperationMeta
from omniverse_kit_mcp.types.navigation import NavPathQueryRequest, SampleWalkablePointsRequest
from omni.mycompany.validation_api.services import navigation_service
from omni.mycompany.validation_api.services.navigation_service import NavigationService
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


def test_navigation_service_uses_isaac6_nav_agent_desc_wrapper():
    service_source = inspect.getsource(NavigationService)
    query_source = inspect.getsource(navigation_service._query_shortest_path)
    desc_source = inspect.getsource(navigation_service._make_nav_agent_desc)

    assert "mesh.query_shortest_path(" not in service_source
    assert "_query_shortest_path(" in service_source
    assert "NavAgentDesc" in desc_source
    assert "np.array([], dtype=np.float32)" in query_source
    assert "agent_radius=float(agent_radius)" in query_source


def test_navmesh_playground_uses_shared_query_wrapper():
    root = Path(__file__).resolve().parents[2]
    package_dir = (
        root / "kkr-extensions" / "omni.mycompany.navmesh_playground"
        / "omni" / "mycompany" / "navmesh_playground"
    )
    sampler_source = (package_dir / "navmesh_sampler.py").read_text()

    assert "def query_shortest_path(" in sampler_source
    assert "NavAgentDesc" in sampler_source

    for filename in ("people_controller.py", "robot_controller.py", "ui_panel.py"):
        source = (package_dir / filename).read_text()
        assert "mesh.query_shortest_path(" not in source
        assert "query_shortest_path(" in source


# Phase J — sample_walkable_points


@pytest.mark.asyncio
async def test_sample_walkable_points_default(nav_module, mock_client, meta):
    request = SampleWalkablePointsRequest(count=3, seed=42)
    result = await nav_module.sample_walkable_points(meta, request)
    assert result.ok is True
    assert len(result.data.points) == 3
    assert result.data.method == "area_weighted"
    assert result.data.seed == 42
    name, payload = mock_client.calls[-1]
    assert name == "navigation_sample_walkable_points"
    assert payload == {"count": 3, "seed": 42}


@pytest.mark.asyncio
async def test_sample_walkable_points_with_bounds(nav_module, mock_client, meta):
    request = SampleWalkablePointsRequest(
        count=5,
        bounds_min=(-10.0, -10.0, 0.0),
        bounds_max=(10.0, 10.0, 5.0),
    )
    await nav_module.sample_walkable_points(meta, request)
    _, payload = mock_client.calls[-1]
    assert payload["count"] == 5
    assert payload["bounds_min"] == [-10.0, -10.0, 0.0]
    assert payload["bounds_max"] == [10.0, 10.0, 5.0]


@pytest.mark.asyncio
async def test_sample_walkable_points_server_error_maps(nav_module, mock_client, meta):
    mock_client.responses["navigation_sample_walkable_points"] = {
        "ok": False, "reason": "NavMesh not baked",
    }
    request = SampleWalkablePointsRequest(count=1)
    result = await nav_module.sample_walkable_points(meta, request)
    assert result.ok is False
    assert result.error_code == "NAVIGATION_SAMPLE_ERROR"
    assert "not baked" in (result.message or "")
