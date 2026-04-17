"""scripts/harvest_extension_metadata.py 단위 테스트."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import harvest_extension_metadata as harvest


class TestStripVersionTag:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("isaacsim.core.api", "isaacsim.core.api"),
            ("omni.physx.demos-107.3.26+107.3.3.cp311.u353", "omni.physx.demos"),
            ("omni.kit.widget.prompt-1.0.7+69cbf6ad", "omni.kit.widget.prompt"),
            ("omni.anim.graph.core-107.3.4+107.3.3.wx64.r.cp311.u353", "omni.anim.graph.core"),
            ("carb.audio-0.1.0+69cbf6ad.wx64.r.cp311", "carb.audio"),
            ("isaacsim.anim.robot-0.0.15+107.3.3", "isaacsim.anim.robot"),
            ("omni.physx-107.3.26+107.3.3.wx64.r.cp311.u353", "omni.physx"),
            ("omni.kit.loop-isaac", "omni.kit.loop-isaac"),
        ],
    )
    def test_strips_known_suffixes(self, raw: str, expected: str) -> None:
        assert harvest.strip_version_tag(raw) == expected

    def test_preserves_name_without_version(self) -> None:
        assert harvest.strip_version_tag("isaacsim.storage.native") == "isaacsim.storage.native"
