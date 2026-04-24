"""Unit tests for CatalogModule — local queries over extensions.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from isaacsim_mcp.modules.base import make_meta
from isaacsim_mcp.modules.catalog_module import CatalogModule
from isaacsim_mcp.types.common import ModuleName, OperationMeta


@pytest.fixture
def catalog_path(tmp_path: Path) -> Path:
    """Minimal catalog fixture with three ext entries covering match cases."""
    data = {
        "schema_version": 2,
        "extensions": [
            {
                "name": "isaacsim.robot.manipulators",
                "title": "Isaac Sim Robot Manipulators",
                "summary": "로봇 조작기 기본 기능",
                "category": "Robotics",
                "apps": {"isaacsim": {"version": "5.1"}},
                "keywords": ["robot", "manipulator"],
                "raw_description": "Manipulator primitives",
                "mcp_research_hint": "grip 제어 래핑 후보",
                "key_symbols": [{"name": "SingleManipulator", "kind": "class", "desc": ""}],
                "enrichment_status": "enriched",
            },
            {
                "name": "omni.genproc.core",
                "title": "General Proceduralism Core",
                "summary": "절차적 콘텐츠 생성 core",
                "category": "Procedural Generation",
                "apps": {"usd_composer": {"version": "110.0"}, "isaacsim": {"version": "107.3"}},
                "keywords": ["genproc"],
                "raw_description": "Procedural graph nodes",
                "mcp_research_hint": "terrain 생성",
                "key_symbols": [],
                "enrichment_status": "enriched",
            },
            {
                "name": "omni.light_rigs",
                "title": "Light Rigs",
                "summary": "조명 rig 프리셋",
                "category": "Lighting Rigs",
                "apps": {"usd_composer": {"version": "106.3"}},
                "keywords": ["lighting"],
                "raw_description": "Provides lighting rig presets",
                "mcp_research_hint": "studio lighting 프리셋",
                "key_symbols": [],
                "enrichment_status": "enriched",
            },
        ],
    }
    path = tmp_path / "extensions.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def meta() -> OperationMeta:
    return make_meta(ModuleName.EXTENSION)


@pytest.mark.asyncio
async def test_search_by_keyword_in_name(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="manipulator")
    assert result.ok, f"result not ok: {result.error}"
    assert len(result.data) == 1
    assert result.data[0]["name"] == "isaacsim.robot.manipulators"


@pytest.mark.asyncio
async def test_search_by_keyword_in_summary(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="절차적")
    assert result.ok
    assert len(result.data) == 1
    assert result.data[0]["name"] == "omni.genproc.core"


@pytest.mark.asyncio
async def test_search_by_keyword_in_mcp_research_hint(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="studio lighting")
    assert result.ok
    assert len(result.data) == 1
    assert result.data[0]["name"] == "omni.light_rigs"


@pytest.mark.asyncio
async def test_search_filter_by_app(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="", app="usd_composer")
    assert result.ok
    names = {e["name"] for e in result.data}
    assert names == {"omni.genproc.core", "omni.light_rigs"}


@pytest.mark.asyncio
async def test_search_filter_by_isaacsim_only(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="", app="isaacsim")
    assert result.ok
    names = {e["name"] for e in result.data}
    assert names == {"isaacsim.robot.manipulators", "omni.genproc.core"}


@pytest.mark.asyncio
async def test_search_filter_by_category(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="", category="Robotics")
    assert result.ok
    assert len(result.data) == 1
    assert result.data[0]["name"] == "isaacsim.robot.manipulators"


@pytest.mark.asyncio
async def test_search_limit_applied(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="", limit=1)
    assert result.ok
    assert len(result.data) == 1


@pytest.mark.asyncio
async def test_search_no_match_returns_empty(catalog_path: Path, meta: OperationMeta) -> None:
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="nonexistent_xyzzy")
    assert result.ok
    assert result.data == []


@pytest.mark.asyncio
async def test_search_response_fields(catalog_path: Path, meta: OperationMeta) -> None:
    """Returned entries must include name, title, summary, category, apps, key_symbols, mcp_research_hint."""
    module = CatalogModule(catalog_path)
    result = await module.search(meta, keyword="manipulator")
    assert result.ok
    entry = result.data[0]
    assert set(entry.keys()) >= {
        "name", "title", "summary", "category", "apps",
        "key_symbols", "mcp_research_hint",
    }
    assert entry["apps"] == ["isaacsim"]


@pytest.mark.asyncio
async def test_catalog_cached_after_first_load(catalog_path: Path, meta: OperationMeta) -> None:
    """Second search should not re-read the file — cache once."""
    module = CatalogModule(catalog_path)
    await module.search(meta, keyword="")
    # Delete file to prove cache is used
    catalog_path.unlink()
    result = await module.search(meta, keyword="manipulator")
    assert result.ok
    assert len(result.data) == 1
