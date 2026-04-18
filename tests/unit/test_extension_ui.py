"""Unit tests for Phase D ExtensionModule UI / log additions."""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.extension_module import ExtensionModule
from isaacsim_mcp.types.common import ModuleName, OperationMeta
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def ext_module(mock_client):
    return ExtensionModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(
        request_id="test",
        module=ModuleName.EXTENSION,
        started_at_epoch_ms=1000,
    )


# --- extension_activate --------------------------------------------------

@pytest.mark.asyncio
async def test_activate_success(ext_module, mock_client, meta):
    result = await ext_module.activate(meta, ext_id="omni.mycompany.ui_demo")
    assert result.ok is True
    assert result.data is not None
    assert result.data.ext_id == "omni.mycompany.ui_demo"
    assert result.data.enabled is True
    # No-op reload by default
    assert result.data.reloaded is False

    # Client payload carries reload flag unchanged
    name, payload = mock_client.calls[-1]
    assert name == "extension_activate"
    assert payload == {"ext_id": "omni.mycompany.ui_demo", "reload": False}


@pytest.mark.asyncio
async def test_activate_with_reload(ext_module, mock_client, meta):
    mock_client.responses["extension_activate"] = {
        "ok": True,
        "ext_id": "omni.mycompany.ui_demo",
        "was_enabled": True,
        "enabled": True,
        "reloaded": True,
    }
    result = await ext_module.activate(
        meta, ext_id="omni.mycompany.ui_demo", reload=True,
    )
    assert result.ok is True
    assert result.data.was_enabled is True
    assert result.data.reloaded is True


@pytest.mark.asyncio
async def test_activate_unknown_ext(ext_module, mock_client, meta):
    async def _boom(*_a, **_kw):
        raise RuntimeError("HTTP 400 — unknown ext_id")
    mock_client.extension_activate = _boom
    result = await ext_module.activate(meta, ext_id="does.not.exist")
    assert result.ok is False
    assert result.error_code == "EXTENSION_ACTIVATE_ERROR"


# --- extension_get_ui_tree -----------------------------------------------

@pytest.mark.asyncio
async def test_get_ui_tree_default_payload(ext_module, mock_client, meta):
    result = await ext_module.get_ui_tree(meta, window="UI Demo")
    assert result.ok is True
    tree = result.data
    assert tree is not None
    assert tree.window == "UI Demo"
    assert "UI Demo" in tree.matched_windows
    assert tree.widget_count == 2
    assert len(tree.widgets) == 2
    # Widget fields materialize correctly
    button = tree.widgets[0]
    assert button.type == "Button"
    assert button.enabled is True
    assert button.value is None
    stringfield = tree.widgets[1]
    assert stringfield.type == "StringField"
    assert stringfield.value == ""

    # Verify client was called with the right query
    name, payload = mock_client.calls[-1]
    assert name == "extension_ui_tree"
    assert payload == {"ext_id": None, "window": "UI Demo"}


@pytest.mark.asyncio
async def test_get_ui_tree_no_window_lists_windows(ext_module, mock_client, meta):
    mock_client.responses["extension_ui_tree"] = {
        "ok": True,
        "ext_id": None,
        "window": None,
        "matched_windows": [],
        "windows": [
            {"title": "Viewport", "visible": True, "docked": False},
            {"title": "Stage", "visible": True, "docked": True},
        ],
        "widgets": [],
        "widget_count": 0,
        "walk_errors": [],
    }
    result = await ext_module.get_ui_tree(meta)
    assert result.ok is True
    assert result.data.widget_count == 0
    titles = [w.title for w in result.data.windows]
    assert titles == ["Viewport", "Stage"]


# --- extension_ui_invoke -------------------------------------------------

@pytest.mark.asyncio
async def test_ui_invoke_click(ext_module, mock_client, meta):
    result = await ext_module.ui_invoke(
        meta,
        widget_path="UI Demo//Frame/VStack/Button[0]",
        action="click",
    )
    assert result.ok is True
    assert result.data.action_performed == "click"
    assert result.data.post_state.type == "Button"
    # click→label "Clicked 1 times" from default mock
    assert "Clicked" in result.data.post_state.label


@pytest.mark.asyncio
async def test_ui_invoke_type_with_value(ext_module, mock_client, meta):
    mock_client.responses["extension_ui_invoke"] = {
        "ok": True,
        "widget_path": "UI Demo//Frame/VStack/StringField[0]",
        "action_performed": "type",
        "value": "hello",
        "post_state": {
            "path": "UI Demo//Frame/VStack/StringField[0]",
            "label": "",
            "type": "StringField",
            "enabled": True,
            "visible": True,
            "value": "hello",
        },
    }
    result = await ext_module.ui_invoke(
        meta,
        widget_path="UI Demo//Frame/VStack/StringField[0]",
        action="type",
        value="hello",
    )
    assert result.ok is True
    assert result.data.action_performed == "type"
    assert result.data.value == "hello"
    assert result.data.post_state.value == "hello"

    _, payload = mock_client.calls[-1]
    assert payload == {
        "widget_path": "UI Demo//Frame/VStack/StringField[0]",
        "action": "type",
        "value": "hello",
    }


@pytest.mark.asyncio
async def test_ui_invoke_widget_not_found(ext_module, mock_client, meta):
    async def _boom(*_a, **_kw):
        raise RuntimeError("HTTP 400 — widget not found")
    mock_client.extension_ui_invoke = _boom
    result = await ext_module.ui_invoke(
        meta, widget_path="Bogus//x", action="click",
    )
    assert result.ok is False
    assert result.error_code == "EXTENSION_UI_INVOKE_ERROR"


# --- extension_capture_logs ----------------------------------------------

@pytest.mark.asyncio
async def test_capture_logs_default(ext_module, mock_client, meta):
    result = await ext_module.capture_logs(meta)
    assert result.ok is True
    logs = result.data
    assert logs.count == 1
    assert logs.truncated is False
    assert logs.level_filter == "INFO"
    entry = logs.entries[0]
    assert entry.level == "INFO"
    assert entry.source == "omni.mycompany.ui_demo"
    assert entry.msg == "hello"


@pytest.mark.asyncio
async def test_capture_logs_filter_passthrough(ext_module, mock_client, meta):
    await ext_module.capture_logs(
        meta, ext_id="omni.mycompany", since_ms=1_700_000_001_000, level="ERROR", limit=10,
    )
    name, payload = mock_client.calls[-1]
    assert name == "extension_logs"
    assert payload == {
        "ext_id": "omni.mycompany",
        "since_ms": 1_700_000_001_000,
        "level": "ERROR",
        "limit": 10,
    }


@pytest.mark.asyncio
async def test_capture_logs_error(ext_module, mock_client, meta):
    async def _boom(*_a, **_kw):
        raise RuntimeError("log hook dead")
    mock_client.extension_logs = _boom
    result = await ext_module.capture_logs(meta)
    assert result.ok is False
    assert result.error_code == "EXTENSION_LOGS_ERROR"
