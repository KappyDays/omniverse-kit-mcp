"""Unit tests for scripts/sync_official_asset_catalog.py."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

from scripts import sync_official_asset_catalog as sync


def test_allowlisted_env_loader_reads_only_path_keys(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "ISAAC_SIM_KIT_FILE=C:/Apps/Isaac/apps/isaacsim.exp.full.kit",
                "USD_COMPOSER_KIT_EXE='C:/Apps/Composer/kit/kit.exe'",
                "SECRET_TOKEN=do-not-load",
            ]
        ),
        encoding="utf-8",
    )

    values = sync.load_allowlisted_env_values([env_path])

    assert values == {
        "ISAAC_SIM_KIT_FILE": "C:/Apps/Isaac/apps/isaacsim.exp.full.kit",
        "USD_COMPOSER_KIT_EXE": "C:/Apps/Composer/kit/kit.exe",
    }


def test_profile_root_uses_repo_env_kit_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(sync, "PROJECT_ROOT", tmp_path)
    for key in sync.ALLOWLISTED_PATH_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "USD_COMPOSER_KIT_FILE=C:/Apps/Composer/release/apps/kkr_usd_composer.kit\n",
        encoding="utf-8",
    )

    assert sync.profile_root("usd-composer") == Path("C:/Apps/Composer/release")


def test_find_extension_dir_uses_profile_user_cache(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for key in sync.ALLOWLISTED_PATH_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    local_app_data = tmp_path / "local"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    kit_file = tmp_path / "composer" / "release" / "apps" / "kkr_usd_composer.kit"
    kit_file.parent.mkdir(parents=True)
    kit_file.write_text(
        """
[package]
title = "KKR USD Composer"
version = "0.1.1"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("USD_COMPOSER_KIT_FILE", str(kit_file))
    ext_dir = (
        local_app_data
        / "ov"
        / "data"
        / "Kit"
        / "KKR USD Composer"
        / "0.1"
        / "exts"
        / "3"
        / "omni.kit.browser.asset-1.3.16"
    )
    (ext_dir / "config").mkdir(parents=True)

    found = sync.find_extension_dir(
        sync.profile_root("usd-composer"),
        "usd-composer",
        "omni.kit.browser.asset",
    )

    assert found == ext_dir


def test_provider_roots_reads_profile_user_cache_extension(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for key in sync.ALLOWLISTED_PATH_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    local_app_data = tmp_path / "local"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    kit_file = tmp_path / "composer" / "release" / "apps" / "kkr_usd_composer.kit"
    kit_file.parent.mkdir(parents=True)
    kit_file.write_text(
        """
[package]
title = "KKR USD Composer"
version = "0.1.1"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("USD_COMPOSER_KIT_FILE", str(kit_file))
    ext_dir = (
        local_app_data
        / "ov"
        / "data"
        / "Kit"
        / "KKR USD Composer"
        / "0.1"
        / "exts"
        / "3"
        / "omni.simready.explorer-1.1.4"
    )
    (ext_dir / "config").mkdir(parents=True)
    (ext_dir / "config" / "extension.toml").write_text(
        """
[package]
version = "1.1.4"

[settings.exts."omni.simready.explorer"]
folders = ["https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content"]
""",
        encoding="utf-8",
    )

    providers, errors = sync.provider_roots_for_profile(
        "usd-composer",
        enabled_providers={"omni.simready.explorer"},
    )

    assert errors == []
    assert providers[0]["extension_dir"] == str(ext_dir)
    assert providers[0]["source_roots"] == [
        "https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content"
    ]


def test_discover_material_overrides_browser_material_section(tmp_path: Path) -> None:
    kit_file = tmp_path / "composer.kit"
    kit_file.write_text(
        """
[settings.exts."omni.kit.browser.material"]
enabled = false
folders = [
    "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Materials/2023_2_1/Automotive/",
    "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Materials/2023_2_1/Base",
    "vMaterials::https://omniverse-content-production.s3.us-west-2.amazonaws.com/Materials/vMaterials_2/",
]
""",
        encoding="utf-8",
    )

    overrides = sync.discover_material_overrides(kit_file)

    assert overrides == [
        "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Materials/2023_2_1/Automotive",
        "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Materials/2023_2_1/Base",
        "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Materials/vMaterials_2",
    ]


def test_list_s3_objects_percent_encodes_keys_with_spaces(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return b"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <IsTruncated>false</IsTruncated>
  <Contents>
    <Key>Assets/ArchVis/Residential/Lighting/Floor Lamps/ArcFloorLamp.usd</Key>
  </Contents>
</ListBucketResult>"""

    monkeypatch.setattr(sync.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    urls, errors = sync.list_s3_objects(
        "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/ArchVis/Residential",
        max_entries=10,
    )

    assert errors == []
    assert urls == [
        "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
        "Assets/ArchVis/Residential/Lighting/Floor%20Lamps/ArcFloorLamp.usd"
    ]


def test_write_latest_catalogs_adds_per_profile_pointers(tmp_path: Path) -> None:
    snapshots = [
        {
            "app_profile": "isaac-sim",
            "generated_at": "2099-01-01T00:00:00Z",
            "items": [{"id": "url:https://example.com/a.usd", "canonical_url": "https://example.com/a.usd"}],
        },
        {
            "app_profile": "usd-composer",
            "generated_at": "2099-01-01T00:00:00Z",
            "items": [{"id": "url:https://example.com/m.mdl", "canonical_url": "https://example.com/m.mdl"}],
        },
    ]
    catalog = sync.build_catalog("run-1", snapshots)

    written = sync.write_latest_catalogs(tmp_path, "run-1", catalog, snapshots)

    assert written["default"] == tmp_path / "latest.json"
    assert written["isaac-sim"] == tmp_path / "latest-isaac-sim.json"
    assert written["usd-composer"] == tmp_path / "latest-usd-composer.json"
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["run_id"] == "run-1"
    isaac_latest = json.loads(
        (tmp_path / "latest-isaac-sim.json").read_text(encoding="utf-8")
    )
    composer_latest = json.loads(
        (tmp_path / "latest-usd-composer.json").read_text(encoding="utf-8")
    )
    assert [s["app_profile"] for s in isaac_latest["snapshots"]] == ["isaac-sim"]
    assert [s["app_profile"] for s in composer_latest["snapshots"]] == ["usd-composer"]


def test_parse_args_pins_bounded_live_verification_chunk_contract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "official-assets"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sync_official_asset_catalog.py",
            "--source-run-id",
            "url-discovery-run",
            "--run-id",
            "live-chunk-run",
            "--profiles",
            "isaac-sim",
            "--providers",
            "omni.simready.explorer",
            "--output-dir",
            str(output_dir),
            "--verify",
            "full",
            "--verify-kind",
            "asset",
            "--verify-provider",
            "omni.simready.explorer",
            "--verify-id",
            "url:https://example.com/Assets/Pallet.usd",
            "--verify-id",
            "https://example.com/Assets/Pallet.usd",
            "--verify-limit",
            "50",
            "--rerun-classified",
            "--asset-timeout-s",
            "180",
            "--material-timeout-s",
            "180",
            "--retry",
            "2",
            "--base-url",
            "isaac-sim=http://127.0.0.1:18111",
            "--resume",
        ],
    )

    args = sync.parse_args()

    assert args.source_run_id == "url-discovery-run"
    assert args.run_id == "live-chunk-run"
    assert args.profiles == ["isaac-sim"]
    assert args.providers == ["omni.simready.explorer"]
    assert args.output_dir == output_dir
    assert args.verify == "full"
    assert args.verify_kind == ["asset"]
    assert args.verify_provider == ["omni.simready.explorer"]
    assert args.verify_id == [
        "url:https://example.com/Assets/Pallet.usd",
        "https://example.com/Assets/Pallet.usd",
    ]
    assert args.verify_limit == 50
    assert args.rerun_classified is True
    assert args.asset_timeout_s == 180.0
    assert args.material_timeout_s == 180.0
    assert args.retry == 2
    assert sync.base_url_map(args.base_url)["isaac-sim"] == "http://127.0.0.1:18111"
    assert args.resume is True


@pytest.mark.asyncio
async def test_verify_profile_items_rehydrates_successful_resume_record(
    tmp_path: Path,
) -> None:
    item = {
        "id": "url:https://example.com/Asset.usd",
        "kind": "asset",
        "name": "Asset.usd",
        "canonical_url": "https://example.com/Asset.usd",
        "loadable_in": [],
        "verification_status": "url_validated",
    }
    record = {
        "id": item["id"],
        "kind": "asset",
        "name": "Asset.usd",
        "canonical_url": item["canonical_url"],
        "app_profile": "isaac-sim",
        "verification_status": "load_verified",
        "checked_at": "2099-01-01T00:00:00Z",
        "elapsed_ms": 123,
        "bbox": {"min": [0, 0, 0], "max": [1, 1, 1]},
        "meters_per_unit": 1.0,
        "up_axis": "Y",
        "prim_count": 7,
        "error": None,
    }
    verify_log = tmp_path / "verification" / "resume-run.jsonl"
    verify_log.parent.mkdir(parents=True)
    verify_log.write_text(json.dumps(record) + "\n", encoding="utf-8")

    items = await sync.verify_profile_items(
        "isaac-sim",
        [item],
        tmp_path,
        "resume-run",
        "http://127.0.0.1:9",
        asset_timeout_s=1.0,
        material_timeout_s=1.0,
        retry=0,
    )

    assert items[0]["verification_status"] == "load_verified"
    assert items[0]["loadable_in"][0]["verification_status"] == "load_verified"
    assert items[0]["loadable_in"][0]["elapsed_ms"] == 123
    assert len(verify_log.read_text(encoding="utf-8").splitlines()) == 1


@pytest.mark.asyncio
async def test_verify_profile_items_treats_failed_resume_record_as_classified(
    tmp_path: Path,
) -> None:
    item = {
        "id": "url:https://example.com/Broken.usd",
        "kind": "asset",
        "name": "Broken.usd",
        "canonical_url": "https://example.com/Broken.usd",
        "verification_status": "url_validated",
    }
    record = {
        "id": item["id"],
        "kind": "asset",
        "name": "Broken.usd",
        "canonical_url": item["canonical_url"],
        "app_profile": "isaac-sim",
        "verification_status": "failed",
        "checked_at": "2099-01-01T00:00:00Z",
        "error": "invalid bbox evidence: sentinel_magnitude",
    }
    verify_log = tmp_path / "verification" / "resume-run.jsonl"
    verify_log.parent.mkdir(parents=True)
    verify_log.write_text(json.dumps(record) + "\n", encoding="utf-8")

    items = await sync.verify_profile_items(
        "isaac-sim",
        [item],
        tmp_path,
        "resume-run",
        "http://127.0.0.1:9",
        asset_timeout_s=1.0,
        material_timeout_s=1.0,
        retry=0,
    )

    assert items[0]["verification_status"] == "failed"
    assert items[0]["error"] == "invalid bbox evidence: sentinel_magnitude"
    assert len(verify_log.read_text(encoding="utf-8").splitlines()) == 1


@pytest.mark.asyncio
async def test_verify_profile_items_limit_processes_next_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    items = [
        {
            "id": "url:https://example.com/A.usd",
            "kind": "asset",
            "name": "A.usd",
            "canonical_url": "https://example.com/A.usd",
            "verification_status": "url_validated",
        },
        {
            "id": "url:https://example.com/B.usd",
            "kind": "asset",
            "name": "B.usd",
            "canonical_url": "https://example.com/B.usd",
            "verification_status": "url_validated",
        },
    ]

    async def fake_verify_one(_client, item, profile_name, *_args):
        return {
            "id": item["id"],
            "kind": item["kind"],
            "name": item["name"],
            "canonical_url": item["canonical_url"],
            "app_profile": profile_name,
            "verification_status": "load_verified",
            "checked_at": "2099-01-01T00:00:00Z",
            "error": None,
        }

    monkeypatch.setattr(sync, "verify_one", fake_verify_one)

    result = await sync.verify_profile_items(
        "isaac-sim",
        items,
        tmp_path,
        "chunk-run",
        "http://127.0.0.1:9",
        asset_timeout_s=1.0,
        material_timeout_s=1.0,
        retry=0,
        verify_limit=1,
    )

    assert result[0]["verification_status"] == "load_verified"
    assert result[1]["verification_status"] == "url_validated"
    verify_log = tmp_path / "verification" / "chunk-run.jsonl"
    assert len(verify_log.read_text(encoding="utf-8").splitlines()) == 1


@pytest.mark.asyncio
async def test_verify_profile_items_filters_exact_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    items = [
        {
            "id": "url:https://example.com/A.usd",
            "kind": "asset",
            "name": "A.usd",
            "canonical_url": "https://example.com/A.usd",
            "verification_status": "url_validated",
        },
        {
            "id": "url:https://example.com/B.usd",
            "kind": "asset",
            "name": "B.usd",
            "canonical_url": "https://example.com/B.usd",
            "verification_status": "url_validated",
        },
    ]

    async def fake_verify_one(_client, item, profile_name, *_args):
        return {
            "id": item["id"],
            "kind": item["kind"],
            "name": item["name"],
            "canonical_url": item["canonical_url"],
            "app_profile": profile_name,
            "verification_status": "load_verified",
            "checked_at": "2099-01-01T00:00:00Z",
            "error": None,
        }

    monkeypatch.setattr(sync, "verify_one", fake_verify_one)

    result = await sync.verify_profile_items(
        "isaac-sim",
        items,
        tmp_path,
        "id-filter-run",
        "http://127.0.0.1:9",
        asset_timeout_s=1.0,
        material_timeout_s=1.0,
        retry=0,
        verify_ids={"url:https://example.com/B.usd"},
    )

    assert result[0]["verification_status"] == "url_validated"
    assert result[1]["verification_status"] == "load_verified"
    verify_log = tmp_path / "verification" / "id-filter-run.jsonl"
    assert len(verify_log.read_text(encoding="utf-8").splitlines()) == 1


def test_load_source_snapshots_filters_requested_profiles(tmp_path: Path) -> None:
    snapshots = [
        {"app_profile": "isaac-sim", "items": [{"id": "url:https://example.com/a.usd"}]},
        {"app_profile": "usd-composer", "items": [{"id": "url:https://example.com/m.mdl"}]},
    ]
    snapshot_path = tmp_path / "snapshots" / "url-run.json"
    snapshot_path.parent.mkdir()
    snapshot_path.write_text(
        json.dumps({"run_id": "url-run", "snapshots": snapshots, "items": []}),
        encoding="utf-8",
    )

    loaded = sync.load_source_snapshots(tmp_path, "url-run", ["usd-composer"])

    assert set(loaded) == {"usd-composer"}
    assert loaded["usd-composer"]["source_run_id"] == "url-run"


@pytest.mark.asyncio
async def test_verify_material_records_create_and_assign_evidence(monkeypatch) -> None:
    async def fake_rest_post(_client, path: str, _payload=None, request_timeout_s=None):
        assert request_timeout_s == 7.0
        if path.endswith("/stage/create_prim"):
            return {"ok": False, "error": "create failed"}
        if path.endswith("/material/assign_mdl"):
            return {"ok": True, "material_path": "/Looks/Test"}
        raise AssertionError(path)

    async def fake_rest_get(_client, path: str, request_timeout_s=None, **_params):
        assert request_timeout_s == 7.0
        assert path.endswith("/material/get_bound")
        return {"ok": True, "material_path": "/Looks/Test"}

    async def fake_rest_delete(_client, path: str, request_timeout_s=None, **_params):
        assert request_timeout_s == sync.CLEANUP_TIMEOUT_S
        assert path.endswith("/stage/prim")
        return {"ok": True}

    monkeypatch.setattr(sync, "rest_post", fake_rest_post)
    monkeypatch.setattr(sync, "rest_get", fake_rest_get)
    monkeypatch.setattr(sync, "rest_delete", fake_rest_delete)

    record = await sync.verify_material(
        object(),
        {
            "id": "url:https://example.com/Material.mdl",
            "kind": "material",
            "name": "Material.mdl",
            "canonical_url": "https://example.com/Material.mdl",
        },
        "usd-composer",
        7.0,
    )

    assert record["verification_status"] == "failed"
    assert record["create_prim"]["ok"] is False
    assert record["assign"]["ok"] is True
    assert record["bound"]["material_path"] == "/Looks/Test"


@pytest.mark.asyncio
async def test_cleanup_prim_records_timeout(monkeypatch) -> None:
    async def never_returns(_client, _path, **_params):
        await asyncio.sleep(60)
        return {"ok": True}

    monkeypatch.setattr(sync, "CLEANUP_TIMEOUT_S", 0.01)
    monkeypatch.setattr(sync, "rest_delete", never_returns)

    record = await sync.cleanup_prim(object(), "/World/Stuck")

    assert record["ok"] is False
    assert record["error_code"] == "TimeoutError"
    assert record["timeout_s"] == 0.01


def test_official_load_quality_helper_accepts_valid_bbox() -> None:
    evidence = sync.official_asset_load_quality_evidence(
        {"ok": True, "has_children": True},
        {
            "ok": True,
            "min": [0.0, 0.0, 0.0],
            "max": [1.0, 1.0, 1.0],
            "size": [1.0, 1.0, 1.0],
            "is_empty": False,
        },
        {"ok": True, "default_prim": "/World", "prim_count": 1},
    )

    assert evidence["load_quality"] == "valid"
    assert evidence["bbox_valid"] is True
    assert evidence["load_quality_warning"] is None


def test_official_load_quality_helper_accepts_content_without_bbox() -> None:
    sentinel = 3.4028234663852886e38
    evidence = sync.official_asset_load_quality_evidence(
        {"ok": True, "has_children": True},
        {
            "ok": True,
            "min": [sentinel, sentinel, sentinel],
            "max": [-sentinel, -sentinel, -sentinel],
            "size": [0.0, 0.0, 0.0],
            "is_empty": True,
        },
        {"ok": True, "default_prim": "/World", "prim_count": 1},
    )

    assert evidence["load_quality"] == "content_verified_no_bbox"
    assert evidence["bbox_valid"] is False
    assert "sentinel_magnitude" in evidence["bbox_validation_reasons"]
    assert evidence["load_quality_warning"] is not None


def test_official_load_quality_helper_rejects_empty_content() -> None:
    sentinel = 3.4028234663852886e38
    evidence = sync.official_asset_load_quality_evidence(
        {"ok": True, "has_children": False},
        {
            "ok": True,
            "min": [sentinel, sentinel, sentinel],
            "max": [-sentinel, -sentinel, -sentinel],
            "size": [0.0, 0.0, 0.0],
            "is_empty": True,
        },
        {"ok": True, "default_prim": "", "prim_count": 0},
    )

    assert evidence["load_quality"] == "empty_content"
    assert evidence["bbox_valid"] is False
    assert "sentinel_magnitude" in evidence["bbox_validation_reasons"]


def test_safe_name_prefixes_leading_digit_for_usd_paths() -> None:
    assert sync.safe_name({"name": "4Tier_Fountain.usd"}) == "Asset_4Tier_Fountain"
