"""Unit tests for MaterialModule + material_* MCP tool registration (Phase F)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server
from isaacsim_mcp.modules.material_module import MaterialModule
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.material import (
    MaterialAssignMdlRequest,
    MaterialAssignMdlResult,
    MaterialGetBoundRequest,
    MaterialGetBoundResult,
    MaterialListMdlRequest,
    MaterialListMdlResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="test", module=ModuleName.MATERIAL, started_at_epoch_ms=0,
    )


# --- Tool registration -----------------------------------------------------


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_material_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    for tool in ("material_list_mdl", "material_assign_mdl", "material_get_bound"):
        assert tool in names, f"{tool} not registered"


def test_material_enum_registered():
    assert ModuleName.MATERIAL.value == "material"


# --- Module unit tests -----------------------------------------------------


@pytest.mark.asyncio
async def test_list_mdl_returns_entries():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = MaterialModule(client)
    result = await module.list_mdl(_meta(), MaterialListMdlRequest())

    assert result.ok
    assert isinstance(result.data, MaterialListMdlResult)
    assert result.data.count == 3
    names = {e.name for e in result.data.entries}
    assert "OmniPBR" in names
    assert "OmniGlass" in names


@pytest.mark.asyncio
async def test_assign_mdl_binds_to_prim():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = MaterialModule(client)
    request = MaterialAssignMdlRequest(
        prim_path="/World/Cube",
        mdl_url="OmniPBR.mdl",
        material_name="OmniPBR",
    )
    result = await module.assign_mdl(_meta(), request)

    assert result.ok
    assert isinstance(result.data, MaterialAssignMdlResult)
    assert result.data.material_prim_path == "/World/Materials/OmniPBR"
    assert result.data.mdl_url == "OmniPBR.mdl"


@pytest.mark.asyncio
async def test_get_bound_reads_binding():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = MaterialModule(client)
    result = await module.get_bound(
        _meta(), MaterialGetBoundRequest(prim_path="/World/Cube"),
    )

    assert result.ok
    assert isinstance(result.data, MaterialGetBoundResult)
    assert result.data.material_path == "/World/Materials/OmniPBR"
    assert result.data.binding_strength == "strongerThanDescendants"


@pytest.mark.asyncio
async def test_assign_mdl_propagates_client_error():
    class BrokenClient:
        async def material_assign_mdl(self, _req):
            raise RuntimeError("MDL library missing")

    module = MaterialModule(BrokenClient())  # type: ignore[arg-type]
    request = MaterialAssignMdlRequest(
        prim_path="/World/Cube", mdl_url="x.mdl", material_name="X",
    )
    result = await module.assign_mdl(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "MATERIAL_ASSIGN_MDL_ERROR"
