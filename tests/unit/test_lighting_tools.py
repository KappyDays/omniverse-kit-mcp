"""Unit tests for LightingModule + lighting_* MCP tool registration (Phase F)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig
from isaacsim_mcp.mcp.server import create_mcp_server
from isaacsim_mcp.modules.lighting_module import LightingModule
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from isaacsim_mcp.types.lighting import (
    LightingCreateDiskRequest,
    LightingCreateDistantRequest,
    LightingCreateDomeRequest,
    LightingCreateRectRequest,
    LightingCreateResult,
    LightingCreateSphereRequest,
    LightingSetExposureRequest,
    LightingSetExposureResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="test", module=ModuleName.LIGHTING, started_at_epoch_ms=0,
    )


# --- Tool registration -----------------------------------------------------


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_lighting_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    for tool in (
        "lighting_create_dome",
        "lighting_create_distant",
        "lighting_create_disk",
        "lighting_create_rect",
        "lighting_create_sphere",
        "lighting_set_exposure",
    ):
        assert tool in names, f"{tool} not registered"


def test_lighting_enum_registered():
    assert ModuleName.LIGHTING.value == "lighting"


# --- Module unit tests -----------------------------------------------------


@pytest.mark.asyncio
async def test_create_dome_with_texture():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = LightingModule(client)
    request = LightingCreateDomeRequest(
        prim_path="/World/Lights/Dome",
        intensity=1500.0,
        texture="kloofendal_48d_partly_cloudy.hdr",
    )
    result = await module.create_dome(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, LightingCreateResult)
    assert result.data.light_type == "DomeLight"
    assert result.data.intensity == 1500.0
    assert result.data.extra["texture"] == "kloofendal_48d_partly_cloudy.hdr"


@pytest.mark.asyncio
async def test_create_distant_light():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = LightingModule(client)
    request = LightingCreateDistantRequest(
        prim_path="/World/Lights/Sun", intensity=2000.0, angle_deg=1.0,
    )
    result = await module.create_distant(_meta(), request)

    assert result.ok
    assert result.data.light_type == "DistantLight"
    assert result.data.extra["angle_deg"] == 1.0


@pytest.mark.asyncio
async def test_create_disk_light():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = LightingModule(client)
    request = LightingCreateDiskRequest(
        prim_path="/World/Lights/Disk", intensity=800.0, radius=0.5,
    )
    result = await module.create_disk(_meta(), request)

    assert result.ok
    assert result.data.light_type == "DiskLight"
    assert result.data.extra["radius"] == 0.5


@pytest.mark.asyncio
async def test_create_rect_light():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = LightingModule(client)
    request = LightingCreateRectRequest(
        prim_path="/World/Lights/Window",
        intensity=1200.0, width=2.0, height=3.0,
    )
    result = await module.create_rect(_meta(), request)

    assert result.ok
    assert result.data.light_type == "RectLight"
    assert result.data.extra["width"] == 2.0
    assert result.data.extra["height"] == 3.0


@pytest.mark.asyncio
async def test_create_sphere_light():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = LightingModule(client)
    request = LightingCreateSphereRequest(
        prim_path="/World/Lights/Bulb", intensity=500.0, radius=0.1,
    )
    result = await module.create_sphere(_meta(), request)

    assert result.ok
    assert result.data.light_type == "SphereLight"
    assert result.data.extra["radius"] == 0.1


@pytest.mark.asyncio
@pytest.mark.parametrize("exposure", [-2.0, 0.0, 1.5])
async def test_set_exposure(exposure):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = LightingModule(client)
    request = LightingSetExposureRequest(exposure=exposure)
    result = await module.set_exposure(_meta(), request)

    assert result.ok
    assert isinstance(result.data, LightingSetExposureResult)
    assert result.data.exposure == exposure
    assert result.data.setting_path == "/rtx/post/tonemap/exposure"


@pytest.mark.asyncio
async def test_create_dome_propagates_client_error():
    class BrokenClient:
        async def lighting_create(self, _kind, _req):
            raise RuntimeError("ext offline")

    module = LightingModule(BrokenClient())  # type: ignore[arg-type]
    request = LightingCreateDomeRequest(prim_path="/World/Lights/Dome")
    result = await module.create_dome(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert "DOMELIGHT" in (result.error_code or "")
