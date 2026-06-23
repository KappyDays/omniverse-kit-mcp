"""Standalone scenario runner.

Bypasses the cached MCP-server import graph so updates to action_registry /
runner / schema take effect without restarting the Claude Code session.

Usage:
    .venv/Scripts/python.exe scripts/run_scenario_standalone.py <scenario_path>
    .venv/Scripts/python.exe scripts/run_scenario_standalone.py --dry-run <scenario_path>
"""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.clients.lakehouse_client import LakehouseClient
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
from omniverse_kit_mcp.scenario.runner import ScenarioRunner
from omniverse_kit_mcp.tools.scenario_tools import (
    _apply_input_overrides,
    _scenario_plan_payload,
)


async def run(
    scenario_path: str,
    *,
    dry_run: bool = False,
    input_overrides: dict[str, object] | None = None,
    report_format: str = "both",
    redact_local_paths: bool = False,
) -> int:
    os.chdir(PROJECT_ROOT)
    config = AppConfig()
    resolved_path = _resolve_scenario_path(scenario_path, config)
    raw = load_scenario(resolved_path)
    _apply_input_overrides(raw, input_overrides)
    scenario = compile_scenario(raw)
    normalized_report_format = _normalize_report_format(report_format)
    if dry_run:
        plan = _scenario_plan_payload(scenario)
        print("===== DRY RUN PLAN =====")
        print(json.dumps({
            **plan,
            "dry_run": True,
            "steps": plan["total_steps"],
            "compiled": True,
        }, indent=2, ensure_ascii=False))
        return 0

    isaac_client = IsaacRestClient(config.isaac_sim)
    lakehouse_client = LakehouseClient(config.lakehouse)
    try:
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

        runner = ScenarioRunner(
            stage, viewport, lakehouse, extension, simulation,
            robot, job, asset, character,
            window, navigation, sensor, physics, lighting,
            material, replicator, omnigraph, content,
        )

        summary = await runner.run(scenario)

        if normalized_report_format in {"json", "both"}:
            print("===== JSON REPORT =====")
            print(to_json(summary, redact_local_paths=redact_local_paths))
        if normalized_report_format in {"markdown", "both"}:
            print("===== MARKDOWN REPORT =====")
            print(to_markdown(summary, redact_local_paths=redact_local_paths))

        return 0 if summary.status.value == "passed" else 1
    finally:
        try:
            await isaac_client.close()
        finally:
            await lakehouse_client.close()


def _resolve_scenario_path(user_path: str, config) -> str:
    """Resolve *user_path* against config.scenario.scenarios_dir / project root.

    Absolute paths pass through unchanged; relative paths are looked up
    first under the configured scenarios_dir, then under the project root
    (so both ``smoke/foo.yaml`` and ``scenarios/smoke/foo.yaml`` work).
    """
    p = Path(user_path)
    if p.is_absolute():
        return str(p)
    scenarios_dir = Path(config.scenario.scenarios_dir)
    if not scenarios_dir.is_absolute():
        scenarios_dir = PROJECT_ROOT / scenarios_dir
    candidate = scenarios_dir / p
    if candidate.exists():
        return str(candidate)
    root_candidate = PROJECT_ROOT / p
    if root_candidate.exists():
        return str(root_candidate)
    return str(candidate)  # let loader raise with a sensible path


def _parse_input_overrides(raw_json: str | None) -> dict[str, object] | None:
    if raw_json is None:
        return None
    parsed = json.loads(raw_json)
    if not isinstance(parsed, dict):
        raise ValueError("--input-overrides-json must decode to a JSON object")
    return parsed


def _normalize_report_format(report_format: str) -> str:
    normalized = report_format.strip().lower()
    if normalized == "md":
        return "markdown"
    if normalized in {"json", "markdown", "both"}:
        return normalized
    raise ValueError("--report-format must be 'json', 'markdown', 'md', or 'both'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_path")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compile only and print the scenario_plan-compatible payload.",
    )
    parser.add_argument(
        "--input-overrides-json",
        help="JSON object merged into spec.variables before compile/run.",
    )
    parser.add_argument(
        "--report-format",
        default="both",
        help="Normal-run report output: json, markdown, md, or both.",
    )
    parser.add_argument(
        "--redact-local-paths",
        action="store_true",
        help="Redact local paths and process/thread identifiers in normal reports.",
    )
    args = parser.parse_args(argv)
    try:
        input_overrides = _parse_input_overrides(args.input_overrides_json)
        report_format = _normalize_report_format(args.report_format)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid standalone scenario option: {exc}", file=sys.stderr)
        return 2
    return asyncio.run(
        run(
            args.scenario_path,
            dry_run=args.dry_run,
            input_overrides=input_overrides,
            report_format=report_format,
            redact_local_paths=args.redact_local_paths,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
