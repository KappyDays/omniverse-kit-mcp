"""Static MCP resources — off-schema reference material Claude can read on demand.

These are **not** tools. Each resource is exposed via the MCP `resources/list`
+ `resources/read` protocol, so its contents don't inflate the session-start
tool schema. Claude Code fetches a resource only when it decides the content
is relevant to the current task.

Adding resources here costs ~0 tokens at session start.

## Source-file drift
``tool_catalog`` and ``sensor_menu`` read from disk on every request, so edits
to the underlying markdown are picked up without restarting the MCP server.
``scenario_schema`` resolves ``SCENARIO_SCHEMA`` from Python import — schema
edits require an MCP server restart (import cache).

Resource URI → source mapping is also declared as :data:`RESOURCE_SOURCES`
so the drift test (``tests/unit/test_resources_paths.py``) can assert each
source file exists without spawning the server.
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.scenario.loader import list_scenarios
from omniverse_kit_mcp.scenario.schema import SCENARIO_SCHEMA

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# URI → (source_path, is_file_backed) for the drift test.
# Python-backed resources (None) skip the file-existence check.
RESOURCE_SOURCES: dict[str, Path | None] = {
    "isaacsim://tool-catalog": _PROJECT_ROOT / "docs" / "tool-catalog.md",
    "isaacsim://sensor-menu": _PROJECT_ROOT / "docs" / "references" / "sensor_menu_catalog.md",
    "isaacsim://asset-catalog": _PROJECT_ROOT / "docs" / "assets" / "isaac" / "asset_inventory.md",
    "isaacsim://scenario-schema": None,
    "isaacsim://scenarios": None,
}


def register_resources(mcp: FastMCP, config: AppConfig) -> None:
    """Register read-only documentation resources on the MCP server."""

    @mcp.resource(
        "isaacsim://tool-catalog",
        name="omniverse-kit-mcp Tool Catalog",
        description=(
            "Full live MCP tool catalog grouped by domain (Process / Stage / "
            "Simulation / Viewport / Sensor / Physics / Lighting / Material / "
            "Robot / Character / Navigation / Replicator / OmniGraph / Content "
            "/ Extension / Window / Asset / Lakehouse / Job / Scenario). Use "
            "when deciding which tool fits a given request."
        ),
        mime_type="text/markdown",
    )
    def tool_catalog() -> str:
        path = RESOURCE_SOURCES["isaacsim://tool-catalog"]
        assert path is not None  # file-backed
        if not path.exists():
            return (
                "# Tool catalog\n\n"
                f"(Source file missing: `{path}`. Run "
                "`scripts/generate_tool_catalog.py` or update "
                "`RESOURCE_SOURCES['isaacsim://tool-catalog']`.)"
            )
        return path.read_text(encoding="utf-8")

    @mcp.resource(
        "isaacsim://sensor-menu",
        name="Isaac Sim Create > Sensors Menu Catalog",
        description=(
            "Full Isaac Sim 5.1 Create > Sensors menu contents (RTX Lidar / "
            "Radar / Camera / Depth / PhysX Contact / IMU / LightBeam) by "
            "vendor × model. Source of truth when the user asks for a "
            "specific sensor — pair with window_menu_trigger."
        ),
        mime_type="text/markdown",
    )
    def sensor_menu() -> str:
        path = RESOURCE_SOURCES["isaacsim://sensor-menu"]
        assert path is not None  # file-backed
        if not path.exists():
            return (
                "# Sensor menu catalog\n\n"
                f"(Source file missing: `{path}`. Update "
                "`RESOURCE_SOURCES['isaacsim://sensor-menu']` or restore "
                "the file.)"
            )
        return path.read_text(encoding="utf-8")

    @mcp.resource(
        "isaacsim://asset-catalog",
        name="Isaac Sim NVIDIA Asset Catalog Index",
        description=(
            "READ FIRST before building a scene or adding any robot / "
            "character / environment / prop / SimReady asset — the curated "
            "NVIDIA / Isaac Sim 5.1 asset inventory (robots 100+, "
            "environments 10, people / animations, props, SimReady 1000+). "
            "Maps a request type to the catalog file that holds concrete USD "
            "URLs so you load a real NVIDIA asset (Validation Rule R1 — never "
            "substitute a primitive Cube/Sphere). Pair with the asset_search "
            "tool for natural-language lookup and docs/invariants/"
            "asset-discovery.md for the full discovery workflow."
        ),
        mime_type="text/markdown",
    )
    def asset_catalog() -> str:
        path = RESOURCE_SOURCES["isaacsim://asset-catalog"]
        assert path is not None  # file-backed
        if not path.exists():
            return (
                "# Asset catalog\n\n"
                f"(Source file missing: `{path}`. Update "
                "`RESOURCE_SOURCES['isaacsim://asset-catalog']` or restore "
                "the file.)"
            )
        return path.read_text(encoding="utf-8")

    @mcp.resource(
        "isaacsim://scenario-schema",
        name="Scenario YAML JSON Schema",
        description=(
            "JSON Schema for scenario YAML files (apiVersion / kind / metadata "
            "/ spec.{defaults,variables,arrange,act,assert,cleanup}). Use "
            "when authoring a new scenario YAML."
        ),
        mime_type="application/json",
    )
    def scenario_schema_resource() -> str:
        return json.dumps(SCENARIO_SCHEMA, indent=2, ensure_ascii=False)

    @mcp.resource(
        "isaacsim://scenarios",
        name="Available Scenario YAMLs",
        description=(
            "Live listing of validation scenario YAMLs (IDs, names, tags) "
            "from the configured scenarios directory. Use when picking a "
            "scenario to run via scenario_validate / scenario_plan."
        ),
        mime_type="application/json",
    )
    def scenarios_list_resource() -> str:
        scenarios = list_scenarios(config.scenario.scenarios_dir)
        return json.dumps(scenarios, indent=2, ensure_ascii=False)
