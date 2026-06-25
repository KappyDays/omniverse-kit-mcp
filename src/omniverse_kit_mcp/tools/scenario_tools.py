"""Layer 2: Scenario-level MCP Tools (3 tools for automated validation).

Scenario listing and schema are MCP resources:
``isaacsim://scenarios`` and ``isaacsim://scenario-schema``.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.modules.asset_module import AssetModule
from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.modules.content_module import ContentModule
from omniverse_kit_mcp.modules.extension_module import ExtensionModule
from omniverse_kit_mcp.modules.job_module import JobModule
from omniverse_kit_mcp.modules.lakehouse_module import LakehouseModule
from omniverse_kit_mcp.modules.lighting_module import LightingModule
from omniverse_kit_mcp.modules.material_module import MaterialModule
from omniverse_kit_mcp.modules.navigation_module import NavigationModule
from omniverse_kit_mcp.modules.omnigraph_module import OmnigraphModule
from omniverse_kit_mcp.modules.physics_module import PhysicsModule
from omniverse_kit_mcp.modules.replicator_module import ReplicatorModule
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.modules.sensor_module import SensorModule
from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.modules.stage_module import StageModule
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.modules.window_module import WindowModule
from omniverse_kit_mcp.scenario.compiler import compile_scenario
from omniverse_kit_mcp.scenario.loader import load_scenario
from omniverse_kit_mcp.scenario.reporters import to_json, to_markdown
from omniverse_kit_mcp.scenario.runner import (
    ScenarioRunner,
    _scenario_needs_fallback_cleanup,
)
from omniverse_kit_mcp.types.scenario import (
    CompiledScenario,
    CompiledStep,
    ScenarioRunSummary,
)
from omniverse_kit_mcp.tools.tool_profiles import (
    PROFILE_FULL,
    ToolSelection,
    build_tool_selection,
    selected_tool_decorator,
)

# Module-level store for last run reports
_last_reports: dict[str, str] = {}
_last_report_summaries: dict[str, ScenarioRunSummary] = {}
_last_report_id: str | None = None

_EVIDENCE_STEP_SPECS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("asset", "official_verify"): (
        "official_asset_verify",
        ("asset_id", "app_profile", "timeout_s"),
    ),
    ("sensor", "lidar_get_point_cloud"): (
        "rtx_lidar_point_cloud",
        ("sensor_prim", "frames_to_wait", "min_points", "max_points", "fail_on_warning"),
    ),
    ("viewport", "frame_prims"): (
        "viewport_framing",
        ("prim_paths", "margin", "view_direction", "set_camera"),
    ),
    ("viewport", "capture"): (
        "visual_capture",
        ("width", "height", "warmup_frames", "return_stats"),
    ),
    ("viewport", "capture_assert"): (
        "visual_capture",
        ("width", "height", "warmup_frames", "min_mean", "min_variance"),
    ),
    ("window", "capture"): (
        "visual_capture",
        ("window_title", "wait_stable", "timeout_s"),
    ),
}
_DIAGNOSTIC_STEP_SPECS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("asset", "official_sync_status"): (
        "official_asset_sync_status",
        ("app_profile",),
    ),
    ("asset", "official_search"): (
        "official_asset_search",
        ("query", "kind", "app_profile", "provider", "min_status", "allow_stale", "limit"),
    ),
    ("asset", "official_resolve"): (
        "official_asset_resolve",
        ("name_or_id", "kind", "app_profile", "prefer_loadable"),
    ),
    ("asset", "official_get"): (
        "official_asset_get",
        ("asset_id", "app_profile"),
    ),
}
_STAGE_MUTATION_STEP_SPECS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("extension", "trigger"): (
        "extension_trigger_potential_stage_effect",
        ("operation", "wait_for_idle", "idle_timeout_s"),
    ),
    ("simulation", "stage_new"): ("stage_reset", ()),
    ("simulation", "stage_open"): ("stage_open", ("url",)),
    ("simulation", "stage_load_usd"): (
        "stage_load_usd",
        ("usd_url", "prim_path", "position", "rotation"),
    ),
    ("simulation", "stage_create_prim"): (
        "stage_create_prim",
        ("prim_path", "prim_type", "position"),
    ),
    ("simulation", "stage_set_property"): (
        "stage_set_property",
        ("prim_path", "property_name", "value", "type_hint"),
    ),
    ("simulation", "stage_set_semantic_label"): (
        "stage_set_semantic_label",
        ("prim_path", "label", "label_type"),
    ),
    ("simulation", "stage_delete_prim"): ("stage_delete_prim", ("prim_path",)),
    ("robot", "load"): (
        "robot_load",
        ("usd_url", "prim_path", "position", "rotation"),
    ),
    ("character", "load"): (
        "character_load",
        ("usd_url", "prim_path", "position", "yaw"),
    ),
    ("character", "load_crowd"): (
        "character_load_crowd",
        ("count", "layout", "base_name", "center", "usd_url"),
    ),
    ("sensor", "attach_rtx_camera"): (
        "sensor_attach_rtx_camera",
        ("robot_prim", "sensor_name", "mount_offset", "mount_rotation", "resolution"),
    ),
    ("sensor", "attach_rtx_lidar"): (
        "sensor_attach_rtx_lidar",
        ("robot_prim", "sensor_name", "mount_offset", "mount_rotation", "config_preset"),
    ),
    ("sensor", "attach_rtx_depth_camera"): (
        "sensor_attach_rtx_depth_camera",
        ("robot_prim", "sensor_name", "mount_offset", "mount_rotation", "resolution"),
    ),
    ("sensor", "attach_contact"): (
        "sensor_attach_contact",
        ("prim_path", "sensor_name", "frequency", "translation", "radius"),
    ),
    ("sensor", "attach_imu"): (
        "sensor_attach_imu",
        ("prim_path", "sensor_name", "frequency", "mount_offset"),
    ),
    ("sensor", "set_annotator"): (
        "sensor_annotator_binding",
        ("sensor_prim", "annotators", "resolution"),
    ),
    ("sensor", "set_visualization"): (
        "sensor_visualization_toggle",
        ("sensor_prim", "mode"),
    ),
    ("navigation", "add_exclude_volume"): (
        "navigation_add_exclude_volume",
        ("prim_path", "padding"),
    ),
    ("asset", "official_verify"): (
        "official_asset_verify_stage_probe",
        ("asset_id", "app_profile", "timeout_s"),
    ),
    ("lighting", "create_dome"): (
        "lighting_create_dome",
        ("prim_path", "intensity", "texture"),
    ),
    ("lighting", "create_distant"): (
        "lighting_create_distant",
        ("prim_path", "intensity", "angle_deg"),
    ),
    ("lighting", "create_disk"): (
        "lighting_create_disk",
        ("prim_path", "intensity", "radius"),
    ),
    ("lighting", "create_rect"): (
        "lighting_create_rect",
        ("prim_path", "intensity", "width", "height"),
    ),
    ("lighting", "create_sphere"): (
        "lighting_create_sphere",
        ("prim_path", "intensity", "radius"),
    ),
    ("physics", "apply_rigid_body"): (
        "physics_apply_rigid_body",
        ("prim_path", "mass", "dynamic"),
    ),
    ("physics", "apply_collider"): (
        "physics_apply_collider",
        ("prim_path", "approximation"),
    ),
    ("physics", "apply_material"): (
        "physics_apply_material",
        ("prim_path", "friction", "restitution", "density", "material_name"),
    ),
    ("physics", "create_joint"): (
        "physics_create_joint",
        ("joint_type", "body_a", "body_b", "joint_prim_path"),
    ),
    ("physics", "set_scene"): (
        "physics_set_scene",
        ("scene_prim_path", "gravity", "timestep"),
    ),
    ("material", "assign_mdl"): (
        "material_assign_mdl",
        ("prim_path", "mdl_url", "material_name"),
    ),
    ("omnigraph", "create_node"): (
        "omnigraph_create_node",
        ("graph_path", "node_type", "node_name"),
    ),
    ("omnigraph", "connect"): (
        "omnigraph_connect",
        ("src_attr", "dst_attr"),
    ),
    ("omnigraph", "create_ros2_publisher"): (
        "omnigraph_create_ros2_publisher",
        ("graph_path", "topic", "source_prim", "msg_type"),
    ),
    ("omnigraph", "create_script_controller"): (
        "omnigraph_create_script_controller",
        ("graph_path", "script_path", "node_name"),
    ),
}
_TIMELINE_CONTROL_STEP_SPECS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("simulation", "play"): ("play", ()),
    ("simulation", "pause"): ("pause", ()),
    ("simulation", "stop"): ("stop", ()),
    ("simulation", "step"): ("step", ("frames",)),
    ("simulation", "set_time"): ("set_time", ("time",)),
    ("simulation", "wait_until"): ("wait_until", ("until_time", "timeout_s")),
}
_PLAY_REQUIRED_STEP_SPECS: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {
    ("robot", "set_joint_positions"): (
        "robot_articulation_write",
        ("prim_path", "positions"),
    ),
    ("robot", "navigate_to"): (
        "robot_navigation",
        ("prim_path", "target_position", "timeout_s"),
    ),
    ("robot", "navigate_path"): (
        "robot_navigation_path",
        ("prim_path", "waypoints", "timeout_s"),
    ),
    ("robot", "drive_physics"): (
        "robot_physics_drive",
        ("prim_path", "target_position", "duration_s"),
    ),
    ("robot", "gripper_control"): (
        "robot_gripper_control",
        ("prim_path", "action", "position"),
    ),
    ("robot", "set_ee_target"): (
        "robot_ik_target",
        ("prim_path", "target_position", "end_effector_frame"),
    ),
    ("robot", "run_franka_pick_place"): (
        "robot_pick_place_controller",
        ("robot_prim_path", "cube_prim_path", "target_position"),
    ),
    ("character", "navigate_to"): (
        "character_navigation",
        ("prim_path", "target_position", "timeout_s"),
    ),
    ("sensor", "attach_rtx_lidar"): (
        "rtx_lidar_attach_during_play",
        ("robot_prim", "sensor_name", "config_preset"),
    ),
    ("sensor", "lidar_get_point_cloud"): (
        "rtx_lidar_readback",
        ("sensor_prim", "frames_to_wait", "min_points", "max_points", "fail_on_warning"),
    ),
    ("simulation", "wait_until"): (
        "simulation_time_wait",
        ("until_time", "timeout_s"),
    ),
}


def _resolve_safe_path(user_path: str, scenarios_root: str) -> str:
    """Resolve a scenario path safely within the configured scenarios root.

    Prevents path traversal attacks (M-5) by ensuring the resolved path
    is within the scenarios directory.
    """
    from pathlib import Path
    root = Path(scenarios_root).resolve()
    # If user_path is a scenario ID (no separators), look for it under root
    candidate = Path(user_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    # Ensure resolved path is under the scenarios root
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Scenario path '{user_path}' resolves outside the allowed "
            f"scenarios directory '{root}'"
        )
    return str(resolved)


def register_scenario_tools(
    mcp: FastMCP,
    config: AppConfig,
    stage: StageModule,
    viewport: ViewportModule,
    lakehouse: LakehouseModule,
    extension: ExtensionModule,
    simulation: SimulationModule,
    robot: RobotModule,
    job: JobModule,
    asset: AssetModule,
    character: CharacterModule,
    window: WindowModule,
    navigation: NavigationModule,
    sensor: SensorModule,
    physics: PhysicsModule,
    lighting: LightingModule,
    material: MaterialModule,
    replicator: ReplicatorModule,
    omnigraph: OmnigraphModule,
    content: ContentModule,
    *,
    selection: ToolSelection | None = None,
) -> None:
    """Register all 3 scenario-level tools on the MCP server."""
    if selection is None:
        selection = build_tool_selection(profile=PROFILE_FULL)
    tool = selected_tool_decorator(mcp, selection)

    runner = ScenarioRunner(
        stage, viewport, lakehouse, extension, simulation, robot, job, asset, character,
        window, navigation, sensor, physics, lighting, material,
        replicator, omnigraph, content,
    )

    @tool()
    async def scenario_validate(
        scenario_path: str,
        dry_run: bool = False,
        fail_fast: bool | None = None,
        input_overrides: dict[str, Any] | None = None,
        report_format: str = "json",
        redact_local_paths: bool = False,
    ) -> str:
        """Execute YAML validation scenario (Arrange→Act→Assert→Cleanup).

        Returns JSON by default; pass report_format='markdown' for a
        human-readable report with data summary highlights. Set
        redact_local_paths=true before copying a live report into public
        artifacts. input_overrides substitutes scenario variables.
        """
        global _last_report_id
        try:
            normalized_report_format = _normalize_report_format(report_format)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        safe_path = _resolve_safe_path(scenario_path, config.scenario.scenarios_dir)
        raw = load_scenario(safe_path)

        _apply_input_overrides(raw, input_overrides)

        scenario = compile_scenario(raw)

        if dry_run:
            plan = _scenario_plan_payload(scenario)
            return json.dumps({
                **plan,
                "dry_run": True,
                "steps": plan["total_steps"],
                "compiled": True,
            }, indent=2, ensure_ascii=False)

        summary = await runner.run(
            scenario,
            fail_fast_override=fail_fast,
        )
        report = to_json(summary)
        _last_reports[scenario.scenario_id] = report
        _last_report_summaries[scenario.scenario_id] = summary
        _last_report_id = scenario.scenario_id
        return _format_report(
            summary,
            normalized_report_format,
            redact_local_paths=redact_local_paths,
        )

    @tool()
    async def scenario_plan(
        scenario_path: str,
        input_overrides: dict[str, Any] | None = None,
    ) -> str:
        """Compile scenario YAML and show execution plan without running it.

        input_overrides substitutes scenario variables.
        """
        safe_path = _resolve_safe_path(scenario_path, config.scenario.scenarios_dir)
        raw = load_scenario(safe_path)
        _apply_input_overrides(raw, input_overrides)
        scenario = compile_scenario(raw)

        plan = _scenario_plan_payload(scenario)
        return json.dumps(plan, indent=2, ensure_ascii=False)

    # Note: scenario_list and scenario_schema are MCP resources, not tools
    # (isaacsim://scenarios, isaacsim://scenario-schema)
    # — see src/omniverse_kit_mcp/mcp/resources.py.

    @tool()
    async def scenario_last_report(
        scenario_id: str | None = None,
        report_format: str = "json",
        redact_local_paths: bool = False,
    ) -> str:
        """Get the latest scenario_validate report, or a specific report by scenario_id.

        Defaults to JSON; pass report_format='markdown' for a human-readable
        report with data summary highlights. Set redact_local_paths=true before
        copying live evidence into public artifacts.
        """
        try:
            normalized_report_format = _normalize_report_format(report_format)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        target_id = scenario_id or _last_report_id
        if target_id is None:
            return json.dumps({"error": "No scenario reports have been recorded"})
        if normalized_report_format == "markdown":
            summary = _last_report_summaries.get(target_id)
            if summary is None:
                return json.dumps({
                    "error": (
                        f"No markdown report found for scenario '{target_id}'. "
                        "Run scenario_validate again before requesting markdown."
                    )
                })
            return to_markdown(summary, redact_local_paths=redact_local_paths)
        if redact_local_paths:
            summary = _last_report_summaries.get(target_id)
            if summary is None:
                return json.dumps({
                    "error": (
                        f"No redactable report found for scenario '{target_id}'. "
                        "Run scenario_validate again before requesting redaction."
                    )
                })
            return to_json(summary, redact_local_paths=True)
        report = _last_reports.get(target_id)
        if report is None:
            return json.dumps({"error": f"No report found for scenario '{target_id}'"})
        return report


def _apply_input_overrides(
    raw: dict[str, Any],
    input_overrides: dict[str, Any] | None,
) -> None:
    if not input_overrides:
        return
    spec_vars = raw.get("spec", {}).get("variables", {})
    spec_vars.update(input_overrides)
    raw.setdefault("spec", {})["variables"] = spec_vars


def _scenario_plan_payload(scenario: CompiledScenario) -> dict[str, Any]:
    phases = {
        "arrange": [
            _plan_step(s, default_timeout_s=scenario.defaults.step_timeout_s)
            for s in scenario.arrange_steps
        ],
        "act": [
            _plan_step(s, default_timeout_s=scenario.defaults.step_timeout_s)
            for s in scenario.act_steps
        ],
        "assert": [
            _plan_step(s, default_timeout_s=scenario.defaults.step_timeout_s)
            for s in scenario.assert_steps
        ],
        "cleanup": [
            _plan_step(s, default_timeout_s=scenario.defaults.step_timeout_s)
            for s in scenario.cleanup_steps
        ],
    }
    if _scenario_needs_fallback_cleanup(scenario):
        phases["cleanup"].append(_plan_fallback_cleanup_step())
    phase_counts = {phase: len(steps) for phase, steps in phases.items()}
    stage_mutation_steps = _plan_stage_mutation_steps(phases)
    stage_mutation_summary = _plan_stage_mutation_summary(stage_mutation_steps)
    diagnostic_steps = _plan_diagnostic_steps(phases)
    evidence_steps = _plan_evidence_steps(phases)
    retry_steps = _plan_retry_steps(phases)
    simulation_state_steps = _plan_simulation_state_steps(phases)
    timeline_control_steps = _plan_timeline_control_steps(phases)
    simulation_state_summary = _plan_simulation_state_summary(
        simulation_state_steps,
        timeline_control_steps,
    )
    live_validation_checklist = _plan_live_validation_checklist(
        stage_mutation_summary=stage_mutation_summary,
        diagnostic_steps=diagnostic_steps,
        evidence_steps=evidence_steps,
        simulation_state_summary=simulation_state_summary,
    )
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "tags": list(scenario.tags),
        "defaults": {
            "step_timeout_s": scenario.defaults.step_timeout_s,
            "fail_fast": scenario.defaults.fail_fast,
        },
        "variables": scenario.variables,
        "total_steps": sum(phase_counts.values()),
        "phase_counts": phase_counts,
        "diagnostic_steps": diagnostic_steps,
        "stage_mutation_summary": stage_mutation_summary,
        "stage_mutation_steps": stage_mutation_steps,
        "evidence_steps": evidence_steps,
        "retry_steps": retry_steps,
        "preflight_requirements": _plan_preflight_requirements(
            scenario_tags=scenario.tags,
            stage_mutation_summary=stage_mutation_summary,
            simulation_state_summary=simulation_state_summary,
            live_validation_checklist=live_validation_checklist,
            retry_steps=retry_steps,
        ),
        "simulation_state_summary": simulation_state_summary,
        "live_validation_checklist": live_validation_checklist,
        "simulation_state_steps": simulation_state_steps,
        "timeline_control_steps": timeline_control_steps,
        "phases": phases,
    }


def _plan_fallback_cleanup_step() -> dict[str, Any]:
    return {
        "id": "__fallback_cleanup_reset",
        "module": "extension",
        "action": "reset",
        "args": {},
        "automatic": True,
    }


def _plan_step(
    step: CompiledStep,
    *,
    default_timeout_s: float | None = None,
) -> dict[str, Any]:
    planned: dict[str, Any] = {
        "id": step.id,
        "module": step.module.value,
        "action": step.action,
        "args": dict(step.args),
    }
    if step.timeout_s is not None and step.timeout_s != default_timeout_s:
        planned["timeoutSeconds"] = step.timeout_s
    if step.idempotent:
        planned["idempotent"] = True
    if step.continue_on_failure:
        planned["continueOnFailure"] = True
    if step.retry_policy is not None:
        planned["retries"] = {
            "maxAttempts": step.retry_policy.max_attempts,
            "initialBackoffSeconds": step.retry_policy.initial_backoff_s,
            "maxBackoffSeconds": step.retry_policy.max_backoff_s,
        }
    return planned


def _plan_evidence_steps(
    phases: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    evidence_steps: list[dict[str, Any]] = []
    for phase, steps in phases.items():
        for step in steps:
            spec = _EVIDENCE_STEP_SPECS.get((step["module"], step["action"]))
            if spec is None:
                continue
            evidence_kind, arg_keys = spec
            planned: dict[str, Any] = {
                "id": step["id"],
                "phase": phase,
                "module": step["module"],
                "action": step["action"],
                "evidence_kind": evidence_kind,
            }
            key_args = _selected_plan_args(step.get("args"), arg_keys)
            if key_args:
                planned["key_args"] = key_args
            _copy_plan_control_fields(step, planned)
            evidence_steps.append(planned)
    return evidence_steps


def _plan_diagnostic_steps(
    phases: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    diagnostic_steps: list[dict[str, Any]] = []
    for phase, steps in phases.items():
        for step in steps:
            spec = _DIAGNOSTIC_STEP_SPECS.get((step["module"], step["action"]))
            if spec is None:
                continue
            diagnostic_kind, arg_keys = spec
            planned: dict[str, Any] = {
                "id": step["id"],
                "phase": phase,
                "module": step["module"],
                "action": step["action"],
                "diagnostic_kind": diagnostic_kind,
            }
            key_args = _selected_plan_args(step.get("args"), arg_keys)
            if key_args:
                planned["key_args"] = key_args
            _copy_plan_control_fields(step, planned)
            diagnostic_steps.append(planned)
    return diagnostic_steps


def _plan_stage_mutation_steps(
    phases: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    mutation_steps: list[dict[str, Any]] = []
    for phase, steps in phases.items():
        for step in steps:
            spec = _STAGE_MUTATION_STEP_SPECS.get((step["module"], step["action"]))
            if spec is None:
                spec = _conditional_stage_mutation_spec(step)
            if spec is None:
                continue
            mutation_kind, arg_keys = spec
            planned: dict[str, Any] = {
                "id": step["id"],
                "phase": phase,
                "module": step["module"],
                "action": step["action"],
                "mutation_kind": mutation_kind,
            }
            key_args = _selected_plan_args(step.get("args"), arg_keys)
            if key_args:
                planned["key_args"] = key_args
            _copy_plan_control_fields(step, planned)
            mutation_steps.append(planned)
    return mutation_steps


def _plan_stage_mutation_summary(
    mutation_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    phase_counts = {phase: 0 for phase in ("arrange", "act", "assert", "cleanup")}
    mutation_kinds: set[str] = set()
    for step in mutation_steps:
        phase = step.get("phase")
        if isinstance(phase, str):
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        mutation_kind = step.get("mutation_kind")
        if isinstance(mutation_kind, str):
            mutation_kinds.add(mutation_kind)
    return {
        "read_only": not mutation_steps,
        "requires_scratch_stage": bool(mutation_steps),
        "mutation_count": len(mutation_steps),
        "phase_counts": phase_counts,
        "mutation_kinds": sorted(mutation_kinds),
    }


def _plan_simulation_state_steps(
    phases: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    state_steps: list[dict[str, Any]] = []
    is_playing = False
    for phase, steps in phases.items():
        for step in steps:
            spec = _PLAY_REQUIRED_STEP_SPECS.get((step["module"], step["action"]))
            if spec is not None:
                requirement_kind, arg_keys = spec
                planned: dict[str, Any] = {
                    "id": step["id"],
                    "phase": phase,
                    "module": step["module"],
                    "action": step["action"],
                    "requirement_kind": requirement_kind,
                    "requires": "simulation_play_active",
                    "play_state_before_step": is_playing,
                }
                key_args = _selected_plan_args(step.get("args"), arg_keys)
                if key_args:
                    planned["key_args"] = key_args
                _copy_plan_control_fields(step, planned)
                state_steps.append(planned)
            is_playing = _timeline_state_after_step(step, is_playing)
    return state_steps


def _plan_timeline_control_steps(
    phases: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    control_steps: list[dict[str, Any]] = []
    for phase, steps in phases.items():
        for step in steps:
            spec = _TIMELINE_CONTROL_STEP_SPECS.get((step["module"], step["action"]))
            if spec is None:
                continue
            control_kind, arg_keys = spec
            planned: dict[str, Any] = {
                "id": step["id"],
                "phase": phase,
                "module": step["module"],
                "action": step["action"],
                "control_kind": control_kind,
            }
            key_args = _selected_plan_args(step.get("args"), arg_keys)
            if key_args:
                planned["key_args"] = key_args
            _copy_plan_control_fields(step, planned)
            control_steps.append(planned)
    return control_steps


def _plan_simulation_state_summary(
    simulation_state_steps: list[dict[str, Any]],
    timeline_control_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    control_counts = {
        kind: 0
        for kind, _arg_keys in _TIMELINE_CONTROL_STEP_SPECS.values()
    }
    for step in timeline_control_steps:
        control_kind = step.get("control_kind")
        if isinstance(control_kind, str):
            control_counts[control_kind] = control_counts.get(control_kind, 0) + 1
    missing_play_count = sum(
        1
        for step in simulation_state_steps
        if not step.get("play_state_before_step")
    )
    warnings = []
    if missing_play_count:
        warnings.append("simulation_play_missing_before_required_steps")
    return {
        "requires_play": bool(simulation_state_steps),
        "requires_play_count": len(simulation_state_steps),
        "play_state_missing_count": missing_play_count,
        "has_simulation_play": control_counts.get("play", 0) > 0,
        "has_simulation_pause": control_counts.get("pause", 0) > 0,
        "has_simulation_stop": control_counts.get("stop", 0) > 0,
        "timeline_control_counts": dict(sorted(control_counts.items())),
        "warnings": warnings,
    }


def _plan_preflight_requirements(
    *,
    scenario_tags: tuple[str, ...],
    stage_mutation_summary: dict[str, Any],
    simulation_state_summary: dict[str, Any],
    live_validation_checklist: dict[str, Any],
    retry_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    runtime_checks = [
        "tool_profile",
        "app_profile",
        "tool_count",
        "source_newer_than_import=false",
        "restart_required_for_latest_mcp_code=false",
    ]
    if "robot" in scenario_tags:
        runtime_checks.extend([
            "robot_probe_result_has_checks=true",
            "robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE",
            (
                "robot_probe_unknown_profile_error_data_path="
                "data.checks.probe.evidence"
            ),
            "robot_probe_unknown_profile_fallback_tool_order",
        ])
    return {
        "runtime_info": {
            "required": True,
            "checks": runtime_checks,
        },
        "scratch_stage": {
            "required": bool(stage_mutation_summary.get("requires_scratch_stage")),
            "pass_condition": "use scratch/test stage for mutating scenarios",
        },
        "log_capture": {
            "recommended": bool(
                live_validation_checklist.get("log_capture_recommended")
            ),
            "pass_condition": "clear logs before mutating run, capture WARN+ after run",
        },
        "simulation_play_gate": {
            "required": bool(simulation_state_summary.get("requires_play")),
            "missing_before_required_step_count": (
                simulation_state_summary.get("play_state_missing_count")
            ),
            "pass_condition": "play_state_missing_count == 0",
        },
        "retry_gate": {
            "required": bool(retry_steps),
            "retry_step_count": len(retry_steps),
            "pass_condition": "retry_steps[].key_args match intended proof thresholds",
        },
    }


def _plan_live_validation_checklist(
    *,
    stage_mutation_summary: dict[str, Any],
    diagnostic_steps: list[dict[str, Any]],
    evidence_steps: list[dict[str, Any]],
    simulation_state_summary: dict[str, Any],
) -> dict[str, Any]:
    log_capture_recommended = bool(
        diagnostic_steps
        or evidence_steps
        or stage_mutation_summary.get("requires_scratch_stage")
        or simulation_state_summary.get("requires_play")
    )
    steps: list[dict[str, Any]] = []

    def append_step(
        *,
        phase: str,
        tool: str,
        purpose: str,
        args: dict[str, Any] | None = None,
    ) -> None:
        step: dict[str, Any] = {
            "order": len(steps) + 1,
            "phase": phase,
            "tool": tool,
            "purpose": purpose,
        }
        if args:
            step["args"] = args
        steps.append(step)

    append_step(
        phase="preflight",
        tool="mcp_runtime_info",
        purpose="confirm_profile_and_import_freshness",
    )
    append_step(
        phase="startup",
        tool="kit_app_start",
        purpose="attach_or_start_workspace_kit",
    )
    append_step(
        phase="preflight",
        tool="simulation_get_status",
        purpose="record_timeline_baseline",
    )
    append_step(
        phase="preflight",
        tool="scenario_plan",
        purpose="confirm_plan_shape_before_mutation",
    )
    if stage_mutation_summary.get("requires_scratch_stage"):
        append_step(
            phase="preflight",
            tool="scenario_validate",
            args={"dry_run": True},
            purpose="confirm_scratch_stage_boundary_before_mutation",
        )
    if log_capture_recommended:
        append_step(
            phase="preflight",
            tool="extension_clear_logs",
            purpose="start_request_scoped_warn_error_window",
        )
    append_step(
        phase="execute",
        tool="scenario_validate",
        purpose="run_scenario",
    )
    append_step(
        phase="evidence",
        tool="scenario_last_report",
        args={
            "report_format": "markdown",
            "redact_local_paths": True,
        },
        purpose="capture_public_safe_triage_report",
    )
    if log_capture_recommended:
        append_step(
            phase="triage",
            tool="extension_capture_logs",
            args={
                "level": "WARN",
                "stop_after_capture": True,
            },
            purpose="capture_warn_error_after_run",
        )
    return {
        "scratch_stage_required": bool(
            stage_mutation_summary.get("requires_scratch_stage")
        ),
        "log_capture_recommended": log_capture_recommended,
        "steps": steps,
    }


def _timeline_state_after_step(
    step: dict[str, Any],
    is_playing: bool,
) -> bool:
    if step["module"] != "simulation":
        return is_playing
    if step["action"] == "play":
        return True
    if step["action"] in {"pause", "stop"}:
        return False
    return is_playing


def _conditional_stage_mutation_spec(
    step: dict[str, Any],
) -> tuple[str, tuple[str, ...]] | None:
    args = step.get("args")
    if not isinstance(args, dict):
        return None
    if (
        step["module"] == "extension"
        and step["action"] == "reset"
        and args.get("reset_stage_changes") is True
    ):
        return (
            "extension_reset_stage_changes",
            ("reset_stage_changes", "reset_internal_state", "clear_caches"),
        )
    return None


def _plan_retry_steps(
    phases: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    retry_steps: list[dict[str, Any]] = []
    for phase, steps in phases.items():
        for step in steps:
            if not step.get("idempotent") and "retries" not in step:
                continue
            planned = {
                "id": step["id"],
                "phase": phase,
                "module": step["module"],
                "action": step["action"],
            }
            spec = _EVIDENCE_STEP_SPECS.get((step["module"], step["action"]))
            if spec is not None:
                _, arg_keys = spec
                key_args = _selected_plan_args(step.get("args"), arg_keys)
                if key_args:
                    planned["key_args"] = key_args
            _copy_plan_control_fields(step, planned)
            retry_steps.append(planned)
    return retry_steps


def _selected_plan_args(
    args: Any,
    keys: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(args, dict):
        return {}
    return {key: args[key] for key in keys if key in args}


def _copy_plan_control_fields(
    source: dict[str, Any],
    target: dict[str, Any],
) -> None:
    for key in ("timeoutSeconds", "idempotent", "continueOnFailure", "retries"):
        if key in source:
            target[key] = source[key]


def _normalize_report_format(report_format: str) -> str:
    normalized = report_format.strip().lower()
    if normalized == "md":
        return "markdown"
    if normalized in {"json", "markdown"}:
        return normalized
    raise ValueError(
        "report_format must be 'json', 'markdown', or 'md'"
    )


def _format_report(
    summary: ScenarioRunSummary,
    report_format: str,
    *,
    redact_local_paths: bool = False,
) -> str:
    if report_format == "markdown":
        return to_markdown(summary, redact_local_paths=redact_local_paths)
    return to_json(summary, redact_local_paths=redact_local_paths)
