"""Cross-reference substance tests (category F).

Complements ``test_doc_integrity`` (syntactic link validity) by checking
that things the documentation *claims* exist — files, MCP tools, scripts,
code symbols — actually exist at their declared locations.
"""

from __future__ import annotations

import ast
import re
import shlex
from pathlib import Path

import pytest
import yaml

import scripts.probe_mcp_surface as mcp_probe

PROJECT = Path(__file__).resolve().parents[2]
ROOT_CLAUDE = PROJECT / "CLAUDE.md"

_CUE_RE = re.compile(
    r"(reference|details|read|before|required|see|SoT|Source of truth|Related Boundaries)",
    re.IGNORECASE,
)
_BACKTICK_FILE_RE = re.compile(
    r"`([A-Za-z0-9_./\-]+\.(?:md|py|sh|bat|yaml|yml|json|ts|toml))`"
)
_BACKTICK_SCRIPT_RE = re.compile(
    r"`(scripts/[A-Za-z0-9_./\-]+\.(?:py|sh|bat))`"
)
_BACKTICK_PYSYM_RE = re.compile(
    r"`([A-Za-z0-9_./\-]+\.py)(?:::([A-Za-z_][A-Za-z0-9_]*))?`"
)
_SNAKE_TOKEN_RE = re.compile(r"`([a-z][a-z0-9_]*_[a-z0-9_]+)`")
_MCP_PROBE_COMMAND_RE = re.compile(r"`(scripts/probe_mcp_surface\.py [^`]+)`")

# Files produced/maintained outside the repo — exclude from F1 (they will
# never resolve under PROJECT and their presence in docs is expected).
_F1_EXTERNAL_BASENAMES = frozenset({
    "isaac-sim.bat",        # NVIDIA Isaac Sim launcher (installed product)
    "user.config.json",     # Kit runtime config written by Isaac Sim itself
    "extensions.json",      # ignored local generated reference catalog
    "extensions-catalog.md",  # ignored local generated reference catalog render
})

# Source-tree roots used by F1/F6 for unique-basename fallback. We avoid
# scanning `.venv/`, `__pycache__/`, and other generated trees.
_SOURCE_ROOTS = (
    "src", "kkr-extensions", "scripts", "tests",
    "scenarios", "docs", "setup",
)

# Scenario YAMLs that intentionally use a local fixture (documented inline).
# The plan's R1 rule ("S3 only") applies to production scenarios — not to
# URDF importer tests that need a deterministic local USD.
_F4_LOCAL_FIXTURES_ALLOWED = frozenset({
    "scenarios/smoke/usd_load_robot.yaml",
})


def _referenced_path_exists(rel: str, md_parent: Path) -> bool:
    """Resolve a referenced relative path through several strategies.

    Orders strategies from most to least specific so that legitimate
    sibling/nephew references (very common in navigation hubs) pass but
    genuinely dangling ones still fail.
    """
    rel_path = Path(rel)
    if (md_parent / rel_path).exists():
        return True
    if (PROJECT / rel_path).exists():
        return True
    # Ancestor walk — catches `modules/CLAUDE.md` referred to from a sibling dir.
    for ancestor in md_parent.parents:
        try:
            ancestor.relative_to(PROJECT)
        except ValueError:
            break
        if (ancestor / rel_path).exists():
            return True
        if ancestor == PROJECT:
            break
    # Unique-basename fallback across known source roots. A match is only
    # accepted when exactly one candidate exists — ambiguous matches keep
    # the reference flagged for human review.
    name = rel_path.name
    matches: list[Path] = []
    for sub in _SOURCE_ROOTS:
        root = PROJECT / sub
        if root.exists():
            matches.extend(root.rglob(name))
            if len(matches) > 1:
                break
    return len(matches) == 1


def _all_claude_mds() -> list[Path]:
    return sorted(PROJECT.glob("**/CLAUDE.md"))


def _expected_tool_names() -> set[str]:
    """Parse ``tests/unit/test_tools_registration.py`` for EXPECTED_* frozenset literals.

    Handles both ``EXPECTED_X = frozenset(...)`` and the annotated form
    ``EXPECTED_X: frozenset[str] = frozenset(...)`` that the SoT file uses.
    """
    reg = PROJECT / "tests" / "unit" / "test_tools_registration.py"
    tree = ast.parse(reg.read_text(encoding="utf-8"))
    expected: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
            value: ast.expr | None = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        if not any(
            isinstance(t, ast.Name)
            and t.id.startswith("EXPECTED_")
            and t.id.endswith("_TOOLS")
            for t in targets
        ):
            continue
        if isinstance(value, ast.Call):
            for arg in value.args:
                if isinstance(arg, (ast.Set, ast.List, ast.Tuple)):
                    for elt in arg.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            expected.add(elt.value)
    return expected


# ---------------------------------------------------------------------------
# F1: explicit "reference/details/…" pointers land on real files
# ---------------------------------------------------------------------------

def test_f1_referenced_files_exist():
    missing: list[str] = []
    for md in _all_claude_mds():
        parent = md.parent
        for line in md.read_text(encoding="utf-8").splitlines():
            if not _CUE_RE.search(line):
                continue
            for match in _BACKTICK_FILE_RE.finditer(line):
                rel = match.group(1)
                if ":" in rel or rel.startswith("/"):
                    continue
                if Path(rel).name in _F1_EXTERNAL_BASENAMES:
                    continue
                if not _referenced_path_exists(rel, parent):
                    missing.append(f"{md.relative_to(PROJECT)}: `{rel}`")
    missing = sorted(set(missing))
    assert not missing, (
        "Documents reference missing files (search cue 'reference/details/…'):\n  "
        + "\n  ".join(missing[:40])
    )


# ---------------------------------------------------------------------------
# F2: root CLAUDE.md mentions only tools that are actually registered
# ---------------------------------------------------------------------------

# Backticked snake_case identifiers in docs that look tool-ish but aren't:
# directory names, config keys, env vars, etc. Add sparingly — most
# suspects should either be real tools or actual stale refs to fix.
_F2_NON_TOOL_TOKENS = frozenset({
    "kkr-extensions",   # directory name
})


def test_f2_root_claude_mentions_registered_tools():
    expected = _expected_tool_names()
    if not expected:
        pytest.skip("EXPECTED_*_TOOLS frozenset not parseable")
    root = ROOT_CLAUDE.read_text(encoding="utf-8")
    tokens = set(_SNAKE_TOKEN_RE.findall(root)) - _F2_NON_TOOL_TOKENS
    # Restrict to tokens whose prefix matches a registered tool's prefix.
    # This filters out unrelated snake_case like `file_path`, `env_file`, etc.
    prefixes = {name.split("_", 1)[0] for name in expected}
    suspects = {t for t in tokens if t.split("_", 1)[0] in prefixes}
    unknown = sorted(suspects - expected)
    assert not unknown, (
        "Root CLAUDE.md mentions tool-like tokens that are NOT in "
        "EXPECTED_*_TOOLS (likely stale/typo):\n  " + "\n  ".join(unknown)
    )


# ---------------------------------------------------------------------------
# F3: phase report artifact folders exist
# ---------------------------------------------------------------------------

def test_f3_phase_report_artifacts_exist():
    docs = PROJECT / "docs"
    if not docs.exists():
        pytest.skip("docs/ absent")
    reports = list(docs.glob("phase-*-validation-report.md"))
    if not reports:
        pytest.skip("phase-*-validation-report.md absent")
    missing: list[str] = []
    pat = re.compile(r"artifacts/(phase-[A-Za-z0-9_\-]+)(/[A-Za-z0-9_./\-]*)?")
    for md in reports:
        text = md.read_text(encoding="utf-8")
        for match in pat.finditer(text):
            # Strip trailing punctuation a markdown renderer would not include.
            phase = match.group(1).rstrip(".,);]`")
            rel = match.group(2) or ""
            rel = rel.rstrip(".,);]`")
            target = docs / "artifacts" / phase
            if rel:
                inner = (target / rel.lstrip("/")).resolve()
                if inner.exists() or target.exists():
                    continue
            elif target.exists():
                continue
            missing.append(f"{md.name}: artifacts/{phase}{rel}")
    missing = sorted(set(missing))
    assert not missing, "Dangling artifact refs:\n  " + "\n  ".join(missing[:20])


# ---------------------------------------------------------------------------
# F3b: robot + RTX live proof route keeps the required diagnostic wrapper
# ---------------------------------------------------------------------------

def test_f3b_robot_rtx_live_proof_wrapper_order():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    scripts_doc = (PROJECT / "scripts" / "CLAUDE.md").read_text(encoding="utf-8")
    invariant = (
        PROJECT / "docs" / "invariants" / "scenario-validation.md"
    ).read_text(encoding="utf-8")
    scenario_authoring = (PROJECT / "scenarios" / "CLAUDE.md").read_text(
        encoding="utf-8"
    )
    diagnostic_map = (PROJECT / "docs" / "tool-diagnostic-map.md").read_text(
        encoding="utf-8"
    )
    tool_catalog = (PROJECT / "docs" / "tool-catalog.md").read_text(encoding="utf-8")
    sequence = [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)",
        "scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml, dry_run=true)",
        "extension_clear_logs",
        "scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)",
        'scenario_last_report(report_format="markdown")',
        'scenario_last_report(report_format="markdown", redact_local_paths=true)',
        'extension_capture_logs(level="WARN", stop_after_capture=true)',
    ]

    start = guide.index("Robot + RTX live proof wrapper:")
    end = guide.index("For `official_asset_*`", start)
    wrapper = guide[start:end]
    lidar_tool_start = tool_catalog.index("### `sensor_lidar_get_point_cloud`")
    lidar_tool_end = tool_catalog.index("### `sensor_set_annotator`", lidar_tool_start)
    lidar_tool = tool_catalog[lidar_tool_start:lidar_tool_end]
    positions = [wrapper.find(token) for token in sequence]
    missing = [token for token, pos in zip(sequence, positions) if pos < 0]
    assert not missing, "mcp-usage-guide.md missing robot+RTX wrapper tokens: " + ", ".join(
        missing
    )
    assert positions == sorted(positions), (
        "Robot + RTX live proof wrapper is out of order in mcp-usage-guide.md"
    )
    assert "extension_clear_logs" in invariant
    assert 'extension_capture_logs(level="WARN", stop_after_capture=true)' in invariant
    assert "scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)" in invariant
    assert "scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)" in invariant
    invariant_start = invariant.index("Live proof wrapper:")
    invariant_end = invariant.index("Before stage mutation", invariant_start)
    invariant_wrapper = invariant[invariant_start:invariant_end]
    invariant_sequence = [
        token
        for token in sequence
        if token != 'scenario_last_report(report_format="markdown")'
    ]
    invariant_positions = [
        invariant_wrapper.find(token) for token in invariant_sequence
    ]
    invariant_missing = [
        token for token, pos in zip(invariant_sequence, invariant_positions) if pos < 0
    ]
    assert not invariant_missing, (
        "scenario-validation.md missing robot+RTX wrapper tokens: "
        + ", ".join(invariant_missing)
    )
    assert invariant_positions == sorted(invariant_positions), (
        "Robot + RTX live proof wrapper is out of order in scenario-validation.md"
    )
    assert (
        "--require-live-validation-tools "
        "mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,"
        "scenario_validate,extension_clear_logs,scenario_validate,"
        "scenario_last_report,extension_capture_logs"
    ) in wrapper
    assert "--scenario-validate-dry-run" in wrapper
    assert "--expect-scratch-stage-required true" in wrapper
    assert "--expect-log-capture-recommended true" in wrapper
    assert "--expect-live-cleanup-failures 0" in wrapper
    assert "--expect-live-evidence-kind rtx_lidar_point_cloud" in wrapper
    assert "--expect-live-evidence-kind viewport_framing" in wrapper
    assert "--expect-live-evidence-kind visual_capture" in wrapper
    assert (
        "--expect-live-evidence-field read_lidar_point_cloud:status=passed"
        in wrapper
    )
    assert (
        "--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1"
        in wrapper
    )
    assert (
        "--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false"
        in wrapper
    )
    assert (
        "--expect-live-evidence-field capture_visible_result:passed=true"
        in wrapper
    )
    assert (
        "--expect-live-failure-step-error "
        "read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"
    ) in wrapper
    assert "--expect-live-diagnostic-next-actions-min 1" in wrapper
    assert (
        "--expect-live-diagnostic-field "
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum"
    ) in wrapper
    assert "--expect-live-evidence-kind rtx_lidar_point_cloud" in invariant
    assert "--expect-live-evidence-kind viewport_framing" in invariant
    assert "--expect-live-evidence-kind visual_capture" in invariant
    assert (
        "--expect-live-evidence-field read_lidar_point_cloud:status=passed"
        in invariant
    )
    assert (
        "--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1"
        in invariant
    )
    assert (
        "--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false"
        in invariant
    )
    assert (
        "--expect-live-evidence-field capture_visible_result:passed=true"
        in invariant
    )
    assert (
        "--expect-live-diagnostic-field "
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum"
    ) in invariant
    assert (
        "--expect-live-evidence-field read_lidar_point_cloud:status=passed"
        in scenario_authoring
    )
    assert (
        "--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1"
        in scenario_authoring
    )
    assert "frame_robot_and_sensors:bbox_empty=false" in scenario_authoring
    assert "capture_visible_result:passed=true" in scenario_authoring
    assert (
        "--expect-live-diagnostic-field "
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum"
    ) in scenario_authoring
    assert "retry_steps[].key_args" in guide
    assert "retry_steps[].key_args" in invariant
    assert "stage_mutation_summary" in guide
    assert "stage_mutation_summary" in invariant
    assert "stage_mutation_summary.read_only=false" in invariant
    assert "stage_mutation_steps" in guide
    assert "stage_mutation_steps" in invariant
    assert "simulation_state_summary" in guide
    assert "simulation_state_summary" in invariant
    assert "simulation_state_steps" in guide
    assert "simulation_state_steps" in invariant
    assert "timeline_control_steps" in guide
    assert "timeline_control_steps" in invariant
    assert "live_validation_checklist" in guide
    assert "live_validation_checklist" in invariant
    assert "simulation_state_summary.play_state_missing_count" in guide
    assert "simulation_state_summary.play_state_missing_count" in invariant
    assert "scratch/test stage boundary" in invariant
    assert "diagnostic_steps" in guide
    assert "diagnostic_steps" in invariant
    assert "`scenario_validate(..., dry_run=true)`" in invariant
    assert "`failure_summary`" in invariant
    assert "failure_summary[].last_retry_failure" in invariant
    assert "flat dotted keys" in guide
    assert "not nested `diagnostics`" in guide
    assert "diagnostics.reason" in guide
    assert "diagnostics.reason=simulation_status_error" in guide
    assert "diagnostics.reason=simulation_control_error" in guide
    assert "diagnostics.reason=simulation_step_error" in guide
    assert "diagnostics.reason=simulation_step_observe_error" in guide
    assert "diagnostics.reason=simulation_wait_until_error" in guide
    assert "diagnostics.reason=simulation_set_time_error" in guide
    assert "SIMULATION_CONTROL_ERROR" in invariant
    assert "diagnostics.reason=simulation_step_error" in invariant
    assert "SIMULATION_STEP_OBSERVE_ERROR" in invariant
    assert "SIMULATION_WAIT_UNTIL_ERROR" in invariant
    assert "SIMULATION_SET_TIME_ERROR" in invariant
    assert "simulation_control_error" in diagnostic_map
    assert "simulation_step_error" in diagnostic_map
    assert "simulation_step_observe_error" in diagnostic_map
    assert "simulation_wait_until_error" in diagnostic_map
    assert "simulation_set_time_error" in diagnostic_map
    assert "diagnostics.reason=viewport_frame_prims_error" in guide
    assert "diagnostics.reason=viewport_capture_error" in guide
    assert "VIEWPORT_CAPTURE_ERROR" in diagnostic_map
    assert "diagnostics.reason=viewport_capture_error" in diagnostic_map
    assert "VIEWPORT_FRAME_PRIMS_ERROR" in diagnostic_map
    assert "diagnostics.reason=viewport_frame_prims_error" in diagnostic_map
    assert "diagnostics.prim_paths" in diagnostic_map
    assert "diagnostics.reason=viewport_frame_prims_error" in invariant
    assert "diagnostics.reason=viewport_capture_error" in invariant
    assert "capture_error" in guide
    assert "diagnostics.upstream_error_code" in guide
    assert "data_summary.diagnostics.upstream_error_code" in invariant
    assert "SENSOR_LIDAR_POINT_CLOUD_WARNING" in guide
    assert "SENSOR_LIDAR_POINT_CLOUD_WARNING" in invariant
    assert "SENSOR_LIDAR_POINT_CLOUD_WARNING" in diagnostic_map
    assert "SENSOR_LIDAR_POINT_CLOUD_WARNING" in lidar_tool
    assert "diagnostics.reason=lidar_warning" in guide
    assert "diagnostics.reason=lidar_warning" in invariant
    assert "diagnostics.reason=lidar_warning" in diagnostic_map
    assert "diagnostics.reason=lidar_warning" in lidar_tool
    assert "diagnostics.reason=point_count_below_minimum" in lidar_tool
    assert "diagnostics.reason=lidar_read_error" in lidar_tool
    assert "SENSOR_LIDAR_GET_POINT_CLOUD_ERROR" in invariant
    assert "diagnostics.reason=rtx_lidar_attach_error" in guide
    assert "diagnostics.reason=rtx_camera_attach_error" in guide
    assert "rtx_depth_camera_attach_error" in guide
    assert "rtx_camera_attach_error" in diagnostic_map
    assert "rtx_depth_camera_attach_error" in diagnostic_map
    assert "rtx_lidar_attach_error" in diagnostic_map
    assert "diagnostics.reason=sensor_set_annotator_error" in guide
    assert "sensor_set_annotator_error" in diagnostic_map
    assert "SENSOR_SET_ANNOTATOR_ERROR" in invariant
    assert "RTX lidar point-cloud proof failed?" in diagnostic_map
    assert "diagnostics.reason=point_count_below_minimum" in diagnostic_map
    assert "retry_failures[].data_summary" in diagnostic_map
    assert (
        "--expect-live-diagnostic-field "
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum"
    ) in diagnostic_map
    assert "diagnostics.reason=lidar_read_error" in guide
    assert "diagnostics.reason=lidar_read_error" in invariant
    assert "robot_get_pick_place_demo_status" in guide
    assert "diagnostics.reason=robot_load_error" in guide
    assert "diagnostics.reason=robot_gripper_control_error" in guide
    assert "diagnostics.reason=robot_set_ee_target_error" in guide
    assert "ROBOT_LOAD_ERROR" in diagnostic_map
    assert "CAPABILITY_NOT_SUPPORTED" in diagnostic_map
    assert "robot_gripper_control_error" in diagnostic_map
    assert "robot_set_ee_target_error" in diagnostic_map
    assert "diagnostics.reason=robot_load_error" in diagnostic_map
    assert "ROBOT_SET_EE_TARGET_ERROR" in invariant
    assert "diagnostics.timeout_s" in guide
    assert "diagnostics.fallback_tool_order" in guide
    assert "min_points" in guide
    assert "diagnostics.num_points/min_points" in lidar_tool
    assert "diagnostics.num_points" in guide
    assert "diagnostics.min_points" in guide
    assert (
        "`diagnostic_next_actions[]` flat keys `diagnostics.num_points`"
        in invariant
    )
    assert (
        "flat keys `diagnostics.num_points` / `diagnostics.min_points`"
        in invariant
    )
    assert "retry_failures[].data_summary.diagnostics.num_points" in invariant
    assert "retry_failures[].data_summary.diagnostics.min_points" in invariant
    assert "data_summary.diagnostics.num_points" in invariant
    assert "data_summary.diagnostics.min_points" in invariant
    assert "max_points" in guide
    assert "frames_to_wait" in guide
    assert "fail_on_warning" in guide
    assert (
        "scenario_last_report(report_format=\"markdown\", redact_local_paths=true)"
        in invariant
    )
    assert "scenario_last_report(markdown)" not in invariant
    assert "remove `--scenario-validate-dry-run`" in guide
    assert "it then calls only `scenario_plan`" in guide
    assert "--input-overrides-json '{\"lidar_min_points\":513}'" in guide
    assert "--expect-retry-key-arg read_lidar_point_cloud:min_points=513" in guide
    assert "fails if the" in guide
    assert "override does not reach `retry_steps[].key_args.min_points`" in guide
    assert "scenario_validate(dry_run=true)" in guide
    assert "--expect-retry-key-arg step:key=value" in scripts_doc
    assert "--expect-live-evidence-kind kind" in scripts_doc
    assert "--expect-live-evidence-field selector:key=value" in scripts_doc
    assert "--expect-live-evidence-field-min selector:key=minimum" in scripts_doc
    assert "evidence-field `selector` matches either `evidence_kind` or `step_id`" in (
        scripts_doc
    )
    assert "--expect-live-cleanup-failures 0" in scripts_doc
    assert "--expect-live-failure-step-error step=ERROR_CODE" in scripts_doc
    assert "--expect-live-diagnostic-next-actions-min 1" in scripts_doc
    assert "--expect-live-diagnostic-field step:key=value" in scripts_doc
    assert "--scenario-validate-dry-run" in scripts_doc


def test_f3c_robot_pick_place_catalog_mentions_unsupported_next_actions():
    catalog = (PROJECT / "docs" / "tool-catalog.md").read_text(encoding="utf-8")
    start = catalog.index("### `robot_install_pick_place_playback_demo`")
    end = catalog.index("### `robot_list_arm_profiles`", start)
    section = catalog[start:end]
    normalized = " ".join(section.split())

    for token in (
        "validated_pick_place",
        "status='unsupported'",
        "blocker diagnostics",
        "diagnostics.suggested_next",
        "diagnostics.fallback_tool_order",
    ):
        assert token in normalized


def test_f3b_usage_guide_probe_commands_parse(monkeypatch):
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    commands = _MCP_PROBE_COMMAND_RE.findall(guide)
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    assert commands, "mcp-usage-guide.md should document probe_mcp_surface.py commands"
    for command in commands:
        argv = shlex.split(command)
        assert argv[0] == "scripts/probe_mcp_surface.py"
        assert mcp_probe.main(argv[1:]) == 0, command

    scenario_plans = {call["scenario_plan"] for call in calls}
    assert "smoke/robot_rtx_sensor_golden_workflow.yaml" in scenario_plans
    assert "smoke/official_asset_verify_live.yaml" in scenario_plans
    assert "smoke/official_asset_catalog_diagnostics.yaml" in scenario_plans
    assert any(call["scenario_validate_dry_run"] for call in calls)

    def _contains(call: dict[str, object], key: str, expected: tuple) -> bool:
        return set(expected).issubset(set(call[key]))

    def _live_call(
        scenario_plan: str,
        *,
        marker_key: str,
        expected: tuple,
    ) -> dict[str, object]:
        matches = [
            call
            for call in calls
            if call["scenario_plan"] == scenario_plan
            and call["scenario_validate_dry_run"] is True
            and call["scenario_validate_live"] is True
            and _contains(call, marker_key, expected)
        ]
        assert matches, (
            "mcp-usage-guide.md should keep a live probe command for "
            f"{scenario_plan} with {marker_key}={expected!r}"
        )
        return matches[0]

    robot_success = _live_call(
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
        marker_key="expected_live_evidence_field_minimums",
        expected=(("read_lidar_point_cloud", "num_points", 1.0),),
    )
    assert robot_success["expect_live_cleanup_failures"] == 0
    assert _contains(
        robot_success,
        "expected_live_evidence_kinds",
        ("rtx_lidar_point_cloud", "viewport_framing", "visual_capture"),
    )
    assert _contains(
        robot_success,
        "expected_live_evidence_fields",
        (
            ("read_lidar_point_cloud", "status", "passed"),
            ("frame_robot_and_sensors", "bbox_empty", False),
            ("capture_visible_result", "passed", True),
        ),
    )

    robot_failure = _live_call(
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
        marker_key="expected_live_diagnostic_fields",
        expected=(
            (
                "read_lidar_point_cloud",
                "diagnostics.reason",
                "point_count_below_minimum",
            ),
        ),
    )
    assert robot_failure["input_overrides"] == {"lidar_min_points": 513}
    assert robot_failure["expect_live_status"] == "failed"
    assert robot_failure["expect_live_cleanup_failures"] == 0
    assert robot_failure["expect_live_diagnostic_next_actions_min"] == 1
    assert _contains(
        robot_failure,
        "expected_live_failure_step_errors",
        (
            (
                "read_lidar_point_cloud",
                "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            ),
        ),
    )

    official_verify = _live_call(
        "smoke/official_asset_verify_live.yaml",
        marker_key="expected_live_evidence_fields",
        expected=(
            ("official_asset_verify", "verification_status", "load_verified"),
            ("official_asset_verify", "kind", "asset"),
            ("official_asset_verify", "app_profile", "isaac-sim"),
        ),
    )
    assert official_verify["expect_live_cleanup_failures"] == 0
    assert _contains(
        official_verify,
        "expected_live_evidence_kinds",
        ("official_asset_verify",),
    )

    official_diagnostics = _live_call(
        "smoke/official_asset_catalog_diagnostics.yaml",
        marker_key="expected_live_diagnostic_fields",
        expected=(
            ("search_known_miss", "diagnostics.reason", "query_no_match"),
            (
                "get_pallet_wrong_profile",
                "diagnostics.reason",
                "app_profile_not_covered",
            ),
        ),
    )
    assert official_diagnostics["expect_live_status"] == "passed"
    assert official_diagnostics["expect_live_cleanup_failures"] == 0
    assert official_diagnostics["expect_live_diagnostic_next_actions_min"] == 2
    assert _contains(
        official_diagnostics,
        "expected_live_failure_step_errors",
        (("get_pallet_wrong_profile", "OFFICIAL_ASSET_NOT_FOUND"),),
    )

    for call in (robot_success, robot_failure, official_verify, official_diagnostics):
        assert str(call["workspace"]).replace("\\", "/") == (
            "workspaces/isaac/instance-1"
        )
        assert call["runtime_info"] is True
        assert call["expect_tool_profile"] == "full"
        assert call["expect_app_profile"] == "isaac-sim"
        assert call["expect_tool_count"] == 152
        assert call["require_runtime_fresh"] is True
        assert call["require_robot_probe_error_contract"] is True

    assert "ignored `tmp_mcp_surface.json`" in guide
    assert "repo-relative snapshot path" in guide
    assert "without exposing the local workspace root" in guide


def test_f3b_usage_guide_live_probe_selectors_match_compiled_plans(monkeypatch):
    from omniverse_kit_mcp.scenario.compiler import compile_scenario
    from omniverse_kit_mcp.scenario.loader import load_scenario
    from omniverse_kit_mcp.tools.scenario_tools import _scenario_plan_payload

    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    commands = _MCP_PROBE_COMMAND_RE.findall(guide)
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    for command in commands:
        argv = shlex.split(command)
        assert mcp_probe.main(argv[1:]) == 0, command

    live_calls = [call for call in calls if call["scenario_validate_live"] is True]
    assert live_calls, "usage guide should keep canonical live probe commands"

    plans: dict[str, dict[str, object]] = {}
    for call in live_calls:
        scenario_plan = str(call["scenario_plan"])
        if scenario_plan not in plans:
            raw = load_scenario(PROJECT / "scenarios" / scenario_plan)
            plans[scenario_plan] = _scenario_plan_payload(compile_scenario(raw))
        plan = plans[scenario_plan]
        evidence_steps = plan["evidence_steps"]
        assert isinstance(evidence_steps, list)
        evidence_step_ids = {
            str(step["id"]) for step in evidence_steps if isinstance(step, dict)
        }
        evidence_kinds = {
            str(step["evidence_kind"])
            for step in evidence_steps
            if isinstance(step, dict) and "evidence_kind" in step
        }
        evidence_selectors = evidence_step_ids | evidence_kinds
        phases = plan["phases"]
        assert isinstance(phases, dict)
        step_ids = {
            str(step["id"])
            for steps in phases.values()
            if isinstance(steps, list)
            for step in steps
            if isinstance(step, dict) and "id" in step
        }

        for evidence_kind in call["expected_live_evidence_kinds"]:
            assert evidence_kind in evidence_kinds, (
                f"{scenario_plan} live command expects evidence kind "
                f"{evidence_kind!r}, but compiled plan has {sorted(evidence_kinds)!r}"
            )
        for selector, _key, _value in call["expected_live_evidence_fields"]:
            assert selector in evidence_selectors, (
                f"{scenario_plan} live command expects evidence selector "
                f"{selector!r}, but compiled plan has {sorted(evidence_selectors)!r}"
            )
        for selector, _key, _minimum in call[
            "expected_live_evidence_field_minimums"
        ]:
            assert selector in evidence_selectors, (
                f"{scenario_plan} live command expects evidence selector "
                f"{selector!r}, but compiled plan has {sorted(evidence_selectors)!r}"
            )
        for step_id, _error_code in call["expected_live_failure_step_errors"]:
            assert step_id in step_ids, (
                f"{scenario_plan} live command expects failure step "
                f"{step_id!r}, but compiled plan has {sorted(step_ids)!r}"
            )
        for step_id, _key, _value in call["expected_live_diagnostic_fields"]:
            assert step_id in step_ids, (
                f"{scenario_plan} live command expects diagnostic step "
                f"{step_id!r}, but compiled plan has {sorted(step_ids)!r}"
            )


def test_f3b_usage_guide_artifact_links_exist():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    links = sorted(set(re.findall(r"docs/artifacts/[A-Za-z0-9_./\\-]+\.md", guide)))

    assert links, "mcp-usage-guide.md should link public evidence artifacts"
    missing = [link for link in links if not (PROJECT / link).exists()]
    assert not missing, (
        "mcp-usage-guide.md links missing evidence artifacts:\n  "
        + "\n  ".join(missing)
    )


def test_f3b_workspace_live_probe_commands_keep_dry_run_gate():
    offenders: list[str] = []
    command_re = re.compile(r"`([^`]*scripts[\\/]probe_mcp_surface\.py [^`]+)`")
    for md in sorted((PROJECT / "docs").rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        for command in command_re.findall(text):
            if (
                "--workspace" in command
                and "--scenario-validate-live" in command
                and "--scenario-validate-dry-run" not in command
            ):
                offenders.append(f"{md.relative_to(PROJECT)}: {command}")

    assert not offenders, (
        "workspace live probe commands must keep --scenario-validate-dry-run:\n  "
        + "\n  ".join(offenders[:20])
    )


def test_f3b_artifact_probe_commands_parse(monkeypatch):
    command_re = re.compile(r"`([^`]*scripts[\\/]probe_mcp_surface\.py [^`]+)`")
    commands_by_artifact: dict[Path, list[str]] = {}
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    for md in sorted((PROJECT / "docs" / "artifacts").glob("*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            for raw_command in command_re.findall(line):
                if "..." in raw_command:
                    continue
                marker = re.search(r"scripts[\\/]probe_mcp_surface\.py", raw_command)
                assert marker is not None
                command = "scripts/probe_mcp_surface.py" + raw_command[marker.end() :]
                commands_by_artifact.setdefault(md, []).append(command)

    assert commands_by_artifact, "Runnable artifact probe commands should be guarded"
    for md, commands in commands_by_artifact.items():
        for command in commands:
            argv = shlex.split(command)
            assert argv[0] == "scripts/probe_mcp_surface.py"
            assert "--workspace" in argv, md.relative_to(PROJECT)
            if "--scenario-validate-live" in argv:
                assert "--scenario-validate-dry-run" in argv, md.relative_to(PROJECT)
            assert mcp_probe.main(argv[1:]) == 0, (
                f"{md.relative_to(PROJECT)}: {command}"
            )

    assert calls


def test_f3b_probe_assertion_artifacts_mark_request_scoped_log_capture():
    offenders: list[str] = []
    for md in sorted((PROJECT / "docs" / "artifacts").glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if "WARN+ log capture" in text and "stop_after_capture=true" not in text:
            offenders.append(str(md.relative_to(PROJECT)))

    assert not offenders, (
        "Probe assertion artifacts with WARN+ log capture must mark "
        "stop_after_capture=true:\n  "
        + "\n  ".join(offenders)
    )


def test_f3b_stop_guard_artifacts_record_close_metadata():
    required_markers = (
        "capture_running=false",
        "capture_stop_requested=true",
        "capture_stop_completed=true",
        "capture_stop_timed_out=false",
        "capture_stop_timeout_s=1.0",
    )
    guarded: list[str] = []
    offenders: list[str] = []
    for md in sorted((PROJECT / "docs" / "artifacts").glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if "stop-guard" not in text and "Stop guard" not in text:
            continue
        rel = str(md.relative_to(PROJECT))
        guarded.append(rel)
        missing = [marker for marker in required_markers if marker not in text]
        if missing:
            offenders.append(f"{rel}: missing {', '.join(missing)}")

    assert guarded, "Expected at least one stop-guard artifact"
    assert not offenders, (
        "Stop-guard artifacts must record close metadata:\n  "
        + "\n  ".join(offenders)
    )


def test_f3b_log_capture_tool_catalog_names_close_metadata():
    tool_catalog = (PROJECT / "docs" / "tool-catalog.md").read_text(encoding="utf-8")
    tool_start = tool_catalog.index("### `extension_capture_logs`")
    tool_end = tool_catalog.index("### `extension_clear_logs`", tool_start)
    capture_tool = tool_catalog[tool_start:tool_end]

    for marker in (
        "stop_after_capture=True",
        "data.capture_stop_timed_out",
        "data.capture_running",
    ):
        assert marker in capture_tool


def test_f3b_probe_assertion_e2e_artifact_commands_parse(monkeypatch):
    artifact = (
        PROJECT / "docs" / "artifacts" / "probe-assertion-durable-docs-e2e-2026-06-25.md"
    ).read_text(encoding="utf-8")
    raw_commands = re.findall(r"`([^`]*scripts[\\/]probe_mcp_surface\.py [^`]+)`", artifact)
    commands = [
        "scripts/probe_mcp_surface.py"
        + command[re.search(r"scripts[\\/]probe_mcp_surface\.py", command).end() :]
        for command in raw_commands
    ]
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    assert len(commands) == 3
    for rel in (
        "docs/artifacts/robot-rtx-live-evidence-field-assertions-2026-06-25.md",
        "docs/artifacts/robot-rtx-live-evidence-threshold-assertions-2026-06-25.md",
        (
            "docs/artifacts/"
            "robot-rtx-controlled-failure-diagnostic-field-assertion-2026-06-25.md"
        ),
        "docs/artifacts/official-asset-live-evidence-field-assertions-2026-06-25.md",
        (
            "docs/artifacts/"
            "official-asset-readonly-diagnostic-field-assertions-2026-06-25.md"
        ),
    ):
        assert rel in artifact
        assert (PROJECT / rel).exists()

    for command in commands:
        argv = shlex.split(command)
        assert argv[0] == "scripts/probe_mcp_surface.py"
        assert mcp_probe.main(argv[1:]) == 0, command

    plans = {call["scenario_plan"]: call for call in calls}
    assert set(plans) == {
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
        "smoke/official_asset_verify_live.yaml",
        "smoke/official_asset_catalog_diagnostics.yaml",
    }
    robot = plans["smoke/robot_rtx_sensor_golden_workflow.yaml"]
    assert robot["scenario_validate_dry_run"] is True
    assert robot["scenario_validate_live"] is False
    assert "preflight_requirements" in robot["required_plan_fields"]
    assert "live_validation_checklist" in robot["required_plan_fields"]
    assert robot["expect_scratch_stage_required"] is True
    assert robot["expect_log_capture_recommended"] is True
    assert robot["expected_automatic_cleanup_timeouts"] == (
        ("__fallback_cleanup_reset", 30.0),
    )
    official_verify = plans["smoke/official_asset_verify_live.yaml"]
    assert official_verify["scenario_validate_dry_run"] is True
    assert official_verify["scenario_validate_live"] is False
    assert official_verify["expect_scratch_stage_required"] is True
    assert "evidence_steps" in official_verify["required_plan_fields"]
    official_read_only = plans["smoke/official_asset_catalog_diagnostics.yaml"]
    assert official_read_only["scenario_validate_dry_run"] is True
    assert official_read_only["scenario_validate_live"] is False
    assert official_read_only["expect_scratch_stage_required"] is False


def test_f3b_robot_rtx_public_evidence_redaction_guidance():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")

    assert "same MCP host process that ran" in guide
    assert "fresh stdio host has no in-memory latest report" in guide
    assert "Raw live reports can include host-local capture paths" in guide
    assert "process IDs" in guide
    assert "worker/thread IDs" in guide
    assert "unstable Python object repr addresses" in guide
    assert "redacts those local" in guide
    assert "identifiers while preserving SHA256/pixel stats" in guide
    assert "<validation-api-capture>/capture_<id>.png" in guide
    assert "WARN/ERROR counts" in guide
    assert "public hygiene checks" in guide


def test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    artifacts = [
        "docs/artifacts/robot-rtx-golden-default-live-pass-2026-06-25.md",
        "docs/artifacts/robot-rtx-lidar-controlled-failure-diagnostics-2026-06-25.md",
        "docs/artifacts/robot-rtx-plan-only-override-probe-2026-06-25.md",
        "docs/artifacts/robot-rtx-default-wrapper-refresh-2026-06-25.md",
        "docs/artifacts/robot-rtx-controlled-failure-wrapper-refresh-2026-06-25.md",
        "docs/artifacts/probe-live-evidence-cleanup-assertions-2026-06-25.md",
        "docs/artifacts/robot-rtx-live-evidence-field-assertions-2026-06-25.md",
        "docs/artifacts/robot-rtx-live-evidence-threshold-assertions-2026-06-25.md",
        "docs/artifacts/robot-rtx-controlled-failure-step-error-assertion-2026-06-25.md",
        (
            "docs/artifacts/"
            "robot-rtx-controlled-failure-diagnostic-field-assertion-2026-06-25.md"
        ),
        "docs/artifacts/probe-assertion-durable-docs-e2e-2026-06-25.md",
    ]

    for rel in artifacts:
        assert rel in guide
        artifact = PROJECT / rel
        assert artifact.exists(), f"Missing Robot + RTX evidence artifact: {rel}"
        text = artifact.read_text(encoding="utf-8")
        assert "local absolute" in text or "No raw local capture path" in text
        assert "worker/thread ID" in text or "worker/thread IDs" in text
        assert "secret" in text or "secrets" in text

    for rel in (
        "docs/artifacts/robot-rtx-default-wrapper-refresh-2026-06-25.md",
        "docs/artifacts/robot-rtx-controlled-failure-wrapper-refresh-2026-06-25.md",
    ):
        wrapper_artifact = (PROJECT / rel).read_text(encoding="utf-8")
        assert "extension_capture_logs(level=WARN, stop_after_capture=true)" in (
            wrapper_artifact
        )

    field_artifact = (
        PROJECT
        / "docs/artifacts/robot-rtx-live-evidence-field-assertions-2026-06-25.md"
    ).read_text(encoding="utf-8")
    assert "`--expect-live-evidence-field read_lidar_point_cloud:num_points=512`" in (
        field_artifact
    )
    assert (
        "`--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false`"
        in field_artifact
    )
    assert (
        "`--expect-live-evidence-field capture_visible_result:passed=true`"
        in field_artifact
    )

    threshold_artifact = (
        PROJECT
        / "docs/artifacts/"
        "robot-rtx-live-evidence-threshold-assertions-2026-06-25.md"
    ).read_text(encoding="utf-8")
    assert (
        "`--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1`"
        in threshold_artifact
    )
    assert "minimum threshold `>=1`" in threshold_artifact

    diagnostic_artifact = (
        PROJECT
        / "docs/artifacts/"
        "robot-rtx-controlled-failure-diagnostic-field-assertion-2026-06-25.md"
    ).read_text(encoding="utf-8")
    assert (
        "`--expect-live-diagnostic-field "
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`"
    ) in diagnostic_artifact
    assert "diagnostics.reason=point_count_below_minimum" in diagnostic_artifact


def test_f3b_robot_rtx_controlled_failure_artifact_command_parse(monkeypatch):
    artifact = (
        PROJECT
        / "docs/artifacts/"
        "robot-rtx-controlled-failure-diagnostic-field-assertion-2026-06-25.md"
    ).read_text(encoding="utf-8")
    commands = re.findall(r"`(scripts/probe_mcp_surface\.py [^`]+)`", artifact)
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    assert len(commands) == 1
    argv = shlex.split(commands[0])
    assert argv[0] == "scripts/probe_mcp_surface.py"
    assert mcp_probe.main(argv[1:]) == 0

    call = calls[0]
    assert call["scenario_plan"] == "smoke/robot_rtx_sensor_golden_workflow.yaml"
    assert call["scenario_validate_dry_run"] is True
    assert call["scenario_validate_live"] is True
    assert call["input_overrides"] == {"lidar_min_points": 513}
    assert call["expect_live_status"] == "failed"
    assert call["expect_scratch_stage_required"] is True
    assert call["expect_log_capture_recommended"] is True
    assert call["expect_live_cleanup_failures"] == 0
    assert call["expected_live_evidence_kinds"] == ("rtx_lidar_point_cloud",)
    assert call["expected_live_failure_step_errors"] == (
        (
            "read_lidar_point_cloud",
            "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
        ),
    )
    assert call["expect_live_diagnostic_next_actions_min"] == 1
    assert call["expected_live_diagnostic_fields"] == (
        (
            "read_lidar_point_cloud",
            "diagnostics.reason",
            "point_count_below_minimum",
        ),
    )
    assert call["expected_retry_key_args"] == (
        ("read_lidar_point_cloud", "min_points", 513),
    )


def test_f3b_robot_rtx_success_artifact_commands_parse(monkeypatch):
    artifact_paths = {
        "field": (
            PROJECT
            / "docs/artifacts/"
            "robot-rtx-live-evidence-field-assertions-2026-06-25.md"
        ),
        "threshold": (
            PROJECT
            / "docs/artifacts/"
            "robot-rtx-live-evidence-threshold-assertions-2026-06-25.md"
        ),
    }
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    for path in artifact_paths.values():
        text = path.read_text(encoding="utf-8")
        commands = re.findall(r"`(scripts/probe_mcp_surface\.py [^`]+)`", text)
        assert len(commands) == 1
        argv = shlex.split(commands[0])
        assert argv[0] == "scripts/probe_mcp_surface.py"
        assert mcp_probe.main(argv[1:]) == 0

    assert len(calls) == 2
    for call in calls:
        assert call["scenario_plan"] == "smoke/robot_rtx_sensor_golden_workflow.yaml"
        assert call["scenario_validate_dry_run"] is True
        assert call["scenario_validate_live"] is True
        assert call["expect_live_status"] == "passed"
        assert call["expect_live_cleanup_failures"] == 0
        assert call["expect_scratch_stage_required"] is True
        assert call["expect_log_capture_recommended"] is True
        assert call["expected_live_evidence_kinds"] == (
            "rtx_lidar_point_cloud",
            "viewport_framing",
            "visual_capture",
        )
        assert (
            ("read_lidar_point_cloud", "status", "passed")
            in call["expected_live_evidence_fields"]
        )
        assert (
            ("frame_robot_and_sensors", "bbox_empty", False)
            in call["expected_live_evidence_fields"]
        )
        assert (
            ("capture_visible_result", "passed", True)
            in call["expected_live_evidence_fields"]
        )

    field_call, threshold_call = calls
    assert ("read_lidar_point_cloud", "num_points", 512) in (
        field_call["expected_live_evidence_fields"]
    )
    assert threshold_call["expected_live_evidence_field_minimums"] == (
        ("read_lidar_point_cloud", "num_points", 1.0),
    )


def test_f3b_official_asset_scenario_proof_wrapper_order():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    scripts_claude = (PROJECT / "scripts" / "CLAUDE.md").read_text(encoding="utf-8")
    asset_discovery = (
        PROJECT / "docs" / "invariants" / "asset-discovery.md"
    ).read_text(encoding="utf-8")
    official_catalog = (
        PROJECT / "docs" / "references" / "official-asset-catalog.md"
    ).read_text(encoding="utf-8")
    diagnostic_map = (PROJECT / "docs" / "tool-diagnostic-map.md").read_text(
        encoding="utf-8"
    )
    invariant = (
        PROJECT / "docs" / "invariants" / "scenario-validation.md"
    ).read_text(encoding="utf-8")
    scenario_authoring = (PROJECT / "scenarios" / "CLAUDE.md").read_text(
        encoding="utf-8"
    )
    sequence = [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan(smoke/official_asset_verify_live.yaml)",
        "scenario_validate(smoke/official_asset_verify_live.yaml, dry_run=true)",
        "extension_clear_logs",
        "scenario_validate(smoke/official_asset_verify_live.yaml)",
        'scenario_last_report(report_format="markdown", redact_local_paths=true)',
        'extension_capture_logs(level="WARN", stop_after_capture=true)',
    ]

    start = guide.index("Official asset scenario proof wrapper:")
    end = guide.index("Official asset on-demand live verify wrapper:", start)
    wrapper = guide[start:end]
    positions = [wrapper.find(token) for token in sequence]
    missing = [token for token, pos in zip(sequence, positions) if pos < 0]
    assert not missing, "mcp-usage-guide.md missing official asset proof tokens: " + ", ".join(
        missing
    )
    assert positions == sorted(positions), (
        "Official asset scenario proof wrapper is out of order in mcp-usage-guide.md"
    )
    assert "scenario_plan.evidence_steps" in wrapper
    assert "scenario_plan.diagnostic_steps" in wrapper
    assert "scenario_plan.stage_mutation_summary.read_only=false" in wrapper
    assert "scenario_plan.stage_mutation_steps" in wrapper
    assert "official_asset_verify_stage_probe" in wrapper
    assert "scenario_plan(smoke/official_asset_catalog_diagnostics.yaml)" in wrapper
    assert "`stage_mutation_summary.read_only` should be `true`" in wrapper
    assert "`stage_mutation_steps`" in wrapper
    assert "should be empty" in wrapper
    assert "sync/search/resolve/get" in wrapper
    assert "evidence_kind=official_asset_verify" in wrapper
    assert "evidence_summary[]" in wrapper
    assert "verification_status" in wrapper
    assert "diagnostics.asset_checks" in wrapper
    assert "diagnostics.material_checks" in wrapper
    assert "diagnostics.error_type" in wrapper
    assert "redacted JSON" in wrapper
    assert "redacted Markdown" in wrapper
    read_only_sequence = [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan(smoke/official_asset_catalog_diagnostics.yaml)",
        "extension_clear_logs",
        "scenario_validate(smoke/official_asset_catalog_diagnostics.yaml)",
        'scenario_last_report(report_format="markdown", redact_local_paths=true)',
        'extension_capture_logs(level="WARN", stop_after_capture=true)',
    ]
    read_only_start = wrapper.index("Read-only catalog diagnostics wrapper:")
    read_only_wrapper = wrapper[read_only_start:]
    read_only_positions = [
        read_only_wrapper.find(token) for token in read_only_sequence
    ]
    read_only_missing = [
        token
        for token, pos in zip(read_only_sequence, read_only_positions)
        if pos < 0
    ]
    assert not read_only_missing, (
        "mcp-usage-guide.md missing read-only official asset wrapper tokens: "
        + ", ".join(read_only_missing)
    )
    assert read_only_positions == sorted(read_only_positions), (
        "Read-only official asset wrapper is out of order in mcp-usage-guide.md"
    )
    on_demand_sequence = [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "extension_clear_logs",
        "official_asset_sync_status(app_profile=...)",
        'official_asset_search(app_profile=..., min_status="load_verified")',
        "official_asset_resolve(app_profile=..., prefer_loadable=true)",
        "official_asset_get(app_profile=...)",
        "official_asset_verify(app_profile=..., timeout_s=180)",
        "simulation_get_status",
        'extension_capture_logs(level="WARN", stop_after_capture=true)',
        'extension_capture_logs(level="ERROR", stop_after_capture=true)',
    ]
    on_demand_start = guide.index("Official asset on-demand live verify wrapper:")
    on_demand_end = guide.index("## Timeline Control", on_demand_start)
    on_demand_wrapper = guide[on_demand_start:on_demand_end]
    on_demand_positions = []
    search_from = 0
    for token in on_demand_sequence:
        pos = on_demand_wrapper.find(token, search_from)
        on_demand_positions.append(pos)
        if pos >= 0:
            search_from = pos + len(token)
    on_demand_missing = [
        token
        for token, pos in zip(on_demand_sequence, on_demand_positions)
        if pos < 0
    ]
    assert not on_demand_missing, (
        "mcp-usage-guide.md missing on-demand official asset wrapper tokens: "
        + ", ".join(on_demand_missing)
    )
    assert on_demand_positions == sorted(on_demand_positions), (
        "On-demand official asset wrapper is out of order in mcp-usage-guide.md"
    )
    assert "same live MCP host session" in on_demand_wrapper
    assert "data.capture_stop_timed_out=false" in on_demand_wrapper
    assert "data.capture_running=false" in on_demand_wrapper
    assert "extension_capture_logs WARN+" in on_demand_wrapper
    assert "compact summary" in on_demand_wrapper
    assert (
        "--require-live-validation-tools "
        "mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,"
        "scenario_validate,extension_clear_logs,scenario_validate,"
        "scenario_last_report,extension_capture_logs"
    ) in wrapper
    verify_live_probe = wrapper[
        wrapper.index("--scenario-plan smoke/official_asset_verify_live.yaml"):
        wrapper.index("For the read-only catalog diagnostics path, use")
    ]
    assert "--scenario-validate-dry-run" in verify_live_probe
    assert "--expect-scratch-stage-required true" in wrapper
    assert "--expect-log-capture-recommended true" in verify_live_probe
    assert "--expect-live-cleanup-failures 0" in verify_live_probe
    assert "--expect-live-evidence-kind official_asset_verify" in verify_live_probe
    assert (
        "--expect-live-evidence-field "
        "official_asset_verify:verification_status=load_verified"
    ) in verify_live_probe
    assert (
        "--expect-live-evidence-field official_asset_verify:kind=asset"
    ) in verify_live_probe
    assert (
        "--expect-live-evidence-field official_asset_verify:app_profile=isaac-sim"
    ) in verify_live_probe
    assert "Official asset scenario proof sequence" in invariant
    assert "scenario_plan(smoke/official_asset_verify_live.yaml)" in invariant
    assert "scenario_validate(smoke/official_asset_verify_live.yaml, dry_run=true)" in invariant
    assert "official_asset_verify_stage_probe" in invariant
    assert "evidence_kind=official_asset_verify" in invariant
    assert "--expect-live-evidence-kind official_asset_verify" in invariant
    assert (
        "--expect-live-evidence-field "
        "official_asset_verify:verification_status=load_verified"
    ) in invariant
    assert (
        "--expect-live-evidence-field official_asset_verify:kind=asset"
    ) in invariant
    assert (
        "--expect-live-evidence-field official_asset_verify:app_profile=isaac-sim"
    ) in invariant
    assert "official_asset_verify:verification_status=load_verified" in scenario_authoring
    assert "official_asset_verify:kind=asset" in scenario_authoring
    assert "official_asset_verify:app_profile=isaac-sim" in scenario_authoring
    assert "official read-only catalog diagnostics" in scenario_authoring
    assert "stage_mutation_summary.read_only=true" in scenario_authoring
    assert "search_known_miss:diagnostics.reason=query_no_match" in scenario_authoring
    assert (
        "get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered"
        in scenario_authoring
    )
    for source in (asset_discovery, official_catalog):
        assert "Official asset scenario proof sequence" in source
        assert "docs/mcp-usage-guide.md" in source
        assert "official_asset_verify:verification_status=load_verified" in source
        assert "official_asset_verify:kind=asset" in source
        assert "official_asset_verify:app_profile=isaac-sim" in source
        assert "data.verification_status=load_verified" in source
        assert "data.kind" in source
        assert "data.app_profile" in source
        assert "data.load_quality" in source
        assert "content_verified_with_bbox" in source
        assert "content_verified_no_bbox" in source
        assert "data.diagnostics.reason" in source
        assert "data.diagnostics.asset_checks" in source
        assert "data.diagnostics.material_checks" in source
        assert "data.diagnostics.error_type" in source
        assert "data.diagnostics.suggested_next" in source
        assert "data.diagnostics.fallback_tool_order" in source
        assert "verification-on-demand.jsonl" in source
    assert "Official asset verify failed or found nothing?" in diagnostic_map
    assert "OFFICIAL_ASSET_NOT_FOUND" in diagnostic_map
    assert "diagnostics.candidate_counts" in diagnostic_map
    assert "diagnostics.asset_checks" in diagnostic_map
    assert "diagnostics.material_checks" in diagnostic_map
    assert "evidence_summary[].evidence_kind=official_asset_verify" in diagnostic_map
    assert "smoke/official_asset_catalog_diagnostics.yaml" in wrapper
    assert (
        "--require-live-validation-tools "
        "mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,"
        "extension_clear_logs,scenario_validate,scenario_last_report,"
        "extension_capture_logs"
    ) in wrapper
    read_only_probe = wrapper[
        wrapper.index("--scenario-plan smoke/official_asset_catalog_diagnostics.yaml"):
        wrapper.index("After validation, request redacted JSON")
    ]
    assert "--scenario-validate-dry-run" in read_only_probe
    assert "keep `--scenario-validate-dry-run`" in read_only_probe
    assert "--expect-scratch-stage-required false" in read_only_probe
    assert "--expect-log-capture-recommended true" in read_only_probe
    assert "--expect-live-cleanup-failures 0" in read_only_probe
    assert (
        "--expect-live-failure-step-error "
        "get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND"
    ) in read_only_probe
    assert "--expect-live-diagnostic-next-actions-min 2" in read_only_probe
    assert (
        "--expect-live-diagnostic-field "
        "search_known_miss:diagnostics.reason=query_no_match"
    ) in read_only_probe
    assert (
        "--expect-live-diagnostic-field "
        "get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered"
    ) in read_only_probe
    assert "--expect-scratch-stage-required true" in scripts_claude
    assert "--expect-log-capture-recommended true" in scripts_claude
    assert "only after the dry-run plan gate" in scripts_claude
    assert "Mutating proof must assert `--expect-scratch-stage-required true`" in (
        scripts_claude
    )
    assert (
        "read-only diagnostic proof must assert "
        "`--expect-scratch-stage-required false`"
    ) in scripts_claude
    assert "get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND" in invariant
    assert "search_known_miss:diagnostics.reason=query_no_match" in invariant
    assert (
        "get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered"
        in invariant
    )
    assert "EXTENSION_LOGS_ERROR" in diagnostic_map
    assert "data.diagnostics.reason=extension_logs_error" in diagnostic_map
    assert "data.diagnostics.error_type" in diagnostic_map
    assert "data.diagnostics.fallback_tool_order" in diagnostic_map
    assert "data.capture_stop_timed_out" in diagnostic_map
    assert "data.capture_running" in diagnostic_map
    assert "data.capture_stop_timed_out=false" in (
        PROJECT / "docs" / "invariants" / "usd-load.md"
    ).read_text(encoding="utf-8")
    assert "search_known_miss:diagnostics.reason=query_no_match" in diagnostic_map
    assert (
        "get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered"
        in diagnostic_map
    )


def test_f3b_official_asset_on_demand_direct_result_shape_guidance():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    official_catalog = (
        PROJECT / "docs" / "references" / "official-asset-catalog.md"
    ).read_text(encoding="utf-8")
    tool_catalog = (PROJECT / "docs" / "tool-catalog.md").read_text(encoding="utf-8")

    start = guide.index("Official asset on-demand live verify wrapper:")
    end = guide.index("## Timeline Control", start)
    on_demand_wrapper = guide[start:end]
    tool_start = tool_catalog.index("### `official_asset_verify`")
    tool_end = tool_catalog.index("## Content - browser", tool_start)
    official_asset_verify_tool = tool_catalog[tool_start:tool_end]

    for source in (on_demand_wrapper, official_catalog):
        assert "Direct `official_asset_verify`" in source
        assert "`data.verification_status=load_verified`" in source
        assert "`data.kind=asset`" in source
        assert "`data.app_profile=isaac-sim`" in source
        assert "`data.load_quality`" in source
        assert "`content_verified_with_bbox`" in source
        assert "`content_verified_no_bbox`" in source
        assert "`data.diagnostics.reason`" in source
        assert "`data.diagnostics.asset_checks`" in source
        assert "`data.diagnostics.material_checks`" in source
        assert "`data.diagnostics.error_type`" in source
        assert "`data.diagnostics.suggested_next`" in source
        assert "`data.diagnostics.fallback_tool_order`" in source
        assert "`verification-on-demand.jsonl`" in source

    for token in (
        "diagnostics.asset_checks",
        "diagnostics.material_checks",
        "diagnostics.error_type",
        "diagnostics.target_status",
        "diagnostics.current_catalog_status",
    ):
        assert token in mcp_probe.LIVE_DIAGNOSTIC_NEXT_ACTION_FIELDS

    on_demand_normalized = " ".join(on_demand_wrapper.split())
    catalog_normalized = " ".join(official_catalog.split())
    assert "does not replace the scenario/probe wrapper" in on_demand_normalized
    assert "repeatable public proof is required" in on_demand_normalized
    assert "copy only redacted, stable response fields" in on_demand_normalized
    assert "keep generated catalog/verification files out of public commits" in (
        on_demand_normalized
    )
    assert "bounded operator check" in catalog_normalized
    assert "do not commit generated verification records" in catalog_normalized

    tool_normalized = " ".join(official_asset_verify_tool.split())
    for token in (
        "data.verification_status=load_verified",
        "data.kind",
        "data.app_profile",
        "data.load_quality",
        "content_verified_with_bbox",
        "content_verified_no_bbox",
        "data.diagnostics.reason",
        "asset_checks/material_checks",
        "error_type",
        "suggested_next",
        "fallback_tool_order",
        "verification-on-demand.jsonl",
        "copy only redacted stable fields",
    ):
        assert token in tool_normalized


def test_f3b_official_asset_lookup_tool_diagnostic_shape_guidance():
    tool_catalog = (PROJECT / "docs" / "tool-catalog.md").read_text(encoding="utf-8")

    sections: dict[str, str] = {}
    boundaries = {
        "official_asset_get": "official_asset_resolve",
        "official_asset_resolve": "official_asset_search",
        "official_asset_search": "official_asset_sync_status",
    }
    for tool_name, next_tool_name in boundaries.items():
        start = tool_catalog.index(f"### `{tool_name}`")
        end = tool_catalog.index(f"### `{next_tool_name}`", start)
        sections[tool_name] = " ".join(tool_catalog[start:end].split())

    common_tokens = (
        "data.diagnostics.reason",
        "data.diagnostics.candidate_counts",
        "data.diagnostics.available_profiles",
        "data.diagnostics.available_providers",
        "data.diagnostics.available_kinds",
        "data.diagnostics.status_counts",
        "data.diagnostics.sample_names",
        "data.diagnostics.suggested_next",
        "data.diagnostics.fallback_tool_order",
        "asset_search",
    )
    for tool_name, section in sections.items():
        for token in common_tokens:
            assert token in section, f"{tool_name} missing {token}"

    assert "Zero-result responses" in sections["official_asset_search"]
    assert "before changing filters" in sections["official_asset_search"]
    assert "verify_required_before_use" in sections["official_asset_search"]
    assert "OFFICIAL_ASSET_NOT_FOUND" in sections["official_asset_resolve"]
    assert "catalog-read errors" in sections["official_asset_resolve"]
    assert "prefer_loadable" in sections["official_asset_resolve"]
    assert "OFFICIAL_ASSET_NOT_FOUND" in sections["official_asset_get"]
    assert "catalog-read errors" in sections["official_asset_get"]
    assert "same app_profile" in sections["official_asset_get"]


def test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    artifacts = [
        "docs/artifacts/official-asset-verify-live-pass-2026-06-25.md",
        "docs/artifacts/official-asset-live-evidence-assertions-2026-06-25.md",
        (
            "docs/artifacts/"
            "official-asset-live-evidence-field-assertions-2026-06-25.md"
        ),
        (
            "docs/artifacts/"
            "official-asset-readonly-diagnostic-field-assertions-2026-06-25.md"
        ),
    ]

    for rel in artifacts:
        assert rel in guide
        artifact = PROJECT / rel
        assert artifact.exists(), f"Missing official asset evidence artifact: {rel}"
        text = artifact.read_text(encoding="utf-8")
        assert "local absolute paths" in text
        assert "worker/thread IDs" in text
        assert "secrets" in text

    baseline = (
        PROJECT / "docs/artifacts/official-asset-verify-live-pass-2026-06-25.md"
    ).read_text(encoding="utf-8")
    assert "Verification status: `load_verified`" in baseline
    assert "Load quality: `content_verified_no_bbox`" in baseline

    assertion_artifact = (
        PROJECT
        / "docs/artifacts/official-asset-live-evidence-assertions-2026-06-25.md"
    ).read_text(encoding="utf-8")
    assert "`--expect-live-evidence-kind official_asset_verify`" in assertion_artifact
    assert "Verification status: `load_verified`" in assertion_artifact

    field_assertion_artifact = (
        PROJECT
        / "docs/artifacts/"
        "official-asset-live-evidence-field-assertions-2026-06-25.md"
    ).read_text(encoding="utf-8")
    assert (
        "`--expect-live-evidence-field "
        "official_asset_verify:verification_status=load_verified`"
    ) in field_assertion_artifact
    assert "`--expect-live-evidence-field official_asset_verify:kind=asset`" in (
        field_assertion_artifact
    )
    assert (
        "`--expect-live-evidence-field official_asset_verify:app_profile=isaac-sim`"
        in field_assertion_artifact
    )
    assert "Verification status: `load_verified`" in field_assertion_artifact


def test_f3b_official_asset_readonly_diagnostic_artifact_command_parse(monkeypatch):
    artifact = (
        PROJECT
        / "docs/artifacts/"
        "official-asset-readonly-diagnostic-field-assertions-2026-06-25.md"
    ).read_text(encoding="utf-8")
    commands = re.findall(r"`(scripts/probe_mcp_surface\.py [^`]+)`", artifact)
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    assert len(commands) == 1
    argv = shlex.split(commands[0])
    assert argv[0] == "scripts/probe_mcp_surface.py"
    assert mcp_probe.main(argv[1:]) == 0

    call = calls[0]
    assert call["scenario_plan"] == "smoke/official_asset_catalog_diagnostics.yaml"
    assert call["scenario_validate_dry_run"] is True
    assert call["scenario_validate_live"] is True
    assert call["expect_live_status"] == "passed"
    assert call["expect_live_cleanup_failures"] == 0
    assert call["expect_scratch_stage_required"] is False
    assert call["expect_log_capture_recommended"] is True
    assert call["expected_live_failure_step_errors"] == (
        ("get_pallet_wrong_profile", "OFFICIAL_ASSET_NOT_FOUND"),
    )
    assert call["expect_live_diagnostic_next_actions_min"] == 2
    assert set(call["expected_live_diagnostic_fields"]) == {
        ("search_known_miss", "diagnostics.reason", "query_no_match"),
        (
            "get_pallet_wrong_profile",
            "diagnostics.reason",
            "app_profile_not_covered",
        ),
    }
    assert call["required_live_validation_tools"] == (
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan",
        "extension_clear_logs",
        "scenario_validate",
        "scenario_last_report",
        "extension_capture_logs",
    )


def test_f3b_official_asset_field_artifact_live_probe_command_parse(monkeypatch):
    artifact = (
        PROJECT
        / "docs/artifacts/"
        "official-asset-live-evidence-field-assertions-2026-06-25.md"
    ).read_text(encoding="utf-8")
    commands = re.findall(r"`(scripts/probe_mcp_surface\.py [^`]+)`", artifact)
    calls: list[dict[str, object]] = []

    async def fake_probe(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    assert len(commands) == 1
    argv = shlex.split(commands[0])
    assert argv[0] == "scripts/probe_mcp_surface.py"
    assert mcp_probe.main(argv[1:]) == 0

    call = calls[0]
    assert call["scenario_plan"] == "smoke/official_asset_verify_live.yaml"
    assert call["scenario_validate_dry_run"] is True
    assert call["scenario_validate_live"] is True
    assert call["expect_live_status"] == "passed"
    assert call["expect_live_cleanup_failures"] == 0
    assert call["expect_scratch_stage_required"] is True
    assert call["expect_log_capture_recommended"] is True
    assert call["expected_live_evidence_kinds"] == ("official_asset_verify",)
    assert set(call["expected_live_evidence_fields"]) == {
        ("official_asset_verify", "verification_status", "load_verified"),
        ("official_asset_verify", "kind", "asset"),
        ("official_asset_verify", "app_profile", "isaac-sim"),
    }
    assert call["required_live_validation_tools"] == (
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan",
        "scenario_validate",
        "extension_clear_logs",
        "scenario_validate",
        "scenario_last_report",
        "extension_capture_logs",
    )


def test_f3b_usage_guide_explains_visual_capture_plan_alignment():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")

    assert "report-compatible evidence kinds" in guide
    assert "evidence_kind=visual_capture" in guide
    assert "viewport/window `capture`" in guide
    assert "`capture_assert` plan rows" in guide
    assert "`module`/`action` to distinguish" in guide


def test_f3b_scenario_authoring_guide_mentions_report_and_plan_evidence():
    guide = (PROJECT / "scenarios" / "CLAUDE.md").read_text(encoding="utf-8")

    assert "evidence_summary` for official verify, lidar" in guide
    assert "`failure_summary`" in guide
    assert "Markdown `Failure Summary`" in guide
    assert "redact_local_paths=true" in guide
    assert "scenario_plan` exposes `total_steps`" in guide
    assert "`stage_mutation_summary`" in guide
    assert "stage_mutation_summary.read_only=false" in guide
    assert "`stage_mutation_steps`" in guide
    assert "scratch/test stage" in guide
    assert "`diagnostic_steps`" in guide
    assert "`simulation_state_summary`" in guide
    assert "`simulation_state_steps`" in guide
    assert "`timeline_control_steps`" in guide
    assert "`live_validation_checklist`" in guide
    assert "simulation_state_summary.play_state_missing_count=0" in guide
    assert "`retry_steps` with key args for retried evidence steps" in guide
    assert "status/search/resolve/get diagnostics, read-only" in guide
    assert "`scenario_validate(..., dry_run=true)` returns the same plan fields" in guide
    assert "scripts/run_scenario_standalone.py --dry-run" in guide
    assert "--report-format markdown --redact-local-paths" in guide


def test_f3b_standalone_script_docs_mention_public_safe_reports():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    script_docs = (PROJECT / "scripts" / "CLAUDE.md").read_text(encoding="utf-8")

    assert "--report-format markdown --redact-local-paths" in guide
    assert "--report-format markdown --redact-local-paths" in script_docs
    assert "raw JSON+Markdown" in script_docs


def test_f3c_simulation_guidance_uses_settled_timeline_readback():
    paths = [
        PROJECT / "docs" / "mcp-usage-guide.md",
        PROJECT / "src" / "omniverse_kit_mcp" / "tools" / "CLAUDE.md",
        PROJECT / "src" / "omniverse_kit_mcp" / "modules" / "integration-facts.md",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "timeline_settled" in text, str(path)
        assert "timeline_settle_updates" in text, str(path)
        assert "is_playing=false is possible" not in text, str(path)
        assert "reflected asynchronously" not in text, str(path)


# ---------------------------------------------------------------------------
# F4: scenario YAML usd_url values are S3 (not file://)
# ---------------------------------------------------------------------------

def _walk_usd_urls(obj, offenders: list[str], scope: str) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"usd_url", "url"} and isinstance(v, str) and v:
                if v.startswith(("https://", "http://", "omniverse://")):
                    continue
                if v.startswith(("$", "{", "${")):
                    continue
                offenders.append(f"{scope}: {k}={v}")
            elif isinstance(v, (dict, list)):
                _walk_usd_urls(v, offenders, scope)
    elif isinstance(obj, list):
        for item in obj:
            _walk_usd_urls(item, offenders, scope)


def test_f4_scenario_usd_urls_are_remote():
    scenarios = PROJECT / "scenarios"
    if not scenarios.exists():
        pytest.skip("scenarios/ absent")
    offenders: list[str] = []
    for yml in sorted(scenarios.rglob("*.yaml")):
        rel = str(yml.relative_to(PROJECT)).replace("\\", "/")
        if rel in _F4_LOCAL_FIXTURES_ALLOWED:
            continue
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data is None:
            continue
        _walk_usd_urls(data, offenders, rel)
    assert not offenders, (
        "Scenario uses non-S3 usd_url (R1 violation):\n  "
        + "\n  ".join(offenders[:20])
    )


# ---------------------------------------------------------------------------
# F5: `scripts/X.ext` references actually exist
# ---------------------------------------------------------------------------

def test_f5_referenced_scripts_exist():
    missing: list[str] = []
    for md in _all_claude_mds():
        parent = md.parent
        for match in _BACKTICK_SCRIPT_RE.finditer(md.read_text(encoding="utf-8")):
            rel = match.group(1)
            # Resolve parent-relative first (e.g. a sub-CLAUDE.md referring
            # to its own scripts/), fall back to project-root interpretation.
            if (parent / rel).exists():
                continue
            if (PROJECT / rel).exists():
                continue
            missing.append(f"{md.relative_to(PROJECT)}: {rel}")
    missing = sorted(set(missing))
    assert not missing, "Dangling script refs:\n  " + "\n  ".join(missing)


# ---------------------------------------------------------------------------
# F6: pull-docs reference real Python files (and real symbols if given)
# ---------------------------------------------------------------------------

def _locate_py(rel: str) -> Path | None:
    """Try common project roots for a relative .py reference."""
    candidates = [PROJECT / rel]
    for prefix in ("src", "kkr-extensions", "scripts", "tests"):
        candidates.append(PROJECT / prefix / rel)
    # Explicit full-ext match (handles kkr-extensions/omni.mycompany.*)
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def test_f6_pull_doc_code_refs_exist():
    problems: list[str] = []
    for subdir in ("docs/invariants", "docs/runbooks"):
        base = PROJECT / subdir
        if not base.exists():
            continue
        for md in sorted(base.glob("*.md")):
            for match in _BACKTICK_PYSYM_RE.finditer(md.read_text(encoding="utf-8")):
                rel = match.group(1)
                symbol = match.group(2)
                py = _locate_py(rel)
                if py is None:
                    problems.append(f"{md.relative_to(PROJECT)}: {rel}")
                    continue
                if symbol is None:
                    continue
                try:
                    tree = ast.parse(py.read_text(encoding="utf-8"))
                except SyntaxError:
                    continue
                ok = any(
                    isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and n.name == symbol
                    for n in ast.walk(tree)
                )
                if not ok:
                    problems.append(f"{md.relative_to(PROJECT)}: {rel}::{symbol}")
    assert not problems, "Dangling code refs in pull-docs:\n  " + "\n  ".join(problems[:20])


# ---------------------------------------------------------------------------
# F7: robot arm matrix artifact covers every built-in arm profile exactly once
# ---------------------------------------------------------------------------

def _robot_arm_matrix_artifact() -> Path:
    return (
        PROJECT
        / "docs"
        / "artifacts"
        / "robot-pickplace"
        / "robot-arm-mcp-probe-matrix-2026-06-15.md"
    )


def _robot_arm_matrix_section(text: str, start_heading: str, end_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    return text[start:end]


def _parse_profile_reason_rows(section: str) -> dict[str, str]:
    row_re = re.compile(r"^\| `([^`]+)` \| ([^|]+) \|$", re.MULTILINE)
    return {profile_name: reason.strip() for profile_name, reason in row_re.findall(section)}


def _parse_robot_matrix_full_catalog_rows(
    section: str,
) -> dict[str, tuple[str, str, str, str]]:
    row_re = re.compile(
        r"^\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \| (.*?) \| ([^|]+) \|$",
        re.MULTILINE,
    )
    return {
        profile_name: (
            status,
            family,
            evidence.strip(),
            pick_place_validation.strip(),
        )
        for profile_name, status, family, evidence, pick_place_validation in row_re.findall(
            section
        )
    }


def test_f7_robot_arm_probe_matrix_covers_builtin_profile_catalog():
    from omniverse_kit_mcp.robot_arm_profiles import builtin_robot_arm_profiles

    artifact = _robot_arm_matrix_artifact()
    assert artifact.exists(), f"Missing robot arm matrix artifact: {artifact}"

    text = artifact.read_text(encoding="utf-8")
    section = _robot_arm_matrix_section(
        text,
        "## Full Catalog Coverage",
        "## Adapter Priorities",
    )
    rows = _parse_robot_matrix_full_catalog_rows(section)
    observed = {
        profile_name: (status, family)
        for profile_name, (status, family, _evidence, _pick_place) in rows.items()
    }
    duplicates = sorted(
        profile_name
        for profile_name in observed
        if section.count(f"| `{profile_name}` |") > 1
    )

    profiles = {profile.profile_name: profile for profile in builtin_robot_arm_profiles()}
    missing = sorted(set(profiles) - set(observed))
    extra = sorted(set(observed) - set(profiles))
    mismatched = sorted(
        f"{name}: artifact=({observed[name][0]}, {observed[name][1]}), "
        f"catalog=({profiles[name].support_status}, {profiles[name].family})"
        for name in set(profiles) & set(observed)
        if observed[name] != (profiles[name].support_status, profiles[name].family)
    )

    assert not duplicates, "Duplicate robot matrix rows:\n  " + "\n  ".join(duplicates)
    assert not missing, "Missing robot matrix rows:\n  " + "\n  ".join(missing)
    assert not extra, "Unknown robot matrix rows:\n  " + "\n  ".join(extra)
    assert not mismatched, "Robot matrix status/family drift:\n  " + "\n  ".join(mismatched)


def test_f8_robot_arm_probe_matrix_guard_ledgers_match_code():
    from omniverse_kit_mcp.modules.robot_module import (
        _KNOWN_DYNAMIC_TIMEOUT_PROFILE_REASONS,
        _KNOWN_PICK_PLACE_BLOCKER_PROFILE_REASONS,
    )
    from omniverse_kit_mcp.robot_arm_profiles import builtin_robot_arm_profiles

    artifact = _robot_arm_matrix_artifact()
    assert artifact.exists(), f"Missing robot arm matrix artifact: {artifact}"

    text = artifact.read_text(encoding="utf-8")
    section = _robot_arm_matrix_section(
        text,
        "## Guarded Hazard Ledgers",
        "## Full Catalog Coverage",
    )
    dynamic_section = _robot_arm_matrix_section(
        section,
        "### Known Dynamic Timeout Profiles",
        "### Known Pick/Place Blocker Profiles",
    )
    blocker_start = section.index("### Known Pick/Place Blocker Profiles")
    blocker_section = section[blocker_start:]

    dynamic_rows = _parse_profile_reason_rows(dynamic_section)
    blocker_rows = _parse_profile_reason_rows(blocker_section)
    catalog_names = {profile.profile_name for profile in builtin_robot_arm_profiles()}
    unknown_guarded = sorted((set(dynamic_rows) | set(blocker_rows)) - catalog_names)

    assert dynamic_rows == _KNOWN_DYNAMIC_TIMEOUT_PROFILE_REASONS
    assert blocker_rows == _KNOWN_PICK_PLACE_BLOCKER_PROFILE_REASONS
    assert not unknown_guarded, "Unknown guarded robot profiles:\n  " + "\n  ".join(unknown_guarded)


def test_f9_robot_arm_probe_matrix_pick_place_column_does_not_overclaim():
    from omniverse_kit_mcp.robot_arm_profiles import builtin_robot_arm_profiles

    artifact = _robot_arm_matrix_artifact()
    assert artifact.exists(), f"Missing robot arm matrix artifact: {artifact}"

    text = artifact.read_text(encoding="utf-8")
    section = _robot_arm_matrix_section(
        text,
        "## Full Catalog Coverage",
        "## Adapter Priorities",
    )
    rows = _parse_robot_matrix_full_catalog_rows(section)
    profiles = {profile.profile_name: profile for profile in builtin_robot_arm_profiles()}

    nonvalidated_claims = sorted(
        f"{name}: status={profiles[name].support_status}, pick/place={row[3]!r}"
        for name, row in rows.items()
        if profiles[name].support_status != "validated_pick_place"
        and row[3] != "not validated"
    )
    validated_missing_claim = sorted(
        name
        for name, row in rows.items()
        if profiles[name].support_status == "validated_pick_place"
        and row[3] == "not validated"
    )

    assert not nonvalidated_claims, (
        "Only catalog validated_pick_place profiles may claim pick/place validation:\n  "
        + "\n  ".join(nonvalidated_claims)
    )
    assert not validated_missing_claim, (
        "Catalog validated_pick_place profiles must not be listed as unvalidated:\n  "
        + "\n  ".join(validated_missing_claim)
    )


def test_f10_robot_arm_validated_pick_place_profiles_have_durable_proof_artifacts():
    from omniverse_kit_mcp.robot_arm_profiles import builtin_robot_arm_profiles

    validated_profiles = [
        profile
        for profile in builtin_robot_arm_profiles()
        if profile.support_status == "validated_pick_place"
    ]
    assert validated_profiles, "Expected at least one validated pick/place profile"

    for profile in validated_profiles:
        proof_artifacts = [
            PROJECT / evidence
            for evidence in profile.evidence
            if evidence.startswith("docs/artifacts/robot-pickplace/")
            and "proof" in Path(evidence).name
        ]

        assert proof_artifacts, (
            f"{profile.profile_name} is validated_pick_place but has no "
            "robot-pickplace proof artifact"
        )

        for artifact in proof_artifacts:
            assert artifact.exists(), (
                f"{profile.profile_name} proof artifact does not exist: {artifact}"
            )
            text = artifact.read_text(encoding="utf-8")
            missing_markers = [
                marker
                for marker in (
                    f"Profile: `{profile.profile_name}`",
                    "`validated_pick_place`",
                    "object_fit_ok=true",
                    "done/lifted/placed=true",
                    "uses_kinematic_carry=false",
                )
                if marker not in text
            ]
            assert not missing_markers, (
                f"{profile.profile_name} proof artifact is missing markers "
                f"{missing_markers}: {artifact}"
            )
