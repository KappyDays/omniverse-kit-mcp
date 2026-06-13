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
