"""Unit tests for scenario loader, compiler, and runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omniverse_kit_mcp.exceptions import ScenarioSchemaError
from omniverse_kit_mcp.scenario.compiler import compile_scenario
from omniverse_kit_mcp.scenario.loader import validate_schema
from omniverse_kit_mcp.scenario.schema import SCENARIO_SCHEMA
from omniverse_kit_mcp.tools.scenario_tools import _plan_step

PROJECT = Path(__file__).resolve().parents[2]


def test_validate_valid_scenario(sync_add_cube_scenario_raw):
    validate_schema(sync_add_cube_scenario_raw)


def test_validate_invalid_scenario_missing_metadata():
    with pytest.raises(ScenarioSchemaError):
        validate_schema({"apiVersion": "isaacsim.validation/v1", "kind": "Scenario", "spec": {"assert": []}})


def test_python_scenario_schema_matches_json_schema_file():
    disk_schema = json.loads(
        (PROJECT / "scenarios" / "schema" / "scenario.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert SCENARIO_SCHEMA == disk_schema


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


def test_plan_step_includes_idempotent_retry_metadata():
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "plan_retry", "name": "plan retry"},
        "spec": {
            "assert": [
                {
                    "id": "read_lidar",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "timeoutSeconds": 12.5,
                    "idempotent": True,
                    "continueOnFailure": True,
                    "retries": {
                        "maxAttempts": 3,
                        "initialBackoffSeconds": 0.25,
                        "maxBackoffSeconds": 1.0,
                    },
                    "args": {"sensor_prim": "/World/Lidar"},
                }
            ]
        },
    }
    scenario = compile_scenario(raw)

    planned = _plan_step(scenario.assert_steps[0])

    assert planned["args"] == {"sensor_prim": "/World/Lidar"}
    assert planned["timeoutSeconds"] == 12.5
    assert planned["idempotent"] is True
    assert planned["continueOnFailure"] is True
    assert planned["retries"] == {
        "maxAttempts": 3,
        "initialBackoffSeconds": 0.25,
        "maxBackoffSeconds": 1.0,
    }


def test_plan_step_elides_inherited_default_timeout():
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "plan_default_timeout", "name": "plan default timeout"},
        "spec": {
            "defaults": {"stepTimeoutSeconds": 45.0},
            "assert": [
                {
                    "id": "cube_exists",
                    "module": "stage",
                    "action": "assert_prim_exists",
                    "args": {"prim_path": "/World/Cube"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    planned = _plan_step(
        scenario.assert_steps[0],
        default_timeout_s=scenario.defaults.step_timeout_s,
    )

    assert "timeoutSeconds" not in planned
