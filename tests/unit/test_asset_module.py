"""Unit tests for AssetModule — catalog listing (Phase B+) + offline search."""

from __future__ import annotations

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
