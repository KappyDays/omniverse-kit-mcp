"""scripts/sync_testbed_snapshot.py 단위 테스트."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import sync_testbed_snapshot as sync_mod


def test_readme_meta_contains_required_fields(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "file_a.md").write_text("A", encoding="utf-8")

    dst = tmp_path / "dst"

    sync_mod.sync(src=src, dst=dst)

    readme = dst / "README.md"
    assert readme.exists()
    content = readme.read_text(encoding="utf-8")
    assert "원본" in content
    assert "복사 일시" in content
    assert "파일 개수" in content
    assert "읽기 전용" in content


def test_sync_replaces_destination_completely(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "new.md").write_text("new", encoding="utf-8")

    dst = tmp_path / "dst"
    dst.mkdir()
    (dst / "stale.md").write_text("stale", encoding="utf-8")

    sync_mod.sync(src=src, dst=dst)

    assert (dst / "new.md").exists()
    assert not (dst / "stale.md").exists(), "기존 파일은 삭제되어야 함"


def test_sync_preserves_subdirectories(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "sub" / "deep.md").write_text("deep", encoding="utf-8")

    dst = tmp_path / "dst"

    sync_mod.sync(src=src, dst=dst)

    assert (dst / "sub" / "deep.md").read_text(encoding="utf-8") == "deep"
