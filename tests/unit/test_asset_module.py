"""Unit tests for AssetModule — catalog listing (Phase B+)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.asset_module import AssetModule
from omniverse_kit_mcp.types.asset import AssetCategory, AssetItem, AssetListResult
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="test", module=ModuleName.ASSET, started_at_epoch_ms=0
    )


@pytest.mark.asyncio
async def test_asset_list_categories():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = AssetModule(client)
    result = await module.list(_meta())

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, AssetListResult)
    assert result.data.category is None
    assert len(result.data.categories) >= 1
    assert isinstance(result.data.categories[0], AssetCategory)


@pytest.mark.asyncio
async def test_asset_list_robots():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = AssetModule(client)
    result = await module.list(_meta(), category="robots", subpath="FrankaRobotics")

    assert result.ok
    assert result.data.category == "robots"
    assert result.data.subpath == "FrankaRobotics"
    assert len(result.data.items) == 2
    folders = [i for i in result.data.items if i.is_folder]
    files = [i for i in result.data.items if not i.is_folder]
    assert len(folders) == 1 and isinstance(folders[0], AssetItem)
    assert len(files) == 1 and files[0].name == "franka.usd"
    list_calls = [c for c in client.calls if c[0] == "asset_list"]
    assert list_calls[0][1]["category"] == "robots"


@pytest.mark.asyncio
async def test_asset_list_propagates_error():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def asset_list(self, **kwargs):  # type: ignore[override]
            raise RuntimeError("S3 directory listing failed")

    module = AssetModule(FailingClient())
    result = await module.list(_meta(), category="robots")

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ASSET_LIST_ERROR"
    assert "S3" in (result.message or "")
