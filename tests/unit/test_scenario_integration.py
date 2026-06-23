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
from omniverse_kit_mcp.scenario.reporters import to_json, to_markdown
from omniverse_kit_mcp.scenario.runner import ScenarioRunner
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

    assert (
        "| read\\|lidar | assert | failed | 1/1 | 5ms | "
        "bridge \\| retry<br>line two |"
    ) in markdown
    assert (
        "- `read|lidar` attempt 1: failed ERR_PIPE - "
        "first | failure<br>with detail"
    ) in markdown


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
                    f"capture saved at {capture_path}; pid=<process-id>; "
                    "thread_id=thread-example-7f3a; "
                    "pending_worktree_id=pw_message"
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
                    "pid": "<process-id>",
                    "process_id": "<process-id>",
                    "child_pids": [42125, 42126],
                    "nested": {"kit_pid": 42127},
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
    assert "worker-thread-123" not in serialized
    assert '"pid": "<process-id>"' in serialized
    assert '"process_id": "<process-id>"' in serialized
    assert '"thread_id": "<worker-thread-id>"' in serialized
    assert '"worker_id": "<worker-thread-id>"' in serialized
    assert '"pendingWorktreeId": "<worker-thread-id>"' in serialized
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
    assert "worker-thread-123" not in markdown
    assert "pid=<process-id>" in markdown
    assert "thread_id=<worker-thread-id>" in markdown
    assert "pending_worktree_id=<worker-thread-id>" in markdown


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
        "source": "step",
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
    assert raw_cloud["args"]["min_points"] == 1
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

    summary = await runner.run(scenario)

    assert summary.status == ExecutionStatus.PASSED, summary
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
        "empty_reason": "empty_scan_buffer",
        "suggested_next": "step more frames and retry idempotently",
        "diagnostics.readback_paths_attempted": [
            "cached_lidar_sensor",
            "replicator_annotator",
        ],
    }
    assert report["diagnostic_next_actions"] == [{
        "step_id": "read_lidar",
        "source": "retry_failure",
        "empty_reason": "empty_scan_buffer",
        "suggested_next": "step more frames and retry idempotently",
        "diagnostics.readback_paths_attempted": [
            "cached_lidar_sensor",
            "replicator_annotator",
        ],
        "attempt": 1,
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
        "- `read_lidar attempt 1`: empty_reason=empty_scan_buffer; "
        "suggested_next=step more frames and retry idempotently; "
        "diagnostics.readback_paths_attempted=[cached_lidar_sensor, "
        "replicator_annotator]"
    ) in markdown


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
    assert step_result.attempts == 0
    assert step_result.max_attempts == 2
    assert step_result.retry_failures == ()
    assert "idempotent=true" in (step_result.message or "")


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
    assert result.attempts == 1
    assert result.max_attempts == 3
    assert result.retry_failures == ({
        "attempt": 1,
        "status": "timeout",
        "error_code": None,
        "message": "Step timed out after 7s",
    },)


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

    summary = await runner.run(compile_scenario(raw))

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
    assert "**Steps**: 3 passed, 0 failed, 1 continued, 0 skipped" in markdown
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

    summary = await runner.run(compile_scenario(raw))

    assert summary.status == ExecutionStatus.PASSED, summary
    steps = {step.step_id: step for step in summary.step_results}
    assert "__fallback_cleanup_reset" not in steps
    assert steps["search_pallet_asset"].data_summary["count"] == 1
    assert steps["verify_pallet_asset"].data_summary["verification_status"] == (
        "load_verified"
    )
    assert steps["verify_pallet_asset"].data_summary["load_quality"] == "valid"
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
