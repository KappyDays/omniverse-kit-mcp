"""scripts/render_catalog_md.py 단위 테스트."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import render_catalog_md as render


@pytest.fixture
def sample_catalog(tmp_path: Path) -> Path:
    data = {
        "metadata": {
            "generated_at": "2026-04-17T20:00:00Z",
            "generator_version": "harvest_extension_metadata.py@1.0",
            "isaac_sim_root": "C:/fake/root",
            "isaac_sim_version": "6.0.0-rc.59",
            "kit_version": "110.1.1",
            "total_extensions": 3,
            "source_counts": {"exts": 2, "extscache": 0, "extsDeprecated": 1},
            "last_enriched_at": "2026-04-18T09:30:00Z",
        },
        "extensions": [
            {
                "name": "isaacsim.core.api",
                "version": "4.8.0",
                "source_dir": "exts",
                "path": "exts/isaacsim.core.api",
                "raw_dirname": "isaacsim.core.api",
                "category": "Core Foundation",
                "title": "Isaac Sim Core API",
                "summary": "Isaac Sim 의 메인 SDK 진입점 — 시뮬레이션 상태 관리.",
                "public_modules": ["isaacsim.core.api"],
                "key_symbols": [
                    {"name": "World", "kind": "class", "desc": "시뮬레이션 세계 컨테이너"},
                ],
                "dependencies": ["isaacsim.core.prims"],
                "keywords": ["isaac", "core"],
                "raw_description": "Core SDK",
                "readme_excerpt": None,
                "testbed_refs": ["testbed-snapshot/02-extension-catalog.md#core-foundation-11-extensions"],
                "mcp_extension_idea": "sim_world_create(physics_dt) — World 초기화",
                "enrichment_status": "enriched",
                "skipped_reason": None,
                "harvested_at": "2026-04-17T20:00:00Z",
                "enriched_at": "2026-04-18T09:30:00Z",
            },
            {
                "name": "isaacsim.robot.manipulators",
                "version": "3.3.6",
                "source_dir": "exts",
                "path": "exts/isaacsim.robot.manipulators",
                "raw_dirname": "isaacsim.robot.manipulators",
                "category": "Robot & Manipulation",
                "title": None,
                "summary": "매니퓰레이터 제어 유틸리티.",
                "public_modules": [],
                "key_symbols": [],
                "dependencies": [],
                "keywords": [],
                "raw_description": "",
                "readme_excerpt": None,
                "testbed_refs": [],
                "mcp_extension_idea": None,
                "enrichment_status": "skipped",
                "skipped_reason": "metadata_insufficient",
                "harvested_at": "2026-04-17T20:00:00Z",
                "enriched_at": None,
            },
            {
                "name": "omni.isaac.franka",
                "version": "1.0.0",
                "source_dir": "extsDeprecated",
                "path": "extsDeprecated/omni.isaac.franka",
                "raw_dirname": "omni.isaac.franka",
                "category": "Deprecated (omni.isaac.*)",
                "title": "Franka (deprecated)",
                "summary": "Franka 로봇 예제 — 4.x 레거시.",
                "public_modules": ["omni.isaac.franka"],
                "key_symbols": [],
                "dependencies": [],
                "keywords": [],
                "raw_description": "Deprecated",
                "readme_excerpt": None,
                "testbed_refs": [],
                "mcp_extension_idea": "N/A — deprecated, use isaacsim.robot.manipulators.examples",
                "enrichment_status": "enriched",
                "skipped_reason": None,
                "harvested_at": "2026-04-17T20:00:00Z",
                "enriched_at": "2026-04-18T09:30:00Z",
            },
        ],
    }
    p = tmp_path / "extensions.json"
    p.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return p


def test_render_produces_markdown(sample_catalog: Path, tmp_path: Path) -> None:
    output = tmp_path / "catalog.md"
    render.render(catalog_json=sample_catalog, output=output)

    content = output.read_text(encoding="utf-8")
    assert content.startswith("# Isaac Sim 6.0.0 Extensions — Full Catalog")
    assert "직접 편집 금지" in content
    assert "Core Foundation" in content
    assert "Robot & Manipulation" in content
    assert "Deprecated (omni.isaac.*)" in content
    assert "### isaacsim.core.api" in content
    assert "### omni.isaac.franka" in content
    assert "skipped" in content.lower()


def test_render_entry_count_matches_json(sample_catalog: Path, tmp_path: Path) -> None:
    output = tmp_path / "catalog.md"
    render.render(catalog_json=sample_catalog, output=output)

    content = output.read_text(encoding="utf-8")
    entry_headers = [line for line in content.splitlines() if line.startswith("### ")]
    assert len(entry_headers) == 3


def test_render_is_idempotent(sample_catalog: Path, tmp_path: Path) -> None:
    out1 = tmp_path / "c1.md"
    out2 = tmp_path / "c2.md"
    render.render(catalog_json=sample_catalog, output=out1)
    render.render(catalog_json=sample_catalog, output=out2)
    assert out1.read_bytes() == out2.read_bytes()


def test_render_skipped_entry_has_status_note(sample_catalog: Path, tmp_path: Path) -> None:
    output = tmp_path / "catalog.md"
    render.render(catalog_json=sample_catalog, output=output)
    content = output.read_text(encoding="utf-8")
    idx = content.index("### isaacsim.robot.manipulators")
    section = content[idx:idx+500]
    assert "상태" in section or "skipped" in section
    assert "metadata_insufficient" in section


def test_render_writes_derivative_banner(sample_catalog: Path, tmp_path: Path) -> None:
    output = tmp_path / "catalog.md"
    render.render(catalog_json=sample_catalog, output=output)
    content = output.read_text(encoding="utf-8")
    assert "권위자료" in content
    assert "render_catalog_md.py" in content
