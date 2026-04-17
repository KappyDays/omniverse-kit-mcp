"""extensions.json → extensions-catalog.md 렌더.

Usage:
    uv run python scripts/render_catalog_md.py
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


def _anchor(category: str) -> str:
    slug = category.lower()
    slug = slug.replace("&", "")  # GitHub strips & before slugifying
    slug = _re.sub(r"[^\w\s-]", "", slug)
    slug = _re.sub(r"\s+", "-", slug.strip())
    slug = _re.sub(r"-+", "-", slug)
    return slug


def _render_header(meta: dict[str, Any], per_category: dict[str, list[dict[str, Any]]]) -> str:
    lines = []
    lines.append("# Isaac Sim 5.1.0 Extensions — Full Catalog")
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


def _render_entry(entry: dict[str, Any]) -> str:
    lines = []
    version = entry.get("version") or "—"
    lines.append(f"### {entry['name']} `v{version}`")
    lines.append("")
    lines.append(f"- **위치**: `{entry['path']}/`")
    lines.append(f"- **카테고리**: {entry['category']}")
    lines.append(f"- **한 문장**: {entry['summary']}")

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

    if entry.get("dependencies"):
        deps = ", ".join(f"`{d}`" for d in entry["dependencies"])
        lines.append(f"- **의존성**: {deps}")

    if entry.get("testbed_refs"):
        lines.append("- **testbed 참고**:")
        for ref in entry["testbed_refs"]:
            lines.append(f"  - [{ref}]({ref})")

    idea = entry.get("mcp_extension_idea")
    if idea:
        lines.append(f"- **MCP 확장 아이디어**: {idea}")

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
        lines.append("> ⚠️ **Deprecated Extensions** — Isaac Sim 5.x 에서 제거 예정.")
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

    parts: list[str] = [_render_header(data["metadata"], per_category)]

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
