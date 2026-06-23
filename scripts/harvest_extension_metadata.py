"""Isaac Sim 6.0 extension 전수 카탈로그 bootstrap.

Usage:
    uv run python scripts/harvest_extension_metadata.py [--resume]

상세 동작과 재생성 규칙은 docs/references/CLAUDE.md 참조.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

def _first_existing_root(*candidates: str | Path | None) -> Path:
    paths = [Path(c) for c in candidates if c]
    for path in paths:
        if path.exists():
            return path
    return paths[0]


ISAAC_SIM_ROOT = _first_existing_root(
    os.environ.get("ISAAC_SIM_ROOT"),
    "C:/IsaacSim",
)
USD_COMPOSER_ROOT = Path(
    os.environ.get("USD_COMPOSER_ROOT", "C:/USDComposer")
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_JSON = PROJECT_ROOT / "docs" / "references" / "extensions.json"
PROGRESS_JSON = PROJECT_ROOT / "docs" / "references" / "harvest-progress.json"

# v1 defaults (Isaac Sim only — preserved for bootstrap() backward compat).
SOURCE_DIRS = ("exts", "extscache", "extsDeprecated", "extsInternal")
EXPECTED_COUNTS = {
    "exts": 114,
    "extscache": 493,
    "extsDeprecated": 26,
    "extsInternal": 7,
}

# v2: multi-app config (primary path via run_multi_app_harvest).
# `kit/extscore` 는 Kit 핵심 binary lib (omni.client.lib · omni.kit.async_engine ·
# omni.kit.registry.nucleus) — 양쪽 앱 모두 동일 ext 가 설치돼 있어 둘 다 포함.
APP_ROOTS: dict[str, dict[str, Any]] = {
    "isaacsim": {
        "root": ISAAC_SIM_ROOT,
        "source_dirs": ("exts", "extscache", "extsDeprecated", "extsInternal", "kit/extscore"),
        "kit_version": "110.1.1",
        "app_version": "6.0.0-rc.59+release.41464.5f2772bc.gl",
    },
    "usd_composer": {
        "root": USD_COMPOSER_ROOT,
        "source_dirs": ("exts", "extscache", "extsbuild", "kit/extscore"),
        "kit_version": "110.0-110.1",
        "app_version": "kit-app-template",
    },
}

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
    ("Procedural Generation", [
        re.compile(r"^omni\.genproc(\..*)?$"),
    ]),
    ("Scene Optimization", [
        re.compile(r"^omni\.scene\.(optimizer|visualization)(\..*)?$"),
    ]),
    ("Configurator", [
        re.compile(r"^omni\.configurator.*$"),
        re.compile(r"^omni\.kit\.browser\.configurator_samples$"),
    ]),
    ("No-Code UI", [
        re.compile(r"^omni\.no_code_ui(\..*)?$"),
        re.compile(r"^omni\.kit\.data2ui(\..*)?$"),
    ]),
    ("Lighting Rigs", [
        re.compile(r"^omni\.light_rigs$"),
    ]),
    ("USD Schemas (extended)", [
        re.compile(r"^omni\.usd\.schema\.(omni_projectors|physical_lighting|playback|usd_particle_field|omni_lens_distortion|omni_sensors|scene\.visualization|sequence|semantics|metrics\.assembler|flow|geospatial|audio|omnigraph|omniscripting|render_settings\.rtx)$"),
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


def _parse_toml_raw_fallback(toml_path: Path) -> dict[str, Any]:
    """tomllib.TOMLDecodeError 발생 시 raw 텍스트로 [package] 핵심 필드만 추출.

    이중 선언 등 TOML 스펙 위반 파일에 대한 우회책. 첫 번째 등장 값만 취한다.
    """
    text = toml_path.read_text(encoding="utf-8", errors="replace")

    def _str_val(key: str, src: str) -> str:
        m = re.search(rf'^\s*{re.escape(key)}\s*=\s*["\']([^"\']*)["\']', src, re.MULTILINE)
        return m.group(1).strip() if m else ""

    pkg_m = re.search(r"^\[package\](.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
    pkg_text = pkg_m.group(1) if pkg_m else text

    kw_m = re.search(r"^\s*keywords\s*=\s*\[([^\]]*)\]", pkg_text, re.MULTILINE | re.DOTALL)
    keywords = re.findall(r'"([^"]+)"', kw_m.group(1)) if kw_m else []

    deps_m = re.search(r"^\[dependencies\](.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
    deps = re.findall(r'^\s*"([^"]+)"\s*=', deps_m.group(1), re.MULTILINE) if deps_m else []

    py_modules = re.findall(r'^\s*name\s*=\s*"([^"]+)"', text, re.MULTILINE)

    return {
        "package": {
            "version": _str_val("version", pkg_text) or None,
            "title": _str_val("title", pkg_text) or None,
            "description": _str_val("description", pkg_text),
            "keywords": keywords,
        },
        "dependencies": {d: {} for d in deps},
        "python": {"module": [{"name": m} for m in py_modules]},
    }


def parse_single_extension(ext_dir: Path, source_dir_name: str) -> dict[str, Any]:
    toml_path = ext_dir / "config" / "extension.toml"
    if not toml_path.exists():
        raise FileNotFoundError(f"extension.toml not found in {ext_dir}")

    try:
        with toml_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        data = _parse_toml_raw_fallback(toml_path)

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


# =====================================================================
# v2 Multi-App section — new primary path (see schema-design.md)
# =====================================================================

# Fields that stay top-level (app-agnostic) in v2.
AGNOSTIC_FIELDS = (
    "name",
    "category",
    "title",
    "summary",
    "keywords",
    "public_modules",
    "key_symbols",
    "raw_description",
    "readme_excerpt",
    "testbed_refs",
    "enrichment_status",
    "skipped_reason",
    "enriched_at",
)


def _v2_app_record(v1_or_parsed: dict[str, Any]) -> dict[str, Any]:
    """Build an apps.<app> record from a v1-shape parsed entry."""
    return {
        "present": True,
        "source_dir": v1_or_parsed.get("source_dir"),
        "raw_dirname": v1_or_parsed.get("raw_dirname"),
        "path": v1_or_parsed.get("path"),
        "version": v1_or_parsed.get("version"),
        "dependencies": v1_or_parsed.get("dependencies") or [],
        "deprecated": v1_or_parsed.get("source_dir") == "extsDeprecated",
        "harvested_at": v1_or_parsed.get("harvested_at"),
    }


def migrate_v1_to_v2(v1_entry: dict[str, Any]) -> dict[str, Any]:
    """Transform a legacy single-app entry into the dual-app schema.

    Preserves enrichment and agnostic fields. Renames ``mcp_extension_idea`` →
    ``mcp_research_hint``. All Isaac Sim per-app metadata moves under
    ``apps.isaacsim``.
    """
    v2 = {k: v1_entry.get(k) for k in AGNOSTIC_FIELDS}
    v2["mcp_research_hint"] = v1_entry.get("mcp_extension_idea")
    v2["api_delta_note"] = None
    v2["apps"] = {"isaacsim": _v2_app_record(v1_entry)}
    return v2


def parse_single_extension_v2(
    ext_dir: Path, source_dir_name: str, app_name: str
) -> dict[str, Any]:
    """Parse an extension dir and wrap it as a v2 entry for the given app."""
    v1 = parse_single_extension(ext_dir, source_dir_name)
    v2 = {k: v1.get(k) for k in AGNOSTIC_FIELDS}
    v2["mcp_research_hint"] = v1.get("mcp_extension_idea")
    v2["api_delta_note"] = None
    v2["apps"] = {app_name: _v2_app_record(v1)}
    return v2


def make_error_entry_v2(
    ext_dir: Path, source_dir_name: str, app_name: str, reason: str
) -> dict[str, Any]:
    v1 = make_error_entry(ext_dir, source_dir_name, reason)
    v2 = {k: v1.get(k) for k in AGNOSTIC_FIELDS}
    v2["mcp_research_hint"] = None
    v2["api_delta_note"] = None
    v2["apps"] = {app_name: _v2_app_record(v1)}
    return v2


def _version_major_minor(version_str: str | None) -> str | None:
    """Extract leading X.Y from a pdm-style version string.

    ``107.3.26+107.3.3.cp311.u353`` → ``107.3``.
    """
    if not version_str:
        return None
    m = re.match(r"^(\d+\.\d+)", version_str)
    return m.group(1) if m else version_str


def detect_api_delta(apps_map: dict[str, Any]) -> str | None:
    """Flag when major.minor versions differ across apps (patch diffs ignored).

    Returns a human-readable note, or ``None`` when versions align.
    """
    majors = {
        app: _version_major_minor(data.get("version"))
        for app, data in apps_map.items()
        if data.get("version")
    }
    distinct = {v for v in majors.values() if v}
    if len(distinct) > 1:
        return f"major.minor differs: {majors}"
    return None


def merge_entry(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge `incoming` into `base` at the ext-name level (union of apps)."""
    merged = dict(base)
    merged["apps"] = {**base.get("apps", {}), **incoming.get("apps", {})}
    # Prefer base's agnostic values (already enriched for Isaac Sim catalog);
    # fall back to incoming where base is empty.
    for f in AGNOSTIC_FIELDS:
        if not merged.get(f) and incoming.get(f):
            merged[f] = incoming[f]
    if not merged.get("mcp_research_hint") and incoming.get("mcp_research_hint"):
        merged["mcp_research_hint"] = incoming["mcp_research_hint"]
    # api_delta_note: preserve manual notes (Phase B classification or manual
    # null-clear). Refresh only if missing (new merge) or still in raw
    # auto-detect format ("major.minor differs:" prefix).
    existing = base.get("api_delta_note")
    if "api_delta_note" not in base or (
        isinstance(existing, str) and existing.startswith("major.minor differs:")
    ):
        merged["api_delta_note"] = detect_api_delta(merged["apps"])
    else:
        merged["api_delta_note"] = existing
    return merged


def harvest_app(app_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Walk an app's source dirs and parse every extension.

    Returns ``(entries, errors)``. Entries are v2-shape with only the given
    app populated in ``apps``.
    """
    cfg = APP_ROOTS[app_name]
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for source_dir_name in cfg["source_dirs"]:
        source_dir = cfg["root"] / source_dir_name
        if not source_dir.exists():
            errors.append({
                "app": app_name,
                "source_dir": source_dir_name,
                "message": f"source dir missing: {source_dir}",
                "severity": "warning",
            })
            continue
        for ext_dir in sorted(source_dir.iterdir()):
            if not ext_dir.is_dir():
                continue
            try:
                entry = parse_single_extension_v2(ext_dir, source_dir_name, app_name)
            except Exception as exc:  # noqa: BLE001
                errors.append({
                    "app": app_name,
                    "source_dir": source_dir_name,
                    "ext": ext_dir.name,
                    "message": str(exc),
                    "severity": "error",
                })
                entry = make_error_entry_v2(ext_dir, source_dir_name, app_name, str(exc))
            entries.append(entry)
    return entries, errors


def _build_catalog_v2(
    entries: list[dict[str, Any]], errors: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Compose v2 catalog with multi-app metadata block."""
    isaacsim_only = sum(1 for e in entries if set(e["apps"]) == {"isaacsim"})
    usd_only = sum(1 for e in entries if set(e["apps"]) == {"usd_composer"})
    both = sum(
        1 for e in entries if "isaacsim" in e["apps"] and "usd_composer" in e["apps"]
    )
    api_delta = sum(1 for e in entries if e.get("api_delta_note"))

    per_app_source_counts: dict[str, dict[str, int]] = {}
    for app_name in APP_ROOTS:
        counts: dict[str, int] = {}
        for e in entries:
            rec = e["apps"].get(app_name)
            if not rec:
                continue
            sd = rec.get("source_dir") or "unknown"
            counts[sd] = counts.get(sd, 0) + 1
        per_app_source_counts[app_name] = counts

    return {
        "metadata": {
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "generator_version": "harvest_extension_metadata.py@2.0",
            "schema_version": 2,
            "apps": {
                app: {
                    "root": cfg["root"].as_posix(),
                    "kit_version": cfg["kit_version"],
                    "app_version": cfg["app_version"],
                    "source_dirs": list(cfg["source_dirs"]),
                }
                for app, cfg in APP_ROOTS.items()
            },
            "total_extensions": len(entries),
            "distribution": {
                "isaacsim_only": isaacsim_only,
                "usd_composer_only": usd_only,
                "both_apps": both,
                "api_delta_detected": api_delta,
            },
            "source_counts_per_app": per_app_source_counts,
            "last_enriched_at": max(
                (e.get("enriched_at") for e in entries if e.get("enriched_at")),
                default=None,
            ),
            "harvest_errors": errors or [],
        },
        "extensions": entries,
    }


def run_multi_app_harvest(preserve_enrichment: bool = True) -> None:
    """Produce the v2 ``extensions.json`` combining all configured apps.

    If ``preserve_enrichment`` and an existing v1 catalog is present, that
    catalog is migrated in place (keeping ``enrichment_status=enriched``
    entries with their manual summaries/hints). Isaac Sim extensions are NOT
    re-harvested — migration is trusted as equivalent. USD Composer (and
    future apps) are harvested fresh.
    """
    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)

    by_name: dict[str, dict[str, Any]] = {}
    migrated = 0
    harvested_per_app: dict[str, int] = {}
    all_errors: list[dict[str, Any]] = []

    # Step 1 — migrate existing catalog if requested.
    if preserve_enrichment and CATALOG_JSON.exists():
        try:
            existing = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {"extensions": []}
        for raw in existing.get("extensions", []):
            if "apps" in raw:  # already v2 — keep as is
                by_name[raw["name"]] = raw
            else:
                by_name[raw["name"]] = migrate_v1_to_v2(raw)
                migrated += 1

    # Step 2 — fresh harvest for each app (USD Composer only, unless the
    # existing catalog lacks the Isaac Sim half of the data).
    for app_name in APP_ROOTS:
        if app_name == "isaacsim" and migrated > 0:
            # Isaac Sim already present via migration — skip re-harvest.
            continue
        app_entries, app_errors = harvest_app(app_name)
        harvested_per_app[app_name] = len(app_entries)
        all_errors.extend(app_errors)
        for entry in app_entries:
            name = entry["name"]
            if name in by_name:
                by_name[name] = merge_entry(by_name[name], entry)
            else:
                by_name[name] = entry

    # Step 3 — refresh api_delta only for entries with raw auto-detect note
    # or no note. Preserve manual classifications (Phase B) and manual nulls.
    for e in by_name.values():
        existing = e.get("api_delta_note")
        if "api_delta_note" not in e or (
            isinstance(existing, str) and existing.startswith("major.minor differs:")
        ):
            e["api_delta_note"] = detect_api_delta(e["apps"])

    entries = sorted(by_name.values(), key=lambda x: x["name"])
    catalog = _build_catalog_v2(entries, all_errors)
    CATALOG_JSON.write_text(
        json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"[multi-app harvest] migrated={migrated}  "
        f"harvested_per_app={harvested_per_app}  "
        f"total={len(entries)}  "
        f"errors={len(all_errors)}"
    )
    print(
        f"  distribution: isaacsim_only={catalog['metadata']['distribution']['isaacsim_only']}  "
        f"usd_composer_only={catalog['metadata']['distribution']['usd_composer_only']}  "
        f"both={catalog['metadata']['distribution']['both_apps']}  "
        f"api_delta={catalog['metadata']['distribution']['api_delta_detected']}"
    )


def _build_catalog(entries: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = {source_dir: 0 for source_dir in SOURCE_DIRS}
    for e in entries:
        source_counts[e["source_dir"]] = source_counts.get(e["source_dir"], 0) + 1
    return {
        "metadata": {
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "generator_version": "harvest_extension_metadata.py@1.0",
            "isaac_sim_root": ISAAC_SIM_ROOT.as_posix(),
            "isaac_sim_version": "6.0.0-rc.59+release.41464.5f2772bc.gl",
            "kit_version": "110.1.1",
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
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--mode",
        choices=["multi-app", "v1-bootstrap"],
        default="multi-app",
        help="multi-app (default): migrate existing v1 catalog + harvest USD Composer fresh. "
             "v1-bootstrap (legacy): Isaac Sim single-app harvest.",
    )
    parser.add_argument("--resume", action="store_true",
                        help="v1-bootstrap 에서만 유효. 기존 extensions.json 엔트리 보존.")
    parser.add_argument(
        "--no-preserve-enrichment",
        action="store_true",
        help="multi-app 에서 기존 v1 엔트리 migration 을 건너뛰고 전수 재수확 (파괴적).",
    )
    args = parser.parse_args()
    if args.mode == "v1-bootstrap":
        bootstrap(resume=args.resume)
        print(f"v1 bootstrap complete. See {CATALOG_JSON.as_posix()}")
    else:
        run_multi_app_harvest(preserve_enrichment=not args.no_preserve_enrichment)
        print(f"Multi-app harvest complete. See {CATALOG_JSON.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
