"""Unit tests for KitCommandModule — kit_command_execute + kit_python_run."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.kit_command_module import KitCommandModule
from omniverse_kit_mcp.types.common import ModuleName, OperationMeta
from omniverse_kit_mcp.types.kit_command import (
    KitCommandExecuteRequest,
    KitPythonExecRequest,
)
from tests.conftest import MockIsaacRestClient


@pytest.fixture
def mock_client():
    return MockIsaacRestClient()


@pytest.fixture
def module(mock_client):
    return KitCommandModule(mock_client)


@pytest.fixture
def meta():
    return OperationMeta(
        request_id="test",
        module=ModuleName.EXTENSION,
        started_at_epoch_ms=1000,
    )


# ---------------------------------------------------------------------------
# kit_command_execute (regression — pre-existing path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_command_execute_success(module, meta, mock_client):
    mock_client.responses["kit_command_execute"] = {
        "ok": True,
        "name": "ChangeProperty",
        "succeeded": True,
        "result": None,
    }
    result = await module.execute(
        meta,
        KitCommandExecuteRequest(name="ChangeProperty", payload={"path": "/x"}),
    )
    assert result.ok is True
    assert result.data.name == "ChangeProperty"
    assert result.data.succeeded is True


@pytest.mark.asyncio
async def test_command_execute_failure_propagates_error_code(module, meta, mock_client):
    mock_client.responses["kit_command_execute"] = {
        "ok": False,
        "name": "Bogus",
        "succeeded": False,
        "error": "command_exception",
        "message": "no such command",
    }
    result = await module.execute(
        meta, KitCommandExecuteRequest(name="Bogus")
    )
    assert result.ok is False
    assert result.error_code == "command_exception"
    assert "no such command" in (result.message or "")


# ---------------------------------------------------------------------------
# kit_python_run (new in this cycle)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_python_run_success_captures_stdout(module, meta, mock_client):
    mock_client.responses["kit_python_run"] = {
        "ok": True,
        "stdout": "hello\n",
        "stderr": "",
        "error": None,
        "traceback": None,
        "returned": {},
    }
    result = await module.python_run(
        meta, KitPythonExecRequest(code="print('hello')")
    )
    assert result.ok is True
    assert result.data.stdout == "hello\n"
    assert result.data.error is None


@pytest.mark.asyncio
async def test_python_run_returns_namespace_keys(module, meta, mock_client):
    """return_keys round-trip: caller asks for namespace var, mock echoes it back."""
    mock_client.responses["kit_python_run"] = {
        "ok": True,
        "stdout": "",
        "stderr": "",
        "error": None,
        "traceback": None,
        "returned": {"x": 42, "name": "world"},
    }
    result = await module.python_run(
        meta,
        KitPythonExecRequest(code="x = 42; name = 'world'", return_keys=("x", "name")),
    )
    assert result.ok is True
    assert result.data.returned == {"x": 42, "name": "world"}


@pytest.mark.asyncio
async def test_python_run_script_exception_becomes_error_payload(module, meta, mock_client):
    """Script exceptions don't raise — they're returned as ok=False with a traceback."""
    mock_client.responses["kit_python_run"] = {
        "ok": False,
        "stdout": "",
        "stderr": "",
        "error": "ValueError: bad",
        "traceback": "Traceback (most recent call last):\n  ValueError: bad",
        "returned": {},
    }
    result = await module.python_run(
        meta, KitPythonExecRequest(code="raise ValueError('bad')")
    )
    assert result.ok is False
    assert result.error_code == "KIT_PYTHON_EXEC_ERROR"
    assert "ValueError" in (result.message or "")


@pytest.mark.asyncio
async def test_python_run_passes_return_keys_to_client(module, meta, mock_client):
    """Module forwards return_keys list verbatim to the REST client."""
    mock_client.responses["kit_python_run"] = {
        "ok": True, "stdout": "", "stderr": "",
        "error": None, "traceback": None, "returned": {},
    }
    await module.python_run(
        meta, KitPythonExecRequest(code="pass", return_keys=("a", "b", "c"))
    )
    # Last recorded call must carry the requested keys (mock appends every call)
    assert any(
        kind == "kit_python_run" and payload["return_keys"] == ["a", "b", "c"]
        for kind, payload in mock_client.calls
    )
