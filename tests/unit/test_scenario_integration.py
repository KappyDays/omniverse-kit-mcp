"""Integration tests for scenario runner with SimulationModule routing and
context-aware diff_snapshots dispatch.

Guards against regressions of the Phase-A fixes (B1/B2/B3) and the
`stage.diff_snapshots` context-aware action introduced in F3.
"""

from __future__ import annotations

import pytest

from isaacsim_mcp.modules.asset_module import AssetModule
from isaacsim_mcp.modules.character_module import CharacterModule
from isaacsim_mcp.modules.extension_module import ExtensionModule
from isaacsim_mcp.modules.job_module import JobModule
from isaacsim_mcp.modules.lakehouse_module import LakehouseModule
from isaacsim_mcp.modules.robot_module import RobotModule
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
    from isaacsim_mcp.modules.lighting_module import LightingModule
    from isaacsim_mcp.modules.material_module import MaterialModule
    from isaacsim_mcp.modules.navigation_module import NavigationModule
    from isaacsim_mcp.modules.physics_module import PhysicsModule
    from isaacsim_mcp.modules.sensor_module import SensorModule
    from isaacsim_mcp.modules.window_module import WindowModule

    stage = StageModule(isaac_client)
    viewport = ViewportModule(isaac_client)
    lakehouse = LakehouseModule(lakehouse_client)
    extension = ExtensionModule(isaac_client)
    simulation = SimulationModule(isaac_client)
    robot = RobotModule(isaac_client)
    job = JobModule(isaac_client)
    asset = AssetModule(isaac_client)
    character = CharacterModule(isaac_client)
    window = WindowModule(isaac_client)
    navigation = NavigationModule(isaac_client)
    sensor = SensorModule(isaac_client)
    physics = PhysicsModule(isaac_client)
    lighting = LightingModule(isaac_client)
    material = MaterialModule(isaac_client)
    return ScenarioRunner(
        stage, viewport, lakehouse, extension, simulation, robot, job, asset, character,
        window, navigation, sensor, physics, lighting, material,
    )


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


# ---------------------------------------------------------------------------
# Phase B: Robot + Job routing + context-aware job.status
# ---------------------------------------------------------------------------

def test_module_enum_has_robot_and_job():
    assert ModuleName.ROBOT.value == "robot"
    assert ModuleName.JOB.value == "job"


def test_action_registry_has_robot_builders():
    assert build_request(
        ModuleName.ROBOT, "load", {"usd_url": "a.usd", "prim_path": "/World/R"}
    ) is not None
    assert build_request(
        ModuleName.ROBOT, "navigate_to",
        {"prim_path": "/World/R", "target": [1.0, 0.0, 0.0]},
    ) is not None
    assert build_request(
        ModuleName.ROBOT, "set_joint_positions",
        {"prim_path": "/X", "positions": [0.0]},
    ) is not None
    # get_joint_positions is a single-arg call — kwargs fallback suffices
    assert build_request(ModuleName.ROBOT, "get_joint_positions", {"prim_path": "/X"}) is None


def test_job_status_is_context_aware():
    assert (ModuleName.JOB, "status") in CONTEXT_AWARE_ACTIONS


@pytest.mark.asyncio
async def test_robot_set_joint_positions_routes_through_runner():
    """robot.set_joint_positions uses **kwargs fallback — verify round-trip."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_set_joints", "name": "robot joints"},
        "spec": {
            "assert": [
                {
                    "id": "set_joints",
                    "module": "robot",
                    "action": "set_joint_positions",
                    "args": {"prim_path": "/World/R", "positions": [0.1, 0.2, 0.3]},
                }
            ]
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    set_calls = [c for c in isaac_client.calls if c[0] == "robot_set_joint_positions"]
    assert len(set_calls) == 1
    assert set_calls[0][1]["positions"] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_job_status_resolves_navigate_step_id_from_context():
    """job.status context-aware: navigate_step_id → prior RobotNavigateResult.job_id."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    isaac_client.responses["robot_navigate"] = {
        "ok": True,
        "job_id": "j_ctx_resolved",
        "prim_path": "/World/R",
        "target": [1.0, 0.0, 0.0],
    }
    isaac_client.responses["job_status"] = {
        "job_id": "j_ctx_resolved",
        "status": "done",
        "progress": 1.0,
        "result": {"final_position": [1.0, 0.0, 0.0]},
        "error": None,
        "created_at_epoch_ms": 1000,
        "updated_at_epoch_ms": 2000,
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_job_ctx", "name": "job ctx"},
        "spec": {
            "act": [
                {
                    "id": "nav",
                    "module": "robot",
                    "action": "navigate_to",
                    "args": {"prim_path": "/World/R", "target": [1.0, 0.0, 0.0]},
                }
            ],
            "assert": [
                {
                    "id": "wait_job",
                    "module": "job",
                    "action": "status",
                    "args": {
                        "navigate_step_id": "nav",
                        "expected_status": "done",
                        "poll_interval_s": 0.01,
                        "max_polls": 5,
                    },
                }
            ],
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    job_calls = [c for c in isaac_client.calls if c[0] == "job_status"]
    assert len(job_calls) >= 1
    assert job_calls[0][1]["job_id"] == "j_ctx_resolved"


@pytest.mark.asyncio
async def test_asset_list_routes_through_runner():
    """asset.list uses kwargs fallback — verify YAML → module round-trip."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_asset", "name": "asset catalog"},
        "spec": {
            "assert": [
                {
                    "id": "browse",
                    "module": "asset",
                    "action": "list",
                    "args": {"category": "robots", "subpath": "FrankaRobotics"},
                }
            ]
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    list_calls = [c for c in isaac_client.calls if c[0] == "asset_list"]
    assert len(list_calls) == 1
    assert list_calls[0][1]["category"] == "robots"
    assert list_calls[0][1]["subpath"] == "FrankaRobotics"


@pytest.mark.asyncio
async def test_job_status_fails_on_unexpected_status():
    """job.status with expected_status mismatch → FAILED step."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    isaac_client.responses["job_status"] = {
        "job_id": "j_err",
        "status": "error",
        "progress": 0.0,
        "result": None,
        "error": "simulated failure",
        "created_at_epoch_ms": 1000,
        "updated_at_epoch_ms": 2000,
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_job_err", "name": "job err"},
        "spec": {
            "assert": [
                {
                    "id": "wait",
                    "module": "job",
                    "action": "status",
                    "args": {
                        "job_id": "j_err",
                        "expected_status": "done",
                        "poll_interval_s": 0.01,
                        "max_polls": 3,
                    },
                }
            ]
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.FAILED, summary
    step_result = next(r for r in summary.step_results if r.step_id == "wait")
    assert step_result.status == ExecutionStatus.FAILED
    assert "error" in (step_result.message or "").lower()


# ---------------------------------------------------------------------------
# Phase C: Character routing
# ---------------------------------------------------------------------------

def test_module_enum_has_character():
    """Phase C — ModuleName enum must include CHARACTER."""
    assert ModuleName.CHARACTER.value == "character"


def test_scenario_runner_accepts_character_module():
    """ScenarioRunner must register CHARACTER in its module dispatch dict."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient
    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())
    assert ModuleName.CHARACTER in runner._modules
    assert isinstance(runner._modules[ModuleName.CHARACTER], CharacterModule)


@pytest.mark.asyncio
async def test_character_load_routes_through_runner():
    """End-to-end: YAML module:'character' action:'load' → runner → CharacterModule.load → mock REST."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_char_routing", "name": "char routing test"},
        "spec": {
            "assert": [
                {
                    "id": "load_char",
                    "module": "character",
                    "action": "load",
                    "args": {
                        "usd_url": "https://example/biped.usd",
                        "prim_path": "/World/Characters/c_1",
                        "position": [0.0, 0.0, 0.0],
                        "yaw": 0.0,
                    },
                }
            ]
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)
    assert summary.status == ExecutionStatus.PASSED, summary
    load_calls = [c for c in isaac_client.calls if c[0] == "character_load"]
    assert len(load_calls) == 1
    assert load_calls[0][1]["prim_path"] == "/World/Characters/c_1"


@pytest.mark.asyncio
async def test_character_navigate_to_job_status_context_aware():
    """character.navigate_to → context-aware job.status resolves job_id from CharacterNavigateResult."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    isaac_client.responses["character_navigate"] = {
        "ok": True,
        "job_id": "job_char_xyz",
        "prim_path": "/World/Characters/c_1",
        "target": [1.0, 0.0, 0.0],
    }
    # Stub job_status to return terminal "done" on first poll
    isaac_client.responses["job_status"] = {
        "job_id": "job_char_xyz",
        "status": "done",
        "progress": 1.0,
        "result": {"final_position": [1.0, 0.0, 0.0], "elapsed_s": 0.5},
        "error": None,
        "created_at_epoch_ms": 1000,
        "updated_at_epoch_ms": 2000,
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_char_nav_job", "name": "char nav job test"},
        "spec": {
            "act": [
                {
                    "id": "nav",
                    "module": "character",
                    "action": "navigate_to",
                    "args": {
                        "prim_path": "/World/Characters/c_1",
                        "target": [1.0, 0.0, 0.0],
                        "speed": 1.0,
                    },
                },
                {
                    "id": "wait_nav",
                    "module": "job",
                    "action": "status",
                    "args": {
                        "navigate_step_id": "nav",
                        "expected_status": "done",
                        "poll_interval_s": 0.01,
                        "max_polls": 5,
                    },
                },
            ],
            "assert": [
                {
                    "id": "noop",
                    "module": "stage",
                    "action": "assert_prim_exists",
                    "args": {"prim_path": "/World"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)
    assert summary.status == ExecutionStatus.PASSED, summary
    # Verify the job polling call used the character navigate's job_id
    job_calls = [c for c in isaac_client.calls if c[0] == "job_status"]
    assert len(job_calls) == 1
    assert job_calls[0][1]["job_id"] == "job_char_xyz"
