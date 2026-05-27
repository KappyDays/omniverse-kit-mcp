"""Unit tests for content_* MCP tools (Phase H)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.content_module import ContentModule
from omniverse_kit_mcp.scenario.action_registry import build_request
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.content import (
    ContentBrowseRequest,
    ContentBrowseResult,
    ContentEntry,
    ContentInspectRequest,
    ContentInspectResult,
    ContentPreviewRequest,
    ContentPreviewResult,
    ContentResolveRequest,
    ContentResolveResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="t", module=ModuleName.CONTENT, started_at_epoch_ms=0,
    )


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_content_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "content_browse" in names
    assert "content_preview" in names
    assert "content_inspect" in names
    assert "content_resolve" in names


@pytest.mark.asyncio
async def test_inspect_returns_geometry():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ContentModule(client)
    result = await module.inspect(
        _meta(),
        ContentInspectRequest(url="omniverse://localhost/forklift.usd"),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ContentInspectResult)
    assert result.data.default_prim == "/World"
    assert result.data.bbox_min == (-1.0, -1.0, 0.0)
    assert result.data.bbox_max == (1.0, 1.0, 2.0)
    assert result.data.meters_per_unit == 0.01
    assert result.data.up_axis == "Z"
    assert result.data.prim_count == 42


@pytest.mark.asyncio
async def test_inspect_open_failure_wraps_error():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def content_inspect(self, request):  # type: ignore[override]
            raise ValueError("could not open USD stage 'bad://x'")

    module = ContentModule(FailingClient())
    result = await module.inspect(_meta(), ContentInspectRequest(url="bad://x"))
    assert not result.ok
    assert result.error_code == "CONTENT_INSPECT_ERROR"


@pytest.mark.asyncio
async def test_browse_returns_entries():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ContentModule(client)
    result = await module.browse(
        _meta(),
        ContentBrowseRequest(url="omniverse://localhost/Projects"),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ContentBrowseResult)
    assert result.data.entry_count == 2
    assert all(isinstance(e, ContentEntry) for e in result.data.entries)


@pytest.mark.asyncio
async def test_preview_returns_info():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ContentModule(client)
    result = await module.preview(
        _meta(),
        ContentPreviewRequest(url="omniverse://localhost/a.usd"),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ContentPreviewResult)
    assert "size" in result.data.info or "url" in result.data.info


@pytest.mark.asyncio
async def test_resolve_normalizes_url():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ContentModule(client)
    result = await module.resolve(
        _meta(),
        ContentResolveRequest(url="file:///C:/tmp/a.usd"),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ContentResolveResult)
    assert result.data.resolved


def test_action_registry_phase_h_content_builders():
    req = build_request(
        ModuleName.CONTENT, "browse",
        {"url": "omniverse://localhost/", "recursive": True},
    )
    assert isinstance(req, ContentBrowseRequest)
    assert req.recursive is True

    req2 = build_request(
        ModuleName.CONTENT, "preview", {"url": "file:///C:/a.usd"},
    )
    assert isinstance(req2, ContentPreviewRequest)

    req3 = build_request(
        ModuleName.CONTENT, "resolve", {"url": "omniverse://a/b"},
    )
    assert isinstance(req3, ContentResolveRequest)


def test_action_registry_content_errors():
    with pytest.raises(ValueError, match="url"):
        build_request(ModuleName.CONTENT, "browse", {})
    with pytest.raises(ValueError, match="url"):
        build_request(ModuleName.CONTENT, "preview", {})
    with pytest.raises(ValueError, match="url"):
        build_request(ModuleName.CONTENT, "resolve", {})
