"""YAML scenario loader with JSON Schema validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
import yaml

from omniverse_kit_mcp.exceptions import ScenarioSchemaError
from omniverse_kit_mcp.scenario.schema import SCENARIO_SCHEMA


def load_scenario(path: str | Path) -> dict[str, Any]:
    """Load and validate a scenario YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Scenario file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ScenarioSchemaError(f"Expected YAML mapping, got {type(raw).__name__}")
    validate_schema(raw)
    return raw


def validate_schema(data: dict[str, Any]) -> None:
    """Validate scenario data against JSON Schema."""
    try:
        jsonschema.validate(instance=data, schema=SCENARIO_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise ScenarioSchemaError(f"Schema validation failed: {exc.message}") from exc


def list_scenarios(root_dir: str | Path) -> list[dict[str, Any]]:
    """List all scenario files under root_dir."""
    root = Path(root_dir)
    scenarios = []
    if not root.exists():
        return scenarios
    for yaml_file in sorted(root.rglob("*.yaml")):
        try:
            raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("kind") == "Scenario":
                meta = raw.get("metadata", {})
                scenarios.append({
                    "id": meta.get("id", yaml_file.stem),
                    "name": meta.get("name", ""),
                    "tags": meta.get("tags", []),
                    "path": str(yaml_file),
                })
        except Exception:
            continue
    return scenarios
