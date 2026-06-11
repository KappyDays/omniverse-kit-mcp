"""extensions.json → extensions-catalog.md 렌더.

Usage:
    uv run python scripts/render_catalog_md.py

Supports both v1 (single-app, pre-2026-04-24) and v2 (multi-app, `apps` map)
catalog shapes for backward compatibility with existing fixtures/tests.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re as _re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_JSON_DEFAULT = PROJECT_ROOT / "docs" / "references" / "extensions.json"
OUTPUT_DEFAULT = PROJECT_ROOT / "docs" / "references" / "extensions-catalog.md"
PROGRESS_JSON = PROJECT_ROOT / "docs" / "references" / "harvest-progress.json"

CATEGORY_ORDER = [
    "Core Foundation",
    "Physics & PhysX",
    "Robot & Manipulation",
    "Sensors",
    "Animation",
    "Replicator & SDG",
    "Asset Import/Export",
    "Procedural Generation",
    "Scene Optimization",
    "Configurator",
    "No-Code UI",
    "Lighting Rigs",
    "USD Schemas (extended)",
    "Kit UI & Widget",
    "Kit Viewport & Manipulator",
    "OmniGraph",
    "ROS2",
    "XR (VR/AR)",
    "Cortex & Behavior",
    "Test & Examples",
    "Misc / Utilities",
    "Deprecated (omni.isaac.*)",
    "Error",
]


def _is_v2(entry: dict[str, Any]) -> bool:
    return "apps" in entry and isinstance(entry["apps"], dict)


def _apps_present(entry: dict[str, Any]) -> list[str]:
    if _is_v2(entry):
        return sorted(entry["apps"].keys())
    return ["isaacsim"]  # v1 implies Isaac Sim


def _primary_app_record(entry: dict[str, Any]) -> dict[str, Any]:
    """Return the per-app record to use for single-app fields in the MD.

    For v2 multi-app: Isaac Sim wins if present, else first app alphabetically.
    For v1: synthesize from top-level fields.
    """
    if _is_v2(entry):
        apps = entry["apps"]
        app_name = "isaacsim" if "isaacsim" in apps else sorted(apps.keys())[0]
        return apps[app_name]
    return {
        "source_dir": entry.get("source_dir"),
        "raw_dirname": entry.get("raw_dirname"),
        "path": entry.get("path"),
        "version": entry.get("version"),
        "dependencies": entry.get("dependencies") or [],
        "deprecated": entry.get("source_dir") == "extsDeprecated",
    }


def _mcp_hint(entry: dict[str, Any]) -> str | None:
    return entry.get("mcp_research_hint") or entry.get("mcp_extension_idea")


def _version_per_app(entry: dict[str, Any]) -> str:
    """Human-readable version string combining all apps."""
    if not _is_v2(entry):
        return entry.get("version") or "—"
    parts = []
    for app_name in sorted(entry["apps"].keys()):
        rec = entry["apps"][app_name]
        v = rec.get("version") or "—"
        parts.append(f"{app_name}: {v}")
    return " · ".join(parts)


def _app_paths(entry: dict[str, Any]) -> list[tuple[str, str]]:
    """Return ``[(app_name, path), ...]`` for every populated app."""
    if _is_v2(entry):
        return [
            (app_name, rec["path"])
            for app_name, rec in sorted(entry["apps"].items())
            if rec.get("path")
        ]
    return [("isaacsim", entry.get("path") or "")]


def _is_catalog_v2(data: dict[str, Any]) -> bool:
    return data.get("metadata", {}).get("schema_version") == 2


def _anchor(category: str) -> str:
    slug = category.lower()
    slug = slug.replace("&", "")
    slug = _re.sub(r"[^\w\s-]", "", slug)
    slug = _re.sub(r"\s+", "-", slug.strip())
    slug = _re.sub(r"-+", "-", slug)
    return slug


def _render_header_v1(
    meta: dict[str, Any], per_category: dict[str, list[dict[str, Any]]]
) -> str:
    lines = []
    lines.append("# Isaac Sim 6.0.0 Extensions — Full Catalog")
    lines.append("")
    lines.append(
        f"> **권위자료**. 대상: {meta['total_extensions']} extensions "
        f"(exts/ {meta['source_counts']['exts']} + "
        f"extscache/ {meta['source_counts']['extscache']} + "
        f"extsDeprecated/ {meta['source_counts']['extsDeprecated']})."
    )
    lines.append(
        f"> 수확 스냅샷: {meta['generated_at'][:10]} "
        f"(Isaac Sim {meta['isaac_sim_version']}, Kit {meta['kit_version']})."
    )
    lines.append("> 편집 방법: `docs/references/extensions.json` 수정 후 `uv run python scripts/render_catalog_md.py` 재실행.")
    lines.append("> **직접 편집 금지** (파생물).")
    lines.append("")
    lines.append("## 카테고리 TOC")
    lines.append("")
    lines.append("| 카테고리 | 개수 | 대표 ext |")
    lines.append("|---------|------|---------|")
    for cat in CATEGORY_ORDER:
        entries = per_category.get(cat, [])
        if not entries:
            continue
        reps = ", ".join(f"`{e['name']}`" for e in entries[:2])
        lines.append(f"| [{cat}](#{_anchor(cat)}) | {len(entries)} | {reps} |")
    lines.append("")
    return "\n".join(lines)


def _render_header_v2(
    meta: dict[str, Any], per_category: dict[str, list[dict[str, Any]]]
) -> str:
    lines = []
    lines.append("# Isaac Sim + USD Composer Extensions — Full Catalog")
    lines.append("")
    apps_meta = meta.get("apps", {})
    app_names = ", ".join(f"**{a}** (Kit {cfg['kit_version']})" for a, cfg in apps_meta.items())
    dist = meta.get("distribution", {})
    lines.append(
        f"> **권위자료**. 대상: {meta['total_extensions']} unique extensions "
        f"across {app_names}."
    )
    lines.append(
        f"> 분포: both-apps={dist.get('both_apps', 0)} · "
        f"isaacsim-only={dist.get('isaacsim_only', 0)} · "
        f"usd_composer-only={dist.get('usd_composer_only', 0)} · "
        f"api_delta={dist.get('api_delta_detected', 0)}."
    )
    lines.append(f"> 수확 스냅샷: {meta['generated_at'][:10]}.")
    lines.append(
        "> 편집 방법: `docs/references/extensions.json` 수정 후 "
        "`uv run python scripts/render_catalog_md.py` 재실행."
    )
    lines.append("> **직접 편집 금지** (파생물).")
    lines.append("")
    lines.append("## 카테고리 TOC")
    lines.append("")
    lines.append("| 카테고리 | 개수 | 대표 ext |")
    lines.append("|---------|------|---------|")
    for cat in CATEGORY_ORDER:
        entries = per_category.get(cat, [])
        if not entries:
            continue
        reps = ", ".join(f"`{e['name']}`" for e in entries[:2])
        lines.append(f"| [{cat}](#{_anchor(cat)}) | {len(entries)} | {reps} |")
    lines.append("")
    return "\n".join(lines)


def _render_apps_line(entry: dict[str, Any]) -> str:
    apps = _apps_present(entry)
    badges = " · ".join(f"`{a}`" for a in apps)
    return f"- **앱**: {badges}"


def _render_entry(entry: dict[str, Any]) -> str:
    lines = []
    version_str = _version_per_app(entry)
    lines.append(f"### {entry['name']} `v{version_str}`")
    lines.append("")

    if _is_v2(entry):
        lines.append(_render_apps_line(entry))
        for app_name, path in _app_paths(entry):
            lines.append(f"- **위치 ({app_name})**: `{path}/`")
    else:
        primary = _primary_app_record(entry)
        lines.append(f"- **위치**: `{primary['path']}/`")

    lines.append(f"- **카테고리**: {entry['category']}")
    lines.append(f"- **한 문장**: {entry.get('summary') or '—'}")

    if entry.get("api_delta_note"):
        lines.append(f"- **⚠️ API delta**: {entry['api_delta_note']}")

    if entry.get("public_modules"):
        modules = ", ".join(f"`{m}`" for m in entry["public_modules"])
        lines.append(f"- **공개 모듈**: {modules}")

    if entry.get("key_symbols"):
        lines.append("- **주요 클래스·함수**:")
        for sym in entry["key_symbols"]:
            kind = sym.get("kind", "")
            desc = sym.get("desc", "")
            sym_line = f"  - `{sym['name']}` ({kind})"
            if desc:
                sym_line += f" — {desc}"
            lines.append(sym_line)

    # Dependencies: show per-app for v2 when they differ, else primary only.
    if _is_v2(entry):
        dep_by_app = {a: rec.get("dependencies") or [] for a, rec in entry["apps"].items()}
        all_deps_same = len({tuple(v) for v in dep_by_app.values()}) == 1
        if all_deps_same:
            deps = next(iter(dep_by_app.values()))
            if deps:
                lines.append(f"- **의존성**: {', '.join(f'`{d}`' for d in deps)}")
        else:
            lines.append("- **의존성 (앱별 차이)**:")
            for app_name, deps in dep_by_app.items():
                if deps:
                    lines.append(
                        f"  - {app_name}: {', '.join(f'`{d}`' for d in deps)}"
                    )
    elif entry.get("dependencies"):
        deps = ", ".join(f"`{d}`" for d in entry["dependencies"])
        lines.append(f"- **의존성**: {deps}")

    if entry.get("testbed_refs"):
        lines.append("- **testbed 참고**:")
        for ref in entry["testbed_refs"]:
            lines.append(f"  - [{ref}]({ref})")

    hint = _mcp_hint(entry)
    if hint:
        lines.append(f"- **MCP research hint**: {hint}")

    status = entry.get("enrichment_status")
    if status == "skipped":
        reason = entry.get("skipped_reason", "unknown")
        lines.append(f"- **상태**: skipped ({reason})")
    elif status == "bootstrap":
        lines.append("> ⚠️ 미검수 (bootstrap 만 완료)")

    lines.append("")
    return "\n".join(lines)


def _render_category_section(cat: str, entries: list[dict[str, Any]]) -> str:
    lines = [f"## {cat}", ""]
    if cat == "Deprecated (omni.isaac.*)":
        lines.append("> ⚠️ **Deprecated Extensions** — Isaac Sim 6.x 에서 제거 또는 호환 전용.")
        lines.append("> `extsDeprecated/` 디렉토리에 위치. 신규 코드에서 사용 금지.")
        lines.append("")
    for e in sorted(entries, key=lambda x: x["name"]):
        lines.append(_render_entry(e))
    return "\n".join(lines)


def render(
    catalog_json: Path = CATALOG_JSON_DEFAULT,
    output: Path = OUTPUT_DEFAULT,
) -> None:
    data = json.loads(catalog_json.read_text(encoding="utf-8"))

    per_category: dict[str, list[dict[str, Any]]] = {}
    for e in data["extensions"]:
        per_category.setdefault(e["category"], []).append(e)

    if _is_catalog_v2(data):
        header = _render_header_v2(data["metadata"], per_category)
    else:
        header = _render_header_v1(data["metadata"], per_category)
    parts: list[str] = [header]

    for cat in CATEGORY_ORDER:
        entries = per_category.get(cat)
        if not entries:
            continue
        parts.append(_render_category_section(cat, entries))

    for cat, entries in per_category.items():
        if cat not in CATEGORY_ORDER and entries:
            parts.append(_render_category_section(cat, entries))

    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _update_progress() -> None:
    if not PROGRESS_JSON.exists():
        return
    progress = json.loads(PROGRESS_JSON.read_text(encoding="utf-8"))
    progress["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    progress["phases"]["render"] = {
        "status": "complete",
        "completed_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    PROGRESS_JSON.write_text(
        json.dumps(progress, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_JSON_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    render(catalog_json=args.catalog, output=args.output)
    if not args.no_progress:
        _update_progress()
    print(f"Rendered to {args.output.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
