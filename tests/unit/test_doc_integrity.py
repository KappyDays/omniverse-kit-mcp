"""Static integrity tests for CLAUDE.md / docs markdown (카테고리 A).

Detects drift introduced by documentation restructuring: broken relative
links, oversized roots/subs, missing navigation sections, pull-doc files
growing past their per-category hard caps, pull-doc "N 개" counts drifting
from the actual file count (A8), and invariants/runbooks files missing from
the root/docs index (A9).

Hard caps are injected via env so the same test file is usable from both
the pre baseline (permissive) and the post run (strict).

    CLAUDE_ROOT_HARDCAP        (default 150 — root auto-loads every turn; raised from 100 convention 2026-05-26, env-overridable)
    CLAUDE_SUB_HARDCAP         (default 260 — baseline; post=150)
    CLAUDE_INVARIANT_HARDCAP   (default 200 — docs/invariants/*.md)
    CLAUDE_RUNBOOK_HARDCAP     (default 300 — docs/runbooks/*.md)

These caps are documented in the restructure plan §2.3.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
ROOT_CLAUDE = PROJECT / "CLAUDE.md"

ROOT_HARDCAP = int(os.environ.get("CLAUDE_ROOT_HARDCAP", "150"))
SUB_HARDCAP = int(os.environ.get("CLAUDE_SUB_HARDCAP", "260"))
INVARIANT_HARDCAP = int(os.environ.get("CLAUDE_INVARIANT_HARDCAP", "200"))
RUNBOOK_HARDCAP = int(os.environ.get("CLAUDE_RUNBOOK_HARDCAP", "300"))

# Match [text](relative.md) — skip http(s), mailto, in-page anchors.
_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((?!https?://|mailto:|#)([^)\s]+?\.md)(#[^)]*)?\)"
)
# Headers that qualify as "navigation" under §2.3 (관련 경계 or 문서 맵).
_NAV_SECTION_RE = re.compile(r"^##.*(관련 경계|문서 맵)", re.MULTILINE)

# Memory index location on this workstation. Purely read-only inspection.
_MEMORY_INDEX = (
    Path.home()
    / ".claude"
    / "projects"
    / "C--Users-kang-workspace-omniverse-kit-mcp"
    / "memory"
    / "MEMORY.md"
)


# `docs/superpowers/` holds design artifacts — plans and specs that
# legitimately reference files not yet created (forward references are
# the whole point of a plan) or files in other scopes. Excluded from A1.
_A1_EXCLUDED_ROOTS = (PROJECT / "docs" / "superpowers",)


def _all_claude_mds() -> list[Path]:
    return sorted(PROJECT.glob("**/CLAUDE.md"))


def _sub_claude_mds() -> list[Path]:
    return [p for p in _all_claude_mds() if p != ROOT_CLAUDE]


def _docs_mds() -> list[Path]:
    base = PROJECT / "docs"
    return sorted(base.rglob("*.md")) if base.exists() else []


def _is_design_artifact(path: Path) -> bool:
    return any(
        path.is_relative_to(root) for root in _A1_EXCLUDED_ROOTS if root.exists()
    )


def _line_count(path: Path) -> int:
    # Mirrors `wc -l` on POSIX: number of newline-terminated lines.
    # We count raw newlines so a file without a trailing newline reports
    # the line count you'd see in an editor.
    text = path.read_text(encoding="utf-8")
    return text.count("\n") + (0 if text.endswith("\n") or not text else 1)


def _stated_count(text: str, anchor: str) -> int | None:
    """Return the integer before '개' on the first *anchor* line that has one.

    Anchored count lookup (NOT a global '\\d+ 개' scan) so prose counts like
    root CLAUDE.md's '8 개 13s 통과' (a DO-NOT-EDIT note, not an index count)
    are never matched. Returns None if no anchor line carries a count.
    """
    for line in text.splitlines():
        if anchor in line:
            m = re.search(r"(\d+)\s*개", line)
            if m:
                return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# A1: relative markdown links resolve
# ---------------------------------------------------------------------------

def test_a1_markdown_relative_links_resolve():
    missing: list[str] = []
    scanned = [
        md for md in _all_claude_mds() + _docs_mds()
        if not _is_design_artifact(md)
    ]
    for md in scanned:
        parent = md.parent
        for match in _LINK_RE.finditer(md.read_text(encoding="utf-8")):
            raw = match.group(2).strip()
            # Ignore absolute-looking paths (e.g. C:/…) — only relative in scope.
            if ":" in raw or raw.startswith("/"):
                continue
            target = (parent / raw).resolve()
            if not target.exists():
                missing.append(
                    f"{md.relative_to(PROJECT)} → [{match.group(1)}]({raw})"
                )
    assert not missing, (
        "Broken relative markdown links ("
        f"{len(missing)}):\n  " + "\n  ".join(missing[:30])
    )


# ---------------------------------------------------------------------------
# A2: MEMORY.md pointers resolve (memory dir only)
# ---------------------------------------------------------------------------

def test_a2_memory_index_pointers_resolve():
    if not _MEMORY_INDEX.exists():
        pytest.skip(f"MEMORY.md 부재: {_MEMORY_INDEX}")
    text = _MEMORY_INDEX.read_text(encoding="utf-8")
    pattern = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)\)")
    missing = [
        rel
        for rel in pattern.findall(text)
        if not (_MEMORY_INDEX.parent / rel).resolve().exists()
    ]
    assert not missing, f"Dangling memory pointers: {missing}"


# ---------------------------------------------------------------------------
# A3: root CLAUDE.md ≤ ROOT_HARDCAP
# ---------------------------------------------------------------------------

def test_a3_root_hardcap():
    lines = _line_count(ROOT_CLAUDE)
    assert lines <= ROOT_HARDCAP, (
        f"{ROOT_CLAUDE.relative_to(PROJECT)}: {lines} lines "
        f"> hardcap {ROOT_HARDCAP} (env CLAUDE_ROOT_HARDCAP)"
    )


# ---------------------------------------------------------------------------
# A4: each sub-CLAUDE.md ≤ SUB_HARDCAP
# ---------------------------------------------------------------------------

def test_a4_sub_hardcap():
    oversized = [
        f"{md.relative_to(PROJECT)}: {_line_count(md)} > {SUB_HARDCAP}"
        for md in _sub_claude_mds()
        if _line_count(md) > SUB_HARDCAP
    ]
    assert not oversized, (
        "Oversized sub-CLAUDE.md (env CLAUDE_SUB_HARDCAP):\n  "
        + "\n  ".join(oversized)
    )


# ---------------------------------------------------------------------------
# A5: every CLAUDE.md has a navigation section
# ---------------------------------------------------------------------------

def test_a5_navigation_section_present():
    missing = [
        str(md.relative_to(PROJECT))
        for md in _all_claude_mds()
        if not _NAV_SECTION_RE.search(md.read_text(encoding="utf-8"))
    ]
    assert not missing, (
        "CLAUDE.md missing '## 관련 경계' or '## 문서 맵' section: "
        f"{missing}"
    )


# ---------------------------------------------------------------------------
# A6: docs/invariants and docs/runbooks per-file hard caps
# ---------------------------------------------------------------------------

def test_a6_invariant_and_runbook_hardcaps():
    problems: list[str] = []
    for subdir, cap, env in (
        ("docs/invariants", INVARIANT_HARDCAP, "CLAUDE_INVARIANT_HARDCAP"),
        ("docs/runbooks", RUNBOOK_HARDCAP, "CLAUDE_RUNBOOK_HARDCAP"),
    ):
        root = PROJECT / subdir
        if not root.exists():
            continue
        for md in sorted(root.glob("*.md")):
            lines = _line_count(md)
            if lines > cap:
                problems.append(
                    f"{md.relative_to(PROJECT)}: {lines} > {cap} (env {env})"
                )
    assert not problems, "Oversized pull-doc:\n  " + "\n  ".join(problems)


# ---------------------------------------------------------------------------
# A7: `claude -p` (one-shot) banned in design artifacts (spec §7.1)
# ---------------------------------------------------------------------------

def test_a7_claude_p_oneshot_banned():
    """spec/plan/runbook 에 `claude -p` mention 은 'ban' 컨텍스트만 허용.

    추천 / 사용 예시로 다시 살아나면 fail (spec §7.1).
    """
    files = [
        PROJECT / "docs" / "superpowers" / "specs"
            / "2026-05-13-discord-omniverse-mcp-multi-agent-design.md",
        PROJECT / "docs" / "superpowers" / "plans"
            / "2026-05-13-discord-omniverse-mcp-multi-agent-plan.md",
        PROJECT / "docs" / "superpowers" / "extracts" / "hermes-runbook.md",
    ]
    ban_markers = ("do not use", "금지", "사용 금지", "ban ")
    bad: list[str] = []
    for path in files:
        if not path.exists():
            continue
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if "claude -p" not in line:
                continue
            lowered = line.lower()
            if not any(m in lowered for m in ban_markers):
                bad.append(
                    f"{path.relative_to(PROJECT)}:{line_no} "
                    f"{line.strip()[:120]}"
                )
    assert not bad, (
        "`claude -p` mention outside ban context (spec §7.1):\n  "
        + "\n  ".join(bad)
    )


# ---------------------------------------------------------------------------
# A8: docs/CLAUDE.md pull-doc "N 개" counts match actual file counts
# ---------------------------------------------------------------------------

def test_a8_pull_doc_counts_match():
    text = (PROJECT / "docs" / "CLAUDE.md").read_text(encoding="utf-8")
    problems: list[str] = []
    for cat in ("invariants", "runbooks"):
        stated = _stated_count(text, f"`{cat}/`")
        actual = len(list((PROJECT / "docs" / cat).glob("*.md")))
        if stated is None:
            problems.append(
                f"could not locate 'N 개' count in docs/CLAUDE.md '{cat}/' row"
            )
        elif stated != actual:
            problems.append(
                f"docs/CLAUDE.md {cat} count says {stated} but found "
                f"{actual} files in docs/{cat}/"
            )
    assert not problems, "Pull-doc count drift:\n  " + "\n  ".join(problems)


# ---------------------------------------------------------------------------
# A9: every invariants/runbooks file is indexed in root or docs CLAUDE.md
# ---------------------------------------------------------------------------

def test_a9_pull_docs_indexed():
    index_text = (
        ROOT_CLAUDE.read_text(encoding="utf-8")
        + "\n"
        + (PROJECT / "docs" / "CLAUDE.md").read_text(encoding="utf-8")
    )
    missing: list[str] = []
    for cat in ("invariants", "runbooks"):
        for md in sorted((PROJECT / "docs" / cat).glob("*.md")):
            if md.stem not in index_text:
                missing.append(
                    f"docs/{cat}/{md.name} (stem '{md.stem}') not indexed in "
                    "root CLAUDE.md or docs/CLAUDE.md"
                )
    assert not missing, "Unindexed pull-doc:\n  " + "\n  ".join(missing)
