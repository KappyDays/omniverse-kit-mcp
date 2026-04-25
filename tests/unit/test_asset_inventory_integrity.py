"""Asset inventory markdown invariants for isaac_course/docs/assets/*.md.

Format-only checks (no network). The slow URL-validity check lives in
`scripts/diff_asset_inventory.py` (run manually or via /asset-inventory-sync skill).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ASSETS_DIR = Path(__file__).resolve().parents[2] / "isaac_course" / "docs" / "assets"
INVENTORY_INDEX = Path(__file__).resolve().parents[2] / "isaac_course" / "docs" / "asset_inventory.md"

PREFIX_DECL_RE = re.compile(r"^`(\$\w+)`\s*=\s*`(https?://[^`]+)`", re.MULTILINE)
ROOT_DECL_RE = re.compile(r"^루트:\s*`(\$\w+/[^`]+?)/?`", re.MULTILINE)


@pytest.fixture(scope="module")
def sub_md_files() -> list[Path]:
    return sorted(ASSETS_DIR.glob("*.md"))


def test_assets_dir_exists():
    assert ASSETS_DIR.is_dir(), f"missing: {ASSETS_DIR}"


def test_index_exists():
    assert INVENTORY_INDEX.is_file(), f"missing index: {INVENTORY_INDEX}"


def test_each_sub_md_declares_prefix(sub_md_files):
    """Every sub-md must declare $ISAAC and/or $SIM prefix."""
    offenders = []
    for md in sub_md_files:
        text = md.read_text(encoding="utf-8")
        prefixes = dict(PREFIX_DECL_RE.findall(text))
        if not prefixes:
            offenders.append(md.name)
    assert not offenders, f"sub-md files missing prefix declaration: {offenders}"


def test_index_lists_all_sub_md(sub_md_files):
    """Index file must reference every sub-md by filename."""
    index_text = INVENTORY_INDEX.read_text(encoding="utf-8")
    missing = [md.name for md in sub_md_files if md.name not in index_text]
    assert not missing, f"sub-md files not referenced in index: {missing}"


def test_prefix_url_uses_5_1_or_simready(sub_md_files):
    """Prefix URLs must point to Isaac/5.1 or simready_content (current version baseline)."""
    offenders = []
    for md in sub_md_files:
        text = md.read_text(encoding="utf-8")
        for var, url in PREFIX_DECL_RE.findall(text):
            if "Isaac/5.1" not in url and "simready_content" not in url:
                offenders.append(f"{md.name}: {var}={url}")
    assert not offenders, (
        f"prefix URL must contain 'Isaac/5.1' or 'simready_content': {offenders}"
    )


def test_no_file_protocol_urls(sub_md_files):
    """`file://` URLs are not allowed — Isaac Sim load fails on file:// for S3 assets."""
    offenders = []
    for md in sub_md_files:
        text = md.read_text(encoding="utf-8")
        if "file://" in text:
            offenders.append(md.name)
    assert not offenders, f"file:// found (use full HTTPS S3 URL): {offenders}"


def test_root_declaration_uses_known_prefix(sub_md_files):
    """Each `루트:` declaration must use a prefix variable declared in the same file."""
    offenders = []
    for md in sub_md_files:
        text = md.read_text(encoding="utf-8")
        declared = set(PREFIX_DECL_RE.findall(text))
        declared_vars = {var for var, _ in declared} if declared else set()
        for root_path in ROOT_DECL_RE.findall(text):
            var = root_path.split("/", 1)[0]
            if var not in declared_vars:
                offenders.append(f"{md.name}: 루트 uses {var} but not declared")
    assert not offenders, str(offenders)
