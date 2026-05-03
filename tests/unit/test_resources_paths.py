"""Drift tests for MCP resources.

Resources (``isaacsim://...``) are off-schema — they don't inflate the
session-start tool list — but they do point at source files that can move
over time. These tests guarantee:

1. The resource set registered on the MCP server matches the expected list
   (``EXPECTED_RESOURCES``).
2. Every file-backed resource's source file exists at the declared path
   (``RESOURCE_SOURCES``). If a source file moves, either update the
   mapping in ``src/omniverse_kit_mcp/mcp/resources.py`` or restore the file
   — the test catches the drift either way.
"""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.resources import RESOURCE_SOURCES
from omniverse_kit_mcp.mcp.server import create_mcp_server

EXPECTED_RESOURCES: frozenset[str] = frozenset({
    "isaacsim://tool-catalog",
    "isaacsim://sensor-menu",
    "isaacsim://scenario-schema",
    "isaacsim://scenarios",
})


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_registered_resources_match_expected(mcp_server):
    """Every resource in ``EXPECTED_RESOURCES`` is registered and nothing else."""
    registered = frozenset(
        str(uri) for uri in mcp_server._resource_manager._resources
    )
    missing = EXPECTED_RESOURCES - registered
    unexpected = registered - EXPECTED_RESOURCES
    assert not missing, f"Missing resources: {sorted(missing)}"
    assert not unexpected, f"Unexpected resources: {sorted(unexpected)}"


def test_resource_sources_mapping_covers_all_registered():
    """Every URI in ``EXPECTED_RESOURCES`` has an entry in RESOURCE_SOURCES."""
    missing = EXPECTED_RESOURCES - set(RESOURCE_SOURCES.keys())
    assert not missing, f"Missing in RESOURCE_SOURCES: {sorted(missing)}"


def test_file_backed_resources_have_existing_source():
    """File-backed resources (non-None source) must point at an existing file.

    Raised when ``docs/tool-catalog.md`` or
    ``docs/references/sensor_menu_catalog.md`` moves without a matching
    mapping update.
    """
    missing = [
        (uri, path)
        for uri, path in RESOURCE_SOURCES.items()
        if path is not None and not path.exists()
    ]
    assert not missing, (
        "Source files missing for resources: "
        + ", ".join(f"{uri} -> {path}" for uri, path in missing)
    )


def test_python_backed_resources_have_none_source():
    """Python-module-backed resources map to None (no file drift to check)."""
    assert RESOURCE_SOURCES["isaacsim://scenario-schema"] is None
