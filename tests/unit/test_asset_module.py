"""Unit tests for AssetModule — catalog listing (Phase B+) + offline search."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest

from omniverse_kit_mcp.modules.asset_module import AssetModule, resolve_catalog_asset_url
from omniverse_kit_mcp.modules.external_asset import ExternalAssetRegistry
from omniverse_kit_mcp.types.asset import AssetCategory, AssetItem, AssetListResult
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta

# Real curated catalog (format-guarded by test_asset_inventory_integrity.py).
REAL_CATALOG_DIR = Path(__file__).resolve().parents[2] / "docs" / "assets" / "isaac"
_ISAAC = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com"
    "/Assets/Isaac/6.0/Isaac"
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="test", module=ModuleName.ASSET, started_at_epoch_ms=0
    )


class _ExplodingClient:
    """Any REST call fails — proves asset_search is fully offline (no Isaac)."""

    async def asset_list(self, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("asset_search must not call the live REST client")


@pytest.mark.asyncio
async def test_asset_list_categories():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = AssetModule(client)
    result = await module.list(_meta())

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, AssetListResult)
    assert result.data.category is None
    assert len(result.data.categories) >= 1
    assert isinstance(result.data.categories[0], AssetCategory)


@pytest.mark.asyncio
async def test_asset_list_robots():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = AssetModule(client)
    result = await module.list(_meta(), category="robots", subpath="FrankaRobotics")

    assert result.ok
    assert result.data.category == "robots"
    assert result.data.subpath == "FrankaRobotics"
    assert len(result.data.items) == 2
    folders = [i for i in result.data.items if i.is_folder]
    files = [i for i in result.data.items if not i.is_folder]
    assert len(folders) == 1 and isinstance(folders[0], AssetItem)
    assert len(files) == 1 and files[0].name == "franka.usd"
    list_calls = [c for c in client.calls if c[0] == "asset_list"]
    assert list_calls[0][1]["category"] == "robots"


@pytest.mark.asyncio
async def test_asset_list_propagates_error():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def asset_list(self, **kwargs):  # type: ignore[override]
            raise RuntimeError("S3 directory listing failed")

    module = AssetModule(FailingClient())
    result = await module.list(_meta(), category="robots")

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ASSET_LIST_ERROR"
    assert "S3" in (result.message or "")


# ---------------------------------------------------------------------------
# asset_search — offline semantic search over the curated markdown catalog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_forklift_returns_props_canonical_url():
    """'forklift' → the canonical Props/Forklift/forklift.usd URL, offline."""
    module = AssetModule(_ExplodingClient(), catalog_dir=REAL_CATALOG_DIR)
    result = await module.search(_meta(), query="forklift")

    assert result.ok, result.message
    assert result.data, "expected at least one forklift hit"
    props_hits = [
        h for h in result.data
        if h["category"] == "props" and "forklift" in h["name"].lower()
    ]
    assert props_hits, f"no props forklift hit: {result.data}"
    assert props_hits[0]["url"] == f"{_ISAAC}/Props/Forklift/forklift.usd"
    assert props_hits[0]["source_file"] == "props.md"


@pytest.mark.asyncio
async def test_search_category_filter_environments():
    module = AssetModule(_ExplodingClient(), catalog_dir=REAL_CATALOG_DIR)
    result = await module.search(
        _meta(), query="warehouse", category="environments"
    )

    assert result.ok
    assert result.data
    assert all(h["category"] == "environments" for h in result.data)
    assert any("warehouse" in h["name"].lower() for h in result.data)


@pytest.mark.asyncio
async def test_search_robot_resolves_robots_url():
    module = AssetModule(_ExplodingClient(), catalog_dir=REAL_CATALOG_DIR)
    result = await module.search(_meta(), query="franka")

    assert result.ok
    robot_hits = [h for h in result.data if h["category"] == "robots"]
    assert robot_hits, f"no robot hit: {result.data}"
    assert "/Robots/" in robot_hits[0]["url"]
    assert robot_hits[0]["url"].startswith("https://")


@pytest.mark.asyncio
async def test_search_no_match_returns_empty():
    module = AssetModule(_ExplodingClient(), catalog_dir=REAL_CATALOG_DIR)
    result = await module.search(_meta(), query="zzqq_nonexistent_asset_xyz")

    assert result.ok
    assert result.data == []


@pytest.mark.asyncio
async def test_search_response_fields_exact():
    module = AssetModule(_ExplodingClient(), catalog_dir=REAL_CATALOG_DIR)
    result = await module.search(_meta(), query="forklift", limit=5)

    assert result.ok and result.data
    for h in result.data:
        assert set(h.keys()) == {"name", "url", "category", "source_file"}
        assert h["url"].startswith("https://")
        assert h["url"].endswith((".usd", ".usda"))


@pytest.mark.asyncio
async def test_search_limit_applied():
    module = AssetModule(_ExplodingClient(), catalog_dir=REAL_CATALOG_DIR)
    result = await module.search(_meta(), query="pallet", limit=3)

    assert result.ok
    assert len(result.data) <= 3


@pytest.mark.asyncio
async def test_search_ranks_exact_name_first():
    """A query equal to an asset's filename stem ranks it ahead of substring hits."""
    module = AssetModule(_ExplodingClient(), catalog_dir=REAL_CATALOG_DIR)
    result = await module.search(_meta(), query="forklift")

    assert result.ok and result.data
    # forklift.usd (exact stem) must outrank warehouse_with_forklifts.usd
    assert result.data[0]["name"].lower().startswith("forklift")


@pytest.fixture
def synthetic_catalog(tmp_path: Path) -> Path:
    """Minimal catalog mirroring the real format — locks URL-construction rules."""
    d = tmp_path / "isaac"
    (d / "assets").mkdir(parents=True)
    (d / "asset_inventory.md").write_text("# index\n", encoding="utf-8")
    (d / "assets" / "environments.md").write_text(
        "# Environments\n\n"
        "`$ISAAC` = `https://example.com/Isaac`\n\n"
        "Root: `$ISAAC/Environments/`\n\n"
        "| 환경 | 주요 USD |\n|---|---|\n"
        "| **Simple_Warehouse** | `warehouse.usd` ✓ |\n"
        "| | `full_warehouse.usd` |\n"
        "| | `warehouse_h10m_center.usda` |\n",
        encoding="utf-8",
    )
    (d / "assets" / "people.md").write_text(
        "# People\n\n"
        "`$ISAAC` = `https://example.com/Isaac`\n\n"
        "Root: `$ISAAC/People/`\n\n"
        "## Characters\n\n"
        "Root: `$ISAAC/People/Characters/`\n\n"
        "| 에셋 | USD 경로 |\n|---|---|\n"
        "| F_Business_02 | `Characters/F_Business_02/F_Business_02.usd` ✓ |\n",
        encoding="utf-8",
    )
    (d / "assets" / "simready.md").write_text(
        "# SimReady\n\n"
        "`$SIM` = `https://example.com/simready_content/props`\n\n"
        "**팔레트 (Pallet)**\n"
        "`woodpallet_a01` · `box_a01~a05`\n",
        encoding="utf-8",
    )
    (d / "assets" / "robots.md").write_text(
        "# Robots\n\n"
        "`$ISAAC` = `https://example.com/Isaac`\n\n"
        "| 벤더 | 모델 | 주요 USD |\n|---|---|---|\n"
        "| **FrankaRobotics** | FrankaPanda | `franka.usd` |\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def synthetic_official_catalog(tmp_path: Path) -> Path:
    d = tmp_path / "official-assets"
    d.mkdir()
    sim_root = (
        "https://omniverse-content-staging.s3.us-west-2.amazonaws.com"
        "/Assets/simready_content/props"
    )
    material_root = (
        "https://omniverse-content-production.s3-us-west-2.amazonaws.com"
        "/Assets/Materials/2023_2_1/Base"
    )
    catalog = {
        "schema_version": 1,
        "generated_at": "2099-01-01T00:00:00Z",
        "generator": "test",
        "snapshots": [
            {
                "app_profile": "isaac-sim",
                "app_version": "6.0.0",
                "kit_version": "110.1.1",
                "generated_at": "2099-01-01T00:00:00Z",
                "providers": [
                    {
                        "provider": "omni.simready.explorer",
                        "extension_id": "omni.simready.explorer",
                        "extension_version": "1.1.4",
                        "source_roots": [sim_root],
                    }
                ],
                "counts": {"items": 2, "asset": 2, "url_validated": 2},
                "items": [],
            },
            {
                "app_profile": "usd-composer",
                "app_version": "usd-composer",
                "kit_version": "110.1.1",
                "generated_at": "2099-01-01T00:00:00Z",
                "providers": [
                    {
                        "provider": "omni.kit.browser.material",
                        "extension_id": "omni.kit.browser.material",
                        "extension_version": "1.6.5",
                        "source_roots": [material_root],
                        "material_overrides": [
                            "Materials/2023_2_1/Automotive",
                            "Materials/2023_2_1/Base",
                            "vMaterials_2",
                        ],
                    }
                ],
                "counts": {"items": 1, "material": 1, "assign_verified": 1},
                "items": [],
            },
        ],
        "items": [
            {
                "id": f"url:{sim_root}/aluminumpallet_a01/aluminumpallet_a01.usd",
                "kind": "asset",
                "name": "aluminumpallet_a01.usd",
                "aliases": ["aluminumpallet_a01", "pallet"],
                "canonical_url": f"{sim_root}/aluminumpallet_a01/aluminumpallet_a01.usd",
                "provider": "omni.simready.explorer",
                "source_root": sim_root,
                "category": "pallets",
                "extension_id": "omni.simready.explorer",
                "extension_version": "1.1.4",
                "provided_in": [
                    {
                        "app_profile": "isaac-sim",
                        "app_version": "6.0.0",
                        "kit_version": "110.1.1",
                        "provider": "omni.simready.explorer",
                        "extension_id": "omni.simready.explorer",
                        "extension_version": "1.1.4",
                        "source_root": sim_root,
                        "category": "pallets",
                    }
                ],
                "loadable_in": [],
                "verification_status": "url_validated",
            },
            {
                "id": f"url:{sim_root}/aluminumpallet_a02/aluminumpallet_a02.usd",
                "kind": "asset",
                "name": "aluminumpallet_a02.usd",
                "aliases": ["aluminumpallet_a02", "pallet"],
                "canonical_url": f"{sim_root}/aluminumpallet_a02/aluminumpallet_a02.usd",
                "provider": "omni.simready.explorer",
                "source_root": sim_root,
                "category": "pallets",
                "provided_in": [
                    {
                        "app_profile": "isaac-sim",
                        "app_version": "6.0.0",
                        "kit_version": "110.1.1",
                        "provider": "omni.simready.explorer",
                    }
                ],
                "loadable_in": [],
                "verification_status": "url_validated",
            },
            {
                "id": f"url:{material_root}/Metals/Brushed_Aluminum.mdl",
                "kind": "material",
                "name": "Brushed_Aluminum.mdl",
                "aliases": ["brushed aluminum"],
                "canonical_url": f"{material_root}/Metals/Brushed_Aluminum.mdl",
                "material_name": "Brushed_Aluminum",
                "provider": "omni.kit.browser.material",
                "source_root": material_root,
                "category": "Metals",
                "provided_in": [
                    {
                        "app_profile": "usd-composer",
                        "app_version": "usd-composer",
                        "kit_version": "110.1.1",
                        "provider": "omni.kit.browser.material",
                        "extension_id": "omni.kit.browser.material",
                        "extension_version": "1.6.5",
                        "source_root": material_root,
                        "category": "Metals",
                    }
                ],
                "loadable_in": [
                    {
                        "app_profile": "usd-composer",
                        "app_version": "usd-composer",
                        "kit_version": "110.1.1",
                        "verification_status": "assign_verified",
                        "checked_at": "2099-01-01T00:00:00Z",
                    }
                ],
                "verification_status": "assign_verified",
            },
        ],
    }
    (d / "latest.json").write_text(
        json.dumps(catalog, indent=2),
        encoding="utf-8",
    )
    return d


@pytest.mark.asyncio
async def test_parser_bare_filename_uses_group_folder(synthetic_catalog: Path):
    module = AssetModule(_ExplodingClient(), catalog_dir=synthetic_catalog)
    result = await module.search(_meta(), query="warehouse")

    assert result.ok
    urls = {h["url"] for h in result.data}
    assert "https://example.com/Isaac/Environments/Simple_Warehouse/warehouse.usd" in urls
    # empty-col0 row inherits the bold group folder (rowspan idiom)
    assert "https://example.com/Isaac/Environments/Simple_Warehouse/full_warehouse.usd" in urls
    assert "https://example.com/Isaac/Environments/Simple_Warehouse/warehouse_h10m_center.usda" in urls


@pytest.mark.asyncio
async def test_parser_path_with_slashes_uses_file_root(synthetic_catalog: Path):
    module = AssetModule(_ExplodingClient(), catalog_dir=synthetic_catalog)
    result = await module.search(_meta(), query="business")

    assert result.ok
    urls = {h["url"] for h in result.data}
    assert "https://example.com/Isaac/People/Characters/F_Business_02/F_Business_02.usd" in urls


@pytest.mark.asyncio
async def test_parser_simready_prose_canonical_url(synthetic_catalog: Path):
    module = AssetModule(_ExplodingClient(), catalog_dir=synthetic_catalog)
    result = await module.search(_meta(), query="woodpallet")

    assert result.ok
    urls = {h["url"] for h in result.data}
    assert "https://example.com/simready_content/props/woodpallet_a01/woodpallet_a01.usd" in urls


def test_resolve_catalog_asset_url_uses_markdown_catalog(synthetic_catalog: Path):
    assert (
        resolve_catalog_asset_url(
            "robots",
            "Robots/FrankaRobotics/FrankaPanda/franka.usd",
            catalog_dir=synthetic_catalog,
        )
        == "https://example.com/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd"
    )


# ---------------------------------------------------------------------------
# official_asset_* — generated NVIDIA official browser-extension catalog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_official_asset_search_returns_url_id_and_variant(
    synthetic_official_catalog: Path,
):
    module = AssetModule(
        _ExplodingClient(),
        official_catalog_dir=synthetic_official_catalog,
    )
    result = await module.official_search(
        _meta(),
        query="aluminumpallet_a01",
        app_profile="isaac-sim",
    )

    assert result.ok, result.message
    assert result.data["count"] == 1
    hit = result.data["candidates"][0]
    assert hit["id"].startswith("url:https://")
    assert hit["name"] == "aluminumpallet_a01.usd"
    assert hit["canonical_url"].endswith("/aluminumpallet_a01/aluminumpallet_a01.usd")
    assert hit["verification_status"] == "url_validated"
    assert hit["verify_required_before_use"] is True
    assert hit["provider_evidence"][0]["provider"] == "omni.simready.explorer"
    assert all("a02" not in c["name"] for c in result.data["candidates"])


def _catalog_with_items(
    *,
    run_id: str,
    app_profile: str,
    generated_at: str,
    items: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "generator": "test",
        "run_id": run_id,
        "snapshots": [
            {
                "app_profile": app_profile,
                "app_version": "6.0.0",
                "kit_version": "110.1.1",
                "generated_at": generated_at,
                "providers": [],
                "counts": {"items": len(items)},
                "items": [],
            }
        ],
        "items": items,
    }


def _minimal_official_item(name: str, app_profile: str) -> dict[str, object]:
    url = f"https://example.com/Assets/{name}/{name}.usd"
    return {
        "id": f"url:{url}",
        "kind": "asset",
        "name": f"{name}.usd",
        "aliases": [name],
        "canonical_url": url,
        "provider": "omni.simready.explorer",
        "source_root": "https://example.com/Assets",
        "category": "props",
        "provided_in": [
            {
                "app_profile": app_profile,
                "app_version": "6.0.0",
                "kit_version": "110.1.1",
                "provider": "omni.simready.explorer",
                "source_root": "https://example.com/Assets",
                "category": "props",
            }
        ],
        "loadable_in": [],
        "verification_status": "url_validated",
    }


@pytest.mark.asyncio
async def test_official_asset_search_uses_profile_latest_pointer(tmp_path: Path):
    shared = _catalog_with_items(
        run_id="composer-run",
        app_profile="usd-composer",
        generated_at="2099-01-01T00:00:00Z",
        items=[],
    )
    isaac = _catalog_with_items(
        run_id="isaac-run",
        app_profile="isaac-sim",
        generated_at="2099-01-01T00:00:00Z",
        items=[_minimal_official_item("aluminumpallet_a01", "isaac-sim")],
    )
    tmp_path.joinpath("latest.json").write_text(json.dumps(shared), encoding="utf-8")
    tmp_path.joinpath("latest-isaac-sim.json").write_text(
        json.dumps(isaac), encoding="utf-8"
    )
    module = AssetModule(_ExplodingClient(), official_catalog_dir=tmp_path)

    result = await module.official_search(
        _meta(), query="aluminumpallet_a01", app_profile="isaac-sim"
    )

    assert result.ok, result.message
    assert result.data["count"] == 1
    assert result.data["catalog_path"].endswith("latest-isaac-sim.json")
    assert result.data["catalog_identity"]["run_id"] == "isaac-run"


@pytest.mark.asyncio
async def test_official_asset_search_reloads_when_profile_latest_changes(tmp_path: Path):
    path = tmp_path / "latest-isaac-sim.json"
    path.write_text(
        json.dumps(
            _catalog_with_items(
                run_id="empty-run",
                app_profile="isaac-sim",
                generated_at="2099-01-01T00:00:00Z",
                items=[],
            )
        ),
        encoding="utf-8",
    )
    module = AssetModule(_ExplodingClient(), official_catalog_dir=tmp_path)
    first = await module.official_search(
        _meta(), query="aluminumpallet_a01", app_profile="isaac-sim"
    )
    assert first.ok and first.data["count"] == 0

    path.write_text(
        json.dumps(
            _catalog_with_items(
                run_id="fresh-run",
                app_profile="isaac-sim",
                generated_at="2099-01-01T00:01:00Z",
                items=[_minimal_official_item("aluminumpallet_a01", "isaac-sim")],
            )
        ),
        encoding="utf-8",
    )
    stat = path.stat()
    os.utime(path, (stat.st_atime, stat.st_mtime + 1.0))

    second = await module.official_search(
        _meta(), query="aluminumpallet_a01", app_profile="isaac-sim"
    )

    assert second.ok, second.message
    assert second.data["count"] == 1
    assert second.data["catalog_identity"]["run_id"] == "fresh-run"


@pytest.mark.asyncio
async def test_official_asset_resolve_material_target_and_loadability(
    synthetic_official_catalog: Path,
):
    module = AssetModule(
        _ExplodingClient(),
        official_catalog_dir=synthetic_official_catalog,
    )
    result = await module.official_resolve(
        _meta(),
        name_or_id="brushed aluminum",
        kind="material",
        app_profile="usd-composer",
    )

    assert result.ok, result.message
    assert result.data["kind"] == "material"
    assert result.data["target"] == {
        "mdl_url": result.data["canonical_url"],
        "material_name": "Brushed_Aluminum",
    }
    assert result.data["verify_required_before_use"] is False
    assert result.data["loadable_in"][0]["verification_status"] == "assign_verified"


@pytest.mark.asyncio
async def test_official_asset_stale_snapshot_warns_and_can_be_filtered(
    synthetic_official_catalog: Path,
):
    path = synthetic_official_catalog / "latest.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["snapshots"][0]["stale"] = True
    path.write_text(json.dumps(catalog), encoding="utf-8")
    module = AssetModule(
        _ExplodingClient(),
        official_catalog_dir=synthetic_official_catalog,
    )

    stale = await module.official_search(
        _meta(),
        query="aluminumpallet_a01",
        app_profile="isaac-sim",
        allow_stale=True,
    )
    fresh_only = await module.official_search(
        _meta(),
        query="aluminumpallet_a01",
        app_profile="isaac-sim",
        allow_stale=False,
    )

    assert stale.ok and stale.data["count"] == 1
    assert stale.data["candidates"][0]["status"] == "stale"
    assert stale.data["candidates"][0]["stale_warning"]
    assert stale.data["candidates"][0]["verify_required_before_use"] is True
    assert fresh_only.ok and fresh_only.data["count"] == 0


@pytest.mark.asyncio
async def test_official_asset_sync_status_reports_profile_counts(
    synthetic_official_catalog: Path,
):
    module = AssetModule(
        _ExplodingClient(),
        official_catalog_dir=synthetic_official_catalog,
    )
    result = await module.official_sync_status(_meta(), app_profile="usd-composer")

    assert result.ok, result.message
    assert result.data["profile_count"] == 1
    assert result.data["profiles"][0]["app_profile"] == "usd-composer"
    assert result.data["counts"]["material"] == 1
    assert result.data["counts"]["assign_verified"] == 1


@pytest.mark.asyncio
async def test_official_asset_get_missing_catalog_reports_unavailable(tmp_path: Path):
    module = AssetModule(_ExplodingClient(), official_catalog_dir=tmp_path / "missing")
    result = await module.official_get(_meta(), asset_id="url:https://missing")

    assert not result.ok
    assert result.error_code == "OFFICIAL_ASSET_CATALOG_UNAVAILABLE"


def test_official_safe_prim_name_prefixes_leading_digit() -> None:
    from omniverse_kit_mcp.modules.asset_module import _safe_prim_name

    assert _safe_prim_name({"name": "4Tier_Fountain.usd"}) == "Asset_4Tier_Fountain"


@pytest.mark.asyncio
async def test_official_asset_verify_asset_uses_stage_inspect_and_cleanup(
    synthetic_official_catalog: Path,
):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = AssetModule(client, official_catalog_dir=synthetic_official_catalog)
    asset_id = (
        "url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com"
        "/Assets/simready_content/props/aluminumpallet_a01/aluminumpallet_a01.usd"
    )
    result = await module.official_verify(
        _meta(),
        asset_id=asset_id,
        app_profile="isaac-sim",
        timeout_s=1.0,
    )

    assert result.ok, result.message
    assert result.data["verification_status"] == "load_verified"
    assert result.data["load_quality"] == "valid"
    assert result.data["load_quality_warning"] is None
    assert result.data["bbox_valid"] is True
    assert result.data["has_authored_children"] is True
    assert result.data["prim_count_valid"] is True
    call_names = [name for name, _payload in client.calls]
    assert "simulation_status" in call_names
    assert "stage_load_usd" in call_names
    assert "stage_compute_world_bbox" in call_names
    assert "content_inspect" in call_names
    assert call_names[-1] == "stage_delete_prim"
    assert (synthetic_official_catalog / "verification-on-demand.jsonl").is_file()


@pytest.mark.asyncio
async def test_official_asset_verify_asset_accepts_content_without_bbox(
    synthetic_official_catalog: Path,
):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    sentinel = 3.4028234663852886e38
    client.responses["stage_compute_world_bbox"] = {
        "ok": True,
        "min": [sentinel, sentinel, sentinel],
        "max": [-sentinel, -sentinel, -sentinel],
        "center": [0.0, 0.0, 0.0],
        "size": [0.0, 0.0, 0.0],
        "is_empty": True,
    }
    module = AssetModule(client, official_catalog_dir=synthetic_official_catalog)
    asset_id = (
        "url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com"
        "/Assets/simready_content/props/aluminumpallet_a01/aluminumpallet_a01.usd"
    )

    result = await module.official_verify(
        _meta(),
        asset_id=asset_id,
        app_profile="isaac-sim",
        timeout_s=1.0,
    )

    assert result.ok, result.message
    assert result.data["verification_status"] == "load_verified"
    assert result.data["load_quality"] == "content_verified_no_bbox"
    assert result.data["bbox_valid"] is False
    assert "empty_flag" in result.data["bbox_validation_reasons"]
    assert "min_greater_than_max" in result.data["bbox_validation_reasons"]
    assert "sentinel_magnitude" in result.data["bbox_validation_reasons"]
    assert result.data["load_quality_warning"] is not None
    assert result.data["error"] is None


@pytest.mark.asyncio
async def test_official_asset_verify_asset_rejects_empty_content(
    synthetic_official_catalog: Path,
):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["stage_load_usd"] = {
        "ok": True,
        "prim_path": "/World/OfficialAssetVerify/empty",
        "type_name": "Xform",
        "has_children": False,
    }
    client.responses["content_inspect"] = {
        "ok": True,
        "default_prim": "",
        "prim_count": 0,
    }
    module = AssetModule(client, official_catalog_dir=synthetic_official_catalog)
    asset_id = (
        "url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com"
        "/Assets/simready_content/props/aluminumpallet_a01/aluminumpallet_a01.usd"
    )

    result = await module.official_verify(
        _meta(),
        asset_id=asset_id,
        app_profile="isaac-sim",
        timeout_s=1.0,
    )

    assert result.ok, result.message
    assert result.data["verification_status"] == "failed"
    assert result.data["load_quality"] == "empty_content"
    assert result.data["error"] == "no authored child, default prim, or prim_count evidence"


@pytest.mark.asyncio
async def test_official_asset_verify_material_assigns_and_reads_binding(
    synthetic_official_catalog: Path,
):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = AssetModule(client, official_catalog_dir=synthetic_official_catalog)
    result = await module.official_verify(
        _meta(),
        asset_id=(
            "url:https://omniverse-content-production.s3-us-west-2.amazonaws.com"
            "/Assets/Materials/2023_2_1/Base/Metals/Brushed_Aluminum.mdl"
        ),
        app_profile="usd-composer",
        timeout_s=1.0,
    )

    assert result.ok, result.message
    assert result.data["verification_status"] == "assign_verified"
    call_names = [name for name, _payload in client.calls]
    assert "stage_create_prim" in call_names
    assert "material_assign_mdl" in call_names
    assert "material_get_bound" in call_names
    assert call_names[-1] == "stage_delete_prim"


@pytest.mark.asyncio
async def test_official_asset_verify_material_requires_created_test_prim(
    synthetic_official_catalog: Path,
):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["stage_create_prim"] = {
        "ok": False,
        "error": "create failed",
    }
    module = AssetModule(client, official_catalog_dir=synthetic_official_catalog)

    result = await module.official_verify(
        _meta(),
        asset_id=(
            "url:https://omniverse-content-production.s3-us-west-2.amazonaws.com"
            "/Assets/Materials/2023_2_1/Base/Metals/Brushed_Aluminum.mdl"
        ),
        app_profile="usd-composer",
        timeout_s=1.0,
    )

    assert result.ok, result.message
    assert result.data["verification_status"] == "failed"
    assert result.data["create_prim"]["ok"] is False
    assert result.data["assign"]["ok"] is True
    assert result.data["bound"]["material_path"]
    assert result.data["error"] == "material assign or binding readback failed"


# ---------------------------------------------------------------------------
# external_asset_* — free provider search/download/convert preparation
# ---------------------------------------------------------------------------


def _mock_external_transport(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.startswith("https://api.polyhaven.com/assets"):
        return httpx.Response(
            200,
            json={
                "wooden_chair": {
                    "name": "Wooden Chair",
                    "tags": ["chair", "wood"],
                    "categories": ["furniture"],
                },
                "stone_wall": {
                    "name": "Stone Wall",
                    "tags": ["wall"],
                    "categories": ["architecture"],
                },
            },
        )
    if url.startswith("https://api.sketchfab.com/v3/search"):
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "uid": "sketchfab_monitor",
                        "name": "Sketchfab Monitor",
                        "likeCount": 999,
                        "viewerUrl": "https://sketchfab.com/3d-models/sketchfab_monitor",
                        "license": {
                            "slug": "cc0",
                            "url": "https://creativecommons.org/publicdomain/zero/1.0/",
                        },
                        "user": {"displayName": "Sketchfab Author"},
                    }
                ]
            },
        )
    if url == "https://api.polyhaven.com/info/wooden_chair":
        return httpx.Response(200, json={"name": "Wooden Chair", "authors": "Poly Haven"})
    if url == "https://api.polyhaven.com/files/wooden_chair":
        return httpx.Response(
            200,
            json={
                "glb": {
                    "2k": {
                        "url": "https://cdn.example/wooden_chair.glb",
                    },
                    "textures": {
                        "url": "https://cdn.example/wooden_chair_albedo.jpg",
                    },
                }
            },
        )
    if url == "https://cdn.example/wooden_chair.glb":
        return httpx.Response(200, content=b"glb-data")
    if url == "https://cdn.example/wooden_chair_albedo.jpg":
        return httpx.Response(200, content=b"jpg-data")
    return httpx.Response(404, json={"detail": url})


@pytest.mark.asyncio
async def test_external_asset_registry_default_cache_root_uses_project_named_folder():
    registry = ExternalAssetRegistry()
    try:
        assert registry.cache_root.name == "external_assets"
        assert registry.cache_root.parent.name == ".omniverse-kit-mcp"
    finally:
        await registry.close()


@pytest.mark.asyncio
async def test_external_asset_search_polyhaven_normalizes_candidates(tmp_path: Path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_external_transport)
    ) as http_client:
        registry = ExternalAssetRegistry(cache_root=tmp_path, http_client=http_client)
        module = AssetModule(
            _ExplodingClient(), catalog_dir=REAL_CATALOG_DIR, external_assets=registry
        )
        result = await module.external_search(
            _meta(), query="wood chair", providers=["polyhaven"], limit=5
        )

    assert result.ok, result.message
    assert result.data["provider_status"] == {"polyhaven": "ok"}
    assert result.data["candidates"][0]["provider"] == "polyhaven"
    assert result.data["candidates"][0]["asset_id"] == "wooden_chair"
    assert result.data["candidates"][0]["license"] == "CC0"


@pytest.mark.asyncio
async def test_external_asset_search_default_order_prefers_polyhaven(tmp_path: Path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_external_transport)
    ) as http_client:
        registry = ExternalAssetRegistry(
            cache_root=tmp_path,
            http_client=http_client,
            sketchfab_token="test-token",
        )
        module = AssetModule(
            _ExplodingClient(), catalog_dir=REAL_CATALOG_DIR, external_assets=registry
        )
        result = await module.external_search(_meta(), query="wood chair", limit=5)

    assert result.ok, result.message
    assert result.data["provider_status"] == {
        "polyhaven": "ok",
        "sketchfab": "ok",
    }
    assert result.data["candidates"][0]["provider"] == "polyhaven"


@pytest.mark.asyncio
async def test_external_asset_download_polyhaven_writes_manifest(tmp_path: Path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_external_transport)
    ) as http_client:
        registry = ExternalAssetRegistry(cache_root=tmp_path, http_client=http_client)
        module = AssetModule(
            _ExplodingClient(), catalog_dir=REAL_CATALOG_DIR, external_assets=registry
        )
        result = await module.external_download(
            _meta(), provider="polyhaven", asset_id="wooden_chair"
        )

    assert result.ok, result.message
    manifest_path = Path(result.data["manifest_path"])
    assert manifest_path.is_file()
    assert result.data["chosen_format"] == "glb"
    assert Path(result.data["primary_file"]).read_bytes() == b"glb-data"
    assert len(result.data["files"]) == 2


@pytest.mark.asyncio
async def test_external_asset_search_sketchfab_requires_token(tmp_path: Path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_external_transport)
    ) as http_client:
        registry = ExternalAssetRegistry(cache_root=tmp_path, http_client=http_client)
        module = AssetModule(
            _ExplodingClient(), catalog_dir=REAL_CATALOG_DIR, external_assets=registry
        )
        result = await module.external_search(
            _meta(), query="chair", providers=["sketchfab"], limit=5
        )

    assert result.ok
    assert result.data["provider_status"] == {"sketchfab": "disabled_missing_token"}
    assert result.data["candidates"] == []


@pytest.mark.asyncio
async def test_external_asset_convert_updates_manifest(tmp_path: Path):
    from tests.conftest import MockIsaacRestClient

    source = tmp_path / "polyhaven" / "asset-abc" / "source.glb"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"glb")
    manifest = source.parent / "manifest.json"
    manifest.write_text(
        """
{
  "schema_version": 1,
  "provider": "polyhaven",
  "asset_id": "asset",
  "name": "Asset",
  "source_url": "https://example/asset",
  "author": "Poly Haven",
  "license": "CC0",
  "license_url": "https://polyhaven.com/license",
  "cache_dir": "__CACHE_DIR__",
  "primary_file": "__SOURCE__",
  "chosen_format": "glb",
  "files": [],
  "conversion": {"status": "not_started"}
}
""".replace("__CACHE_DIR__", str(source.parent).replace("\\", "\\\\")).replace(
            "__SOURCE__", str(source).replace("\\", "\\\\")
        ),
        encoding="utf-8",
    )

    client = MockIsaacRestClient()
    registry = ExternalAssetRegistry(cache_root=tmp_path)
    module = AssetModule(client, catalog_dir=REAL_CATALOG_DIR, external_assets=registry)
    result = await module.external_convert(_meta(), manifest_path=str(manifest))

    assert result.ok, result.message
    assert result.data["conversion"]["status"] == "converted"
    assert result.data["converted_path"].endswith("asset.usd")
    assert client.calls[-1][0] == "external_asset_convert"
    assert client.calls[-1][1]["input_path"] == str(source)


@pytest.mark.asyncio
async def test_external_asset_convert_rejects_manifest_outside_cache(tmp_path: Path):
    from tests.conftest import MockIsaacRestClient

    outside = tmp_path.parent / "manifest.json"
    outside.write_text("{}", encoding="utf-8")
    registry = ExternalAssetRegistry(cache_root=tmp_path)
    module = AssetModule(
        MockIsaacRestClient(), catalog_dir=REAL_CATALOG_DIR, external_assets=registry
    )

    result = await module.external_convert(_meta(), manifest_path=str(outside))

    assert not result.ok
    assert result.error_code == "EXTERNAL_ASSET_CONVERT_ERROR"
    assert "outside external asset cache" in (result.message or "")


@pytest.mark.asyncio
async def test_external_asset_converter_rest_rejects_paths_outside_cache(tmp_path: Path):
    from omni.mycompany.validation_api.services.asset_service import AssetService

    source = tmp_path / "source.glb"
    source.write_bytes(b"glb")
    output = tmp_path / "source.usd"

    with pytest.raises(ValueError, match="input_path must be inside"):
        await AssetService().convert_external_asset(
            {
                "input_path": str(source),
                "output_path": str(output),
                "output_format": "usd",
            }
        )


@pytest.mark.asyncio
async def test_external_asset_converter_rest_keeps_output_in_asset_folder(tmp_path: Path):
    from omni.mycompany.validation_api.services.asset_service import AssetService

    asset_dir = tmp_path / ".omniverse-kit-mcp" / "external_assets" / "polyhaven" / "asset-abc"
    asset_dir.mkdir(parents=True)
    source = asset_dir / "source.glb"
    source.write_bytes(b"glb")
    output = asset_dir.parent / "source.usd"

    with pytest.raises(ValueError, match="source asset cache folder"):
        await AssetService().convert_external_asset(
            {
                "input_path": str(source),
                "output_path": str(output),
                "output_format": "usd",
            }
        )
