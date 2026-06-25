"""Cross-reference substance tests (category F).

Complements ``test_doc_integrity`` (syntactic link validity) by checking
that things the documentation *claims* exist — files, MCP tools, scripts,
code symbols — actually exist at their declared locations.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

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
        "extension_capture_logs",
    ]

    start = guide.index("Robot + RTX live proof wrapper:")
    end = guide.index("For `official_asset_*`", start)
    wrapper = guide[start:end]
    positions = [wrapper.find(token) for token in sequence]
    missing = [token for token, pos in zip(sequence, positions) if pos < 0]
    assert not missing, "mcp-usage-guide.md missing robot+RTX wrapper tokens: " + ", ".join(
        missing
    )
    assert positions == sorted(positions), (
        "Robot + RTX live proof wrapper is out of order in mcp-usage-guide.md"
    )
    assert "extension_clear_logs" in invariant
    assert "extension_capture_logs" in invariant
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
    assert "min_points" in guide
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
    assert "--input-overrides-json '{\"lidar_min_points\":513}'" in guide
    assert "--expect-retry-key-arg read_lidar_point_cloud:min_points=513" in guide
    assert "fails if the" in guide
    assert "override does not reach `retry_steps[].key_args.min_points`" in guide
    assert "scenario_validate(dry_run=true)" in guide
    assert "--expect-retry-key-arg step:key=value" in scripts_doc
    assert "--scenario-validate-dry-run" in scripts_doc


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
    ]

    for rel in artifacts:
        assert rel in guide
        artifact = PROJECT / rel
        assert artifact.exists(), f"Missing Robot + RTX evidence artifact: {rel}"
        text = artifact.read_text(encoding="utf-8")
        assert "local absolute" in text or "No raw local capture path" in text
        assert "worker/thread ID" in text or "worker/thread IDs" in text
        assert "secret" in text or "secrets" in text


def test_f3b_official_asset_scenario_proof_wrapper_order():
    guide = (PROJECT / "docs" / "mcp-usage-guide.md").read_text(encoding="utf-8")
    scripts_claude = (PROJECT / "scripts" / "CLAUDE.md").read_text(encoding="utf-8")
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
    assert "--expect-scratch-stage-required false" in read_only_probe
    assert "--expect-log-capture-recommended true" in read_only_probe
    assert "--expect-scratch-stage-required true" in scripts_claude
    assert "--expect-log-capture-recommended true" in scripts_claude


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
