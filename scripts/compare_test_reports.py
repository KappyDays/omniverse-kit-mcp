"""Compare pre/post JSON test reports — surface regressions only.

Context
-------
The CLAUDE.md Pull-First restructure (plan §5-§9) captures a ``pre/`` run
of every static + live test before the rewrite, and a ``post/`` run
afterwards. A test that FAILS in ``post`` but PASSED in ``pre`` is a
regression. Tests that were already FAIL in ``pre`` are treated as
known-FAIL and do NOT regress a ``post`` FAIL of the same test.

Exit code is 0 iff no regression is detected (plan §12.2 AC #14).

Consumes the JSON written by ``scripts/capture_pytest_report.py`` (or any
JSON with ``summary`` + ``cases`` dicts). Scenario E1 and any other JSON
with a flat ``{case_id: status}`` shape are also supported.

Usage
-----

.. code-block:: bash

    .venv/Scripts/python.exe scripts/compare_test_reports.py \\
        docs/artifacts/restructure-baseline/pre \\
        docs/artifacts/restructure-baseline/post

    # Specific report files:
    .venv/Scripts/python.exe scripts/compare_test_reports.py \\
        docs/artifacts/restructure-baseline/pre/unit_tests.json \\
        docs/artifacts/restructure-baseline/post/unit_tests.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_FAILURE_STATUSES = {"FAILED", "ERROR", "FAIL"}
_PASS_STATUSES = {"PASSED", "PASS", "XFAIL", "XPASS", "SKIPPED", "SKIP"}


def _load_cases(path: Path) -> dict[str, str]:
    """Load ``cases`` dict from a capture_pytest_report JSON.

    Accepts either ``{"cases": {...}}`` or a bare ``{case_id: status}`` map.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cases" in data and isinstance(data["cases"], dict):
        return {k: str(v).upper() for k, v in data["cases"].items()}
    if isinstance(data, dict):
        # Flat map — accept any string values.
        return {k: str(v).upper() for k, v in data.items() if isinstance(v, (str, int))}
    raise ValueError(f"Unsupported report shape: {path}")


def _collect_reports(target: Path) -> dict[str, Path]:
    """Return {report_name → path} for every ``*.json`` in a directory."""
    if target.is_file():
        return {target.stem: target}
    if not target.is_dir():
        raise FileNotFoundError(target)
    return {p.stem: p for p in sorted(target.glob("*.json"))}


def _classify(status: str) -> str:
    up = status.upper()
    if up in _FAILURE_STATUSES:
        return "FAIL"
    if up in _PASS_STATUSES:
        return "PASS"
    return up  # unknown statuses pass through for visibility


def _diff_reports(pre: dict[str, str], post: dict[str, str]) -> dict:
    regressions: list[tuple[str, str, str]] = []
    fixed: list[tuple[str, str, str]] = []
    new_failures: list[tuple[str, str]] = []
    disappeared: list[str] = []

    all_cases = set(pre) | set(post)
    for case in sorted(all_cases):
        pre_status = pre.get(case)
        post_status = post.get(case)

        if post_status is None:
            disappeared.append(case)
            continue
        if pre_status is None:
            if _classify(post_status) == "FAIL":
                new_failures.append((case, post_status))
            continue

        pre_c = _classify(pre_status)
        post_c = _classify(post_status)
        if pre_c == "PASS" and post_c == "FAIL":
            regressions.append((case, pre_status, post_status))
        elif pre_c == "FAIL" and post_c == "PASS":
            fixed.append((case, pre_status, post_status))

    return {
        "regressions": regressions,
        "fixed": fixed,
        "new_failures": new_failures,
        "disappeared": disappeared,
        "pre_total": len(pre),
        "post_total": len(post),
    }


def _print_diff(name: str, diff: dict) -> bool:
    """Print the diff summary; return True iff any regression was detected."""
    had_issue = False
    header = f"[{name}]"
    print(f"{header} pre={diff['pre_total']} post={diff['post_total']}")

    if diff["regressions"]:
        had_issue = True
        print(f"{header} ❌ REGRESSION ({len(diff['regressions'])}):")
        for case, pre_s, post_s in diff["regressions"]:
            print(f"  - {case}: {pre_s} → {post_s}")
    if diff["new_failures"]:
        had_issue = True
        print(f"{header} ❌ NEW FAILURE ({len(diff['new_failures'])}):")
        for case, post_s in diff["new_failures"]:
            print(f"  - {case}: (not in pre) → {post_s}")
    if diff["disappeared"]:
        print(f"{header} ℹ️  disappeared ({len(diff['disappeared'])}):")
        for case in diff["disappeared"][:10]:
            print(f"  - {case}")
    if diff["fixed"]:
        print(f"{header} ✅ fixed ({len(diff['fixed'])}):")
        for case, pre_s, post_s in diff["fixed"][:10]:
            print(f"  - {case}: {pre_s} → {post_s}")
    if not (diff["regressions"] or diff["new_failures"]):
        print(f"{header} OK — no regression")
    return had_issue


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diff pre/post test reports — exit 1 on regression.",
    )
    parser.add_argument("pre", type=Path, help="Pre report file or directory")
    parser.add_argument("post", type=Path, help="Post report file or directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pre_reports = _collect_reports(args.pre)
    post_reports = _collect_reports(args.post)

    shared = sorted(set(pre_reports) & set(post_reports))
    pre_only = sorted(set(pre_reports) - set(post_reports))
    post_only = sorted(set(post_reports) - set(pre_reports))

    if pre_only:
        print(f"(pre-only reports — ignored: {pre_only})")
    if post_only:
        print(f"(post-only reports — ignored: {post_only})")
    if not shared:
        print(f"No shared reports between {args.pre} and {args.post}")
        return 1

    any_regression = False
    for name in shared:
        pre_cases = _load_cases(pre_reports[name])
        post_cases = _load_cases(post_reports[name])
        diff = _diff_reports(pre_cases, post_cases)
        if _print_diff(name, diff):
            any_regression = True

    return 1 if any_regression else 0


if __name__ == "__main__":
    sys.exit(main())
