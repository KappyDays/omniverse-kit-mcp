"""Unit tests for Phase H extension management tools (deactivate / list_all / get_info)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server
from isaacsim_mcp.modules.extension_module import ExtensionModule
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.ui import (
    ExtensionDeactivateResult,
    ExtensionInfoResult,
    ExtensionListAllResult,
    ExtensionSummary,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="t", module=ModuleName.EXTENSION, started_at_epoch_ms=0,
    )


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_extension_ext_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "extension_deactivate" in names
    assert "extension_list_all" in names
    assert "extension_get_info" in names


@pytest.mark.asyncio
async def test_deactivate_flips_enabled_flag():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ExtensionModule(client)
    result = await module.deactivate(_meta(), "omni.kit.menu.utils")
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ExtensionDeactivateResult)
    assert result.data.ext_id == "omni.kit.menu.utils"
    assert result.data.was_enabled is True
    assert result.data.enabled is False


@pytest.mark.asyncio
async def test_list_all_returns_summaries():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ExtensionModule(client)
    result = await module.list_all(_meta(), enabled_only=False)
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ExtensionListAllResult)
    assert result.data.count == 2
    assert all(isinstance(e, ExtensionSummary) for e in result.data.extensions)


@pytest.mark.asyncio
async def test_list_all_enabled_only_propagates():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ExtensionModule(client)
    result = await module.list_all(_meta(), enabled_only=True)
    assert result.status is ExecutionStatus.PASSED
    # Our mock always returns 2 entries (doesn't filter); real backend filters —
    # we assert the flag propagated via the call log.
    assert client.calls[-1] == ("extension_list_all", {"enabled_only": True})


@pytest.mark.asyncio
async def test_get_info_returns_dict():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ExtensionModule(client)
    result = await module.get_info(_meta(), "omni.kit.menu.utils")
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ExtensionInfoResult)
    assert result.data.ext_id == "omni.kit.menu.utils"
    assert "version" in result.data.info
