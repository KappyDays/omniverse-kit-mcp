"""Integration tests for scenario runner with SimulationModule routing and
context-aware diff_snapshots dispatch.

Guards against regressions of the Phase-A fixes (B1/B2/B3) and the
`stage.diff_snapshots` context-aware action introduced in F3.
"""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.extension_module import ExtensionModule
from isaacsim_mcp.modules.lakehouse_module import LakehouseModule
from isaacsim_mcp.modules.simulation_module import SimulationModule
from isaacsim_mcp.modules.stage_module import StageModule
from isaacsim_mcp.modules.viewport_module import ViewportModule
from isaacsim_mcp.scenario.action_registry import (
    CONTEXT_AWARE_ACTIONS,
    build_request,
)
from isaacsim_mcp.scenario.compiler import compile_scenario
from isaacsim_mcp.scenario.runner import ScenarioRunner
from isaacsim_mcp.types.common import ExecutionStatus, ModuleName


def _build_runner(isaac_client, lakehouse_client):
    stage = StageModule(isaac_client)
    viewport = ViewportModule(isaac_client)
    lakehouse = LakehouseModule(lakehouse_client)
    extension = ExtensionModule(isaac_client)
    simulation = SimulationModule(isaac_client)
    return ScenarioRunner(stage, viewport, lakehouse, extension, simulation)


def test_action_registry_routes_stage_writes_to_simulation():
    """Stage WRITE actions must live under ModuleName.SIMULATION after B1 fix."""
    assert build_request(ModuleName.SIMULATION, "stage_load_usd", {"usd_url": "a.usd", "prim_path": "/World/X"}) is not None
    assert build_request(ModuleName.SIMULATION, "stage_set_property", {"prim_path": "/X", "property_name": "p", "value": 1}) is not None
    assert build_request(ModuleName.SIMULATION, "stage_create_prim", {"prim_path": "/X"}) is not None
    assert build_request(ModuleName.SIMULATION, "stage_delete_prim", {"prim_path": "/X"}) is not None
    # Stage WRITE entries should no longer exist under STAGE module
    assert build_request(ModuleName.STAGE, "load_usd", {}) is None
    assert build_request(ModuleName.STAGE, "create_prim", {}) is None


def test_scenario_runner_accepts_simulation_module():
    """ScenarioRunner must register SIMULATION in its module dispatch dict (B2 fix)."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())
    assert ModuleName.SIMULATION in runner._modules
    assert isinstance(runner._modules[ModuleName.SIMULATION], SimulationModule)


def test_module_enum_has_simulation():
    """B3 — ModuleName enum must include SIMULATION."""
    assert ModuleName.SIMULATION.value == "simulation"


def test_diff_snapshots_is_context_aware():
    """F3 — diff_snapshots action must be marked for context-aware dispatch."""
    assert (ModuleName.STAGE, "diff_snapshots") in CONTEXT_AWARE_ACTIONS


def test_diff_snapshots_builder_validates_required_args():
    """F3 builder must fail loudly if before_step_id/after_step_id are missing."""
    with pytest.raises(KeyError):
        build_request(ModuleName.STAGE, "diff_snapshots", {})


@pytest.mark.asyncio
async def test_simulation_create_prim_routes_through_runner():
    """End-to-end: YAML → compiler → runner → SimulationModule.stage_create_prim."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_routing", "name": "routing test"},
        "spec": {
            "assert": [
                {
                    "id": "create_x",
                    "module": "simulation",
                    "action": "stage_create_prim",
                    "args": {"prim_path": "/World/X", "prim_type": "Cube"},
                }
            ]
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    create_calls = [c for c in isaac_client.calls if c[0] == "stage_create_prim"]
    assert len(create_calls) == 1
    assert create_calls[0][1]["prim_path"] == "/World/X"


@pytest.mark.asyncio
async def test_diff_snapshots_resolves_prior_ctx_data():
    """F3 — runner must pull prior snapshot data from ScenarioContext."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    # Before snapshot — empty stage
    isaac_client.responses["stage_snapshot"] = {
        "prims": {},
        "root_layer_identifier": "test",
        "stage_identifier": "test",
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_diff", "name": "diff test"},
        "spec": {
            "arrange": [
                {"id": "snap_a", "module": "stage", "action": "capture_snapshot", "args": {}},
                {"id": "snap_b", "module": "stage", "action": "capture_snapshot", "args": {}},
            ],
            "assert": [
                {
                    "id": "diff_ab",
                    "module": "stage",
                    "action": "diff_snapshots",
                    "args": {
                        "before_step_id": "snap_a",
                        "after_step_id": "snap_b",
                        "max_changes": 0,
                    },
                }
            ],
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    # Two identical snapshots → 0 changes → max_changes=0 PASS
    assert summary.status == ExecutionStatus.PASSED, summary


@pytest.mark.asyncio
async def test_diff_snapshots_missing_before_step_errors_out():
    """F3 — referencing a non-existent step_id must produce a clear error."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_missing_snap", "name": "missing snap"},
        "spec": {
            "assert": [
                {
                    "id": "diff_missing",
                    "module": "stage",
                    "action": "diff_snapshots",
                    "args": {
                        "before_step_id": "no_such_step",
                        "after_step_id": "also_missing",
                    },
                }
            ],
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.FAILED
    diff_result = next(r for r in summary.step_results if r.step_id == "diff_missing")
    assert diff_result.status == ExecutionStatus.ERROR
    assert "no snapshot data" in (diff_result.message or "").lower()
