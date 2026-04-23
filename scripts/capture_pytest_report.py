"""Run pytest and capture results as JSON — no plugin dependency.

Used by Phase 1 Task 1.1 Step 6 (baseline) and Phase 5 Task 5.2 (post) to
capture a diff-able record of the unit-test outcome without requiring
``pytest-json-report`` to be installed (the .venv binaries can be locked
by a running MCP session during development).

Output schema
-------------

.. code-block:: json

    {
      "generated_at_epoch": 1700000000,
      "git_sha": "abcdef…",
      "cmd": ["…", "pytest", "tests/unit/", …],
      "exit_code": 0,
      "duration_s": 4.95,
      "summary": {
        "passed": 375, "failed": 0, "skipped": 1,
        "xfailed": 0, "xpassed": 0, "error": 0, "total": 376
      },
      "cases": {
        "tests/unit/test_x.py::test_y": "PASSED", …
      }
    }

Usage
-----

.. code-block:: bash

    .venv/Scripts/python.exe scripts/capture_pytest_report.py \\
        --out docs/artifacts/restructure-baseline/pre/unit_tests.json \\
        -- tests/unit/
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

_PROJECT_DEFAULT = Path(__file__).resolve().parent.parent

_CASE_RE = re.compile(
    r"^(\S+::\S+)\s+(PASSED|FAILED|SKIPPED|XFAIL|XPASS|ERROR)(?:\s|$)"
)
_SUMMARY_TOKEN_RE = re.compile(
    r"(\d+)\s+(passed|failed|skipped|xfailed|xpassed|error|errors|warnings?)"
)


def _git_sha(project: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None


def _find_summary_line(lines: list[str]) -> str:
    """Return the pytest summary line (``=== 357 passed in 4.9s ===``)."""
    for line in reversed(lines):
        if (
            ("passed" in line or "failed" in line or "error" in line)
            and line.strip().startswith("=")
            and line.strip().endswith("=")
        ):
            return line
    # Fallback: last non-empty line.
    for line in reversed(lines):
        if line.strip():
            return line
    return ""


def _parse_summary(text: str) -> dict[str, int]:
    summary = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "error": 0,
    }
    for match in _SUMMARY_TOKEN_RE.finditer(text):
        count = int(match.group(1))
        label = match.group(2)
        if label in ("error", "errors"):
            summary["error"] = count
        elif label in ("warning", "warnings"):
            continue
        elif label in summary:
            summary[label] = count
    summary["total"] = sum(
        v
        for k, v in summary.items()
        if k in {"passed", "failed", "skipped", "xfailed", "xpassed", "error"}
    )
    return summary


def _parse_cases(lines: list[str]) -> dict[str, str]:
    cases: dict[str, str] = {}
    for line in lines:
        m = _CASE_RE.match(line.strip())
        if m:
            # Normalise path separators for diff friendliness.
            name = m.group(1).replace("\\", "/")
            cases[name] = m.group(2)
    return dict(sorted(cases.items()))


def run(project: Path, out: Path, pytest_args: list[str]) -> int:
    python = sys.executable
    cmd = [python, "-m", "pytest", *pytest_args, "-v", "--tb=no", "--no-header"]
    t0 = time.time()
    proc = subprocess.run(
        cmd,
        cwd=project,
        capture_output=True,
        text=True,
    )
    duration = time.time() - t0

    stdout_lines = proc.stdout.splitlines()
    summary_line = _find_summary_line(stdout_lines)
    summary = _parse_summary(summary_line)
    cases = _parse_cases(stdout_lines)

    report = {
        "generated_at_epoch": int(time.time()),
        "git_sha": _git_sha(project),
        "cmd": cmd,
        "exit_code": proc.returncode,
        "duration_s": round(duration, 2),
        "summary": summary,
        "summary_line": summary_line.strip(),
        "cases": cases,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {out}: total={summary['total']} "
        f"passed={summary['passed']} failed={summary['failed']} "
        f"skipped={summary['skipped']} exit={proc.returncode}"
    )
    if proc.returncode != 0 and summary["failed"] == 0 and summary["error"] == 0:
        # No failures but non-zero exit — surface pytest's stderr for humans.
        sys.stderr.write(proc.stderr)
    return proc.returncode


def _parse_args(argv: list[str] | None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run pytest and capture results as JSON (no plugin).",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=_PROJECT_DEFAULT,
        help="Project root (default: parent of this script).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output JSON path.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to pytest (use ``--`` before them).",
    )
    ns = parser.parse_args(argv)
    # argparse.REMAINDER swallows the leading ``--`` if present.
    extra = list(ns.pytest_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    if not extra:
        extra = ["tests/unit/"]
    return ns, extra


def main(argv: list[str] | None = None) -> int:
    ns, pytest_args = _parse_args(argv)
    return run(ns.project, ns.out, pytest_args)


if __name__ == "__main__":
    sys.exit(main())
