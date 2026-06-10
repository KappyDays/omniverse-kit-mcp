"""Unit tests for ProcessModule launch-command assembly / config."""

from __future__ import annotations

from omniverse_kit_mcp.config import IsaacSimProcessConfig


def test_extra_ext_folders_default_empty():
    cfg = IsaacSimProcessConfig()
    assert cfg.extra_ext_folders == ()


def test_extra_ext_folders_from_value():
    cfg = IsaacSimProcessConfig(extra_ext_folders=("C:/x/custom_exts",))
    assert cfg.extra_ext_folders == ("C:/x/custom_exts",)
