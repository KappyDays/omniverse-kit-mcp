"""Compare current extensions.json against a fresh in-memory harvest.

Reports added / removed / version_bumped / category_changed ext per app.
Does NOT write to disk — meant as a dry-run to be invoked after Kit / app
version bumps, to decide which entries need re-enrichment.

Usage:
    uv run python scripts/diff_catalog.py            # 전체 요약
    uv run python scripts/diff_catalog.py --verbose  # 엔트리별 상세
    uv run python scripts/diff_catalog.py --json     # 기계 판독용 출력
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from harvest_extension_metadata import APP_ROOTS, harvest_app  # noqa: E402

CATALOG_JSON = PROJECT_ROOT / "docs" / "references" / "extensions.json"


def _app_index(entries: list[dict[str, Any]], app: str) -> dict[str, dict[str, Any]]:
    """Map ext-name → per-app record, filtered to this app."""
    index: dict[str, dict[str, Any]] = {}
    for e in entries:
        rec = (e.get("apps") or {}).get(app)
        if rec:
            index[e["name"]] = {
                "version": rec.get("version") or "",
                "source_dir": rec.get("source_dir") or "",
                "category": e.get("category") or "",
            }
    return index


def _harvest_index(app: str) -> dict[str, dict[str, Any]]:
    entries, _errors = harvest_app(app)
    return _app_index(entries, app)


def _load_current_index(app: str) -> dict[str, dict[str, Any]]:
    if not CATALOG_JSON.exists():
        return {}
    data = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    return _app_index(data.get("extensions") or [], app)


def diff_app(app: str) -> dict[str, Any]:
    current = _load_current_index(app)
    fresh = _harvest_index(app)

    cur_names = set(current.keys())
    new_names = set(fresh.keys())

    added = sorted(new_names - cur_names)
    removed = sorted(cur_names - new_names)

    version_bumped: list[tuple[str, str, str]] = []
    category_changed: list[tuple[str, str, str]] = []
    for n in sorted(cur_names & new_names):
        if current[n]["version"] != fresh[n]["version"]:
            version_bumped.append((n, current[n]["version"], fresh[n]["version"]))
        if current[n]["category"] != fresh[n]["category"]:
            category_changed.append((n, current[n]["category"], fresh[n]["category"]))

    return {
        "app": app,
        "current_total": len(current),
        "fresh_total": len(fresh),
        "added": added,
        "removed": removed,
        "version_bumped": version_bumped,
        "category_changed": category_changed,
    }


def _print_human(report: dict[str, Any], verbose: bool) -> None:
    app = report["app"]
    print(f"\n=== {app} (current={report['current_total']}  fresh={report['fresh_total']}) ===")
    print(f"  added         : {len(report['added'])}")
    print(f"  removed       : {len(report['removed'])}")
    print(f"  version_bumped: {len(report['version_bumped'])}")
    print(f"  category_changed: {len(report['category_changed'])}")
    if not verbose:
        return
    if report["added"]:
        print("  [added]")
        for n in report["added"]:
            print(f"    + {n}")
    if report["removed"]:
        print("  [removed]")
        for n in report["removed"]:
            print(f"    - {n}")
    if report["version_bumped"]:
        print("  [version_bumped]")
        for n, old, new in report["version_bumped"]:
            print(f"    ~ {n}: {old!r} → {new!r}")
    if report["category_changed"]:
        print("  [category_changed]")
        for n, old, new in report["category_changed"]:
            print(f"    ~ {n}: {old!r} → {new!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Catalog vs fresh-harvest diff.")
    parser.add_argument("--verbose", action="store_true", help="Print every changed entry")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")
    parser.add_argument("--app", choices=list(APP_ROOTS) + ["all"], default="all")
    args = parser.parse_args()

    apps = list(APP_ROOTS) if args.app == "all" else [args.app]
    reports = [diff_app(app) for app in apps]

    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
    else:
        for r in reports:
            _print_human(r, args.verbose)

    any_change = any(
        r["added"] or r["removed"] or r["version_bumped"] or r["category_changed"]
        for r in reports
    )
    return 1 if any_change else 0


if __name__ == "__main__":
    sys.exit(main())
