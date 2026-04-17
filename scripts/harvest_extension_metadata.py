"""Isaac Sim 5.1 extension 전수 카탈로그 bootstrap.

Usage:
    uv run python scripts/harvest_extension_metadata.py [--resume]

상세 동작은 docs/superpowers/specs/2026-04-17-nvidia-reference-harvesting-design.md §5.3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ISAAC_SIM_ROOT = Path(
    "C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_JSON = PROJECT_ROOT / "docs" / "references" / "extensions.json"
PROGRESS_JSON = PROJECT_ROOT / "docs" / "references" / "harvest-progress.json"

SOURCE_DIRS = ("exts", "extscache", "extsDeprecated")
EXPECTED_COUNTS = {"exts": 97, "extscache": 452, "extsDeprecated": 72}

# VERSION_TAG_RE: 디렉토리명 뒤의 `-<digit>.<digit>...` 이후를 버전 태그로 간주.
# 주의: `omni.kit.loop-isaac` 처럼 `-<alpha>` 인 경우는 제거 안 함 (정규식 뒤에 \d 요구).
VERSION_TAG_RE = re.compile(r"-\d+\.\d+.*$")


def strip_version_tag(dirname: str) -> str:
    """`omni.physx.demos-107.3.26+107.3.3.cp311.u353` → `omni.physx.demos`."""
    return VERSION_TAG_RE.sub("", dirname)


# 도메인 분류 규칙 (spec §Appendix A). 위에서 아래 순서로 첫 매칭이 이김.
# 예외: extsDeprecated/ 는 assign_category() 의 source_dir_name 체크가 모든 규칙보다 먼저.
DOMAIN_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    ("Core Foundation", [
        re.compile(r"^isaacsim\.core\.(api|prims|simulation_manager|cloner|nodes|utils|includes|version|throttling|deprecation_manager|experimental\..*)$"),
        re.compile(r"^isaacsim\.simulation_app$"),
        re.compile(r"^isaacsim\.storage\.native$"),
        re.compile(r"^omni\.kit\.loop-isaac$"),
    ]),
    ("Physics & PhysX", [
        re.compile(r"^(omni\.physx(?!\.tests)|omni\.physics|omni\.usdphysics|omni\.convexdecomposition).*$"),
        re.compile(r"^omni\.kit\.property\.physx$"),
    ]),
    ("Cortex & Behavior", [
        re.compile(r"^isaacsim\.cortex\..*$"),
    ]),
    ("Robot & Manipulation", [
        re.compile(r"^isaacsim\.robot(\.|_motion|_setup).*$"),
        re.compile(r"^isaacsim\.anim\.robot$"),
    ]),
    ("Sensors", [
        re.compile(r"^(isaacsim\.sensors\.|omni\.sensors\.nv\.|omni\.sensors\.net).*$"),
    ]),
    ("Animation", [
        re.compile(r"^omni\.anim\..*$"),
        re.compile(r"^omni\.usd\.schema\.anim$"),
    ]),
    ("Replicator & SDG", [
        re.compile(r"^(omni\.replicator|isaacsim\.replicator)\..*$"),
    ]),
    ("Asset Import/Export", [
        re.compile(r"^(isaacsim\.asset|omni\.kit\.asset_converter|omni\.importer|omni\.kit\.converter|omni\.kit\.tool\.asset_).*$"),
        re.compile(r"^omni\.exporter\.urdf$"),
    ]),
    ("OmniGraph", [
        re.compile(r"^(omni\.graph|omni\.kit\.graph)\..*$"),
    ]),
    ("ROS2", [
        re.compile(r"^(isaacsim\.ros2|omni\.isaac\.ros2_).*$"),
    ]),
    ("XR (VR/AR)", [
        re.compile(r"^(omni\.kit\.xr|isaacsim\.xr)\..*$"),
    ]),
    ("Kit Viewport & Manipulator", [
        re.compile(r"^omni\.kit\.viewport(\.|_).*$"),
        re.compile(r"^omni\.kit\.manipulator\..*$"),
    ]),
    ("Test & Examples", [
        re.compile(r"^isaacsim\.(examples|benchmark|test)\..*$"),
        re.compile(r"^omni\.physx\.tests.*$"),
        re.compile(r"^omni\.kit\.test(\..*)?$"),
        re.compile(r"^omni\.kit\.test_suite\..*$"),
    ]),
    ("Kit UI & Widget", [
        re.compile(r"^omni\.kit\.(widget|window|menu|property|hotkeys|context_menu|notification_manager|prim\.icon|quicklayout|mainwindow|uiapp|ui_test)(\..*)?$"),
        re.compile(r"^omni\.ui(\..*)?$"),
        re.compile(r"^isaacsim\.(app|code_editor|gui|util)\..*$"),
    ]),
]


def assign_category(name: str, source_dir_name: str) -> str:
    """Extension 이름과 source_dir 로부터 카테고리를 결정.

    규칙 0 (최우선): source_dir == 'extsDeprecated' 이면 무조건 Deprecated.
    """
    if source_dir_name == "extsDeprecated":
        return "Deprecated (omni.isaac.*)"
    for category, patterns in DOMAIN_RULES:
        for pat in patterns:
            if pat.match(name):
                return category
    return "Misc / Utilities"


def extract_readme_excerpt(ext_dir: Path, max_len: int = 300) -> str | None:
    """<ext>/docs/README.md 의 첫 비어있지 않은 단락을 최대 max_len 자 추출."""
    readme = ext_dir / "docs" / "README.md"
    if not readme.exists():
        return None
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for paragraph in text.split("\n\n"):
        para = paragraph.strip()
        if para and not para.startswith("#"):
            return para[:max_len]
    return None


def parse_single_extension(ext_dir: Path, source_dir_name: str) -> dict[str, Any]:
    toml_path = ext_dir / "config" / "extension.toml"
    if not toml_path.exists():
        raise FileNotFoundError(f"extension.toml not found in {ext_dir}")

    with toml_path.open("rb") as f:
        data = tomllib.load(f)

    pkg = data.get("package", {})
    name = strip_version_tag(ext_dir.name)
    version = pkg.get("version")
    title = pkg.get("title")
    description = (pkg.get("description") or "").strip()
    keywords = list(pkg.get("keywords", []) or [])

    deps = list((data.get("dependencies") or {}).keys())

    py_section = data.get("python", {}) or {}
    py_modules_raw = list(py_section.get("module", [])) + list(py_section.get("modules", []))
    py_modules = [m.get("name") for m in py_modules_raw if isinstance(m, dict) and m.get("name")]

    readme_excerpt = extract_readme_excerpt(ext_dir)

    if description:
        summary = description
    elif readme_excerpt:
        summary = readme_excerpt
    elif title:
        summary = title
    else:
        summary = "(description not provided)"

    return {
        "name": name,
        "version": version,
        "source_dir": source_dir_name,
        "path": f"{source_dir_name}/{ext_dir.name}",
        "raw_dirname": ext_dir.name,
        "category": assign_category(name, source_dir_name),
        "title": title,
        "summary": summary,
        "public_modules": py_modules,
        "key_symbols": [],
        "dependencies": deps,
        "keywords": keywords,
        "raw_description": description,
        "readme_excerpt": readme_excerpt,
        "testbed_refs": [],
        "mcp_extension_idea": None,
        "enrichment_status": "bootstrap",
        "skipped_reason": None,
        "harvested_at": dt.datetime.now(dt.UTC).isoformat(),
        "enriched_at": None,
    }


def make_error_entry(ext_dir: Path, source_dir_name: str, reason: str) -> dict[str, Any]:
    name = strip_version_tag(ext_dir.name)
    return {
        "name": name,
        "version": None,
        "source_dir": source_dir_name,
        "path": f"{source_dir_name}/{ext_dir.name}",
        "raw_dirname": ext_dir.name,
        "category": "Error",
        "title": None,
        "summary": f"PARSE FAILED: {reason}",
        "public_modules": [],
        "key_symbols": [],
        "dependencies": [],
        "keywords": [],
        "raw_description": "",
        "readme_excerpt": None,
        "testbed_refs": [],
        "mcp_extension_idea": None,
        "enrichment_status": "skipped",
        "skipped_reason": f"parse_failure: {reason}",
        "harvested_at": dt.datetime.now(dt.UTC).isoformat(),
        "enriched_at": None,
    }


def _build_catalog(entries: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = {"exts": 0, "extscache": 0, "extsDeprecated": 0}
    for e in entries:
        source_counts[e["source_dir"]] = source_counts.get(e["source_dir"], 0) + 1
    return {
        "metadata": {
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "generator_version": "harvest_extension_metadata.py@1.0",
            "isaac_sim_root": ISAAC_SIM_ROOT.as_posix(),
            "isaac_sim_version": "5.1.0-rc.19",
            "kit_version": "107.3.3",
            "total_extensions": len(entries),
            "source_counts": source_counts,
            "last_enriched_at": max(
                (e.get("enriched_at") for e in entries if e.get("enriched_at")),
                default=None,
            ),
        },
        "extensions": entries,
    }


def _load_progress() -> dict[str, Any]:
    if PROGRESS_JSON.exists():
        return json.loads(PROGRESS_JSON.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "started_at": dt.datetime.now(dt.UTC).isoformat(),
        "updated_at": None,
        "total_extensions": 0,
        "phases": {
            "sync_testbed_snapshot": {"status": "pending"},
            "bootstrap": {"status": "pending", "processed": 0, "errors": []},
            "enrichment": {
                "status": "pending",
                "processed": 0,
                "remaining": 0,
                "last_processed": None,
                "per_source_counts": {
                    s: {"total": EXPECTED_COUNTS[s], "processed": 0}
                    for s in SOURCE_DIRS
                },
                "errors": [],
            },
            "render": {"status": "pending"},
            "verify": {"status": "pending"},
        },
        "notes": "",
    }


def _flush(progress: dict[str, Any], catalog: dict[str, Any]) -> None:
    progress["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    PROGRESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_JSON.write_text(
        json.dumps(progress, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    CATALOG_JSON.write_text(
        json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def bootstrap(resume: bool = False) -> None:
    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)

    progress = _load_progress()
    progress["phases"]["bootstrap"]["status"] = "running"
    progress["phases"]["bootstrap"]["errors"] = []

    existing: dict[str, dict[str, Any]] = {}
    if resume and CATALOG_JSON.exists():
        prev = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
        for e in prev.get("extensions", []):
            existing[e["name"]] = e

    entries: list[dict[str, Any]] = list(existing.values())
    known_names = set(existing.keys())

    for source_dir_name in SOURCE_DIRS:
        source_dir = ISAAC_SIM_ROOT / source_dir_name
        if not source_dir.exists():
            progress["phases"]["bootstrap"]["errors"].append({
                "ext": None, "message": f"source dir missing: {source_dir}",
                "severity": "warning",
            })
            continue
        for ext_dir in sorted(source_dir.iterdir()):
            if not ext_dir.is_dir():
                continue
            candidate_name = strip_version_tag(ext_dir.name)
            if candidate_name in known_names:
                continue
            try:
                entry = parse_single_extension(ext_dir, source_dir_name)
            except Exception as e:  # noqa: BLE001
                progress["phases"]["bootstrap"]["errors"].append({
                    "ext": ext_dir.name, "message": str(e), "severity": "error"
                })
                entry = make_error_entry(ext_dir, source_dir_name, str(e))
            entries.append(entry)
            known_names.add(entry["name"])
            progress["phases"]["bootstrap"]["processed"] = len(entries)
            if progress["phases"]["bootstrap"]["processed"] % 50 == 0:
                _flush(progress, _build_catalog(sorted(entries, key=lambda x: x["name"])))

    entries.sort(key=lambda e: e["name"])
    catalog = _build_catalog(entries)
    progress["phases"]["bootstrap"]["status"] = "complete"
    progress["phases"]["bootstrap"]["completed_at"] = dt.datetime.now(dt.UTC).isoformat()
    progress["total_extensions"] = len(entries)

    pending = sum(1 for e in entries if e["enrichment_status"] == "bootstrap")
    progress["phases"]["enrichment"]["remaining"] = pending

    _flush(progress, catalog)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true",
                        help="기존 extensions.json 의 엔트리 보존하고 누락된 것만 추가")
    args = parser.parse_args()
    bootstrap(resume=args.resume)
    print(f"Bootstrap complete. See {CATALOG_JSON.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
