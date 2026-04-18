"""Unit tests for the LogCaptureService ring buffer (Phase D).

Covers filtering logic and ring-buffer maxlen semantics without requiring
the live carb.logging hook (we call `_on_log` directly to simulate events).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest


# Load the in-Extension module directly without requiring the Kit import chain.
_SERVICE_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "isaac_extension"
    / "omni.mycompany.validation_api"
    / "omni" / "mycompany" / "validation_api"
    / "services" / "log_capture_service.py"
)
_spec = importlib.util.spec_from_file_location(
    "validation_api_log_capture_service", _SERVICE_PATH,
)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)
LogCaptureService = _mod.LogCaptureService


def _emit(svc: LogCaptureService, **overrides) -> None:
    """Simulate a carb hook event."""
    defaults = dict(
        source="omni.mycompany.ui_demo",
        level=-1,
        filename="extension.py",
        line_number=42,
        message="hello",
    )
    defaults.update(overrides)
    svc._on_log(**defaults)


def test_query_returns_all_without_filters():
    svc = LogCaptureService(maxlen=100)
    _emit(svc, message="one")
    _emit(svc, message="two")

    result = svc.query(level="ALL")
    assert result["count"] == 2
    msgs = [e["msg"] for e in result["entries"]]
    assert msgs == ["one", "two"]
    assert result["truncated"] is False


def test_level_filter_includes_higher_severities_only():
    svc = LogCaptureService()
    _emit(svc, level=-1, message="info entry")
    _emit(svc, level=0, message="warn entry")
    _emit(svc, level=1, message="error entry")

    warn_or_higher = svc.query(level="WARN")
    msgs = [e["msg"] for e in warn_or_higher["entries"]]
    assert "info entry" not in msgs
    assert "warn entry" in msgs
    assert "error entry" in msgs

    only_error = svc.query(level="ERROR")
    assert [e["msg"] for e in only_error["entries"]] == ["error entry"]


def test_source_filter_substring():
    svc = LogCaptureService()
    _emit(svc, source="omni.mycompany.ui_demo", message="mine")
    _emit(svc, source="omni.kit.app", message="kit")

    result = svc.query(level="ALL", source_filter="omni.mycompany")
    assert [e["msg"] for e in result["entries"]] == ["mine"]
    assert result["source_filter"] == "omni.mycompany"


def test_since_ms_drops_older_entries(monkeypatch):
    svc = LogCaptureService()
    current = {"t": 1_700_000_000_000}

    def fake_time():
        return current["t"] / 1000.0

    # Monkeypatch the module's time so ts_ms is deterministic.
    monkeypatch.setattr(_mod.time, "time", fake_time)

    _emit(svc, message="old")
    current["t"] = 1_700_000_005_000
    _emit(svc, message="new")

    result = svc.query(since_ms=1_700_000_003_000, level="ALL")
    assert [e["msg"] for e in result["entries"]] == ["new"]


def test_limit_truncates_and_flags():
    svc = LogCaptureService(maxlen=100)
    for i in range(5):
        _emit(svc, message=f"m{i}")

    result = svc.query(level="ALL", limit=3)
    assert result["count"] == 3
    assert result["truncated"] is True
    assert [e["msg"] for e in result["entries"]] == ["m0", "m1", "m2"]


def test_maxlen_drops_oldest_entries():
    svc = LogCaptureService(maxlen=3)
    for i in range(5):
        _emit(svc, message=f"m{i}")

    assert svc.size() == 3
    msgs = [e["msg"] for e in svc.query(level="ALL")["entries"]]
    # Oldest two should have been pushed out of the deque.
    assert msgs == ["m2", "m3", "m4"]


def test_clear_empties_buffer():
    svc = LogCaptureService()
    _emit(svc)
    _emit(svc)
    assert svc.size() == 2

    n = svc.clear()
    assert n == 2
    assert svc.size() == 0


def test_start_is_idempotent():
    """Double-start must be a no-op; we do not have carb in this env, so
    the `start()` path should silently tolerate the import failure."""
    svc = LogCaptureService()
    svc.start()  # carb is absent in the test env — no-op branch runs
    svc.start()  # must not explode
    assert svc._handle is None  # never wired up
    svc.stop()  # idempotent
    svc.stop()


def test_level_name_unknown_falls_through():
    svc = LogCaptureService()
    _emit(svc, level=42, message="weird level")
    entries = svc.query(level="ALL")["entries"]
    assert entries[0]["level"].startswith("LEVEL_")
    assert entries[0]["level_int"] == 42


def test_on_log_swallows_bad_arguments():
    """carb hook must never raise — malformed args are logged silently."""
    svc = LogCaptureService()
    # Intentionally pass a non-stringifiable source (object without __str__ override behaves).
    svc._on_log(source=None, level="not-an-int", filename=None, line_number=None, message=None)
    # level 'not-an-int' should fall through int cast to a 0-entry buffer.
    assert svc.size() == 0
