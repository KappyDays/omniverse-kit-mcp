"""Catalog integrity invariants for docs/references/extensions.json.

Guards against silent drift between file-system (Isaac Sim / USD Composer
installations) and the catalog — such as the kit/extscore omission fixed in
6596c8f. Each Kit / app bump re-runs these invariants via pytest.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CATALOG_PATH = Path(__file__).resolve().parents[2] / "docs" / "references" / "extensions.json"

ALLOWED_ENRICHMENT_STATUS = frozenset({"enriched", "skipped", "bootstrap"})
ALLOWED_APPS = frozenset({"isaacsim", "usd_composer"})
ALLOWED_SOURCE_DIRS_PER_APP: dict[str, frozenset[str]] = {
    "isaacsim": frozenset({"exts", "extscache", "extsDeprecated", "kit/extscore"}),
    "usd_composer": frozenset({"exts", "extscache", "extsbuild", "kit/extscore"}),
}
REQUIRED_TOP_FIELDS = frozenset({
    "name", "apps", "enrichment_status", "category", "public_modules", "keywords",
})
REQUIRED_APP_FIELDS = frozenset({
    "source_dir", "raw_dirname", "path", "version", "present",
})


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def entries(catalog) -> list[dict]:
    return catalog["extensions"]


def test_top_level_required_fields(entries):
    for e in entries:
        missing = REQUIRED_TOP_FIELDS - set(e.keys())
        assert not missing, f"{e.get('name', '?')}: missing fields {missing}"


def test_enrichment_status_allowed(entries):
    for e in entries:
        assert e["enrichment_status"] in ALLOWED_ENRICHMENT_STATUS, (
            f"{e['name']}: invalid enrichment_status={e['enrichment_status']!r}"
        )


def test_skipped_has_reason(entries):
    for e in entries:
        if e["enrichment_status"] == "skipped":
            assert e.get("skipped_reason"), f"{e['name']}: skipped but no skipped_reason"


def test_enriched_has_summary(entries):
    """Enriched entries must have non-empty summary (Phase A/C enrichment contract)."""
    offenders = [
        e["name"] for e in entries
        if e["enrichment_status"] == "enriched" and not (e.get("summary") or "").strip()
    ]
    assert not offenders, f"enriched but empty summary: {offenders}"


def test_apps_keys_allowed(entries):
    for e in entries:
        extra = set(e["apps"].keys()) - ALLOWED_APPS
        assert not extra, f"{e['name']}: unknown app keys {extra}"


def test_apps_nonempty(entries):
    """Every entry must belong to at least one app."""
    orphans = [e["name"] for e in entries if not e["apps"]]
    assert not orphans, f"entries with no apps: {orphans}"


def test_app_record_required_fields(entries):
    for e in entries:
        for app, rec in e["apps"].items():
            missing = REQUIRED_APP_FIELDS - set(rec.keys())
            assert not missing, f"{e['name']}.apps.{app}: missing {missing}"


def test_source_dir_allowed_per_app(entries):
    """Guard against the kit/extscore omission class of bug."""
    for e in entries:
        for app, rec in e["apps"].items():
            allowed = ALLOWED_SOURCE_DIRS_PER_APP[app]
            assert rec["source_dir"] in allowed, (
                f"{e['name']}.apps.{app}: source_dir={rec['source_dir']!r} "
                f"not in {sorted(allowed)}"
            )


def test_names_unique(entries):
    names = [e["name"] for e in entries]
    dupes = [n for n in names if names.count(n) > 1]
    assert not dupes, f"duplicate names: {sorted(set(dupes))}"


def test_deprecated_only_for_isaacsim_extsdeprecated(entries):
    """apps.<app>.deprecated=True should only appear on Isaac extsDeprecated entries."""
    for e in entries:
        for app, rec in e["apps"].items():
            if rec.get("deprecated"):
                assert app == "isaacsim" and rec["source_dir"] == "extsDeprecated", (
                    f"{e['name']}.apps.{app}: deprecated=True but "
                    f"source_dir={rec['source_dir']!r} (should be isaacsim/extsDeprecated)"
                )


def test_api_delta_note_only_on_dual_app_entries(entries):
    """api_delta_note should only be set when both apps present."""
    for e in entries:
        if e.get("api_delta_note") is None:
            continue
        assert len(e["apps"]) >= 2, (
            f"{e['name']}: api_delta_note set but apps={list(e['apps'].keys())}"
        )


def test_kit_extscore_ext_exist_in_both_apps(entries):
    """kit/extscore core libs should be present in both isaacsim and usd_composer.

    Regression guard for the 2026-04-25 fix (6596c8f) — core Kit libraries
    installed under `kit/extscore/` exist in both Isaac Sim 5.1 and USD Composer
    (kit-app-template) by construction.
    """
    names_to_check = {
        "omni.client.lib",
        "omni.kit.async_engine",
        "omni.kit.registry.nucleus",
    }
    for e in entries:
        if e["name"] not in names_to_check:
            continue
        for app in ALLOWED_APPS:
            rec = e["apps"].get(app)
            assert rec is not None, (
                f"{e['name']}: expected both apps but {app} missing"
            )
            assert rec["source_dir"] == "kit/extscore", (
                f"{e['name']}.apps.{app}: expected source_dir=kit/extscore"
            )


def test_metadata_schema_version_is_2(catalog):
    md = catalog.get("metadata") or {}
    assert md.get("schema_version") == 2, f"schema_version != 2: {md.get('schema_version')}"


def test_no_raw_auto_detect_api_delta_notes(entries):
    """All api_delta_note values must be manually classified or null.

    Regression guard for the harvest preserve bug fixed in `feat(harvest):
    preserve manual api_delta_note across re-runs`. The raw auto-detect
    format `"major.minor differs: ..."` should never appear in committed
    catalog — it is the harvester's intermediate signal that humans/Claude
    are expected to refine into a meaningful note (Phase B classification:
    additive / removal / bidirectional / binary-bundle) or clear to null
    when it is a false positive.
    """
    raw_offenders = [
        e["name"] for e in entries
        if isinstance(e.get("api_delta_note"), str)
        and e["api_delta_note"].startswith("major.minor differs:")
    ]
    assert not raw_offenders, (
        f"raw auto-detect api_delta_note found (Phase B refinement missing): "
        f"{raw_offenders}"
    )
