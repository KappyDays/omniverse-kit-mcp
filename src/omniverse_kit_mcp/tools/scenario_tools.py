"""Layer 2: Scenario-level MCP Tools (3 tools for automated validation).

Scenario listing and schema are MCP resources:
``isaacsim://scenarios`` and ``isaacsim://scenario-schema``.
"""

from __future__ import annotations

import json
from dataclasses import asdict
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
from omniverse_kit_mcp.scenario.loader import list_scenarios, load_scenario, validate_schema
from omniverse_kit_mcp.scenario.reporters import to_json, to_markdown
from omniverse_kit_mcp.scenario.runner import ScenarioRunner
from omniverse_kit_mcp.scenario.schema import SCENARIO_SCHEMA
from omniverse_kit_mcp.types.scenario import CompiledStep
from omniverse_kit_mcp.tools.tool_profiles import (
    PROFILE_FULL,
    ToolSelection,
    build_tool_selection,
    selected_tool_decorator,
)

# Module-level store for last run reports
_last_reports: dict[str, str] = {}
_last_report_id: str | None = None


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
    ) -> str:
        """Execute YAML validation scenario (Arrange→Act→Assert→Cleanup). Returns step-level pass/fail summary. input_overrides substitutes scenario variables."""
        global _last_report_id
        safe_path = _resolve_safe_path(scenario_path, config.scenario.scenarios_dir)
        raw = load_scenario(safe_path)

        # Apply variable overrides before compilation
        if input_overrides:
            spec_vars = raw.get("spec", {}).get("variables", {})
            spec_vars.update(input_overrides)
            raw.setdefault("spec", {})["variables"] = spec_vars

        scenario = compile_scenario(raw)

        if dry_run:
            return json.dumps({
                "dry_run": True,
                "scenario_id": scenario.scenario_id,
                "steps": len(scenario.arrange_steps) + len(scenario.act_steps) + len(scenario.assert_steps),
                "variables": scenario.variables,
                "compiled": True,
            }, indent=2)

        summary = await runner.run(
            scenario,
            fail_fast_override=fail_fast,
        )
        report = to_json(summary)
        _last_reports[scenario.scenario_id] = report
        _last_report_id = scenario.scenario_id
        return report

    @tool()
    async def scenario_plan(
        scenario_path: str,
    ) -> str:
        """Compile scenario YAML and show execution plan (variables, phases, step graph) without running it."""
        safe_path = _resolve_safe_path(scenario_path, config.scenario.scenarios_dir)
        raw = load_scenario(safe_path)
        scenario = compile_scenario(raw)

        plan: dict[str, Any] = {
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "tags": list(scenario.tags),
            "defaults": {
                "step_timeout_s": scenario.defaults.step_timeout_s,
                "fail_fast": scenario.defaults.fail_fast,
            },
            "variables": scenario.variables,
            "phases": {
                "arrange": [_plan_step(s) for s in scenario.arrange_steps],
                "act": [_plan_step(s) for s in scenario.act_steps],
                "assert": [_plan_step(s) for s in scenario.assert_steps],
                "cleanup": [_plan_step(s) for s in scenario.cleanup_steps],
            },
        }
        return json.dumps(plan, indent=2, ensure_ascii=False)

    # Note: scenario_list and scenario_schema are MCP resources, not tools
    # (isaacsim://scenarios, isaacsim://scenario-schema)
    # — see src/omniverse_kit_mcp/mcp/resources.py.

    @tool()
    async def scenario_last_report(
        scenario_id: str | None = None,
    ) -> str:
        """Get the latest scenario_validate report, or a specific report by scenario_id."""
        target_id = scenario_id or _last_report_id
        if target_id is None:
            return json.dumps({"error": "No scenario reports have been recorded"})
        report = _last_reports.get(target_id)
        if report is None:
            return json.dumps({"error": f"No report found for scenario '{target_id}'"})
        return report


def _plan_step(step: CompiledStep) -> dict[str, Any]:
    planned: dict[str, Any] = {
        "id": step.id,
        "module": step.module.value,
        "action": step.action,
        "args": dict(step.args),
    }
    if step.idempotent:
        planned["idempotent"] = True
    if step.retry_policy is not None:
        planned["retries"] = {
            "maxAttempts": step.retry_policy.max_attempts,
            "initialBackoffSeconds": step.retry_policy.initial_backoff_s,
            "maxBackoffSeconds": step.retry_policy.max_backoff_s,
        }
    return planned
