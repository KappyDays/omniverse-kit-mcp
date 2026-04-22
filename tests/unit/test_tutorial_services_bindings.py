"""Tests for isaac_tutorial.bindings.services."""

from __future__ import annotations

import sys
import types

import pytest

from omni.mycompany.isaac_tutorial.bindings import services as svc_mod


def _install_fake_rest_router(monkeypatch):
    """Install a fake validation_api.rest_router module with singleton attrs."""
    # Parent package
    pkg = types.ModuleType("omni.mycompany.validation_api")
    pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "omni.mycompany.validation_api", pkg)

    # rest_router with underscore-prefixed singletons
    rr = types.ModuleType("omni.mycompany.validation_api.rest_router")
    rr._stage = "fake_stage"
    rr._robot = "fake_robot"
    rr._character = "fake_character"
    rr._navigation = "fake_navigation"
    rr._sensor = "fake_sensor"
    rr._replicator = "fake_replicator"
    rr._simulation = "fake_simulation"
    rr._job = "fake_job"
    monkeypatch.setitem(sys.modules, "omni.mycompany.validation_api.rest_router", rr)
    pkg.rest_router = rr


def test_get_services_imports_rest_router_singletons(monkeypatch):
    _install_fake_rest_router(monkeypatch)
    svc_mod.reset_cache()

    svcs = svc_mod.get_services()
    assert svcs.stage == "fake_stage"
    assert svcs.robot == "fake_robot"
    assert svcs.character == "fake_character"
    assert svcs.navigation == "fake_navigation"
    assert svcs.sensor == "fake_sensor"
    assert svcs.replicator == "fake_replicator"
    assert svcs.simulation == "fake_simulation"
    assert svcs.jobs == "fake_job"


def test_get_services_caches(monkeypatch):
    _install_fake_rest_router(monkeypatch)
    svc_mod.reset_cache()

    first = svc_mod.get_services()
    second = svc_mod.get_services()
    assert first is second


def test_get_services_raises_if_validation_api_missing(monkeypatch):
    # Remove validation_api from sys.modules so ImportError fires
    for mod_name in list(sys.modules):
        if mod_name.startswith("omni.mycompany.validation_api"):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)
    svc_mod.reset_cache()

    with pytest.raises(RuntimeError, match="validation_api"):
        svc_mod.get_services()
