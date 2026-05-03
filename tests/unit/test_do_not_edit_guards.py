"""DO-NOT-EDIT residual guards for 4h+ debugging conclusions (카테고리 G).

During the CLAUDE.md Pull-First restructure, the root CLAUDE.md §"kit.exe
cold boot hang — stdin pipe deadlock" section is allowed to shrink sharply
as long as the *intent* survives. These tests codify what "survives" means
so that the information cannot silently vanish mid-refactor.

Guards (restructure plan §3.2):
  G1  ``stdin=subprocess.DEVNULL`` literal present in root CLAUDE.md.
  G2  ``process_module.py::start`` location tag present.
  G3  Verification numbers ``240`` and ``13`` both present.
  G4  ``extra_ext_ids`` appears within ±300 chars of ``race|무효|잘못``.
  G5  ``L17`` token appears (lessons-learned traceability).
  G6  Source of truth: the fix literal lives in process_module.py itself.
  G7  When ``docs/runbooks/kit-stdin-deadlock.md`` exists, it carries the
      DO-NOT-EDIT marker (ownership travels with content).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
ROOT_CLAUDE = PROJECT / "CLAUDE.md"
PROCESS_MODULE = PROJECT / "src" / "omniverse_kit_mcp" / "modules" / "process_module.py"
RUNBOOK = PROJECT / "docs" / "runbooks" / "kit-stdin-deadlock.md"


@pytest.fixture(scope="module")
def root_text() -> str:
    return ROOT_CLAUDE.read_text(encoding="utf-8")


# ---- G1 ----
def test_g1_stdin_devnull_literal_in_root(root_text: str):
    assert "stdin=subprocess.DEVNULL" in root_text, (
        "Root CLAUDE.md no longer references the `stdin=subprocess.DEVNULL` fix — "
        "L17 residual guard missing."
    )


# ---- G2 ----
def test_g2_process_module_location_in_root(root_text: str):
    assert re.search(r"process_module\.py::start(?:\(\))?", root_text), (
        "Root CLAUDE.md missing `process_module.py::start` location tag — "
        "readers can no longer jump to the SoT."
    )


# ---- G3 ----
def test_g3_verification_numbers_in_root(root_text: str):
    assert re.search(r"\b240\b", root_text), "`240` timeout figure absent"
    assert re.search(r"\b13\b", root_text), "`13` ready-time figure absent"


# ---- G4 ----
def test_g4_extra_ext_ids_false_trail_refuted(root_text: str):
    refuted = False
    pos = 0
    while True:
        idx = root_text.find("extra_ext_ids", pos)
        if idx == -1:
            break
        window = root_text[max(0, idx - 300): idx + 300]
        if re.search(r"(race|무효|잘못|wrong|false)", window):
            refuted = True
            break
        pos = idx + 1
    assert refuted, (
        "No `extra_ext_ids` + refutation ('race'/'무효'/'잘못'/'wrong'/'false') within "
        "±300 chars — the false 2026-04-23 diagnosis may re-enter."
    )


# ---- G5 ----
def test_g5_L17_reference_in_root(root_text: str):
    assert re.search(r"\bL17\b", root_text), (
        "Root CLAUDE.md no longer cites `L17` — lessons-learned traceability lost."
    )


# ---- G6 ----
def test_g6_source_has_stdin_devnull():
    src = PROCESS_MODULE.read_text(encoding="utf-8")
    assert "stdin=subprocess.DEVNULL" in src, (
        f"{PROCESS_MODULE.relative_to(PROJECT)} lacks `stdin=subprocess.DEVNULL` — "
        "L17 has regressed in the source file itself."
    )


# ---- G7 ----
def test_g7_runbook_carries_do_not_edit_marker_when_present():
    if not RUNBOOK.exists():
        pytest.skip(
            f"{RUNBOOK.relative_to(PROJECT)} is created in Phase 2; "
            "baseline skip is expected."
        )
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "DO-NOT-EDIT" in text, (
        "Runbook exists but lost its `DO-NOT-EDIT` marker — the protection "
        "intent failed to travel with the migrated content."
    )
