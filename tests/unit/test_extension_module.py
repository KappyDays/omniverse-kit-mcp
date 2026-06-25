"""Unit tests for ExtensionModule."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.extension_module import ExtensionModule
from omniverse_kit_mcp.types.common import ModuleName, OperationMeta
from omniverse_kit_mcp.types.extension import ExtensionResetRequest, ExtensionTriggerRequest
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def ext_module(mock_client):
    return ExtensionModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(request_id="test", module=ModuleName.EXTENSION, started_at_epoch_ms=1000)


@pytest.mark.asyncio
async def test_trigger_success(ext_module, meta):
    result = await ext_module.trigger(
        meta,
        ExtensionTriggerRequest(operation="sync_from_lakehouse", wait_for_idle=False),
    )
    assert result.ok is True
    assert result.data is not None
    assert result.data.last_operation == "sync_from_lakehouse"


@pytest.mark.asyncio
async def test_reset_success(ext_module, meta):
    result = await ext_module.reset(meta, ExtensionResetRequest())
    assert result.ok is True
    assert result.data is not None
    assert result.data.busy is False


@pytest.mark.asyncio
async def test_get_state(ext_module, meta):
    result = await ext_module.get_state(meta)
    assert result.ok is True
    assert result.data is not None
    assert result.data.enabled is True


@pytest.mark.asyncio
async def test_capture_logs_preserves_stop_metadata(ext_module, meta, mock_client):
    mock_client.responses["extension_logs"] = {
        "ok": True,
        "entries": [],
        "count": 0,
        "truncated": False,
        "level_filter": "WARN",
        "since_ms": None,
        "source_filter": None,
        "capture_running": True,
        "capture_stop_requested": True,
        "capture_stop_completed": False,
        "capture_stop_timed_out": True,
        "capture_stop_timeout_s": 1.0,
    }

    result = await ext_module.capture_logs(
        meta,
        level="WARN",
        stop_after_capture=True,
    )

    assert result.ok is True
    assert result.data is not None
    assert result.data.capture_running is True
    assert result.data.capture_stop_requested is True
    assert result.data.capture_stop_completed is False
    assert result.data.capture_stop_timed_out is True
    assert result.data.capture_stop_timeout_s == 1.0


@pytest.mark.asyncio
async def test_reload_clean_success(ext_module, meta):
    result = await ext_module.reload_clean(meta, "omni.mycompany.ui_demo")
    assert result.ok is True
    assert result.data is not None
    assert result.data.reloaded is True
    assert result.data.modules_purged == 3
    assert ("extension_reload_clean", {"ext_id": "omni.mycompany.ui_demo"}) in ext_module._client.calls
