"""Unit tests for scenario loader, compiler, and runner."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.exceptions import ScenarioSchemaError
from omniverse_kit_mcp.scenario.compiler import compile_scenario
from omniverse_kit_mcp.scenario.loader import validate_schema
from omniverse_kit_mcp.scenario.schema import SCENARIO_SCHEMA


def test_validate_valid_scenario(sync_add_cube_scenario_raw):
    validate_schema(sync_add_cube_scenario_raw)


def test_validate_invalid_scenario_missing_metadata():
    with pytest.raises(ScenarioSchemaError):
        validate_schema({"apiVersion": "isaacsim.validation/v1", "kind": "Scenario", "spec": {"assert": []}})


def test_compile_scenario(sync_add_cube_scenario_raw):
    scenario = compile_scenario(sync_add_cube_scenario_raw)
    assert scenario.scenario_id == "sync_add_cube"
    assert scenario.name == "Test: Sync Add Cube"
    assert len(scenario.assert_steps) == 1
    assert scenario.assert_steps[0].id == "cube_exists"
    assert scenario.assert_steps[0].action == "assert_prim_exists"


def test_compile_variable_substitution(sync_add_cube_scenario_raw):
    scenario = compile_scenario(sync_add_cube_scenario_raw)
    step = scenario.assert_steps[0]
    assert step.args["prim_path"] == "/World/Cube"


def test_compile_defaults(sync_add_cube_scenario_raw):
    scenario = compile_scenario(sync_add_cube_scenario_raw)
    assert scenario.defaults.step_timeout_s == 10.0
    assert scenario.defaults.fail_fast is True


def test_input_overrides_substitution(sync_add_cube_scenario_raw):
    """M-1: input_overrides should replace variables before compilation."""
    raw = sync_add_cube_scenario_raw.copy()
    raw["spec"] = {**raw["spec"]}
    raw["spec"]["variables"] = {**raw["spec"].get("variables", {}), "prim_path": "/World/Box"}
    scenario = compile_scenario(raw)
    assert scenario.assert_steps[0].args["prim_path"] == "/World/Box"
