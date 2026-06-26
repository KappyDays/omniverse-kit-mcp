"""Integration tests for scenario runner with SimulationModule routing and
context-aware diff_snapshots dispatch.

Guards against regressions of the Phase-A fixes (B1/B2/B3) and the
`stage.diff_snapshots` context-aware action introduced in F3.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from omniverse_kit_mcp.modules.asset_module import AssetModule
from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.modules.extension_module import ExtensionModule
from omniverse_kit_mcp.modules.job_module import JobModule
from omniverse_kit_mcp.modules.lakehouse_module import LakehouseModule
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.modules.stage_module import StageModule
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.scenario.action_registry import (
    CONTEXT_AWARE_ACTIONS,
    build_request,
)
from omniverse_kit_mcp.scenario.compiler import compile_scenario
from omniverse_kit_mcp.scenario.loader import load_scenario
from omniverse_kit_mcp.scenario.reporters import (
    _redact_local_paths,
    to_json,
    to_markdown,
)
from omniverse_kit_mcp.scenario.runner import ScenarioRunner
from omniverse_kit_mcp.tools.scenario_tools import _scenario_plan_payload
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, ModuleResult
from omniverse_kit_mcp.types.scenario import ScenarioRunSummary, StepResult

PROJECT = Path(__file__).resolve().parents[2]


def _build_runner(isaac_client, lakehouse_client):
    from omniverse_kit_mcp.modules.content_module import ContentModule
    from omniverse_kit_mcp.modules.lighting_module import LightingModule
    from omniverse_kit_mcp.modules.material_module import MaterialModule
    from omniverse_kit_mcp.modules.navigation_module import NavigationModule
    from omniverse_kit_mcp.modules.omnigraph_module import OmnigraphModule
    from omniverse_kit_mcp.modules.physics_module import PhysicsModule
    from omniverse_kit_mcp.modules.replicator_module import ReplicatorModule
    from omniverse_kit_mcp.modules.sensor_module import SensorModule
    from omniverse_kit_mcp.modules.window_module import WindowModule

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
    replicator = ReplicatorModule(isaac_client)
    omnigraph = OmnigraphModule(isaac_client)
    content = ContentModule(isaac_client)
    return ScenarioRunner(
        stage, viewport, lakehouse, extension, simulation, robot, job, asset, character,
        window, navigation, sensor, physics, lighting, material,
        replicator, omnigraph, content,
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


def test_extension_trigger_smoke_marks_potential_stage_mutation():
    raw = load_scenario(PROJECT / "scenarios" / "smoke" / "trigger_sync_cube.yaml")

    plan = _scenario_plan_payload(compile_scenario(raw))

    mutation_steps = {step["id"]: step for step in plan["stage_mutation_steps"]}
    assert plan["stage_mutation_summary"] == {
        "read_only": False,
        "requires_scratch_stage": True,
        "mutation_count": 1,
        "phase_counts": {
            "arrange": 0,
            "act": 1,
            "assert": 0,
            "cleanup": 0,
        },
        "mutation_kinds": ["extension_trigger_potential_stage_effect"],
    }
    assert mutation_steps == {
        "sync_extension": {
            "id": "sync_extension",
            "phase": "act",
            "module": "extension",
            "action": "trigger",
            "mutation_kind": "extension_trigger_potential_stage_effect",
            "key_args": {
                "operation": "sync_from_lakehouse",
                "wait_for_idle": True,
                "idle_timeout_s": 30,
            },
        }
    }


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


def test_markdown_highlights_bounded_raw_key_samples():
    summary = ScenarioRunSummary(
        scenario_id="bounded_raw_keys",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read_lidar",
                phase="act",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "num_points": 512,
                    "backend": "omni.replicator.core",
                    "frames_waited": 60,
                    "raw_keys": {
                        "count": 17,
                        "sample": ["azimuth", "channelId", "data"],
                    },
                    "warning": None,
                    "truncated": True,
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)

    assert (
        "- `read_lidar`: num_points=512; backend=omni.replicator.core; "
        "frames_waited=60; raw_keys.count=17; "
        "raw_keys.sample=[azimuth, channelId, data]; warning=null; "
        "truncated=True"
    ) in markdown


def test_markdown_stabilizes_python_object_repr_in_highlights():
    render_product = (
        "<omni.replicator.core.scripts.utils.viewport_manager.HydraTexture "
        "object at 0x00000262619C1D00>"
    )
    summary = ScenarioRunSummary(
        scenario_id="stable_object_repr",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="capture_visible_result",
                phase="assert",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "passed": True,
                    "render_product": render_product,
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)
    report = json.loads(to_json(summary))

    assert "object at 0x" not in markdown
    assert (
        "render_product=<omni.replicator.core.scripts.utils.viewport_manager."
        "HydraTexture object>"
    ) in markdown
    assert report["step_results"][0]["data_summary"]["render_product"] == render_product


def test_markdown_escapes_step_result_table_cells():
    summary = ScenarioRunSummary(
        scenario_id="table_escape",
        status=ExecutionStatus.FAILED,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read|lidar",
                phase="assert",
                status=ExecutionStatus.FAILED,
                message="bridge | retry\nline two",
                duration_ms=5,
                retry_failures=(
                    {
                        "attempt": 1,
                        "status": "failed",
                        "error_code": "ERR_PIPE",
                        "message": "first | failure\nwith detail",
                    },
                ),
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)
    report = json.loads(to_json(summary))

    assert "## Failure Summary" in markdown
    assert (
        "- `read|lidar`: phase=assert; status=failed; attempts=1/1; "
        "message=bridge | retry<br>line two; last_retry=(attempt=1; "
        "status=failed; error_code=ERR_PIPE; message=first | "
        "failure<br>with detail)"
    ) in markdown
    assert (
        "| read\\|lidar | assert | failed | 1/1 | 5ms | "
        "bridge \\| retry<br>line two |"
    ) in markdown
    assert (
        "- `read|lidar` attempt 1: failed ERR_PIPE - "
        "first | failure<br>with detail"
    ) in markdown
    assert report["failure_summary"] == [{
        "step_id": "read|lidar",
        "phase": "assert",
        "status": "failed",
        "display_status": "failed",
        "continued": False,
        "cleanup": False,
        "attempts": 1,
        "max_attempts": 1,
        "retry_failure_count": 1,
        "message": "bridge | retry\nline two",
        "last_retry_failure": {
            "attempt": 1,
            "status": "failed",
            "error_code": "ERR_PIPE",
            "message": "first | failure\nwith detail",
        },
    }]


def test_markdown_escapes_list_code_spans_and_highlight_newlines():
    summary = ScenarioRunSummary(
        scenario_id="list_escape",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read`lidar",
                phase="assert",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "num_points": 1,
                    "warning": "first line\nsecond line",
                },
            ),
        ),
        artifact_paths=("capture`path\nframe.png",),
    )

    markdown = to_markdown(summary)

    assert (
        "- ``read`lidar``: num_points=1; "
        "warning=first line<br>second line"
    ) in markdown
    assert "- ``capture`path<br>frame.png``" in markdown


def test_reporters_can_redact_host_local_artifact_paths():
    capture_path = (
        "C:" + "/Users/" + "localuser"
        + "/AppData/Local/Temp/validation_api_captures/capture_abcd1234.png"
    )
    log_path = (
        "C:" + "/Users/" + "localuser"
        + "/AppData/Local/Temp/omniverse_kit_mcp/kit_123.log"
    )
    generic_path = (
        "C:" + "/Users/" + "localuser"
        + "/workspace/branch/isaac-sim/kit/kit.exe"
    )
    inline_pid = 42123
    inline_json_pid = 42128
    inline_json_process_id = 42129
    data_pid = 42123
    data_process_id = "42124"
    child_pids = [42125, 42126]
    nested_kit_pid = 42127
    summary = ScenarioRunSummary(
        scenario_id="public_safe_report",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="capture_visible_result",
                phase="assert",
                status=ExecutionStatus.PASSED,
                message=(
                    f"capture saved at {capture_path}; pid={inline_pid}; "
                    "thread_id=thread-example-7f3a; "
                    "worker_thread_id=worker-thread-message; "
                    "pending_worktree_id=pw_message; "
                    '{"pendingWorktreeId": "pw_json"}; '
                    "{'worker_thread_id': 'worker-thread-json'}; "
                    f'{{"pid": {inline_json_pid}}}; '
                    f'{{"process_id": "{inline_json_process_id}"}}'
                ),
                artifacts={"image": capture_path},
                data_summary={
                    "artifact": {
                        "path": capture_path,
                        "sha256": "abc123",
                    },
                    "path": capture_path,
                    "log": log_path,
                    "kit_exe": generic_path,
                    "pid": data_pid,
                    "process_id": data_process_id,
                    "child_pids": child_pids,
                    "nested": {"kit_pid": nested_kit_pid},
                    "thread_id": "thread-example-7f3a",
                    "worker_id": "worker-example",
                    "pendingWorktreeId": "pw_12345",
                    "nested_ids": {"worker_thread_id": "worker-thread-123"},
                    "passed": True,
                },
            ),
        ),
        artifact_paths=(capture_path,),
    )

    report = json.loads(to_json(summary, redact_local_paths=True))
    serialized = json.dumps(report)
    message = report["step_results"][0]["message"]
    markdown = to_markdown(summary, redact_local_paths=True)

    assert "<validation-api-capture>/capture_abcd1234.png" in serialized
    assert "<local-kit-log>/kit_123.log" in serialized
    assert "<local-user-path>" in serialized
    assert "C:" not in serialized
    assert "42123" not in serialized
    assert "42124" not in serialized
    assert "42125" not in serialized
    assert "42126" not in serialized
    assert "42127" not in serialized
    assert "thread-example-7f3a" not in serialized
    assert "worker-example" not in serialized
    assert "pw_12345" not in serialized
    assert "pw_message" not in serialized
    assert "pw_json" not in serialized
    assert "worker-thread-123" not in serialized
    assert "worker-thread-json" not in serialized
    assert "worker-thread-message" not in serialized
    assert "42128" not in serialized
    assert "42129" not in serialized
    assert '"pid": "<process-id>"' in serialized
    assert '"process_id": "<process-id>"' in serialized
    assert '"thread_id": "<worker-thread-id>"' in serialized
    assert '"worker_id": "<worker-thread-id>"' in serialized
    assert '"pendingWorktreeId": "<worker-thread-id>"' in serialized
    assert '"pendingWorktreeId": "<worker-thread-id>"' in message
    assert "'worker_thread_id': '<worker-thread-id>'" in message
    assert '"pid": <process-id>' in message
    assert '"process_id": "<process-id>"' in message
    assert "<validation-api-capture>/capture_abcd1234.png" in markdown
    assert "<local-kit-log>/kit_123.log" in markdown
    assert "<local-user-path>" in markdown
    assert "C:" not in markdown
    assert "42123" not in markdown
    assert "42124" not in markdown
    assert "42125" not in markdown
    assert "42126" not in markdown
    assert "42127" not in markdown
    assert "thread-example-7f3a" not in markdown
    assert "worker-example" not in markdown
    assert "pw_12345" not in markdown
    assert "pw_message" not in markdown
    assert "pw_json" not in markdown
    assert "worker-thread-123" not in markdown
    assert "worker-thread-json" not in markdown
    assert "worker-thread-message" not in markdown
    assert "42128" not in markdown
    assert "42129" not in markdown
    assert "pid=<process-id>" in markdown
    assert "thread_id=<worker-thread-id>" in markdown
    assert "worker_thread_id=<worker-thread-id>" in markdown
    assert "pending_worktree_id=<worker-thread-id>" in markdown
    assert '"pendingWorktreeId": "<worker-thread-id>"' in markdown
    assert "'worker_thread_id': '<worker-thread-id>'" in markdown
    assert '"pid": <process-id>' in markdown
    assert '"process_id": "<process-id>"' in markdown


def test_redact_local_paths_handles_nested_runtime_identifiers():
    capture_path = (
        "C:" + "/Users/" + "localuser"
        + "/AppData/Local/Temp/validation_api_captures/capture_tuple.png"
    )
    log_path = (
        "C:" + "/Users/" + "localuser"
        + "/AppData/Local/Temp/omniverse_kit_mcp/kit_789.log"
    )
    workspace_path = "C:" + "/Users/" + "localuser" + "/workspace/scene.usd"
    sanitized_path = "C--Users-" + "localuser" + "-AppData-Local-Temp-scene"
    process_value = 50123
    child_pid_values = (50124, 50125)
    message_pid = "50126"
    message_process_value = "50127"

    redacted = _redact_local_paths(
        {
            "tuple_paths": (
                capture_path,
                log_path,
                workspace_path,
                sanitized_path,
            ),
            "nested": [
                {"pid": process_value, "child_pids": child_pid_values},
                {
                    "threadIds": ("worker-alpha", "worker-beta"),
                    "pendingWorktreeIds": ["pending-alpha"],
                },
            ],
            "message": (
                "pid=" + message_pid + " process_id=\"" + message_process_value + "\" "
                "thread_id=worker-message pendingWorktreeId:pending-message"
            ),
        }
    )
    serialized = json.dumps(redacted)

    assert redacted["tuple_paths"] == [
        "<validation-api-capture>/capture_tuple.png",
        "<local-kit-log>/kit_789.log",
        "<local-user-path>",
        "<local-user-path>",
    ]
    assert redacted["nested"][0]["pid"] == "<process-id>"
    assert redacted["nested"][0]["child_pids"] == [
        "<process-id>",
        "<process-id>",
    ]
    assert redacted["nested"][1]["threadIds"] == [
        "<worker-thread-id>",
        "<worker-thread-id>",
    ]
    assert redacted["nested"][1]["pendingWorktreeIds"] == [
        "<worker-thread-id>"
    ]
    assert "pid=<process-id>" in redacted["message"]
    assert 'process_id="<process-id>"' in redacted["message"]
    assert "thread_id=<worker-thread-id>" in redacted["message"]
    assert "pendingWorktreeId:<worker-thread-id>" in redacted["message"]
    for raw in (
        str(process_value),
        *(str(value) for value in child_pid_values),
        message_pid,
        message_process_value,
        "worker-alpha",
        "worker-beta",
        "pending-alpha",
        "worker-message",
        "pending-message",
        "localuser",
    ):
        assert raw not in serialized


def test_official_verify_evidence_summary_redacts_public_sensitive_fields():
    capture_path = (
        "C:" + "/Users/" + "localuser"
        + "/AppData/Local/Temp/validation_api_captures/capture_material_verify.png"
    )
    log_path = (
        "C:" + "/Users/" + "localuser"
        + "/AppData/Local/Temp/omniverse_kit_mcp/kit_456.log"
    )
    material_process_id = 42130
    thread_id = "12345678" + "-1234-4234-9234-123456789abc"
    pending_id = "019ef2d4" + "-51c3-7533-9c65-decd64e4fa40"
    summary = ScenarioRunSummary(
        scenario_id="official_verify_public_safe_report",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="verify_unbound_material",
                phase="assert",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "id": (
                        "url:https://omniverse-content-production.s3-us-west-2."
                        "amazonaws.com/Assets/Materials/2023_2_1/Base/Metals/"
                        "Brushed_Aluminum.mdl"
                    ),
                    "kind": "material",
                    "name": "Brushed_Aluminum.mdl",
                    "canonical_url": (
                        "https://omniverse-content-production.s3-us-west-2."
                        "amazonaws.com/Assets/Materials/2023_2_1/Base/Metals/"
                        "Brushed_Aluminum.mdl"
                    ),
                    "material_name": "Brushed_Aluminum",
                    "app_profile": "usd-composer",
                    "verification_status": "failed",
                    "attempt": 2,
                    "timeout_s": 1.0,
                    "error": (
                        f"binding failed at {capture_path}; process_id={material_process_id}; "
                        f"thread_id={thread_id}"
                    ),
                    "diagnostics": {
                        "reason": "material_assign_or_binding_failed",
                        "target_status": "assign_verified",
                        "current_catalog_status": "assign_verified",
                        "suggested_next": [
                            f"inspect {log_path}",
                            f"retry pendingWorktreeId={pending_id}",
                        ],
                        "fallback_tool_order": [
                            "official_asset_sync_status",
                            "official_asset_search",
                            "official_asset_resolve",
                            "official_asset_verify",
                            "asset_search",
                        ],
                        "material_checks": {
                            "create_prim_ok": True,
                            "assign_ok": True,
                            "bound_ok": False,
                            "worker_thread_id": "worker-thread-material-123",
                        },
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary, redact_local_paths=True))
    serialized = json.dumps(report)
    markdown = to_markdown(summary, redact_local_paths=True)
    evidence = report["evidence_summary"][0]

    assert evidence["evidence_kind"] == "official_asset_verify"
    assert evidence["verification_status"] == "failed"
    assert evidence["kind"] == "material"
    assert "<validation-api-capture>/capture_material_verify.png" in serialized
    assert "<local-kit-log>/kit_456.log" in serialized
    assert "process_id=<process-id>" in evidence["error"]
    assert "thread_id=<worker-thread-id>" in evidence["error"]
    assert evidence["diagnostics"]["material_checks"]["worker_thread_id"] == (
        "<worker-thread-id>"
    )
    for leaked in (
        capture_path,
        log_path,
        "42130",
        thread_id,
        pending_id,
        "worker-thread-material-123",
    ):
        assert leaked not in serialized
        assert leaked not in markdown
    assert "## Evidence Summary" in markdown
    assert "evidence_kind=official_asset_verify" in markdown
    assert "<validation-api-capture>/capture_material_verify.png" in markdown
    assert "process_id=<process-id>" in markdown
    assert "thread_id=<worker-thread-id>" in markdown


def test_markdown_highlights_nested_diagnostic_reason_and_fallback():
    summary = ScenarioRunSummary(
        scenario_id="official_asset_diagnostics",
        status=ExecutionStatus.FAILED,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="find_asset",
                phase="arrange",
                status=ExecutionStatus.FAILED,
                data_summary={
                    "count": 0,
                    "diagnostics": {
                        "reason": "query_no_match",
                        "candidate_counts": {
                            "total_entries": 4,
                            "after_app_profile": 2,
                            "query_matches": 0,
                        },
                        "suggested_next": [
                            "Retry with a broader asset family.",
                            "Use asset_search if official search still misses.",
                        ],
                        "fallback_tool_order": [
                            "official_asset_sync_status",
                            "official_asset_search",
                            "official_asset_resolve",
                            "official_asset_verify",
                            "asset_search",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)
    report = json.loads(to_json(summary))
    find_asset = report["step_results"][0]

    assert (
        "- `find_asset`: diagnostics.reason=query_no_match; "
        "diagnostics.candidate_counts.total_entries=4; "
        "diagnostics.candidate_counts.after_app_profile=2; "
        "diagnostics.candidate_counts.query_matches=0; "
        "suggested_next=[Retry with a broader asset family., "
        "Use asset_search if official search still misses.]; "
        "diagnostics.fallback_tool_order=[official_asset_sync_status, "
        "official_asset_search, official_asset_resolve, official_asset_verify, "
        "asset_search]; count=0"
    ) in markdown
    assert "## Diagnostic Next Actions" in markdown
    assert (
        "- `find_asset`: diagnostics.reason=query_no_match; "
        "suggested_next=[Retry with a broader asset family., "
        "Use asset_search if official search still misses.]; "
        "diagnostics.fallback_tool_order=[official_asset_sync_status, "
        "official_asset_search, official_asset_resolve, official_asset_verify, "
        "asset_search]"
    ) in markdown
    assert find_asset["diagnostic_next_actions"] == {
        "diagnostics.reason": "query_no_match",
        "suggested_next": [
            "Retry with a broader asset family.",
            "Use asset_search if official search still misses.",
        ],
        "diagnostics.fallback_tool_order": [
            "official_asset_sync_status",
            "official_asset_search",
            "official_asset_resolve",
            "official_asset_verify",
            "asset_search",
        ],
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "find_asset",
        "phase": "arrange",
        "source": "step",
        "status": "failed",
        **find_asset["diagnostic_next_actions"],
    }]


def test_markdown_highlights_sync_status_profile_diagnostics():
    summary = ScenarioRunSummary(
        scenario_id="sync_status_diagnostics",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="check_catalog_profile",
                phase="arrange",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "app_profile": "kit-app",
                    "profile_count": 0,
                    "diagnostics": {
                        "reason": "app_profile_not_covered",
                        "requested_app_profile": "kit-app",
                        "available_profiles": ["isaac-sim", "usd-composer"],
                        "available_providers": ["omni.simready.explorer"],
                        "matching_item_count": 0,
                        "suggested_next": [
                            "Call official_asset_sync_status without app_profile.",
                        ],
                        "fallback_tool_order": [
                            "official_asset_sync_status",
                            "official_asset_search",
                            "asset_search",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)
    report = json.loads(to_json(summary))

    assert (
        "- `check_catalog_profile`: "
        "diagnostics.reason=app_profile_not_covered; "
        "diagnostics.requested_app_profile=kit-app; "
        "diagnostics.available_profiles=[isaac-sim, usd-composer]; "
        "diagnostics.available_providers=[omni.simready.explorer]; "
        "diagnostics.matching_item_count=0"
    ) in markdown
    assert "profile_count=0" in markdown
    assert (
        "- `check_catalog_profile`: diagnostics.reason=app_profile_not_covered; "
        "suggested_next=[Call official_asset_sync_status without app_profile.]; "
        "diagnostics.fallback_tool_order=[official_asset_sync_status, "
        "official_asset_search, asset_search]"
    ) in markdown
    assert report["step_results"][0]["diagnostic_next_actions"][
        "diagnostics.reason"
    ] == "app_profile_not_covered"
    assert report["diagnostic_next_actions"][0]["source"] == "step"


def test_markdown_highlights_official_asset_bounded_diagnostic_details():
    summary = ScenarioRunSummary(
        scenario_id="official_asset_bounded_diagnostics",
        status=ExecutionStatus.FAILED,
        passed_steps=1,
        failed_steps=2,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="search_assets",
                phase="arrange",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "count": 0,
                    "diagnostics": {
                        "reason": "query_no_match",
                        "available_kinds": ["asset", "material"],
                        "status_counts": {"failed": 2, "load_verified": 1},
                        "sample_names": ["Pallet", "Brushed Metal"],
                        "suggested_next": ["Retry with a broader query."],
                        "fallback_tool_order": [
                            "official_asset_sync_status",
                            "official_asset_search",
                            "asset_search",
                        ],
                    },
                },
            ),
            StepResult(
                step_id="verify_asset",
                phase="assert",
                status=ExecutionStatus.FAILED,
                data_summary={
                    "diagnostics": {
                        "reason": "asset_load_quality_failed",
                        "target_status": "load_verified",
                        "current_catalog_status": "failed",
                        "error_type": "TimeoutError",
                        "asset_checks": {
                            "load_quality": "invalid_empty_content",
                            "bbox_valid": False,
                            "bbox_validation_reasons": ["bbox_invalid"],
                            "has_authored_children": False,
                            "has_default_prim": False,
                            "prim_count_valid": False,
                        },
                        "suggested_next": ["Inspect load_quality before retry."],
                        "fallback_tool_order": ["official_asset_get", "asset_search"],
                    },
                },
            ),
            StepResult(
                step_id="verify_material",
                phase="assert",
                status=ExecutionStatus.FAILED,
                data_summary={
                    "diagnostics": {
                        "reason": "material_assign_or_binding_failed",
                        "target_status": "assign_verified",
                        "current_catalog_status": "url_validated",
                        "material_checks": {
                            "create_prim_ok": True,
                            "assign_ok": True,
                            "bound_ok": False,
                        },
                        "suggested_next": ["Check material binding readback."],
                        "fallback_tool_order": ["official_asset_get", "asset_search"],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)
    report = json.loads(to_json(summary))
    verify_asset = report["step_results"][1]
    verify_material = report["step_results"][2]

    assert "diagnostics.available_kinds=[asset, material]" in markdown
    assert (
        'diagnostics.status_counts={"failed":2,"load_verified":1}'
        in markdown
    )
    assert "diagnostics.sample_names=[Pallet, Brushed Metal]" in markdown
    assert "diagnostics.target_status=load_verified" in markdown
    assert "diagnostics.current_catalog_status=failed" in markdown
    assert "diagnostics.error_type=TimeoutError" in markdown
    assert "diagnostics.asset_checks.load_quality=invalid_empty_content" in markdown
    assert "diagnostics.asset_checks.bbox_valid=False" in markdown
    assert (
        "diagnostics.asset_checks.bbox_validation_reasons=[bbox_invalid]"
        in markdown
    )
    assert "diagnostics.asset_checks.has_authored_children=False" in markdown
    assert "diagnostics.asset_checks.has_default_prim=False" in markdown
    assert "diagnostics.asset_checks.prim_count_valid=False" in markdown
    assert "diagnostics.material_checks.create_prim_ok=True" in markdown
    assert "diagnostics.material_checks.assign_ok=True" in markdown
    assert "diagnostics.material_checks.bound_ok=False" in markdown
    assert verify_asset["diagnostic_next_actions"] == {
        "diagnostics.reason": "asset_load_quality_failed",
        "diagnostics.target_status": "load_verified",
        "diagnostics.current_catalog_status": "failed",
        "diagnostics.error_type": "TimeoutError",
        "suggested_next": ["Inspect load_quality before retry."],
        "diagnostics.fallback_tool_order": ["official_asset_get", "asset_search"],
        "diagnostics.asset_checks": {
            "load_quality": "invalid_empty_content",
            "bbox_valid": False,
            "bbox_validation_reasons": ["bbox_invalid"],
            "has_authored_children": False,
            "has_default_prim": False,
            "prim_count_valid": False,
        },
    }
    assert verify_material["diagnostic_next_actions"] == {
        "diagnostics.reason": "material_assign_or_binding_failed",
        "diagnostics.target_status": "assign_verified",
        "diagnostics.current_catalog_status": "url_validated",
        "suggested_next": ["Check material binding readback."],
        "diagnostics.fallback_tool_order": ["official_asset_get", "asset_search"],
        "diagnostics.material_checks": {
            "create_prim_ok": True,
            "assign_ok": True,
            "bound_ok": False,
        },
    }
    assert any(
        action["step_id"] == "verify_asset"
        and action["diagnostics.asset_checks"]["load_quality"]
        == "invalid_empty_content"
        for action in report["diagnostic_next_actions"]
    )
    assert (
        'diagnostics.asset_checks={"load_quality":"invalid_empty_content",'
        '"bbox_valid":false'
    ) in markdown
    assert (
        'diagnostics.material_checks={"create_prim_ok":true,'
        '"assign_ok":true,"bound_ok":false}'
    ) in markdown


def test_report_does_not_promote_reason_only_diagnostics_to_next_actions():
    summary = ScenarioRunSummary(
        scenario_id="reason_only_diagnostics",
        status=ExecutionStatus.FAILED,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read_lidar",
                phase="assert",
                status=ExecutionStatus.FAILED,
                data_summary={
                    "num_points": 0,
                    "diagnostics": {
                        "reason": "empty_scan_buffer",
                        "readback_paths_attempted": [
                            "cached_lidar_sensor",
                            "replicator_annotator",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)

    assert report["diagnostic_next_actions"] == []
    assert "diagnostic_next_actions" not in report["step_results"][0]
    assert "## Diagnostic Next Actions" not in markdown


def test_report_surfaces_lidar_warning_next_actions():
    summary = ScenarioRunSummary(
        scenario_id="lidar_warning_next_actions",
        status=ExecutionStatus.FAILED,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read_lidar",
                phase="assert",
                status=ExecutionStatus.FAILED,
                error_code="SENSOR_LIDAR_POINT_CLOUD_WARNING",
                data_summary={
                    "num_points": 3,
                    "warning": "partial scan buffer",
                    "raw_keys": ["data"],
                    "diagnostics": {
                        "reason": "lidar_warning",
                        "suggested_next": [
                            "Step more simulation frames before retrying the lidar read.",
                            "Inspect raw_keys and WARN/ERROR logs if the warning persists.",
                        ],
                        "fallback_tool_order": [
                            "simulation_step",
                            "sensor_lidar_get_point_cloud",
                            "extension_capture_logs",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)
    step = report["step_results"][0]

    assert step["diagnostic_next_actions"] == {
        "diagnostics.reason": "lidar_warning",
        "suggested_next": [
            "Step more simulation frames before retrying the lidar read.",
            "Inspect raw_keys and WARN/ERROR logs if the warning persists.",
        ],
        "diagnostics.fallback_tool_order": [
            "simulation_step",
            "sensor_lidar_get_point_cloud",
            "extension_capture_logs",
        ],
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "read_lidar",
        "phase": "assert",
        "source": "step",
        "status": "failed",
        "error_code": "SENSOR_LIDAR_POINT_CLOUD_WARNING",
        **step["diagnostic_next_actions"],
    }]
    assert "## Diagnostic Next Actions" in markdown
    assert "diagnostics.reason=lidar_warning" in markdown
    assert "extension_capture_logs" in markdown


def test_report_surfaces_lidar_read_error_next_actions():
    summary = ScenarioRunSummary(
        scenario_id="lidar_read_error_next_actions",
        status=ExecutionStatus.ERROR,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read_lidar",
                phase="assert",
                status=ExecutionStatus.ERROR,
                error_code="SENSOR_LIDAR_GET_POINT_CLOUD_ERROR",
                data_summary={
                    "ok": False,
                    "sensor_prim": "/World/Cam",
                    "num_points": 0,
                    "frames_waited": 0,
                    "diagnostics": {
                        "reason": "lidar_read_error",
                        "upstream_error_code": (
                            "SENSOR_LIDAR_GET_POINT_CLOUD_ERROR"
                        ),
                        "upstream_message": "not rtx_lidar",
                        "num_points": 0,
                        "min_points": 0,
                        "suggested_next": [
                            (
                                "Confirm the prim is an RTX lidar created by "
                                "sensor_attach_rtx_lidar."
                            ),
                            (
                                "Step more simulation frames, then retry "
                                "sensor_lidar_get_point_cloud."
                            ),
                        ],
                        "fallback_tool_order": [
                            "simulation_step",
                            "sensor_lidar_get_point_cloud",
                            "extension_capture_logs",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)
    step = report["step_results"][0]

    assert step["diagnostic_next_actions"] == {
        "diagnostics.reason": "lidar_read_error",
        "diagnostics.num_points": 0,
        "diagnostics.min_points": 0,
        "suggested_next": [
            (
                "Confirm the prim is an RTX lidar created by "
                "sensor_attach_rtx_lidar."
            ),
            (
                "Step more simulation frames, then retry "
                "sensor_lidar_get_point_cloud."
            ),
        ],
        "diagnostics.fallback_tool_order": [
            "simulation_step",
            "sensor_lidar_get_point_cloud",
            "extension_capture_logs",
        ],
        "diagnostics.upstream_error_code": "SENSOR_LIDAR_GET_POINT_CLOUD_ERROR",
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "read_lidar",
        "phase": "assert",
        "source": "step",
        "status": "error",
        "error_code": "SENSOR_LIDAR_GET_POINT_CLOUD_ERROR",
        **step["diagnostic_next_actions"],
    }]
    assert "## Diagnostic Next Actions" in markdown
    assert "diagnostics.reason=lidar_read_error" in markdown
    assert (
        "diagnostics.upstream_error_code=SENSOR_LIDAR_GET_POINT_CLOUD_ERROR"
        in markdown
    )


def test_report_surfaces_pick_place_status_timeout_next_actions():
    summary = ScenarioRunSummary(
        scenario_id="pick_place_status_timeout_next_actions",
        status=ExecutionStatus.ERROR,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="check_pick_place_status",
                phase="assert",
                status=ExecutionStatus.ERROR,
                error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT",
                data_summary={
                    "ok": False,
                    "status": "timeout",
                    "last_error": (
                        "Franka pick-place demo status timed out after 0.5s"
                    ),
                    "diagnostics": {
                        "reason": "pick_place_demo_status_timeout",
                        "upstream_error_code": (
                            "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT"
                        ),
                        "timeout_s": 0.5,
                        "suggested_next": [
                            (
                                "Check simulation_get_status before treating "
                                "the proof loop as valid."
                            ),
                            (
                                "Retry robot_get_pick_place_demo_status with "
                                "a short timeout to confirm the status "
                                "endpoint recovers."
                            ),
                        ],
                        "fallback_tool_order": [
                            "simulation_get_status",
                            "robot_get_pick_place_demo_status",
                            "extension_capture_logs",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)
    step = report["step_results"][0]

    assert step["diagnostic_next_actions"] == {
        "diagnostics.reason": "pick_place_demo_status_timeout",
        "suggested_next": [
            "Check simulation_get_status before treating the proof loop as valid.",
            (
                "Retry robot_get_pick_place_demo_status with a short timeout "
                "to confirm the status endpoint recovers."
            ),
        ],
        "diagnostics.fallback_tool_order": [
            "simulation_get_status",
            "robot_get_pick_place_demo_status",
            "extension_capture_logs",
        ],
        "diagnostics.upstream_error_code": (
            "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT"
        ),
        "diagnostics.timeout_s": 0.5,
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "check_pick_place_status",
        "phase": "assert",
        "source": "step",
        "status": "error",
        "error_code": "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT",
        **step["diagnostic_next_actions"],
    }]
    assert "## Diagnostic Next Actions" in markdown
    assert "diagnostics.reason=pick_place_demo_status_timeout" in markdown
    assert "diagnostics.timeout_s=0.5" in markdown


def test_report_surfaces_pick_place_unsupported_next_actions():
    summary = ScenarioRunSummary(
        scenario_id="pick_place_unsupported_next_actions",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="install_pick_place_playback",
                phase="action",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "ok": False,
                    "status": "unsupported",
                    "profile_name": "ur10",
                    "support_status": "candidate_pick_place",
                    "diagnostics": {
                        "reason": "pick_place_profile_unsupported",
                        "target_status": "validated_pick_place",
                        "suggested_next": [
                            (
                                "Call robot_list_arm_profiles and choose a "
                                "support_status=validated_pick_place profile "
                                "before installing playback."
                            ),
                            (
                                "Use robot_probe_arm_profile only for "
                                "controllability evidence; probe success is "
                                "not pick/place validation."
                            ),
                        ],
                        "fallback_tool_order": [
                            "robot_list_arm_profiles",
                            "robot_probe_arm_profile",
                            "robot_install_pick_place_playback_demo",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)
    step = report["step_results"][0]

    assert step["diagnostic_next_actions"] == {
        "diagnostics.reason": "pick_place_profile_unsupported",
        "diagnostics.target_status": "validated_pick_place",
        "suggested_next": [
            (
                "Call robot_list_arm_profiles and choose a "
                "support_status=validated_pick_place profile before "
                "installing playback."
            ),
            (
                "Use robot_probe_arm_profile only for controllability "
                "evidence; probe success is not pick/place validation."
            ),
        ],
        "diagnostics.fallback_tool_order": [
            "robot_list_arm_profiles",
            "robot_probe_arm_profile",
            "robot_install_pick_place_playback_demo",
        ],
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "install_pick_place_playback",
        "phase": "action",
        "source": "step",
        "status": "passed",
        **step["diagnostic_next_actions"],
    }]
    assert "## Diagnostic Next Actions" in markdown
    assert "diagnostics.reason=pick_place_profile_unsupported" in markdown
    assert "diagnostics.target_status=validated_pick_place" in markdown
    assert (
        "diagnostics.fallback_tool_order=[robot_list_arm_profiles, "
        "robot_probe_arm_profile, robot_install_pick_place_playback_demo]"
    ) in markdown


def test_report_preserves_retry_next_action_status_and_error_code():
    summary = ScenarioRunSummary(
        scenario_id="retry_next_action_metadata",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read_lidar",
                phase="assert",
                status=ExecutionStatus.PASSED,
                attempts=2,
                max_attempts=3,
                data_summary={
                    "num_points": 12,
                    "diagnostics": {"reason": "scan_buffer_ready"},
                },
                retry_failures=(
                    {
                        "attempt": 1,
                        "status": "failed",
                        "error_code": "SENSOR_LIDAR_EMPTY",
                        "message": "first scan returned zero points",
                        "data_summary": {
                            "num_points": 0,
                            "empty_reason": "empty_scan_buffer",
                            "diagnostics": {
                                "reason": "empty_scan_buffer",
                                "suggested_next": [
                                    "Step simulation frames before another read."
                                ],
                                "fallback_tool_order": [
                                    "simulation_step",
                                    "sensor_lidar_get_point_cloud",
                                    "extension_capture_logs",
                                ],
                            },
                        },
                    },
                ),
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)
    retry_failure = report["step_results"][0]["retry_failures"][0]

    assert retry_failure["diagnostic_next_actions"] == {
        "diagnostics.reason": "empty_scan_buffer",
        "empty_reason": "empty_scan_buffer",
        "suggested_next": ["Step simulation frames before another read."],
        "diagnostics.fallback_tool_order": [
            "simulation_step",
            "sensor_lidar_get_point_cloud",
            "extension_capture_logs",
        ],
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "read_lidar",
        "phase": "assert",
        "source": "retry_failure",
        "status": "failed",
        "error_code": "SENSOR_LIDAR_EMPTY",
        "final_step_status": "passed",
        "attempt": 1,
        **retry_failure["diagnostic_next_actions"],
    }]
    assert (
        "- `read_lidar attempt 1`: diagnostics.reason=empty_scan_buffer; "
        "empty_reason=empty_scan_buffer; "
        "suggested_next=[Step simulation frames before another read.]; "
        "diagnostics.fallback_tool_order=[simulation_step, "
        "sensor_lidar_get_point_cloud, extension_capture_logs]"
    ) in markdown


def test_report_preserves_failed_step_next_action_error_code():
    summary = ScenarioRunSummary(
        scenario_id="failed_step_next_action_metadata",
        status=ExecutionStatus.FAILED,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="read_lidar",
                phase="act",
                status=ExecutionStatus.FAILED,
                message="point cloud contained fewer points than min_points",
                error_code="SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
                data_summary={
                    "num_points": 0,
                    "empty_reason": "empty_scan_buffer",
                    "diagnostics": {
                        "reason": "point_count_below_minimum",
                        "suggested_next": [
                            "Step simulation frames before another read."
                        ],
                        "fallback_tool_order": [
                            "simulation_step",
                            "sensor_lidar_get_point_cloud",
                            "extension_capture_logs",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    step_result = report["step_results"][0]

    assert step_result["error_code"] == "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    assert report["diagnostic_next_actions"] == [{
        "step_id": "read_lidar",
        "phase": "act",
        "source": "step",
        "status": "failed",
        "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
        **step_result["diagnostic_next_actions"],
    }]


def test_report_promotes_viewport_capture_assert_diagnostics():
    summary = ScenarioRunSummary(
        scenario_id="viewport_capture_assert_failure",
        status=ExecutionStatus.FAILED,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="capture_visible_result",
                phase="assert",
                status=ExecutionStatus.FAILED,
                message="Viewport capture assertion failed",
                error_code="VIEWPORT_CAPTURE_ASSERT_FAILED",
                data_summary={
                    "passed": False,
                    "artifact": {
                        "path": "/tmp/blank.png",
                        "sha256": "abc123",
                        "width": 1280,
                        "height": 720,
                        "pixel_mean": [0.0, 0.0, 0.0],
                        "pixel_variance": [0.0, 0.0, 0.0],
                        "warmup_frames_used": 8,
                    },
                    "pixel_mean_average": 0.0,
                    "pixel_variance_average": 0.0,
                    "failure_codes": [
                        "PIXEL_MEAN_BELOW_THRESHOLD",
                        "PIXEL_VARIANCE_BELOW_THRESHOLD",
                    ],
                    "diagnostics": {
                        "reason": "capture_blank_or_flat",
                        "failure_codes": [
                            "PIXEL_MEAN_BELOW_THRESHOLD",
                            "PIXEL_VARIANCE_BELOW_THRESHOLD",
                        ],
                        "pixel_mean_average": 0.0,
                        "pixel_variance_average": 0.0,
                        "min_mean": 8.0,
                        "min_variance": 1.0,
                        "suggested_next": [
                            "Frame the target prims with viewport_frame_prims, then retry viewport_capture_assert with warmup_frames > 0.",
                            "Add or brighten a DomeLight or DistantLight before retrying if the frame remains dark.",
                        ],
                        "fallback_tool_order": [
                            "simulation_get_status",
                            "viewport_frame_prims",
                            "viewport_capture_assert",
                            "extension_capture_logs",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)
    step_result = report["step_results"][0]

    assert step_result["diagnostic_next_actions"] == {
        "diagnostics.reason": "capture_blank_or_flat",
        "suggested_next": [
            "Frame the target prims with viewport_frame_prims, then retry viewport_capture_assert with warmup_frames > 0.",
            "Add or brighten a DomeLight or DistantLight before retrying if the frame remains dark.",
        ],
        "diagnostics.fallback_tool_order": [
            "simulation_get_status",
            "viewport_frame_prims",
            "viewport_capture_assert",
            "extension_capture_logs",
        ],
        "diagnostics.failure_codes": [
            "PIXEL_MEAN_BELOW_THRESHOLD",
            "PIXEL_VARIANCE_BELOW_THRESHOLD",
        ],
        "diagnostics.pixel_mean_average": 0.0,
        "diagnostics.pixel_variance_average": 0.0,
        "diagnostics.min_mean": 8.0,
        "diagnostics.min_variance": 1.0,
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "capture_visible_result",
        "phase": "assert",
        "source": "step",
        "status": "failed",
        "error_code": "VIEWPORT_CAPTURE_ASSERT_FAILED",
        **step_result["diagnostic_next_actions"],
    }]
    assert "## Diagnostic Next Actions" in markdown
    assert "diagnostics.reason=capture_blank_or_flat" in markdown
    assert (
        "diagnostics.fallback_tool_order=[simulation_get_status, "
        "viewport_frame_prims, viewport_capture_assert, extension_capture_logs]"
    ) in markdown
    assert "diagnostics.pixel_mean_average=0.0" in markdown
    assert "diagnostics.pixel_variance_average=0.0" in markdown
    assert "diagnostics.min_mean=8.0" in markdown
    assert "diagnostics.min_variance=1.0" in markdown


def test_report_promotes_viewport_capture_error_diagnostics():
    summary = ScenarioRunSummary(
        scenario_id="viewport_capture_assert_capture_error",
        status=ExecutionStatus.ERROR,
        passed_steps=0,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="capture_visible_result",
                phase="assert",
                status=ExecutionStatus.ERROR,
                message="viewport unavailable",
                error_code="VIEWPORT_CAPTURE_ERROR",
                data_summary={
                    "passed": False,
                    "artifact": None,
                    "pixel_mean_average": None,
                    "pixel_variance_average": None,
                    "failure_codes": ["VIEWPORT_CAPTURE_ERROR"],
                    "diagnostics": {
                        "reason": "capture_error",
                        "failure_codes": ["VIEWPORT_CAPTURE_ERROR"],
                        "upstream_error_code": "VIEWPORT_CAPTURE_ERROR",
                        "upstream_message": "viewport unavailable",
                        "pixel_mean_average": None,
                        "pixel_variance_average": None,
                        "min_mean": 8.0,
                        "min_variance": 1.0,
                        "suggested_next": [
                            (
                                "Confirm Isaac Sim is running in GUI mode "
                                "with simulation_get_status, then retry "
                                "viewport_capture_assert with warmup_frames > 0."
                            ),
                            (
                                "Frame target prims with viewport_frame_prims "
                                "and capture WARN/ERROR logs if the retry "
                                "still fails."
                            ),
                        ],
                        "fallback_tool_order": [
                            "simulation_get_status",
                            "viewport_frame_prims",
                            "viewport_capture_assert",
                            "extension_capture_logs",
                        ],
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    report = json.loads(to_json(summary))
    markdown = to_markdown(summary)
    step_result = report["step_results"][0]

    assert step_result["diagnostic_next_actions"] == {
        "diagnostics.reason": "capture_error",
        "suggested_next": [
            (
                "Confirm Isaac Sim is running in GUI mode with "
                "simulation_get_status, then retry viewport_capture_assert "
                "with warmup_frames > 0."
            ),
            (
                "Frame target prims with viewport_frame_prims and capture "
                "WARN/ERROR logs if the retry still fails."
            ),
        ],
        "diagnostics.fallback_tool_order": [
            "simulation_get_status",
            "viewport_frame_prims",
            "viewport_capture_assert",
            "extension_capture_logs",
        ],
        "diagnostics.failure_codes": ["VIEWPORT_CAPTURE_ERROR"],
        "diagnostics.upstream_error_code": "VIEWPORT_CAPTURE_ERROR",
        "diagnostics.min_mean": 8.0,
        "diagnostics.min_variance": 1.0,
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "capture_visible_result",
        "phase": "assert",
        "source": "step",
        "status": "error",
        "error_code": "VIEWPORT_CAPTURE_ERROR",
        **step_result["diagnostic_next_actions"],
    }]
    assert "## Diagnostic Next Actions" in markdown
    assert "diagnostics.reason=capture_error" in markdown
    assert "diagnostics.upstream_error_code=VIEWPORT_CAPTURE_ERROR" in markdown
    assert (
        "diagnostics.fallback_tool_order=[simulation_get_status, "
        "viewport_frame_prims, viewport_capture_assert, extension_capture_logs]"
    ) in markdown


def test_markdown_reports_cleanup_failures_as_non_fatal():
    summary = ScenarioRunSummary(
        scenario_id="cleanup_shape",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=1,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="main_step",
                phase="assert",
                status=ExecutionStatus.PASSED,
            ),
            StepResult(
                step_id="__fallback_cleanup_reset",
                phase="cleanup",
                status=ExecutionStatus.ERROR,
                message="All connection attempts failed",
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)

    assert "**Status**: PASSED" in markdown
    assert "**Steps**: 1 passed, 0 failed, 0 skipped" in markdown
    assert "**Cleanup**: 1 non-fatal failure(s)" in markdown
    assert (
        "| __fallback_cleanup_reset | cleanup | error | 1/1 | - | "
        "All connection attempts failed |"
    ) in markdown


def test_markdown_does_not_label_stage_path_as_capture_path():
    summary = ScenarioRunSummary(
        scenario_id="stage_path_summary",
        status=ExecutionStatus.PASSED,
        passed_steps=2,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="reset_stage",
                phase="arrange",
                status=ExecutionStatus.PASSED,
                data_summary={"path": "anon:0000021234567890:robot_sensor.usd"},
            ),
            StepResult(
                step_id="capture_viewport",
                phase="assert",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "artifact": {
                        "path": "<capture-artifact>/capture.png",
                        "sha256": "abc123",
                    },
                    "non_empty": True,
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)

    assert "`reset_stage`:" not in markdown
    assert "capture_path=anon:" not in markdown
    assert (
        "- `capture_viewport`: capture_path=<capture-artifact>/capture.png; "
        "sha256=abc123; non_empty=True"
    ) in markdown


def test_markdown_labels_top_level_image_artifact_path_as_capture_path():
    summary = ScenarioRunSummary(
        scenario_id="capture_path_summary",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="capture_viewport",
                phase="assert",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "artifact_id": "capture-1",
                    "path": "<capture-artifact>/capture.png",
                    "width": 1280,
                    "height": 720,
                    "sha256": "abc123",
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)

    assert "- `capture_viewport`: capture_path=<capture-artifact>/capture.png" in markdown
    assert "sha256=abc123" in markdown
    assert "; path=<capture-artifact>/capture.png" not in markdown


def test_markdown_omits_optional_timeline_nulls():
    summary = ScenarioRunSummary(
        scenario_id="timeline_null_summary",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="advance_sensor_frames",
                phase="act",
                status=ExecutionStatus.PASSED,
                data_summary={
                    "frames": 60,
                    "status": {
                        "is_playing": True,
                        "is_stopped": False,
                        "timeline_settled": None,
                        "timeline_settle_updates": None,
                    },
                },
            ),
        ),
        artifact_paths=(),
    )

    markdown = to_markdown(summary)

    assert (
        "- `advance_sensor_frames`: is_playing=True; is_stopped=False; frames=60"
    ) in markdown
    assert "timeline_settled=null" not in markdown
    assert "timeline_settle_updates=null" not in markdown


def test_external_asset_actions_have_registry_builders():
    search = build_request(
        ModuleName.ASSET,
        "external_search",
        {"query": "monitor", "providers": ["polyhaven"], "limit": 3},
    )
    download = build_request(
        ModuleName.ASSET,
        "external_download",
        {"provider": "polyhaven", "asset_id": "monitor"},
    )
    convert = build_request(
        ModuleName.ASSET,
        "external_convert",
        {"manifest_path": "manifest.json"},
    )

    assert search == {
        "query": "monitor",
        "providers": ["polyhaven"],
        "limit": 3,
    }
    assert download == {
        "provider": "polyhaven",
        "asset_id": "monitor",
        "format_preference": None,
    }
    assert convert == {
        "manifest_path": "manifest.json",
        "output_format": "usd",
        "timeout_s": 180.0,
    }


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


def test_action_registry_has_robot_rtx_sensor_golden_builders():
    capture = build_request(
        ModuleName.VIEWPORT,
        "capture",
        {"warmup_frames": 8, "return_stats": True},
    )
    frame = build_request(
        ModuleName.VIEWPORT,
        "frame_prims",
        {"prim_paths": ["/World/Robot"], "view_direction": [1.0, -1.0, 0.5]},
    )
    capture_assert = build_request(
        ModuleName.VIEWPORT,
        "capture_assert",
        {"warmup_frames": 8, "min_mean": 8.0, "min_variance": 1.0},
    )
    cloud = build_request(
        ModuleName.SENSOR,
        "lidar_get_point_cloud",
        {
            "sensor_prim": "/World/Robot/Lidar",
            "max_points": 128,
            "min_points": 1,
            "fail_on_warning": True,
        },
    )

    assert capture is not None
    assert capture.warmup_frames == 8
    assert capture.return_stats is True
    assert frame is not None
    assert frame.prim_paths == ("/World/Robot",)
    assert capture_assert is not None
    assert capture_assert.warmup_frames == 8
    assert cloud is not None
    assert cloud.sensor_prim == "/World/Robot/Lidar"
    assert cloud.max_points == 128
    assert cloud.min_points == 1
    assert cloud.fail_on_warning is True


def test_omnigraph_create_script_controller_builder():
    request = build_request(
        ModuleName.OMNIGRAPH,
        "create_script_controller",
        {
            "graph_path": "/World/ActionGraph",
            "script_path": "C:/tmp/controller.py",
            "node_name": "PickPlaceController",
            "tick_node_name": "Tick",
            "reset_state": False,
        },
    )

    assert request is not None
    assert request.graph_path == "/World/ActionGraph"
    assert request.script_path == "C:/tmp/controller.py"
    assert request.node_name == "PickPlaceController"
    assert request.tick_node_name == "Tick"
    assert request.reset_state is False


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
async def test_omnigraph_create_script_controller_routes_through_runner():
    """YAML → runner → OmnigraphModule.create_script_controller."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())

    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_script_controller", "name": "script controller"},
        "spec": {
            "assert": [
                {
                    "id": "wire_controller",
                    "module": "omnigraph",
                    "action": "create_script_controller",
                    "args": {
                        "graph_path": "/World/ActionGraph",
                        "script_path": "C:/tmp/controller.py",
                    },
                }
            ]
        },
    }
    scenario = compile_scenario(raw)
    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    calls = [
        c for c in isaac_client.calls
        if c[0] == "omnigraph_create_script_controller"
    ]
    assert len(calls) == 1
    assert calls[0][1]["graph_path"] == "/World/ActionGraph"
    assert calls[0][1]["script_path"] == "C:/tmp/controller.py"


@pytest.mark.asyncio
async def test_robot_rtx_sensor_golden_workflow_routes_through_runner():
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    isaac_client.responses["viewport_capture"] = {
        "artifact_id": "golden_robot_sensor",
        "path": "/tmp/golden_robot_sensor.png",
        "width": 1280,
        "height": 720,
        "sha256": "abc123",
        "created_at_epoch_ms": 0,
        "pixel_mean": [32.0, 34.0, 36.0],
        "pixel_variance": [8.0, 9.0, 10.0],
        "warmup_frames_used": 8,
    }
    isaac_client.responses["simulation_step"] = {
        "ok": True,
        "is_playing": True,
        "is_stopped": False,
        "current_time": 1.0,
        "start_time": 0.0,
        "end_time": 10.0,
        "time_codes_per_second": 24.0,
        "timeline_settled": True,
        "timeline_settle_updates": 1,
        "frames": 60,
        "start_time_before_step": 0.0,
        "advance_mode": "play_burst",
        "was_playing": True,
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())
    raw = load_scenario(
        PROJECT / "scenarios" / "smoke" / "robot_rtx_sensor_golden_workflow.yaml"
    )
    raw_cloud = next(
        step for step in raw["spec"]["act"] if step["id"] == "read_lidar_point_cloud"
    )
    assert raw_cloud["args"]["min_points"] == "${variables.lidar_min_points}"
    assert raw_cloud["args"]["max_points"] == "${variables.lidar_max_points}"
    assert raw_cloud["args"]["fail_on_warning"] is True
    assert raw_cloud["idempotent"] is True
    assert raw_cloud["retries"]["maxAttempts"] == 3
    raw_assert_steps = raw["spec"]["assert"]
    raw_frame = next(
        step for step in raw_assert_steps if step["id"] == "frame_robot_and_sensors"
    )
    raw_capture = next(
        step for step in raw_assert_steps if step["id"] == "capture_visible_result"
    )
    assert raw_assert_steps.index(raw_frame) < raw_assert_steps.index(raw_capture)
    assert raw_frame["args"]["set_camera"] is True
    assert raw_frame["args"]["prim_paths"] == [
        "${variables.robot_prim}",
        "${variables.camera_prim}",
        "${variables.lidar_prim}",
        "${variables.lidar_targets_prim}",
    ]
    assert raw_capture["args"]["width"] == 1280
    assert raw_capture["args"]["height"] == 720
    assert raw_capture["args"]["warmup_frames"] == 8
    assert raw_capture["args"]["min_mean"] == 8.0
    assert raw_capture["args"]["min_variance"] == 1.0
    scenario = compile_scenario(raw)
    plan = _scenario_plan_payload(scenario)
    assert plan["total_steps"] == 32
    assert plan["phase_counts"] == {
        "arrange": 11,
        "act": 9,
        "assert": 5,
        "cleanup": 7,
    }
    assert plan["stage_mutation_summary"] == {
        "read_only": False,
        "requires_scratch_stage": True,
        "mutation_count": 18,
        "phase_counts": {
            "arrange": 9,
            "act": 4,
            "assert": 0,
            "cleanup": 5,
        },
        "mutation_kinds": [
            "lighting_create_dome",
            "robot_load",
            "sensor_annotator_binding",
            "sensor_attach_rtx_camera",
            "sensor_attach_rtx_lidar",
            "sensor_visualization_toggle",
            "stage_create_prim",
            "stage_delete_prim",
            "stage_load_usd",
            "stage_reset",
        ],
    }
    stage_mutation_steps = {
        step["id"]: step for step in plan["stage_mutation_steps"]
    }
    assert len(stage_mutation_steps) == 18
    assert stage_mutation_steps["reset_stage"] == {
        "id": "reset_stage",
        "phase": "arrange",
        "module": "simulation",
        "action": "stage_new",
        "mutation_kind": "stage_reset",
    }
    assert stage_mutation_steps["load_nova_carter"]["mutation_kind"] == "robot_load"
    assert stage_mutation_steps["load_nova_carter"]["key_args"][
        "prim_path"
    ] == "/World/Robot/NovaCarter"
    assert stage_mutation_steps["attach_top_lidar"][
        "mutation_kind"
    ] == "sensor_attach_rtx_lidar"
    assert stage_mutation_steps["attach_top_lidar"]["key_args"][
        "config_preset"
    ] == "Example_Rotary"
    assert stage_mutation_steps["hide_lidar_debug_draw"] == {
        "id": "hide_lidar_debug_draw",
        "phase": "cleanup",
        "module": "sensor",
        "action": "set_visualization",
        "mutation_kind": "sensor_visualization_toggle",
        "key_args": {
            "sensor_prim": "/World/Robot/NovaCarter/TopLidar",
            "mode": "off",
        },
        "continueOnFailure": True,
    }
    assert stage_mutation_steps["remove_robot"] == {
        "id": "remove_robot",
        "phase": "cleanup",
        "module": "simulation",
        "action": "stage_delete_prim",
        "mutation_kind": "stage_delete_prim",
        "key_args": {"prim_path": "/World/Robot"},
        "continueOnFailure": True,
    }
    assert plan["phases"]["cleanup"][-1] == {
        "id": "__fallback_cleanup_reset",
        "module": "extension",
        "action": "reset",
        "args": {},
        "timeoutSeconds": 30.0,
        "automatic": True,
    }
    evidence_steps = {step["id"]: step for step in plan["evidence_steps"]}
    assert evidence_steps["read_lidar_point_cloud"] == {
        "id": "read_lidar_point_cloud",
        "phase": "act",
        "module": "sensor",
        "action": "lidar_get_point_cloud",
        "evidence_kind": "rtx_lidar_point_cloud",
        "key_args": {
            "sensor_prim": "/World/Robot/NovaCarter/TopLidar",
            "frames_to_wait": 180,
            "min_points": 1,
            "max_points": 512,
            "fail_on_warning": True,
        },
        "idempotent": True,
        "retries": {
            "maxAttempts": 3,
            "initialBackoffSeconds": 0.25,
            "maxBackoffSeconds": 1.0,
        },
    }
    assert evidence_steps["frame_robot_and_sensors"]["evidence_kind"] == (
        "viewport_framing"
    )
    assert evidence_steps["frame_robot_and_sensors"]["key_args"]["prim_paths"] == [
        "/World/Robot/NovaCarter",
        "/World/Robot/NovaCarter/FrontCamera",
        "/World/Robot/NovaCarter/TopLidar",
        "/World/LidarTargets",
    ]
    assert evidence_steps["capture_visible_result"] == {
        "id": "capture_visible_result",
        "phase": "assert",
        "module": "viewport",
        "action": "capture_assert",
        "evidence_kind": "visual_capture",
        "key_args": {
            "width": 1280,
            "height": 720,
            "warmup_frames": 8,
            "min_mean": 8.0,
            "min_variance": 1.0,
        },
    }
    assert plan["retry_steps"] == [
        {
            "id": "read_lidar_point_cloud",
            "phase": "act",
            "module": "sensor",
            "action": "lidar_get_point_cloud",
            "key_args": {
                "sensor_prim": "/World/Robot/NovaCarter/TopLidar",
                "frames_to_wait": 180,
                "min_points": 1,
                "max_points": 512,
                "fail_on_warning": True,
            },
            "idempotent": True,
            "retries": {
                "maxAttempts": 3,
                "initialBackoffSeconds": 0.25,
                "maxBackoffSeconds": 1.0,
            },
        }
    ]
    assert plan["preflight_requirements"] == {
        "runtime_info": {
            "required": True,
            "checks": [
                "tool_profile",
                "app_profile",
                "tool_count",
                "source_newer_than_import=false",
                "restart_required_for_latest_mcp_code=false",
                "robot_probe_result_has_checks=true",
                (
                    "robot_probe_unknown_profile_error_code="
                    "ROBOT_PROBE_UNKNOWN_PROFILE"
                ),
                (
                    "robot_probe_unknown_profile_error_data_path="
                    "data.checks.probe.evidence"
                ),
                "robot_probe_unknown_profile_fallback_tool_order",
            ],
        },
        "scratch_stage": {
            "required": True,
            "pass_condition": "use scratch/test stage for mutating scenarios",
        },
        "log_capture": {
            "recommended": True,
            "pass_condition": "clear logs before mutating run, capture WARN+ after run",
        },
        "simulation_play_gate": {
            "required": True,
            "missing_before_required_step_count": 0,
            "pass_condition": "play_state_missing_count == 0",
        },
        "retry_gate": {
            "required": True,
            "retry_step_count": 1,
            "pass_condition": (
                "retry_steps[].key_args match intended proof thresholds"
            ),
        },
    }
    assert plan["simulation_state_summary"] == {
        "requires_play": True,
        "requires_play_count": 2,
        "play_state_missing_count": 0,
        "has_simulation_play": True,
        "has_simulation_pause": True,
        "has_simulation_stop": True,
        "timeline_control_counts": {
            "pause": 1,
            "play": 2,
            "set_time": 0,
            "step": 2,
            "stop": 2,
            "wait_until": 0,
        },
        "warnings": [],
    }
    live_validation_checklist = plan["live_validation_checklist"]
    assert live_validation_checklist["scratch_stage_required"] is True
    assert live_validation_checklist["log_capture_recommended"] is True
    assert [
        step["tool"] for step in live_validation_checklist["steps"]
    ] == [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan",
        "scenario_validate",
        "extension_clear_logs",
        "scenario_validate",
        "scenario_last_report",
        "extension_capture_logs",
    ]
    assert live_validation_checklist["steps"][4]["args"] == {"dry_run": True}
    assert live_validation_checklist["steps"][7]["args"] == {
        "report_format": "markdown",
        "redact_local_paths": True,
    }
    assert live_validation_checklist["steps"][8]["args"] == {
        "level": "WARN",
        "stop_after_capture": True,
    }
    assert [step["id"] for step in plan["timeline_control_steps"]] == [
        "warm_up_play",
        "warm_up_stop",
        "play_for_sensor_data",
        "pre_lidar_attach_warmup",
        "advance_sensor_frames",
        "pause_after_sensor_data",
        "final_sim_stop",
    ]
    simulation_state_steps = {
        step["id"]: step for step in plan["simulation_state_steps"]
    }
    assert simulation_state_steps["attach_top_lidar"] == {
        "id": "attach_top_lidar",
        "phase": "act",
        "module": "sensor",
        "action": "attach_rtx_lidar",
        "requirement_kind": "rtx_lidar_attach_during_play",
        "requires": "simulation_play_active",
        "play_state_before_step": True,
        "key_args": {
            "robot_prim": "/World/Robot/NovaCarter",
            "sensor_name": "TopLidar",
            "config_preset": "Example_Rotary",
        },
    }
    assert simulation_state_steps["read_lidar_point_cloud"] == {
        "id": "read_lidar_point_cloud",
        "phase": "act",
        "module": "sensor",
        "action": "lidar_get_point_cloud",
        "requirement_kind": "rtx_lidar_readback",
        "requires": "simulation_play_active",
        "play_state_before_step": True,
        "key_args": {
            "sensor_prim": "/World/Robot/NovaCarter/TopLidar",
            "frames_to_wait": 180,
            "min_points": 1,
            "max_points": 512,
            "fail_on_warning": True,
        },
        "idempotent": True,
        "retries": {
            "maxAttempts": 3,
            "initialBackoffSeconds": 0.25,
            "maxBackoffSeconds": 1.0,
        },
    }

    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    assert summary.passed_steps == plan["total_steps"]
    assert summary.failed_steps == 0
    assert summary.skipped_steps == 0
    act_step_ids = [step["id"] for step in raw["spec"]["act"]]
    assert act_step_ids.index("play_for_sensor_data") < act_step_ids.index(
        "attach_top_lidar"
    )
    assert act_step_ids.index("pre_lidar_attach_warmup") < act_step_ids.index(
        "attach_top_lidar"
    )
    call_names = [name for name, _payload in isaac_client.calls]
    for expected in (
        "stage_load_usd",
        "stage_create_prim",
        "robot_load",
        "sensor_attach_rtx_camera",
        "sensor_set_annotator",
        "sensor_attach_rtx_lidar",
        "sensor_lidar_get_point_cloud",
        "viewport_frame_prims",
        "viewport_capture",
    ):
        assert expected in call_names
    play_indices = [
        idx for idx, name in enumerate(call_names) if name == "simulation_play"
    ]
    lidar_attach_idx = call_names.index("sensor_attach_rtx_lidar")
    assert play_indices[-1] < lidar_attach_idx
    assert call_names.index("sensor_attach_rtx_lidar") < call_names.index(
        "sensor_lidar_get_point_cloud"
    )
    assert call_names.index("simulation_step") < call_names.index(
        "sensor_lidar_get_point_cloud"
    )
    assert call_names.index("sensor_lidar_get_point_cloud") < call_names.index(
        "simulation_pause"
    )
    assert call_names.index("simulation_pause") < call_names.index(
        "viewport_frame_prims"
    )
    assert call_names.index("viewport_frame_prims") < call_names.index("viewport_capture")
    stop_indices = [
        idx for idx, name in enumerate(call_names) if name == "simulation_stop"
    ]
    assert stop_indices[-1] > call_names.index("viewport_capture")
    assert stop_indices[-1] < call_names.index("stage_delete_prim")
    create_payloads = [
        payload for name, payload in isaac_client.calls if name == "stage_create_prim"
    ]
    created_paths = {payload["prim_path"] for payload in create_payloads}
    assert "/World/LidarTargets" in created_paths
    assert "/World/LidarTargets/TargetForward" in created_paths
    assert "/World/LidarTargets/TargetBack" in created_paths
    assert "/World/LidarTargets/TargetLeft" in created_paths
    assert "/World/LidarTargets/TargetRight" in created_paths
    cloud_payload = next(
        payload for name, payload in isaac_client.calls
        if name == "sensor_lidar_get_point_cloud"
    )
    assert cloud_payload["frames_to_wait"] == 180
    capture_payload = next(
        payload for name, payload in isaac_client.calls if name == "viewport_capture"
    )
    assert capture_payload["width"] == 1280
    assert capture_payload["height"] == 720
    assert capture_payload["return_stats"] is True
    assert capture_payload["warmup_frames"] == 8
    cloud_step = next(
        result for result in summary.step_results
        if result.step_id == "read_lidar_point_cloud"
    )
    assert cloud_step.data_summary["num_points"] == 3
    assert cloud_step.data_summary["backend"] == "omni.replicator.core"
    assert cloud_step.data_summary["frames_waited"] == 180
    assert cloud_step.data_summary["raw_keys"] == [
        "azimuth",
        "data",
        "distance",
        "elevation",
        "intensity",
    ]
    assert cloud_step.data_summary["points"] == {
        "count": 3,
        "sample": [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
        ],
    }
    report = json.loads(to_json(summary))
    cloud_report = next(
        result for result in report["step_results"]
        if result["step_id"] == "read_lidar_point_cloud"
    )
    assert cloud_report["data_summary"]["num_points"] == 3
    assert cloud_report["data_summary"]["backend"] == "omni.replicator.core"
    assert cloud_report["data_summary"]["frames_waited"] == 180
    assert cloud_report["data_summary"]["raw_keys"] == [
        "azimuth",
        "data",
        "distance",
        "elevation",
        "intensity",
    ]
    assert cloud_report["data_summary"]["warning"] is None
    evidence_report = {
        result["step_id"]: result for result in report["evidence_summary"]
    }
    assert evidence_report["read_lidar_point_cloud"] == {
        "step_id": "read_lidar_point_cloud",
        "phase": "act",
        "status": "passed",
        "attempts": 1,
        "max_attempts": 3,
        "retry_failure_count": 0,
        "evidence_kind": "rtx_lidar_point_cloud",
        "num_points": 3,
        "backend": "omni.replicator.core",
        "frames_waited": 180,
        "empty_reason": None,
        "warning": None,
        "truncated": False,
    }
    assert evidence_report["frame_robot_and_sensors"] == {
        "step_id": "frame_robot_and_sensors",
        "phase": "assert",
        "status": "passed",
        "attempts": 1,
        "max_attempts": 1,
        "retry_failure_count": 0,
        "evidence_kind": "viewport_framing",
        "camera_path": "/OmniverseKit_Persp",
        "viewport_name": "Viewport",
        "distance": 2.0,
        "prim_count": 4,
        "bbox_empty": False,
    }
    assert evidence_report["capture_visible_result"] == {
        "step_id": "capture_visible_result",
        "phase": "assert",
        "status": "passed",
        "attempts": 1,
        "max_attempts": 1,
        "retry_failure_count": 0,
        "evidence_kind": "visual_capture",
        "capture_path": "/tmp/golden_robot_sensor.png",
        "sha256": "abc123",
        "width": 1280,
        "height": 720,
        "pixel_mean": [32.0, 34.0, 36.0],
        "pixel_variance": [8.0, 9.0, 10.0],
        "warmup_frames_used": 8,
        "passed": True,
        "pixel_mean_average": 34.0,
        "pixel_variance_average": 9.0,
        "failure_codes": [],
    }
    markdown = to_markdown(summary)
    assert (
        "- `read_lidar_point_cloud`: num_points=3; "
        "backend=omni.replicator.core; frames_waited=180; "
        "raw_keys=[azimuth, data, distance, elevation, intensity]; "
        "warning=null; truncated=False"
    ) in markdown
    assert (
        "- `advance_sensor_frames`: timeline_settled=True; "
        "timeline_settle_updates=1; is_playing=True; is_stopped=False"
    ) in markdown
    assert (
        "- `capture_visible_result`: capture_path=/tmp/golden_robot_sensor.png; "
        "sha256=abc123; passed=True"
    ) in markdown
    assert (
        "- `read_lidar_point_cloud`: "
        "evidence_kind=rtx_lidar_point_cloud; status=passed; attempts=1/3; "
        "num_points=3; backend=omni.replicator.core; frames_waited=180; "
        "warning=null; truncated=False"
    ) in markdown
    assert (
        "- `frame_robot_and_sensors`: "
        "evidence_kind=viewport_framing; status=passed; attempts=1/1; "
        "camera_path=/OmniverseKit_Persp; viewport_name=Viewport; "
        "distance=2.0; prim_count=4; bbox_empty=False"
    ) in markdown
    assert (
        "- `capture_visible_result`: "
        "evidence_kind=visual_capture; status=passed; attempts=1/1; "
        "capture_path=/tmp/golden_robot_sensor.png; sha256=abc123; "
        "width=1280; height=720; pixel_mean=[32.0, 34.0, 36.0]; "
        "pixel_variance=[8.0, 9.0, 10.0]; warmup_frames_used=8; "
        "passed=True; pixel_mean_average=34.0; pixel_variance_average=9.0; "
        "failure_codes=[]"
    ) in markdown


def test_scenario_plan_visual_capture_evidence_kinds_match_report_rows():
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "visual_capture_plan_alignment",
            "name": "visual capture plan alignment",
        },
        "spec": {
            "assert": [
                {
                    "id": "capture_viewport",
                    "module": "viewport",
                    "action": "capture",
                    "args": {
                        "width": 640,
                        "height": 360,
                        "warmup_frames": 4,
                        "return_stats": True,
                    },
                },
                {
                    "id": "assert_viewport_capture",
                    "module": "viewport",
                    "action": "capture_assert",
                    "args": {
                        "width": 640,
                        "height": 360,
                        "warmup_frames": 4,
                        "min_mean": 8.0,
                        "min_variance": 1.0,
                    },
                },
                {
                    "id": "capture_window",
                    "module": "window",
                    "action": "capture",
                    "args": {
                        "window_title": "Viewport",
                        "wait_stable": True,
                        "timeout_s": 1.0,
                    },
                },
            ],
        },
    }

    plan = _scenario_plan_payload(compile_scenario(raw))
    evidence_steps = {step["id"]: step for step in plan["evidence_steps"]}

    assert evidence_steps["capture_viewport"]["evidence_kind"] == "visual_capture"
    assert evidence_steps["capture_viewport"]["action"] == "capture"
    assert evidence_steps["capture_viewport"]["key_args"] == {
        "width": 640,
        "height": 360,
        "warmup_frames": 4,
        "return_stats": True,
    }
    assert evidence_steps["assert_viewport_capture"]["evidence_kind"] == (
        "visual_capture"
    )
    assert evidence_steps["assert_viewport_capture"]["action"] == "capture_assert"
    assert evidence_steps["assert_viewport_capture"]["key_args"] == {
        "width": 640,
        "height": 360,
        "warmup_frames": 4,
        "min_mean": 8.0,
        "min_variance": 1.0,
    }
    assert evidence_steps["capture_window"]["evidence_kind"] == "visual_capture"
    assert evidence_steps["capture_window"]["module"] == "window"
    assert evidence_steps["capture_window"]["key_args"] == {
        "window_title": "Viewport",
        "wait_stable": True,
        "timeout_s": 1.0,
    }


@pytest.mark.asyncio
async def test_robot_rtx_sensor_golden_workflow_reports_capture_assert_diagnostics():
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    isaac_client.responses["viewport_capture"] = {
        "artifact_id": "blank_robot_sensor",
        "path": "/tmp/blank_robot_sensor.png",
        "width": 1280,
        "height": 720,
        "sha256": "abc123",
        "created_at_epoch_ms": 0,
        "pixel_mean": [0.0, 0.0, 0.0],
        "pixel_variance": [0.0, 0.0, 0.0],
        "warmup_frames_used": 8,
    }
    isaac_client.responses["simulation_step"] = {
        "ok": True,
        "is_playing": True,
        "is_stopped": False,
        "current_time": 1.0,
        "start_time": 0.0,
        "end_time": 10.0,
        "time_codes_per_second": 24.0,
        "timeline_settled": True,
        "timeline_settle_updates": 1,
        "frames": 60,
        "start_time_before_step": 0.0,
        "advance_mode": "play_burst",
        "was_playing": True,
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())
    scenario = compile_scenario(
        load_scenario(
            PROJECT / "scenarios" / "smoke" / "robot_rtx_sensor_golden_workflow.yaml"
        )
    )

    summary = await runner.run(scenario)
    report = json.loads(to_json(summary))
    failed_capture = next(
        result for result in report["step_results"]
        if result["step_id"] == "capture_visible_result"
    )

    assert summary.status == ExecutionStatus.FAILED, summary
    assert failed_capture["error_code"] == "VIEWPORT_CAPTURE_ASSERT_FAILED"
    assert failed_capture["data_summary"]["diagnostics"]["reason"] == (
        "capture_blank_or_flat"
    )
    assert failed_capture["diagnostic_next_actions"][
        "diagnostics.fallback_tool_order"
    ] == [
        "simulation_get_status",
        "viewport_frame_prims",
        "viewport_capture_assert",
        "extension_capture_logs",
    ]
    assert report["diagnostic_next_actions"] == [{
        "step_id": "capture_visible_result",
        "phase": "assert",
        "source": "step",
        "status": "failed",
        "error_code": "VIEWPORT_CAPTURE_ASSERT_FAILED",
        **failed_capture["diagnostic_next_actions"],
    }]
    evidence_report = {
        result["step_id"]: result for result in report["evidence_summary"]
    }
    assert evidence_report["capture_visible_result"] == {
        "step_id": "capture_visible_result",
        "phase": "assert",
        "status": "failed",
        "attempts": 1,
        "max_attempts": 1,
        "retry_failure_count": 0,
        "evidence_kind": "visual_capture",
        "error_code": "VIEWPORT_CAPTURE_ASSERT_FAILED",
        "capture_path": "/tmp/blank_robot_sensor.png",
        "sha256": "abc123",
        "width": 1280,
        "height": 720,
        "pixel_mean": [0.0, 0.0, 0.0],
        "pixel_variance": [0.0, 0.0, 0.0],
        "warmup_frames_used": 8,
        "passed": False,
        "pixel_mean_average": 0.0,
        "pixel_variance_average": 0.0,
        "failure_codes": [
            "PIXEL_MEAN_BELOW_THRESHOLD",
            "PIXEL_VARIANCE_BELOW_THRESHOLD",
        ],
    }
    markdown = to_markdown(summary)
    assert (
        "- `capture_visible_result`: "
        "evidence_kind=visual_capture; status=failed; attempts=1/1; "
        "error_code=VIEWPORT_CAPTURE_ASSERT_FAILED; "
        "capture_path=/tmp/blank_robot_sensor.png; sha256=abc123; "
        "width=1280; height=720; pixel_mean=[0.0, 0.0, 0.0]; "
        "pixel_variance=[0.0, 0.0, 0.0]; warmup_frames_used=8; "
        "passed=False; pixel_mean_average=0.0; pixel_variance_average=0.0; "
        "failure_codes=[PIXEL_MEAN_BELOW_THRESHOLD, "
        "PIXEL_VARIANCE_BELOW_THRESHOLD]"
    ) in markdown


def test_scenario_plan_flags_missing_simulation_play_for_robot_steps():
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "robot_drive_without_play",
            "name": "Robot drive missing play preflight",
            "tags": ["robot"],
        },
        "spec": {
            "defaults": {"stepTimeoutSeconds": 30, "failFast": True},
            "act": [
                {
                    "id": "drive_without_play",
                    "module": "robot",
                    "action": "drive_physics",
                    "args": {
                        "prim_path": "/World/Robot",
                        "target_position": [1.0, 0.0, 0.0],
                        "duration_s": 1.0,
                    },
                },
            ],
        },
    }

    plan = _scenario_plan_payload(compile_scenario(raw))

    assert plan["simulation_state_summary"] == {
        "requires_play": True,
        "requires_play_count": 1,
        "play_state_missing_count": 1,
        "has_simulation_play": False,
        "has_simulation_pause": False,
        "has_simulation_stop": False,
        "timeline_control_counts": {
            "pause": 0,
            "play": 0,
            "set_time": 0,
            "step": 0,
            "stop": 0,
            "wait_until": 0,
        },
        "warnings": ["simulation_play_missing_before_required_steps"],
    }
    assert plan["timeline_control_steps"] == []
    assert plan["simulation_state_steps"] == [
        {
            "id": "drive_without_play",
            "phase": "act",
            "module": "robot",
            "action": "drive_physics",
            "requirement_kind": "robot_physics_drive",
            "requires": "simulation_play_active",
            "play_state_before_step": False,
            "key_args": {
                "prim_path": "/World/Robot",
                "target_position": [1.0, 0.0, 0.0],
                "duration_s": 1.0,
            },
        }
    ]


def test_robot_rtx_sensor_golden_workflow_allows_lidar_point_overrides():
    raw = load_scenario(
        PROJECT / "scenarios" / "smoke" / "robot_rtx_sensor_golden_workflow.yaml"
    )
    raw["spec"]["variables"]["lidar_min_points"] = 513
    raw["spec"]["variables"]["lidar_max_points"] = 1024

    scenario = compile_scenario(raw)
    read_lidar = next(
        step for step in scenario.act_steps if step.id == "read_lidar_point_cloud"
    )
    plan = _scenario_plan_payload(scenario)
    evidence_steps = {step["id"]: step for step in plan["evidence_steps"]}

    assert read_lidar.args["min_points"] == 513
    assert isinstance(read_lidar.args["min_points"], int)
    assert read_lidar.args["max_points"] == 1024
    assert isinstance(read_lidar.args["max_points"], int)
    assert evidence_steps["read_lidar_point_cloud"]["key_args"]["min_points"] == 513
    assert evidence_steps["read_lidar_point_cloud"]["key_args"]["max_points"] == 1024


@pytest.mark.asyncio
async def test_scenario_runner_retries_transient_lidar_read_failure():
    """Scenario step retries must absorb transient RTX lidar empty-buffer reads."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    isaac_client.responses["sensor_lidar_get_point_cloud_sequence"] = [
        {
            "ok": True,
            "sensor_prim": "/World/Robot/Lidar",
            "annotator": "RtxSensorCpuIsaacCreateRTXLidarScanBuffer",
            "backend": "omni.replicator.core",
            "num_points": 0,
            "points": [],
            "intensities": [],
            "truncated": False,
            "frames_waited": 12,
            "raw_keys": ["azimuth", "distance"],
            "warning": "polar arrays contained 0 elements",
            "empty_reason": "empty_scan_buffer",
            "diagnostics": {
                "empty_reason": "empty_scan_buffer",
                "suggested_next": "step more frames and retry idempotently",
                "cached_lidar_instance": True,
                "readback_paths_attempted": [
                    "cached_lidar_sensor",
                    "replicator_annotator",
                ],
            },
        },
        {
            "ok": True,
            "sensor_prim": "/World/Robot/Lidar",
            "annotator": "RtxSensorCpuIsaacCreateRTXLidarScanBuffer",
            "backend": "omni.replicator.core",
            "num_points": 2,
            "points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            "intensities": [1.0, 1.0],
            "truncated": False,
            "frames_waited": 12,
            "raw_keys": ["azimuth", "distance"],
            "warning": None,
            "empty_reason": None,
            "diagnostics": {
                "cached_lidar_instance": True,
                "readback_paths_attempted": ["cached_lidar_sensor"],
            },
        },
    ]
    runner = _build_runner(isaac_client, MockLakehouseClient())
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_lidar_retry", "name": "lidar retry"},
        "spec": {
            "assert": [
                {
                    "id": "read_lidar",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "retries": {
                        "maxAttempts": 2,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {
                        "sensor_prim": "/World/Robot/Lidar",
                        "frames_to_wait": 12,
                        "min_points": 1,
                        "fail_on_warning": True,
                    },
                }
            ]
        },
    }
    scenario = compile_scenario(raw)
    plan = _scenario_plan_payload(scenario)
    assert plan["retry_steps"] == [{
        "id": "read_lidar",
        "phase": "assert",
        "module": "sensor",
        "action": "lidar_get_point_cloud",
        "key_args": {
            "sensor_prim": "/World/Robot/Lidar",
            "frames_to_wait": 12,
            "min_points": 1,
            "fail_on_warning": True,
        },
        "idempotent": True,
        "retries": {
            "maxAttempts": 2,
            "initialBackoffSeconds": 0.0,
            "maxBackoffSeconds": 0.0,
        },
    }]

    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    lidar_calls = [
        c for c in isaac_client.calls if c[0] == "sensor_lidar_get_point_cloud"
    ]
    assert len(lidar_calls) == 2
    step_result = next(r for r in summary.step_results if r.step_id == "read_lidar")
    assert step_result.status == ExecutionStatus.PASSED
    assert step_result.attempts == 2
    assert step_result.max_attempts == 2
    assert len(step_result.retry_failures) == 1
    retry_failure = step_result.retry_failures[0]
    assert retry_failure["attempt"] == 1
    assert retry_failure["status"] == "failed"
    assert retry_failure["error_code"] == "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    assert "warning=polar arrays contained 0 elements" in str(
        retry_failure["message"]
    )
    assert "empty_reason=empty_scan_buffer" in str(retry_failure["message"])
    assert "suggested_next=step more frames and retry idempotently" in str(
        retry_failure["message"]
    )
    assert "cached_lidar_instance=True" in str(retry_failure["message"])
    assert (
        "readback_paths_attempted=cached_lidar_sensor,replicator_annotator"
        in str(retry_failure["message"])
    )
    assert retry_failure["data_summary"]["num_points"] == 0
    assert retry_failure["data_summary"]["diagnostics"]["cached_lidar_instance"] is True
    assert retry_failure["data_summary"]["diagnostics"][
        "readback_paths_attempted"
    ] == [
        "cached_lidar_sensor",
        "replicator_annotator",
    ]
    assert step_result.data_summary["num_points"] == 2
    assert step_result.data_summary["empty_reason"] is None
    report = json.loads(to_json(summary))
    lidar_report = next(
        result for result in report["step_results"]
        if result["step_id"] == "read_lidar"
    )
    assert lidar_report["attempts"] == 2
    assert lidar_report["max_attempts"] == 2
    assert lidar_report["retry_failures"][0]["error_code"] == (
        "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    )
    assert lidar_report["retry_failures"][0]["data_summary"]["diagnostics"][
        "readback_paths_attempted"
    ] == [
        "cached_lidar_sensor",
        "replicator_annotator",
    ]
    assert lidar_report["retry_failures"][0]["diagnostic_next_actions"] == {
        "diagnostics.reason": "point_count_below_minimum",
        "empty_reason": "empty_scan_buffer",
        "diagnostics.num_points": 0,
        "diagnostics.min_points": 1,
        "suggested_next": "step more frames and retry idempotently",
        "diagnostics.fallback_tool_order": [
            "simulation_step",
            "sensor_lidar_get_point_cloud",
            "extension_capture_logs",
        ],
        "diagnostics.readback_paths_attempted": [
            "cached_lidar_sensor",
            "replicator_annotator",
        ],
        "diagnostics.cached_lidar_instance": True,
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "read_lidar",
        "phase": "assert",
        "source": "retry_failure",
        "status": "failed",
        "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
        "final_step_status": "passed",
        "attempt": 1,
        "diagnostics.reason": "point_count_below_minimum",
        "empty_reason": "empty_scan_buffer",
        "diagnostics.num_points": 0,
        "diagnostics.min_points": 1,
        "suggested_next": "step more frames and retry idempotently",
        "diagnostics.fallback_tool_order": [
            "simulation_step",
            "sensor_lidar_get_point_cloud",
            "extension_capture_logs",
        ],
        "diagnostics.readback_paths_attempted": [
            "cached_lidar_sensor",
            "replicator_annotator",
        ],
        "diagnostics.cached_lidar_instance": True,
    }]
    markdown = to_markdown(summary)
    assert "| Step | Phase | Status | Attempts | Duration | Message |" in markdown
    assert "| read_lidar | assert | passed | 2/2 |" in markdown
    assert "## Data Summary Highlights" in markdown
    assert (
        "- `read_lidar`: num_points=2; backend=omni.replicator.core; "
        "frames_waited=12; diagnostics.cached_lidar_instance=True; "
        "diagnostics.readback_paths_attempted=[cached_lidar_sensor]; "
        "raw_keys=[azimuth, distance]; warning=null; "
        "truncated=False"
    ) in markdown
    assert "empty_reason=null" not in markdown
    assert "## Retry Failures" in markdown
    assert (
        "- `read_lidar` attempt 1: failed "
        "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS -"
    ) in markdown
    assert "cached_lidar_instance=True" in markdown
    assert (
        "readback_paths_attempted=cached_lidar_sensor,replicator_annotator"
        in markdown
    )
    assert (
        "[num_points=0; backend=omni.replicator.core; "
        "frames_waited=12; empty_reason=empty_scan_buffer"
    ) in markdown
    assert "## Diagnostic Next Actions" in markdown
    assert (
        "- `read_lidar attempt 1`: "
        "diagnostics.reason=point_count_below_minimum; "
        "empty_reason=empty_scan_buffer; "
        "diagnostics.num_points=0; "
        "diagnostics.min_points=1; "
        "suggested_next=step more frames and retry idempotently; "
        "diagnostics.fallback_tool_order=[simulation_step, "
        "sensor_lidar_get_point_cloud, extension_capture_logs]; "
        "diagnostics.readback_paths_attempted=[cached_lidar_sensor, "
        "replicator_annotator]"
    ) in markdown


@pytest.mark.asyncio
async def test_scenario_runner_reports_diagnostic_actions_for_exhausted_lidar_retry():
    """Exhausted RTX lidar retries must preserve final-step and attempt actions."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    isaac_client.responses["sensor_lidar_get_point_cloud_sequence"] = [
        {
            "ok": True,
            "sensor_prim": "/World/Robot/Lidar",
            "annotator": "IsaacCreateRTXLidarScanBuffer",
            "backend": "isaacsim.sensors.experimental.rtx.LidarSensor",
            "num_points": 2,
            "points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            "intensities": [1.0, 1.0],
            "truncated": True,
            "frames_waited": 180,
            "raw_keys": ["cached_lidar_sensor"],
            "warning": None,
            "empty_reason": None,
            "diagnostics": {
                "cached_lidar_instance": True,
                "readback_paths_attempted": ["cached_lidar_sensor"],
            },
        }
        for _ in range(3)
    ]
    runner = _build_runner(isaac_client, MockLakehouseClient())
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_lidar_retry_exhausted", "name": "lidar retry"},
        "spec": {
            "assert": [
                {
                    "id": "read_lidar",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "retries": {
                        "maxAttempts": 3,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {
                        "sensor_prim": "/World/Robot/Lidar",
                        "frames_to_wait": 180,
                        "min_points": 4,
                        "max_points": 2,
                    },
                }
            ]
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.FAILED
    lidar_calls = [
        c for c in isaac_client.calls if c[0] == "sensor_lidar_get_point_cloud"
    ]
    assert len(lidar_calls) == 3
    step_result = next(r for r in summary.step_results if r.step_id == "read_lidar")
    assert step_result.status == ExecutionStatus.FAILED
    assert step_result.attempts == 3
    assert step_result.max_attempts == 3
    assert step_result.error_code == "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    assert len(step_result.retry_failures) == 3
    assert {failure["attempt"] for failure in step_result.retry_failures} == {1, 2, 3}

    expected_action = {
        "diagnostics.reason": "point_count_below_minimum",
        "diagnostics.num_points": 2,
        "diagnostics.min_points": 4,
        "suggested_next": [
            "Step more simulation frames before retrying the lidar read.",
            "Lower min_points only for bounded diagnostics if the scan is "
            "otherwise healthy.",
            "Inspect readback_paths_attempted and WARN/ERROR logs if the buffer "
            "stays short.",
        ],
        "diagnostics.fallback_tool_order": [
            "simulation_step",
            "sensor_lidar_get_point_cloud",
            "extension_capture_logs",
        ],
        "diagnostics.readback_paths_attempted": ["cached_lidar_sensor"],
        "diagnostics.cached_lidar_instance": True,
    }
    report = json.loads(to_json(summary))
    assert len(report["failure_summary"]) == 1
    failure = report["failure_summary"][0]
    assert failure["step_id"] == "read_lidar"
    assert failure["phase"] == "assert"
    assert failure["status"] == "failed"
    assert failure["attempts"] == 3
    assert failure["max_attempts"] == 3
    assert failure["retry_failure_count"] == 3
    assert failure["error_code"] == "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    assert "diagnostics.reason=point_count_below_minimum" in failure["data_highlight"]
    assert "diagnostics.cached_lidar_instance=True" in failure["data_highlight"]
    assert failure["last_retry_failure"]["attempt"] == 3
    assert failure["last_retry_failure"]["error_code"] == (
        "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    )
    assert (
        "diagnostics.readback_paths_attempted=[cached_lidar_sensor]"
        in failure["last_retry_failure"]["data_highlight"]
    )
    assert report["diagnostic_next_actions"] == [
        {
            "step_id": "read_lidar",
            "phase": "assert",
            "source": "step",
            "status": "failed",
            "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            **expected_action,
        },
        *[
            {
                "step_id": "read_lidar",
                "phase": "assert",
                "source": "retry_failure",
                "status": "failed",
                "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
                "final_step_status": "failed",
                "attempt": attempt,
                **expected_action,
            }
            for attempt in (1, 2, 3)
        ],
    ]
    lidar_report = next(
        result for result in report["step_results"]
        if result["step_id"] == "read_lidar"
    )
    assert lidar_report["diagnostic_next_actions"] == expected_action
    for failure in lidar_report["retry_failures"]:
        assert failure["diagnostic_next_actions"] == expected_action
        assert failure["data_summary"]["diagnostics"]["num_points"] == 2
        assert failure["data_summary"]["diagnostics"]["min_points"] == 4

    evidence_report = {
        result["step_id"]: result for result in report["evidence_summary"]
    }
    assert evidence_report["read_lidar"] == {
        "step_id": "read_lidar",
        "phase": "assert",
        "status": "failed",
        "attempts": 3,
        "max_attempts": 3,
        "retry_failure_count": 3,
        "evidence_kind": "rtx_lidar_point_cloud",
        "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
        "num_points": 2,
        "backend": "isaacsim.sensors.experimental.rtx.LidarSensor",
        "frames_waited": 180,
        "empty_reason": None,
        "warning": None,
        "truncated": True,
        "diagnostics": {
            "reason": "point_count_below_minimum",
            "min_points": 4,
            "cached_lidar_instance": True,
            "readback_paths_attempted": ["cached_lidar_sensor"],
            "suggested_next": expected_action["suggested_next"],
            "fallback_tool_order": expected_action["diagnostics.fallback_tool_order"],
        },
    }

    markdown = to_markdown(summary)
    assert "## Failure Summary" in markdown
    assert (
        "- `read_lidar`: phase=assert; status=failed; attempts=3/3; "
        "error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    ) in markdown
    assert "last_retry=(attempt=3; status=failed" in markdown
    assert "## Diagnostic Next Actions" in markdown
    assert (
        "- `read_lidar`: evidence_kind=rtx_lidar_point_cloud; status=failed; "
        "attempts=3/3; retry_failure_count=3"
    ) in markdown
    assert '"reason":"point_count_below_minimum"' in markdown
    assert '"min_points":4' in markdown
    assert (
        "- `read_lidar`: diagnostics.reason=point_count_below_minimum; "
        "diagnostics.num_points=2; diagnostics.min_points=4"
    ) in markdown
    assert (
        "- `read_lidar attempt 3`: diagnostics.reason=point_count_below_minimum; "
        "diagnostics.num_points=2; diagnostics.min_points=4"
    ) in markdown
    assert "diagnostics.num_points=2" in markdown
    assert "diagnostics.min_points=4" in markdown
    assert "diagnostics.cached_lidar_instance=True" in markdown


@pytest.mark.asyncio
async def test_scenario_runner_rejects_retries_without_idempotent_flag():
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_retry_requires_idempotent", "name": "retry guard"},
        "spec": {
            "assert": [
                {
                    "id": "unsafe_retry",
                    "module": "simulation",
                    "action": "stage_create_prim",
                    "retries": {
                        "maxAttempts": 2,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"prim_path": "/World/Unsafe", "prim_type": "Cube"},
                }
            ]
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.FAILED, summary
    create_calls = [c for c in isaac_client.calls if c[0] == "stage_create_prim"]
    assert create_calls == []
    step_result = next(r for r in summary.step_results if r.step_id == "unsafe_retry")
    assert step_result.status == ExecutionStatus.ERROR
    assert step_result.error_code == "SCENARIO_RETRY_REQUIRES_IDEMPOTENT_STEP"
    assert step_result.attempts == 0
    assert step_result.max_attempts == 2
    assert step_result.retry_failures == ()
    assert "idempotent=true" in (step_result.message or "")
    unsafe_report = next(
        result for result in json.loads(to_json(summary))["step_results"]
        if result["step_id"] == "unsafe_retry"
    )
    assert unsafe_report["error_code"] == "SCENARIO_RETRY_REQUIRES_IDEMPOTENT_STEP"


@pytest.mark.asyncio
async def test_scenario_runner_reports_skipped_retry_steps_as_unattempted():
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_skipped_retry", "name": "skipped retry"},
        "spec": {
            "arrange": [
                {
                    "id": "unsafe_retry",
                    "module": "simulation",
                    "action": "stage_create_prim",
                    "retries": {
                        "maxAttempts": 2,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"prim_path": "/World/Unsafe", "prim_type": "Cube"},
                }
            ],
            "assert": [
                {
                    "id": "skipped_lidar",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "retries": {
                        "maxAttempts": 3,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"sensor_prim": "/World/Missing/Lidar"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    skipped = next(r for r in summary.step_results if r.step_id == "skipped_lidar")
    assert skipped.status == ExecutionStatus.SKIPPED
    assert skipped.attempts == 0
    assert skipped.max_attempts == 3
    assert skipped.retry_failures == ()


@pytest.mark.asyncio
async def test_scenario_runner_reports_retry_context_on_hard_timeout(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())

    async def raise_timeout(_step, _ctx, _scenario_id, _timeout):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(runner, "_execute_step_with_retries", raise_timeout)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_retry_timeout", "name": "retry timeout"},
        "spec": {
            "assert": [
                {
                    "id": "timeout_lidar",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "timeoutSeconds": 7,
                    "retries": {
                        "maxAttempts": 3,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"sensor_prim": "/World/Timeout/Lidar"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    assert summary.failed_steps == 1
    assert json.loads(to_json(summary))["failed_steps"] == 1
    assert "**Steps**: 1 passed, 1 failed, 0 skipped" in to_markdown(summary)
    result = next(r for r in summary.step_results if r.step_id == "timeout_lidar")
    assert result.status == ExecutionStatus.TIMEOUT
    assert result.error_code == "SCENARIO_STEP_TIMEOUT"
    assert result.attempts == 1
    assert result.max_attempts == 3
    assert result.retry_failures == ({
        "attempt": 1,
        "status": "timeout",
        "error_code": None,
        "message": "Step timed out after 7s",
    },)


@pytest.mark.asyncio
async def test_scenario_runner_bounds_fallback_cleanup_reset_timeout(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())

    async def hanging_reset(_meta, _request):
        await asyncio.sleep(10)

    monkeypatch.setattr(runner._extension, "reset", hanging_reset)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_cleanup_timeout", "name": "cleanup timeout"},
        "spec": {
            "defaults": {"stepTimeoutSeconds": 0.01},
            "assert": [
                {
                    "id": "state_probe",
                    "module": "extension",
                    "action": "get_state",
                    "timeoutSeconds": 1,
                    "args": {},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    cleanup = next(
        r for r in summary.step_results
        if r.step_id == "__fallback_cleanup_reset"
    )
    assert summary.status == ExecutionStatus.PASSED
    assert summary.cleanup_failed_steps == 1
    assert summary.fatal_failed_steps == 0
    assert cleanup.status == ExecutionStatus.TIMEOUT
    assert cleanup.error_code == "SCENARIO_CLEANUP_TIMEOUT"
    assert cleanup.message == "Fallback cleanup reset timed out after 0.01s"


@pytest.mark.asyncio
async def test_scenario_runner_retries_hard_timeout_for_idempotent_step(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())
    calls = 0

    async def timeout_then_pass(_step, _ctx, _scenario_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise asyncio.TimeoutError()
        return ModuleResult(
            ok=True,
            status=ExecutionStatus.PASSED,
            data=None,
        )

    monkeypatch.setattr(runner, "_execute_step", timeout_then_pass)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_retry_timeout_pass", "name": "retry timeout pass"},
        "spec": {
            "assert": [
                {
                    "id": "timeout_then_pass",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "timeoutSeconds": 7,
                    "retries": {
                        "maxAttempts": 2,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"sensor_prim": "/World/Retry/Lidar"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    result = next(r for r in summary.step_results if r.step_id == "timeout_then_pass")
    assert result.status == ExecutionStatus.PASSED
    assert calls == 2
    assert result.attempts == 2
    assert result.max_attempts == 2
    assert result.retry_failures == ({
        "attempt": 1,
        "status": "timeout",
        "error_code": "SCENARIO_STEP_TIMEOUT",
        "message": "Step timed out after 7s",
    },)


@pytest.mark.asyncio
async def test_scenario_runner_reports_exhausted_hard_timeout_retries(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())
    calls = 0

    async def always_timeout(_step, _ctx, _scenario_id):
        nonlocal calls
        calls += 1
        raise asyncio.TimeoutError()

    monkeypatch.setattr(runner, "_execute_step", always_timeout)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "test_retry_timeout_exhausted",
            "name": "retry timeout exhausted",
        },
        "spec": {
            "assert": [
                {
                    "id": "always_timeout",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "timeoutSeconds": 7,
                    "retries": {
                        "maxAttempts": 2,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"sensor_prim": "/World/Retry/Lidar"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    assert summary.failed_steps == 1
    assert summary.continued_steps == 0
    assert summary.fatal_failed_steps == 1
    assert summary.cleanup_failed_steps == 0
    json_report = json.loads(to_json(summary))
    assert json_report["failed_steps"] == 1
    assert json_report["continued_steps"] == 0
    assert json_report["fatal_failed_steps"] == 1
    assert json_report["cleanup_failed_steps"] == 0
    result = next(r for r in summary.step_results if r.step_id == "always_timeout")
    assert result.status == ExecutionStatus.TIMEOUT
    assert calls == 2
    assert result.attempts == 2
    assert result.max_attempts == 2
    assert result.retry_failures == (
        {
            "attempt": 1,
            "status": "timeout",
            "error_code": "SCENARIO_STEP_TIMEOUT",
            "message": "Step timed out after 7s",
        },
        {
            "attempt": 2,
            "status": "timeout",
            "error_code": "SCENARIO_STEP_TIMEOUT",
            "message": "Step timed out after 7s",
        },
    )


@pytest.mark.asyncio
async def test_scenario_runner_bounds_hard_error_retry_messages(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())

    async def raise_long_error(_step, _ctx, _scenario_id, _timeout):
        raise RuntimeError("x" * 800)

    monkeypatch.setattr(runner, "_execute_step_with_retries", raise_long_error)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_retry_error", "name": "retry error"},
        "spec": {
            "assert": [
                {
                    "id": "error_lidar",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "retries": {
                        "maxAttempts": 3,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"sensor_prim": "/World/Error/Lidar"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    assert summary.failed_steps == 1
    assert summary.continued_steps == 0
    assert summary.fatal_failed_steps == 1
    assert summary.cleanup_failed_steps == 0
    json_report = json.loads(to_json(summary))
    assert json_report["failed_steps"] == 1
    assert json_report["continued_steps"] == 0
    assert json_report["fatal_failed_steps"] == 1
    assert json_report["cleanup_failed_steps"] == 0
    assert "**Steps**: 1 passed, 1 failed, 0 skipped" in to_markdown(summary)
    result = next(r for r in summary.step_results if r.step_id == "error_lidar")
    assert result.status == ExecutionStatus.ERROR
    assert result.attempts == 1
    assert result.max_attempts == 3
    assert len(result.retry_failures) == 1
    message = str(result.retry_failures[0]["message"])
    assert len(message) == 515
    assert message.endswith("...")


@pytest.mark.asyncio
async def test_scenario_runner_retries_hard_exception_for_idempotent_step(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())
    calls = 0

    async def error_then_pass(_step, _ctx, _scenario_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient bridge error")
        return ModuleResult(
            ok=True,
            status=ExecutionStatus.PASSED,
            data=None,
        )

    monkeypatch.setattr(runner, "_execute_step", error_then_pass)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "test_retry_error_pass", "name": "retry error pass"},
        "spec": {
            "assert": [
                {
                    "id": "error_then_pass",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "retries": {
                        "maxAttempts": 2,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"sensor_prim": "/World/Retry/Lidar"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    result = next(r for r in summary.step_results if r.step_id == "error_then_pass")
    assert result.status == ExecutionStatus.PASSED
    assert calls == 2
    assert result.attempts == 2
    assert result.max_attempts == 2
    assert result.retry_failures == ({
        "attempt": 1,
        "status": "error",
        "error_code": "SCENARIO_STEP_EXCEPTION",
        "message": "transient bridge error",
    },)


@pytest.mark.asyncio
async def test_scenario_runner_reports_exhausted_hard_exception_retries(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())
    calls = 0

    async def always_error(_step, _ctx, _scenario_id):
        nonlocal calls
        calls += 1
        raise RuntimeError("bridge stayed down")

    monkeypatch.setattr(runner, "_execute_step", always_error)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "test_retry_error_exhausted",
            "name": "retry error exhausted",
        },
        "spec": {
            "assert": [
                {
                    "id": "always_error",
                    "module": "sensor",
                    "action": "lidar_get_point_cloud",
                    "idempotent": True,
                    "retries": {
                        "maxAttempts": 2,
                        "initialBackoffSeconds": 0,
                        "maxBackoffSeconds": 0,
                    },
                    "args": {"sensor_prim": "/World/Retry/Lidar"},
                }
            ],
        },
    }
    scenario = compile_scenario(raw)

    summary = await runner.run(scenario)

    result = next(r for r in summary.step_results if r.step_id == "always_error")
    assert result.status == ExecutionStatus.ERROR
    assert calls == 2
    assert result.attempts == 2
    assert result.max_attempts == 2
    assert result.retry_failures == (
        {
            "attempt": 1,
            "status": "error",
            "error_code": "SCENARIO_STEP_EXCEPTION",
            "message": "bridge stayed down",
        },
        {
            "attempt": 2,
            "status": "error",
            "error_code": "SCENARIO_STEP_EXCEPTION",
            "message": "bridge stayed down",
        },
    )


@pytest.mark.asyncio
async def test_continued_hard_timeout_and_exception_report_as_continued(monkeypatch):
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    runner = _build_runner(MockIsaacRestClient(), MockLakehouseClient())

    async def raise_by_step(step, _ctx, _scenario_id, _timeout):
        if step.id == "continued_timeout":
            raise asyncio.TimeoutError()
        raise RuntimeError("continued bridge error")

    monkeypatch.setattr(runner, "_execute_step_with_retries", raise_by_step)
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "test_continued_hard_failures",
            "name": "continued hard failures",
        },
        "spec": {
            "assert": [
                {
                    "id": "continued_timeout",
                    "module": "asset",
                    "action": "official_get",
                    "continueOnFailure": True,
                    "timeoutSeconds": 7,
                    "args": {"asset_id": "url:https://example.invalid/a.usd"},
                },
                {
                    "id": "continued_error",
                    "module": "asset",
                    "action": "official_resolve",
                    "continueOnFailure": True,
                    "args": {"name_or_id": "missing"},
                },
            ],
        },
    }

    summary = await runner.run(compile_scenario(raw))

    assert summary.status == ExecutionStatus.PASSED
    assert summary.failed_steps == 2
    assert summary.continued_steps == 2
    assert summary.fatal_failed_steps == 0
    assert summary.cleanup_failed_steps == 0
    steps = {step.step_id: step for step in summary.step_results}
    assert steps["continued_timeout"].continue_on_failure is True
    assert steps["continued_timeout"].status == ExecutionStatus.TIMEOUT
    assert steps["continued_error"].continue_on_failure is True
    assert steps["continued_error"].status == ExecutionStatus.ERROR
    markdown = to_markdown(summary)
    assert "**Steps**: 0 passed, 0 failed, 2 continued, 0 skipped" in markdown
    assert "| continued_timeout | assert | timeout (continued) |" in markdown
    assert "| continued_error | assert | error (continued) |" in markdown
    json_report = json.loads(to_json(summary))
    assert json_report["failed_steps"] == 2
    assert json_report["continued_steps"] == 2
    assert json_report["fatal_failed_steps"] == 0
    assert json_report["cleanup_failed_steps"] == 0
    json_steps = {step["step_id"]: step for step in json_report["step_results"]}
    assert json_steps["continued_timeout"]["continue_on_failure"] is True
    assert json_steps["continued_error"]["continue_on_failure"] is True


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
async def test_official_asset_diagnostics_survive_runner_failure(tmp_path: Path):
    """asset.official_resolve failures must keep diagnostics in scenario reports."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    catalog_dir = _write_minimal_official_catalog(tmp_path)
    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    runner._modules[ModuleName.ASSET] = AssetModule(
        isaac_client,
        official_catalog_dir=catalog_dir,
    )
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {"id": "official_asset_diag", "name": "official asset diag"},
        "spec": {
            "assert": [
                {
                    "id": "resolve_missing",
                    "module": "asset",
                    "action": "official_resolve",
                    "args": {
                        "name_or_id": "forklift",
                        "kind": "asset",
                        "app_profile": "isaac-sim",
                    },
                }
            ]
        },
    }

    summary = await runner.run(compile_scenario(raw))

    step = summary.step_results[0]
    assert step.status == ExecutionStatus.ERROR
    assert step.data_summary["diagnostics"]["reason"] == "query_no_match"
    assert step.data_summary["diagnostics"]["candidate_counts"]["query_matches"] == 0
    assert step.data_summary["diagnostics"]["available_profiles"] == ["isaac-sim"]
    assert step.data_summary["diagnostics"]["available_providers"] == [
        "omni.simready.explorer"
    ]
    markdown = to_markdown(summary)
    assert "diagnostics.reason=query_no_match" in markdown
    assert "diagnostics.available_profiles=[isaac-sim]" in markdown
    assert "diagnostics.available_providers=[omni.simready.explorer]" in markdown
    assert "diagnostics.fallback_tool_order=[official_asset_sync_status" in markdown


@pytest.mark.asyncio
async def test_official_asset_sync_status_diagnostics_survive_runner(
    tmp_path: Path,
):
    """asset.official_sync_status diagnostics must survive successful steps."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    catalog_dir = _write_minimal_official_catalog(tmp_path)
    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    runner._modules[ModuleName.ASSET] = AssetModule(
        isaac_client,
        official_catalog_dir=catalog_dir,
    )
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "official_asset_sync_status_diag",
            "name": "official asset sync status diag",
        },
        "spec": {
            "assert": [
                {
                    "id": "check_profile",
                    "module": "asset",
                    "action": "official_sync_status",
                    "args": {"app_profile": "kit-app"},
                }
            ]
        },
    }

    summary = await runner.run(compile_scenario(raw))

    assert summary.status == ExecutionStatus.PASSED, summary
    step = summary.step_results[0]
    assert step.status == ExecutionStatus.PASSED
    diagnostics = step.data_summary["diagnostics"]
    assert diagnostics["reason"] == "app_profile_not_covered"
    assert diagnostics["requested_app_profile"] == "kit-app"
    assert diagnostics["available_profiles"] == ["isaac-sim"]
    assert diagnostics["available_providers"] == ["omni.simready.explorer"]
    assert diagnostics["matching_item_count"] == 0
    markdown = to_markdown(summary)
    assert "diagnostics.reason=app_profile_not_covered" in markdown
    assert "diagnostics.requested_app_profile=kit-app" in markdown
    assert "diagnostics.available_profiles=[isaac-sim]" in markdown
    assert "diagnostics.available_providers=[omni.simready.explorer]" in markdown
    assert "diagnostics.matching_item_count=0" in markdown


@pytest.mark.asyncio
async def test_official_asset_catalog_diagnostics_smoke_routes_through_runner(
    tmp_path: Path,
):
    """The official asset diagnostics smoke scenario must compile and route."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    catalog_dir = _write_minimal_official_catalog(tmp_path)
    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    runner._modules[ModuleName.ASSET] = AssetModule(
        isaac_client,
        official_catalog_dir=catalog_dir,
    )
    raw = load_scenario(
        PROJECT / "scenarios" / "smoke" / "official_asset_catalog_diagnostics.yaml"
    )
    scenario = compile_scenario(raw)
    plan = _scenario_plan_payload(scenario)
    diagnostic_steps = {step["id"]: step for step in plan["diagnostic_steps"]}
    assert list(diagnostic_steps) == [
        "check_isaac_catalog",
        "search_known_miss",
        "search_pallet_asset",
        "resolve_pallet_asset",
        "get_pallet_wrong_profile",
    ]
    assert diagnostic_steps["check_isaac_catalog"] == {
        "id": "check_isaac_catalog",
        "phase": "assert",
        "module": "asset",
        "action": "official_sync_status",
        "diagnostic_kind": "official_asset_sync_status",
        "key_args": {"app_profile": "isaac-sim"},
    }
    assert diagnostic_steps["search_known_miss"]["diagnostic_kind"] == (
        "official_asset_search"
    )
    assert diagnostic_steps["search_known_miss"]["key_args"] == {
        "query": "definitely-not-a-real-official-asset-name-zzzz",
        "kind": "asset",
        "app_profile": "isaac-sim",
        "min_status": "discovered",
        "limit": 5,
    }
    assert diagnostic_steps["get_pallet_wrong_profile"]["diagnostic_kind"] == (
        "official_asset_get"
    )
    assert diagnostic_steps["resolve_pallet_asset"] == {
        "id": "resolve_pallet_asset",
        "phase": "assert",
        "module": "asset",
        "action": "official_resolve",
        "diagnostic_kind": "official_asset_resolve",
        "key_args": {
            "name_or_id": "pallet",
            "kind": "asset",
            "app_profile": "isaac-sim",
            "prefer_loadable": True,
        },
    }
    assert diagnostic_steps["get_pallet_wrong_profile"]["continueOnFailure"] is True
    assert plan["stage_mutation_summary"] == {
        "read_only": True,
        "requires_scratch_stage": False,
        "mutation_count": 0,
        "phase_counts": {
            "arrange": 0,
            "act": 0,
            "assert": 0,
            "cleanup": 0,
        },
        "mutation_kinds": [],
    }
    assert plan["stage_mutation_steps"] == []
    live_validation_checklist = plan["live_validation_checklist"]
    assert live_validation_checklist["scratch_stage_required"] is False
    assert live_validation_checklist["log_capture_recommended"] is True
    assert [step["tool"] for step in live_validation_checklist["steps"]] == [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan",
        "extension_clear_logs",
        "scenario_validate",
        "scenario_last_report",
        "extension_capture_logs",
    ]
    assert not any(
        step.get("args") == {"dry_run": True}
        for step in live_validation_checklist["steps"]
    )
    assert live_validation_checklist["steps"][6]["args"] == {
        "report_format": "markdown",
        "redact_local_paths": True,
    }
    assert live_validation_checklist["steps"][7]["args"] == {
        "level": "WARN",
        "stop_after_capture": True,
    }

    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
    assert summary.failed_steps == 1
    assert summary.continued_steps == 1
    assert summary.fatal_failed_steps == 0
    assert summary.cleanup_failed_steps == 0
    steps = {step.step_id: step for step in summary.step_results}
    assert "__fallback_cleanup_reset" not in steps
    assert steps["check_isaac_catalog"].status == ExecutionStatus.PASSED
    assert steps["search_known_miss"].data_summary["count"] == 0
    assert steps["search_known_miss"].data_summary["diagnostics"]["reason"] == (
        "query_no_match"
    )
    assert steps["search_pallet_asset"].data_summary["count"] == 1
    assert steps["resolve_pallet_asset"].status == ExecutionStatus.PASSED
    assert steps["resolve_pallet_asset"].data_summary["name"] == (
        "aluminumpallet_a01.usd"
    )
    assert steps["get_pallet_wrong_profile"].status == ExecutionStatus.ERROR
    assert steps["get_pallet_wrong_profile"].continue_on_failure is True
    mismatch_diagnostics = steps["get_pallet_wrong_profile"].data_summary[
        "diagnostics"
    ]
    assert mismatch_diagnostics["reason"] == "app_profile_not_covered"
    assert mismatch_diagnostics["candidate_counts"]["total_entries"] == 1
    assert mismatch_diagnostics["candidate_counts"]["after_app_profile"] == 0
    assert mismatch_diagnostics["available_profiles"] == ["isaac-sim"]
    assert mismatch_diagnostics["available_providers"] == ["omni.simready.explorer"]

    markdown = to_markdown(summary)
    assert "search_known_miss" in markdown
    assert "diagnostics.reason=query_no_match" in markdown
    assert "search_pallet_asset" in markdown
    assert "get_pallet_wrong_profile" in markdown
    assert "**Steps**: 4 passed, 0 failed, 1 continued, 0 skipped" in markdown
    assert "| get_pallet_wrong_profile | assert | error (continued) |" in markdown
    assert "diagnostics.reason=app_profile_not_covered" in markdown
    assert "diagnostics.available_profiles=[isaac-sim]" in markdown
    assert "diagnostics.available_providers=[omni.simready.explorer]" in markdown
    assert "diagnostics.candidate_counts.total_entries=1" in markdown
    assert "diagnostics.candidate_counts.after_app_profile=0" in markdown
    json_report = json.loads(to_json(summary))
    assert json_report["failed_steps"] == 1
    assert json_report["continued_steps"] == 1
    assert json_report["fatal_failed_steps"] == 0
    assert json_report["cleanup_failed_steps"] == 0
    json_steps = {step["step_id"]: step for step in json_report["step_results"]}
    assert json_steps["get_pallet_wrong_profile"]["continue_on_failure"] is True


@pytest.mark.asyncio
async def test_official_asset_verify_failure_diagnostics_survive_runner_report(
    tmp_path: Path,
):
    """official_asset_verify failed records must remain actionable in reports."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    catalog_dir = _write_minimal_official_catalog(tmp_path)
    isaac_client = MockIsaacRestClient()
    isaac_client.responses["stage_load_usd"] = {
        "ok": True,
        "prim_path": "/World/OfficialAssetVerify/empty",
        "type_name": "Xform",
        "has_children": False,
    }
    isaac_client.responses["content_inspect"] = {
        "ok": True,
        "default_prim": "",
        "prim_count": 0,
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())
    runner._modules[ModuleName.ASSET] = AssetModule(
        isaac_client,
        official_catalog_dir=catalog_dir,
    )
    asset_id = (
        "url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com/"
        "Assets/simready_content/common_assets/props/aluminumpallet_a01/"
        "aluminumpallet_a01.usd"
    )
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "official_asset_verify_failed_diag",
            "name": "official asset verify failed diag",
        },
        "spec": {
            "assert": [
                {
                    "id": "verify_empty_asset",
                    "module": "asset",
                    "action": "official_verify",
                    "args": {
                        "asset_id": asset_id,
                        "app_profile": "isaac-sim",
                        "timeout_s": 1.0,
                    },
                }
            ]
        },
    }

    summary = await runner.run(compile_scenario(raw))

    assert summary.status == ExecutionStatus.PASSED, summary
    step = summary.step_results[0]
    assert step.status == ExecutionStatus.PASSED
    assert step.data_summary["verification_status"] == "failed"
    diagnostics = step.data_summary["diagnostics"]
    assert diagnostics["reason"] == "asset_load_quality_failed"
    assert diagnostics["target_status"] == "load_verified"
    assert diagnostics["asset_checks"]["load_quality"] == "empty_content"
    assert diagnostics["asset_checks"]["has_authored_children"] is False
    assert diagnostics["fallback_tool_order"] == [
        "official_asset_sync_status",
        "official_asset_search",
        "official_asset_resolve",
        "official_asset_verify",
        "asset_search",
    ]

    json_report = json.loads(to_json(summary))
    assert json_report["diagnostic_next_actions"] == [{
        "step_id": "verify_empty_asset",
        "phase": "assert",
        "source": "step",
        "status": "passed",
        "diagnostics.reason": "asset_load_quality_failed",
        "diagnostics.target_status": "load_verified",
        "diagnostics.current_catalog_status": "load_verified",
        "suggested_next": [
            "Inspect load_quality, load_quality_warning, and "
            "bbox_validation_reasons before stage placement.",
            "Use content_inspect or regenerate the official catalog if the "
            "source URL or app version changed.",
        ],
        "diagnostics.fallback_tool_order": [
            "official_asset_sync_status",
            "official_asset_search",
            "official_asset_resolve",
            "official_asset_verify",
            "asset_search",
        ],
        "diagnostics.asset_checks": {
            "load_quality": "empty_content",
            "load_quality_warning": (
                "no authored child, default prim, or prim_count evidence"
            ),
            "bbox_valid": True,
            "bbox_validation_reasons": [],
            "has_authored_children": False,
            "has_default_prim": False,
            "prim_count_valid": False,
        },
    }]
    json_step = json_report["step_results"][0]
    assert json_step["diagnostic_next_actions"][
        "diagnostics.asset_checks"
    ]["load_quality"] == "empty_content"
    evidence_report = {
        result["step_id"]: result for result in json_report["evidence_summary"]
    }
    assert evidence_report["verify_empty_asset"] == {
        "step_id": "verify_empty_asset",
        "phase": "assert",
        "status": "passed",
        "attempts": 1,
        "max_attempts": 1,
        "retry_failure_count": 0,
        "evidence_kind": "official_asset_verify",
        "id": asset_id,
        "kind": "asset",
        "name": "aluminumpallet_a01.usd",
        "app_profile": "isaac-sim",
        "verification_status": "failed",
        "load_quality": "empty_content",
        "attempt": 2,
        "timeout_s": 1.0,
        "retry_count": 1,
        "error": "no authored child, default prim, or prim_count evidence",
        "diagnostics": {
            "reason": "asset_load_quality_failed",
            "target_status": "load_verified",
            "current_catalog_status": "load_verified",
            "stale_warning": None,
            "suggested_next": json_report["diagnostic_next_actions"][0][
                "suggested_next"
            ],
            "fallback_tool_order": json_report["diagnostic_next_actions"][0][
                "diagnostics.fallback_tool_order"
            ],
            "asset_checks": json_report["diagnostic_next_actions"][0][
                "diagnostics.asset_checks"
            ],
        },
    }

    markdown = to_markdown(summary)
    assert "## Diagnostic Next Actions" in markdown
    assert "## Evidence Summary" in markdown
    assert (
        "`verify_empty_asset`: evidence_kind=official_asset_verify; "
        "status=passed; attempts=1/1"
    ) in markdown
    assert "- `verify_empty_asset`: diagnostics.reason=asset_load_quality_failed" in markdown
    assert "diagnostics.asset_checks.load_quality=empty_content" in markdown
    assert "diagnostics.asset_checks.has_authored_children=False" in markdown


@pytest.mark.asyncio
async def test_official_asset_verify_not_found_diagnostics_survive_runner_report(
    tmp_path: Path,
):
    """official_asset_verify not-found errors must remain actionable in reports."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    catalog_dir = _write_minimal_official_catalog(tmp_path)
    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    runner._modules[ModuleName.ASSET] = AssetModule(
        isaac_client,
        official_catalog_dir=catalog_dir,
    )
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "official_asset_verify_missing_diag",
            "name": "official asset verify missing diag",
        },
        "spec": {
            "assert": [
                {
                    "id": "verify_missing_asset",
                    "module": "asset",
                    "action": "official_verify",
                    "args": {
                        "asset_id": "missing forklift",
                        "app_profile": "isaac-sim",
                        "timeout_s": 1.0,
                    },
                }
            ]
        },
    }

    summary = await runner.run(compile_scenario(raw))

    assert summary.status == ExecutionStatus.FAILED, summary
    step = summary.step_results[0]
    assert step.status == ExecutionStatus.ERROR
    assert step.error_code == "OFFICIAL_ASSET_NOT_FOUND"
    assert step.data_summary["name_or_id"] == "missing forklift"
    diagnostics = step.data_summary["diagnostics"]
    assert diagnostics["reason"] == "query_no_match"
    assert diagnostics["candidate_counts"]["total_entries"] == 1
    assert diagnostics["candidate_counts"]["query_matches"] == 0
    assert diagnostics["available_profiles"] == ["isaac-sim"]
    assert diagnostics["available_providers"] == ["omni.simready.explorer"]
    assert diagnostics["sample_names"] == ["aluminumpallet_a01.usd"]
    assert diagnostics["fallback_tool_order"] == [
        "official_asset_sync_status",
        "official_asset_search",
        "official_asset_resolve",
        "official_asset_verify",
        "asset_search",
    ]
    assert isaac_client.calls == []

    json_report = json.loads(to_json(summary))
    assert json_report["failure_summary"][0]["error_code"] == (
        "OFFICIAL_ASSET_NOT_FOUND"
    )
    assert "diagnostics.candidate_counts.query_matches=0" in (
        json_report["failure_summary"][0]["data_highlight"]
    )
    assert json_report["diagnostic_next_actions"] == [{
        "step_id": "verify_missing_asset",
        "phase": "assert",
        "source": "step",
        "status": "error",
        "error_code": "OFFICIAL_ASSET_NOT_FOUND",
        "diagnostics.reason": "query_no_match",
        "suggested_next": [
            "Retry with a broader asset family, category, provider, or filename stem.",
            "If official search still misses, use asset_search for Isaac curated USD assets.",
        ],
        "diagnostics.fallback_tool_order": [
            "official_asset_sync_status",
            "official_asset_search",
            "official_asset_resolve",
            "official_asset_verify",
            "asset_search",
        ],
    }]
    assert json_report["evidence_summary"] == []

    markdown = to_markdown(summary)
    assert "## Failure Summary" in markdown
    assert "## Data Summary Highlights" in markdown
    assert "## Diagnostic Next Actions" in markdown
    assert "error_code=OFFICIAL_ASSET_NOT_FOUND" in markdown
    assert "diagnostics.reason=query_no_match" in markdown
    assert "diagnostics.candidate_counts.query_matches=0" in markdown
    assert (
        "diagnostics.fallback_tool_order=[official_asset_sync_status, "
        "official_asset_search, official_asset_resolve, official_asset_verify, "
        "asset_search]"
    ) in markdown


def test_official_asset_verify_evidence_summary_preserves_error_type():
    summary = ScenarioRunSummary(
        scenario_id="official_verify_timeout",
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=0,
        ended_at_epoch_ms=1,
        artifact_paths=(),
        step_results=(
            StepResult(
                step_id="verify_timeout_asset",
                phase="assert",
                status=ExecutionStatus.PASSED,
                error_code="OFFICIAL_ASSET_VERIFY_TIMEOUT",
                data_summary={
                    "id": "url:https://example.invalid/asset.usd",
                    "kind": "asset",
                    "name": "asset.usd",
                    "app_profile": "isaac-sim",
                    "verification_status": "failed",
                    "load_quality": "content_verified_no_bbox",
                    "attempt": 2,
                    "timeout_s": 0.001,
                    "retry_count": 1,
                    "error": "TimeoutError",
                    "canonical_url": "https://example.invalid/asset.usd",
                    "diagnostics": {
                        "reason": "verify_timeout",
                        "target_status": "load_verified",
                        "current_catalog_status": "discovered",
                        "error_type": "TimeoutError",
                        "suggested_next": [
                            "Retry official_asset_verify with a larger timeout_s.",
                        ],
                        "fallback_tool_order": [
                            "official_asset_sync_status",
                            "official_asset_verify",
                        ],
                        "asset_checks": {
                            "load_quality": None,
                            "bbox_valid": None,
                        },
                    },
                },
            ),
        ),
    )

    report = json.loads(to_json(summary))
    evidence = report["evidence_summary"][0]

    assert evidence["evidence_kind"] == "official_asset_verify"
    assert evidence["error_code"] == "OFFICIAL_ASSET_VERIFY_TIMEOUT"
    assert evidence["load_quality"] == "content_verified_no_bbox"
    assert evidence["diagnostics"]["reason"] == "verify_timeout"
    assert evidence["diagnostics"]["error_type"] == "TimeoutError"
    markdown = to_markdown(summary)
    assert "error_code=OFFICIAL_ASSET_VERIFY_TIMEOUT" in markdown
    assert "diagnostics.error_type=TimeoutError" in markdown


@pytest.mark.asyncio
async def test_official_asset_verify_material_failure_diagnostics_survive_runner_report(
    tmp_path: Path,
):
    """Material verify failures must keep assign/bind diagnostics in reports."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    catalog_dir = _write_minimal_official_material_catalog(tmp_path)
    isaac_client = MockIsaacRestClient()
    isaac_client.responses["material_get_bound"] = {
        "ok": True,
        "prim_path": "/World/OfficialMaterialVerify/Brushed_AluminumTarget",
        "material_path": "",
    }
    runner = _build_runner(isaac_client, MockLakehouseClient())
    runner._modules[ModuleName.ASSET] = AssetModule(
        isaac_client,
        official_catalog_dir=catalog_dir,
    )
    material_id = (
        "url:https://omniverse-content-production.s3-us-west-2.amazonaws.com"
        "/Assets/Materials/2023_2_1/Base/Metals/Brushed_Aluminum.mdl"
    )
    raw = {
        "apiVersion": "isaacsim.validation/v1",
        "kind": "Scenario",
        "metadata": {
            "id": "official_material_verify_failed_diag",
            "name": "official material verify failed diag",
        },
        "spec": {
            "assert": [
                {
                    "id": "verify_unbound_material",
                    "module": "asset",
                    "action": "official_verify",
                    "args": {
                        "asset_id": material_id,
                        "app_profile": "usd-composer",
                        "timeout_s": 1.0,
                    },
                }
            ]
        },
    }

    summary = await runner.run(compile_scenario(raw))

    assert summary.status == ExecutionStatus.PASSED, summary
    step = summary.step_results[0]
    assert step.status == ExecutionStatus.PASSED
    assert step.data_summary["verification_status"] == "failed"
    diagnostics = step.data_summary["diagnostics"]
    assert diagnostics["reason"] == "material_assign_or_binding_failed"
    assert diagnostics["target_status"] == "assign_verified"
    assert diagnostics["material_checks"] == {
        "create_prim_ok": True,
        "assign_ok": True,
        "bound_ok": False,
    }

    json_report = json.loads(to_json(summary))
    assert json_report["diagnostic_next_actions"] == [{
        "step_id": "verify_unbound_material",
        "phase": "assert",
        "source": "step",
        "status": "passed",
        "diagnostics.reason": "material_assign_or_binding_failed",
        "diagnostics.target_status": "assign_verified",
        "diagnostics.current_catalog_status": "assign_verified",
        "suggested_next": [
            "Inspect create_prim, assign, and bound fields to locate the "
            "material binding failure.",
            "Retry in the app_profile that provides the material before "
            "assigning it in a user scene.",
        ],
        "diagnostics.fallback_tool_order": [
            "official_asset_sync_status",
            "official_asset_search",
            "official_asset_resolve",
            "official_asset_verify",
            "asset_search",
        ],
        "diagnostics.material_checks": {
            "create_prim_ok": True,
            "assign_ok": True,
            "bound_ok": False,
        },
    }]
    json_step = json_report["step_results"][0]
    assert json_step["diagnostic_next_actions"][
        "diagnostics.material_checks"
    ]["bound_ok"] is False
    evidence_report = {
        result["step_id"]: result for result in json_report["evidence_summary"]
    }
    material_evidence = evidence_report["verify_unbound_material"]
    assert material_evidence["evidence_kind"] == "official_asset_verify"
    assert material_evidence["verification_status"] == "failed"
    assert material_evidence["kind"] == "material"
    assert material_evidence["app_profile"] == "usd-composer"
    assert material_evidence["diagnostics"]["reason"] == (
        "material_assign_or_binding_failed"
    )
    assert material_evidence["diagnostics"]["material_checks"]["bound_ok"] is False

    markdown = to_markdown(summary)
    assert "## Diagnostic Next Actions" in markdown
    assert "## Evidence Summary" in markdown
    assert (
        "`verify_unbound_material`: "
        "evidence_kind=official_asset_verify; status=passed"
    ) in markdown
    assert (
        "- `verify_unbound_material`: "
        "diagnostics.reason=material_assign_or_binding_failed"
    ) in markdown
    assert "diagnostics.material_checks.create_prim_ok=True" in markdown
    assert "diagnostics.material_checks.assign_ok=True" in markdown
    assert "diagnostics.material_checks.bound_ok=False" in markdown


@pytest.mark.asyncio
async def test_official_asset_verify_live_smoke_routes_through_runner(
    tmp_path: Path,
):
    """The official asset verify smoke scenario must route without fallback reset."""
    from tests.conftest import MockIsaacRestClient, MockLakehouseClient

    catalog_dir = _write_minimal_official_catalog(tmp_path)
    isaac_client = MockIsaacRestClient()
    runner = _build_runner(isaac_client, MockLakehouseClient())
    runner._modules[ModuleName.ASSET] = AssetModule(
        isaac_client,
        official_catalog_dir=catalog_dir,
    )
    raw = load_scenario(
        PROJECT / "scenarios" / "smoke" / "official_asset_verify_live.yaml"
    )
    plan = _scenario_plan_payload(compile_scenario(raw))
    diagnostic_steps = {step["id"]: step for step in plan["diagnostic_steps"]}
    assert list(diagnostic_steps) == [
        "check_isaac_catalog",
        "search_pallet_asset",
        "resolve_pallet_asset",
        "get_pallet_entry",
    ]
    assert diagnostic_steps["resolve_pallet_asset"] == {
        "id": "resolve_pallet_asset",
        "phase": "assert",
        "module": "asset",
        "action": "official_resolve",
        "diagnostic_kind": "official_asset_resolve",
        "key_args": {
            "name_or_id": "pallet",
            "kind": "asset",
            "app_profile": "isaac-sim",
            "prefer_loadable": True,
        },
    }
    evidence_steps = {step["id"]: step for step in plan["evidence_steps"]}
    assert evidence_steps["verify_pallet_asset"] == {
        "id": "verify_pallet_asset",
        "phase": "assert",
        "module": "asset",
        "action": "official_verify",
        "evidence_kind": "official_asset_verify",
        "key_args": {
            "asset_id": (
                "url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com/"
                "Assets/simready_content/common_assets/props/aluminumpallet_a01/"
                "aluminumpallet_a01.usd"
            ),
            "app_profile": "isaac-sim",
            "timeout_s": 180,
        },
    }
    mutation_steps = {step["id"]: step for step in plan["stage_mutation_steps"]}
    assert plan["stage_mutation_summary"] == {
        "read_only": False,
        "requires_scratch_stage": True,
        "mutation_count": 1,
        "phase_counts": {
            "arrange": 0,
            "act": 0,
            "assert": 1,
            "cleanup": 0,
        },
        "mutation_kinds": ["official_asset_verify_stage_probe"],
    }
    assert mutation_steps["verify_pallet_asset"] == {
        "id": "verify_pallet_asset",
        "phase": "assert",
        "module": "asset",
        "action": "official_verify",
        "mutation_kind": "official_asset_verify_stage_probe",
        "key_args": {
            "asset_id": (
                "url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com/"
                "Assets/simready_content/common_assets/props/aluminumpallet_a01/"
                "aluminumpallet_a01.usd"
            ),
            "app_profile": "isaac-sim",
            "timeout_s": 180,
        },
    }
    live_validation_checklist = plan["live_validation_checklist"]
    assert live_validation_checklist["scratch_stage_required"] is True
    assert live_validation_checklist["log_capture_recommended"] is True
    assert [step["tool"] for step in live_validation_checklist["steps"]] == [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan",
        "scenario_validate",
        "extension_clear_logs",
        "scenario_validate",
        "scenario_last_report",
        "extension_capture_logs",
    ]
    assert live_validation_checklist["steps"][4]["args"] == {"dry_run": True}
    assert live_validation_checklist["steps"][7]["args"] == {
        "report_format": "markdown",
        "redact_local_paths": True,
    }
    assert live_validation_checklist["steps"][8]["args"] == {
        "level": "WARN",
        "stop_after_capture": True,
    }

    summary = await runner.run(compile_scenario(raw))

    assert summary.status == ExecutionStatus.PASSED, summary
    steps = {step.step_id: step for step in summary.step_results}
    assert "__fallback_cleanup_reset" not in steps
    assert steps["search_pallet_asset"].data_summary["count"] == 1
    assert steps["resolve_pallet_asset"].data_summary["name"] == (
        "aluminumpallet_a01.usd"
    )
    assert steps["verify_pallet_asset"].data_summary["verification_status"] == (
        "load_verified"
    )
    assert steps["verify_pallet_asset"].data_summary["load_quality"] == "valid"
    json_report = json.loads(to_json(summary))
    evidence_report = {
        result["step_id"]: result for result in json_report["evidence_summary"]
    }
    assert evidence_report["verify_pallet_asset"]["evidence_kind"] == (
        "official_asset_verify"
    )
    assert evidence_report["verify_pallet_asset"]["verification_status"] == (
        "load_verified"
    )
    assert evidence_report["verify_pallet_asset"]["kind"] == "asset"
    assert evidence_report["verify_pallet_asset"]["app_profile"] == "isaac-sim"
    markdown = to_markdown(summary)
    assert "## Evidence Summary" in markdown
    assert (
        "`verify_pallet_asset`: "
        "evidence_kind=official_asset_verify; status=passed"
    ) in markdown
    assert ("stage_load_usd", {
        "usd_url": (
            "https://omniverse-content-staging.s3.us-west-2.amazonaws.com/"
            "Assets/simready_content/common_assets/props/aluminumpallet_a01/"
            "aluminumpallet_a01.usd"
        ),
        "prim_path": "/World/OfficialAssetVerify/aluminumpallet_a01",
        "position": None,
        "rotation": None,
    }) in isaac_client.calls
    assert ("stage_set_selection", {
        "prim_paths": [],
        "expand_in_stage": False,
    }) in isaac_client.calls
    assert ("stage_delete_prim", {
        "prim_path": "/World/OfficialAssetVerify/aluminumpallet_a01",
    }) in isaac_client.calls
    assert not any(call[0] == "extension_reset" for call in isaac_client.calls)


def _write_minimal_official_catalog(tmp_path: Path) -> Path:
    catalog_dir = tmp_path / "official-assets"
    catalog_dir.mkdir()
    url = (
        "https://omniverse-content-staging.s3.us-west-2.amazonaws.com/"
        "Assets/simready_content/common_assets/props/aluminumpallet_a01/"
        "aluminumpallet_a01.usd"
    )
    catalog_dir.joinpath("latest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2099-01-01T00:00:00Z",
                "snapshots": [
                    {
                        "app_profile": "isaac-sim",
                        "app_version": "6.0.0",
                        "kit_version": "110.1.1",
                        "providers": [],
                    }
                ],
                "items": [
                    {
                        "id": f"url:{url}",
                        "kind": "asset",
                        "name": "aluminumpallet_a01.usd",
                        "aliases": ["pallet", "aluminumpallet"],
                        "canonical_url": url,
                        "provider": "omni.simready.explorer",
                        "provided_in": [
                            {
                                "app_profile": "isaac-sim",
                                "provider": "omni.simready.explorer",
                            }
                        ],
                        "loadable_in": [
                            {
                                "app_profile": "isaac-sim",
                                "verification_status": "load_verified",
                            }
                        ],
                        "verification_status": "load_verified",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return catalog_dir


def _write_minimal_official_material_catalog(tmp_path: Path) -> Path:
    catalog_dir = tmp_path / "official-materials"
    catalog_dir.mkdir()
    url = (
        "https://omniverse-content-production.s3-us-west-2.amazonaws.com"
        "/Assets/Materials/2023_2_1/Base/Metals/Brushed_Aluminum.mdl"
    )
    catalog_dir.joinpath("latest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2099-01-01T00:00:00Z",
                "snapshots": [
                    {
                        "app_profile": "usd-composer",
                        "app_version": "2026.1.0",
                        "kit_version": "110.1.1",
                        "providers": [],
                    }
                ],
                "items": [
                    {
                        "id": f"url:{url}",
                        "kind": "material",
                        "name": "Brushed_Aluminum.mdl",
                        "aliases": ["brushed aluminum", "aluminum"],
                        "canonical_url": url,
                        "provider": "omni.kit.browser.material",
                        "provided_in": [
                            {
                                "app_profile": "usd-composer",
                                "provider": "omni.kit.browser.material",
                            }
                        ],
                        "loadable_in": [
                            {
                                "app_profile": "usd-composer",
                                "verification_status": "assign_verified",
                            }
                        ],
                        "verification_status": "assign_verified",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return catalog_dir


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
