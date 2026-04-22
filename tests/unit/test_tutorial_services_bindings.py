"""Tests for isaac_tutorial.bindings.services."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


_ext_root = Path(__file__).parent.parent.parent / "isaac_extension" / "omni.mycompany.isaac_tutorial"
_services_file = _ext_root / "omni" / "mycompany" / "isaac_tutorial" / "bindings" / "services.py"


def _create_namespace_pkg(name: str) -> types.ModuleType:
    """Create a namespace package."""
    pkg = types.ModuleType(name)
    pkg.__path__ = []
    return pkg


def _load_services_module():
    """Load services.py directly from the filesystem."""
    spec = importlib.util.spec_from_file_location("services", _services_file)
    services_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(services_mod)
    return services_mod


def _install_validation_api_services(monkeypatch) -> None:
    """validation_api.services.* 모듈을 fake 로 주입."""
    # Build validation_api namespace with all service modules
    validation_api = _create_namespace_pkg("omni.mycompany.validation_api")
    monkeypatch.setitem(sys.modules, "omni.mycompany.validation_api", validation_api)

    services_pkg = _create_namespace_pkg("omni.mycompany.validation_api.services")
    monkeypatch.setitem(sys.modules, "omni.mycompany.validation_api.services", services_pkg)

    # Create individual service modules with mock classes
    for name in [
        "stage_service", "robot_service", "character_service",
        "navigation_service", "sensor_service", "replicator_service",
        "simulation_service", "job_service",
    ]:
        mod = types.ModuleType(f"omni.mycompany.validation_api.services.{name}")
        cls_name = "".join(p.title() for p in name.split("_"))
        setattr(mod, cls_name, type(cls_name, (), {}))
        monkeypatch.setitem(sys.modules, mod.__name__, mod)
        setattr(services_pkg, name, mod)


def test_get_services_imports_all_services(monkeypatch):
    # Install fake validation_api
    _install_validation_api_services(monkeypatch)

    # Load services module directly
    services = _load_services_module()
    services._cached = None

    svcs = services.get_services()
    for attr in ["stage", "robot", "character", "navigation",
                 "sensor", "replicator", "simulation", "jobs"]:
        assert hasattr(svcs, attr), f"missing {attr}"


def test_get_services_caches(monkeypatch):
    # Install fake validation_api
    _install_validation_api_services(monkeypatch)

    # Load services module directly
    services = _load_services_module()
    services._cached = None

    first = services.get_services()
    second = services.get_services()
    assert first is second


def test_get_services_raises_if_validation_api_missing(monkeypatch):
    # DO NOT install validation_api — test that RuntimeError is raised
    # Clean up validation_api if it exists
    for mod_name in list(sys.modules):
        if mod_name.startswith("omni.mycompany.validation_api"):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)

    # Load services module directly
    services = _load_services_module()
    services._cached = None

    with pytest.raises(RuntimeError, match="validation_api"):
        services.get_services()
