"""Protected regression guards for the L17 kit cold-boot diagnosis.

The root CLAUDE.md should stay a compact router. These tests protect the
expensive incident knowledge in its canonical homes instead: the process
lifecycle invariant, the stdin-deadlock runbook, and the launch source.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
ROOT_CLAUDE = PROJECT / "CLAUDE.md"
PROCESS_MODULE = PROJECT / "src" / "omniverse_kit_mcp" / "modules" / "process_module.py"
INVARIANT = PROJECT / "docs" / "invariants" / "process-lifecycle.md"
RUNBOOK = PROJECT / "docs" / "runbooks" / "kit-stdin-deadlock.md"


@pytest.fixture(scope="module")
def incident_text() -> str:
    return INVARIANT.read_text(encoding="utf-8") + "\n" + RUNBOOK.read_text(encoding="utf-8")


def test_root_routes_to_canonical_incident_docs():
    root = ROOT_CLAUDE.read_text(encoding="utf-8")
    assert "stdin=subprocess.DEVNULL" in root
    assert "docs/invariants/process-lifecycle.md" in root
    assert "docs/runbooks/kit-stdin-deadlock.md" in root


def test_incident_docs_keep_stdin_devnull_literal(incident_text: str):
    assert "stdin=subprocess.DEVNULL" in incident_text


def test_incident_docs_keep_process_module_location(incident_text: str):
    assert re.search(r"process_module\.py::start(?:\(\))?", incident_text)


def test_incident_docs_keep_verification_numbers(incident_text: str):
    assert re.search(r"\b240\b", incident_text), "`240` timeout figure absent"
    assert re.search(r"\b13(?:\.0)?\b", incident_text), "`13` ready-time figure absent"


def test_incident_docs_refute_extra_ext_ids_false_trail(incident_text: str):
    refuted = False
    pos = 0
    while True:
        idx = incident_text.find("extra_ext_ids", pos)
        if idx == -1:
            break
        window = incident_text[max(0, idx - 300): idx + 300]
        if re.search(r"(race|무효|잘못|wrong|false|Void|incorrect|invalid)", window):
            refuted = True
            break
        pos = idx + 1
    assert refuted, (
        "No `extra_ext_ids` false-trail refutation near the incident note; "
        "the 2026-04-23 wrong diagnosis may re-enter."
    )


def test_incident_docs_keep_l17_traceability(incident_text: str):
    assert re.search(r"\bL17\b", incident_text)


def test_source_has_stdin_devnull():
    src = PROCESS_MODULE.read_text(encoding="utf-8")
    assert "stdin=subprocess.DEVNULL" in src, (
        f"{PROCESS_MODULE.relative_to(PROJECT)} lacks `stdin=subprocess.DEVNULL`"
    )


def test_runbook_carries_protected_regression_marker():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "Protected regression" in text
