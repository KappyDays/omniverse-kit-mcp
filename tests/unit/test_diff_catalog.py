"""Smoke tests for scripts/diff_catalog.py — ensures the diff tool imports and
runs without crashing. Invoked by developers after Kit/app upgrades."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


@pytest.mark.slow
def test_diff_catalog_importable_and_callable():
    """diff_app(app) returns the expected report shape for both configured apps."""
    from diff_catalog import diff_app
    for app in ("isaacsim", "usd_composer"):
        report = diff_app(app)
        assert report["app"] == app
        assert isinstance(report["current_total"], int)
        assert isinstance(report["fresh_total"], int)
        for key in ("added", "removed", "version_bumped", "category_changed"):
            assert isinstance(report[key], list)
