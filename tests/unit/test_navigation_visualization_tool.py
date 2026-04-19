"""Unit tests for navigation_set_visualization (Phase E NavMesh overlay toggle)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server
from isaacsim_mcp.modules.navigation_module import NavigationModule
from isaacsim_mcp.scenario.action_registry import build_request
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.navigation import (
    NavigationSetVisualizationRequest,
    NavigationSetVisualizationResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="test", module=ModuleName.NAVIGATION, started_at_epoch_ms=0,
    )


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_navigation_set_visualization_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "navigation_set_visualization" in names


@pytest.mark.parametrize("mode", ["walkable", "obstacles", "off"])
@pytest.mark.asyncio
async def test_set_visualization_mode_round_trip(mode):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = NavigationModule(client)
    request = NavigationSetVisualizationRequest(mode=mode)
    result = await module.set_visualization(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, NavigationSetVisualizationResult)
    assert result.data.mode == mode
    assert result.data.backend == "carb_settings"

    calls = [c for c in client.calls if c[0] == "navigation_set_visualization"]
    assert len(calls) == 1
    assert calls[0][1]["mode"] == mode


def test_set_visualization_builder_accepts_valid_modes():
    for mode in ("walkable", "obstacles", "off"):
        req = build_request(
            ModuleName.NAVIGATION, "set_visualization", {"mode": mode},
        )
        assert isinstance(req, NavigationSetVisualizationRequest)
        assert req.mode == mode


def test_set_visualization_builder_rejects_invalid_mode():
    with pytest.raises(ValueError, match="mode must be"):
        build_request(
            ModuleName.NAVIGATION, "set_visualization", {"mode": "bogus"},
        )


@pytest.mark.asyncio
async def test_set_visualization_error_propagation():
    class BrokenClient:
        async def navigation_set_visualization(self, _req):
            raise RuntimeError("carb settings not reachable")

    module = NavigationModule(BrokenClient())  # type: ignore[arg-type]
    request = NavigationSetVisualizationRequest(mode="walkable")
    result = await module.set_visualization(_meta(), request)

    assert not result.ok
    assert result.error_code == "NAVIGATION_SET_VISUALIZATION_ERROR"
