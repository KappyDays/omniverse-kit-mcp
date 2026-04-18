"""Unit tests for WindowModule (Phase E)."""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.window_module import WindowModule
from isaacsim_mcp.types.common import ModuleName, OperationMeta
from isaacsim_mcp.types.window import WindowCaptureRequest
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def window_module(mock_client):
    return WindowModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(
        request_id="test", module=ModuleName.WINDOW, started_at_epoch_ms=1,
    )


@pytest.mark.asyncio
async def test_capture_default_mode(window_module, mock_client, meta):
    result = await window_module.capture(meta, WindowCaptureRequest())
    assert result.ok is True
    assert result.data.artifact_id == "win_abc"
    assert result.data.path == "/tmp/window_abc.png"
    assert result.data.mode == "kit"
    # Artifact path is exposed for the scenario engine
    assert result.artifacts == {"image": "/tmp/window_abc.png"}

    name, payload = mock_client.calls[-1]
    assert name == "window_capture"
    assert payload["mode"] == "kit"
    assert payload["wait_stable"] is False


@pytest.mark.asyncio
async def test_capture_wait_stable_passthrough(window_module, mock_client, meta):
    request = WindowCaptureRequest(
        wait_stable=True, stable_consecutive=3, stable_diff_threshold=0.005,
    )
    mock_client.responses["window_capture"] = {
        "ok": True, "artifact_id": "w", "path": "/t/w.png",
        "width": 1, "height": 1, "hwnd": 7, "title": "Kit", "class_name": "GLFW30",
        "mode": "kit", "used_printwindow": True, "used_bitblt_fallback": False,
        "sha256": "x", "wait_stable": True, "stabilized": True, "polls": 4,
        "last_diff": 0.003, "max_diff_seen": 0.02, "diff_threshold": 0.005,
        "diff_history": [0.1, 0.05, 0.01, 0.003],
    }
    result = await window_module.capture(meta, request)
    assert result.data.stabilized is True
    assert result.data.polls == 4
    assert result.data.diff_history == (0.1, 0.05, 0.01, 0.003)


@pytest.mark.asyncio
async def test_capture_error_maps(window_module, mock_client, meta):
    async def _boom(*a, **kw):
        raise RuntimeError("capture blew up")
    mock_client.window_capture = _boom
    result = await window_module.capture(meta, WindowCaptureRequest())
    assert result.ok is False
    assert result.error_code == "WINDOW_CAPTURE_ERROR"


@pytest.mark.asyncio
async def test_list_windows(window_module, meta):
    result = await window_module.list_windows(meta)
    assert result.ok is True
    assert result.data.pid == 1234
    assert result.data.count == 1
    assert result.data.windows[0].class_name == "GLFW30"


@pytest.mark.asyncio
async def test_list_ui_windows_filter(window_module, mock_client, meta):
    result = await window_module.list_ui_windows(meta, name_filter="Stage")
    assert result.ok is True
    name, payload = mock_client.calls[-1]
    assert name == "window_ui_list"
    assert payload == {"name_filter": "Stage"}


@pytest.mark.asyncio
async def test_show_ui_window(window_module, mock_client, meta):
    result = await window_module.show_ui_window(meta, name="Viewport", focus=False)
    assert result.ok is True
    assert result.data.found is True
    assert result.data.resolved_via == "exact"
    name, payload = mock_client.calls[-1]
    assert name == "window_ui_show"
    assert payload == {
        "name": "Viewport", "visible": True, "focus": False, "settle_frames": 5,
    }


@pytest.mark.asyncio
async def test_list_menu_items(window_module, meta):
    result = await window_module.list_menu_items(meta, menu_path="Window")
    assert result.ok is True
    assert result.data.count == 1
    item = result.data.items[0]
    assert item.onclick_action == ("omni.kit.viewport", "Viewport")


@pytest.mark.asyncio
async def test_trigger_menu_returns_created_prims(window_module, mock_client, meta):
    mock_client.responses["window_menu_trigger"] = {
        "ok": True, "menu_path": "Create/Mesh/Cube",
        "action": ["omni.kit.primitive.mesh", "CreateMeshPrim_Cube"],
        "created_prims": ["/World/Cube"],
    }
    result = await window_module.trigger_menu(meta, "Create/Mesh/Cube")
    assert result.ok is True
    assert result.data.created_prims == ("/World/Cube",)
    assert result.data.action == (
        "omni.kit.primitive.mesh", "CreateMeshPrim_Cube",
    )
