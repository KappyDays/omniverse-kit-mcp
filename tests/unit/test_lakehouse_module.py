"""Unit tests for LakehouseModule — query only."""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.lakehouse_module import LakehouseModule
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.lakehouse import LakehouseDatasetRef, LakehouseQueryRequest
from tests.conftest import MockLakehouseClient


@pytest.fixture
def mock_client(lakehouse_query_result_raw):
    return MockLakehouseClient(responses={"query": lakehouse_query_result_raw})


@pytest.fixture
def lakehouse_module(mock_client):
    return LakehouseModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(request_id="test", module=ModuleName.LAKEHOUSE, started_at_epoch_ms=1000)


@pytest.mark.asyncio
async def test_query_with_target(lakehouse_module, meta):
    request = LakehouseQueryRequest(
        target=LakehouseDatasetRef(namespace="qa", dataset="stage_changes"),
        limit=10,
    )
    result = await lakehouse_module.query(meta, request)
    assert result.ok is True
    assert result.data is not None
    assert result.data.row_count == 1
    assert len(result.data.rows) == 1
    assert result.data.rows[0].values["prim_path"] == "/World/Cube"


@pytest.mark.asyncio
async def test_query_with_sql(lakehouse_module, meta):
    request = LakehouseQueryRequest(sql="SELECT * FROM stage_changes LIMIT 1")
    result = await lakehouse_module.query(meta, request)
    assert result.ok is True


@pytest.mark.asyncio
async def test_no_inject_or_cleanup_methods():
    """Verify LakehouseModule has no inject or cleanup methods."""
    assert not hasattr(LakehouseModule, "inject")
    assert not hasattr(LakehouseModule, "cleanup")
