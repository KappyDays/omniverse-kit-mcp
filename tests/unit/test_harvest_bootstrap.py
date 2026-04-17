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


class TestAssignCategory:
    def test_rule_zero_extsdeprecated_wins(self) -> None:
        assert harvest.assign_category("omni.isaac.core_archive", "exts") != "Deprecated (omni.isaac.*)"
        assert harvest.assign_category("omni.isaac.franka", "extsDeprecated") == "Deprecated (omni.isaac.*)"
        assert harvest.assign_category("isaacsim.replicator.scene_blox", "extsDeprecated") == "Deprecated (omni.isaac.*)"

    @pytest.mark.parametrize(
        "name,expected",
        [
            # Core Foundation
            ("isaacsim.core.api", "Core Foundation"),
            ("isaacsim.core.prims", "Core Foundation"),
            ("isaacsim.core.experimental.prims", "Core Foundation"),
            ("isaacsim.simulation_app", "Core Foundation"),
            ("isaacsim.storage.native", "Core Foundation"),
            ("omni.kit.loop-isaac", "Core Foundation"),
            # Physics & PhysX
            ("omni.physx", "Physics & PhysX"),
            ("omni.physx.cct", "Physics & PhysX"),
            ("omni.physx.vehicle", "Physics & PhysX"),
            ("omni.physics.physx", "Physics & PhysX"),
            ("omni.usdphysics", "Physics & PhysX"),
            ("omni.kit.property.physx", "Physics & PhysX"),
            # Cortex (Robot 보다 먼저)
            ("isaacsim.cortex.framework", "Cortex & Behavior"),
            ("isaacsim.cortex.behaviors", "Cortex & Behavior"),
            # Robot
            ("isaacsim.robot.manipulators", "Robot & Manipulation"),
            ("isaacsim.robot_motion.motion_generation", "Robot & Manipulation"),
            ("isaacsim.robot_setup.wizard", "Robot & Manipulation"),
            ("isaacsim.anim.robot", "Robot & Manipulation"),
            # Sensors
            ("isaacsim.sensors.camera", "Sensors"),
            ("isaacsim.sensors.rtx", "Sensors"),
            ("omni.sensors.nv.lidar", "Sensors"),
            # Animation
            ("omni.anim.people", "Animation"),
            ("omni.anim.graph.core", "Animation"),
            ("omni.usd.schema.anim", "Animation"),
            # Replicator
            ("omni.replicator.core", "Replicator & SDG"),
            ("isaacsim.replicator.behavior", "Replicator & SDG"),
            # Asset Import/Export
            ("isaacsim.asset.importer.urdf", "Asset Import/Export"),
            ("omni.kit.asset_converter", "Asset Import/Export"),
            ("omni.importer.onshape", "Asset Import/Export"),
            ("omni.kit.converter.cad", "Asset Import/Export"),
            # OmniGraph
            ("omni.graph.core", "OmniGraph"),
            ("omni.graph.action", "OmniGraph"),
            ("omni.kit.graph.editor.core", "OmniGraph"),
            # ROS2
            ("isaacsim.ros2.bridge", "ROS2"),
            ("isaacsim.ros2.urdf", "ROS2"),
            # XR
            ("omni.kit.xr.core", "XR (VR/AR)"),
            ("isaacsim.xr.openxr", "XR (VR/AR)"),
            # Kit Viewport & Manipulator
            ("omni.kit.viewport.window", "Kit Viewport & Manipulator"),
            ("omni.kit.manipulator.prim", "Kit Viewport & Manipulator"),
            ("omni.kit.viewport_widgets_manager", "Kit Viewport & Manipulator"),
            # Kit UI & Widget
            ("omni.kit.widget.prompt", "Kit UI & Widget"),
            ("omni.kit.window.property", "Kit UI & Widget"),
            ("omni.ui", "Kit UI & Widget"),
            ("omni.kit.menu.utils", "Kit UI & Widget"),
            ("isaacsim.gui.components", "Kit UI & Widget"),
            ("isaacsim.app.about", "Kit UI & Widget"),
            # Test & Examples
            ("isaacsim.examples.interactive", "Test & Examples"),
            ("isaacsim.benchmark.services", "Test & Examples"),
            ("omni.physx.tests", "Test & Examples"),
            ("omni.kit.test", "Test & Examples"),
            # Misc (기본)
            ("omni.warp", "Misc / Utilities"),
            ("omni.cuopt.examples", "Misc / Utilities"),
            ("omni.simready.explorer", "Misc / Utilities"),
            ("omni.pip.cloud", "Misc / Utilities"),
            ("omni.kvdb", "Misc / Utilities"),
        ],
    )
    def test_matches_domain_rules(self, name: str, expected: str) -> None:
        assert harvest.assign_category(name, source_dir_name="exts") == expected


@pytest.fixture
def sample_ext_dir(tmp_path: Path) -> Path:
    """최소 extension.toml 만 있는 가짜 extension 디렉토리."""
    ext = tmp_path / "isaacsim.robot.manipulators"
    (ext / "config").mkdir(parents=True)
    (ext / "config" / "extension.toml").write_text(
        """
[package]
version = "3.3.6"
category = "Robot"
title = "Isaac Sim Robot Manipulators"
description = "Manipulator utilities for Isaac Sim robots."
keywords = ["isaac", "robot", "manipulator"]

[dependencies]
"isaacsim.core.api" = {}
"omni.physx" = {}

[[python.module]]
name = "isaacsim.robot.manipulators"
""",
        encoding="utf-8",
    )
    return ext


@pytest.fixture
def sample_ext_dir_with_readme(tmp_path: Path) -> Path:
    ext = tmp_path / "omni.physx.demos-107.3.26+107.3.3.cp311.u353"
    (ext / "config").mkdir(parents=True)
    (ext / "config" / "extension.toml").write_text(
        """
[package]
version = "107.3.26"
title = "PhysX Demos"
description = ""
keywords = []
""",
        encoding="utf-8",
    )
    (ext / "docs").mkdir()
    (ext / "docs" / "README.md").write_text(
        "# PhysX Demos\n\nThis is the first paragraph that describes what the demos contain.\n\nAnother paragraph.",
        encoding="utf-8",
    )
    return ext


class TestParseSingleExtension:
    def test_basic_fields(self, sample_ext_dir: Path) -> None:
        entry = harvest.parse_single_extension(sample_ext_dir, "exts")
        assert entry["name"] == "isaacsim.robot.manipulators"
        assert entry["version"] == "3.3.6"
        assert entry["source_dir"] == "exts"
        assert entry["raw_dirname"] == "isaacsim.robot.manipulators"
        assert entry["title"] == "Isaac Sim Robot Manipulators"
        assert entry["raw_description"] == "Manipulator utilities for Isaac Sim robots."
        assert entry["keywords"] == ["isaac", "robot", "manipulator"]
        assert entry["dependencies"] == ["isaacsim.core.api", "omni.physx"]
        assert entry["public_modules"] == ["isaacsim.robot.manipulators"]
        assert entry["category"] == "Robot & Manipulation"
        assert entry["enrichment_status"] == "bootstrap"
        assert entry["summary"]

    def test_strips_version_tag_in_name(self, sample_ext_dir_with_readme: Path) -> None:
        entry = harvest.parse_single_extension(sample_ext_dir_with_readme, "extscache")
        assert entry["name"] == "omni.physx.demos"
        assert entry["raw_dirname"] == "omni.physx.demos-107.3.26+107.3.3.cp311.u353"

    def test_readme_excerpt_used_when_description_empty(
        self, sample_ext_dir_with_readme: Path
    ) -> None:
        entry = harvest.parse_single_extension(sample_ext_dir_with_readme, "extscache")
        assert entry["readme_excerpt"] is not None
        assert "first paragraph" in entry["readme_excerpt"]
        assert "first paragraph" in entry["summary"]

    def test_missing_toml_raises(self, tmp_path: Path) -> None:
        ext = tmp_path / "no_toml"
        ext.mkdir()
        with pytest.raises(FileNotFoundError):
            harvest.parse_single_extension(ext, "exts")

    def test_path_field_posix_format(self, sample_ext_dir: Path) -> None:
        entry = harvest.parse_single_extension(sample_ext_dir, "exts")
        assert "/" in entry["path"] or len(entry["path"].split("/")) >= 2
        assert entry["path"].startswith("exts/")

    def test_extsdeprecated_forces_deprecated_category(self, sample_ext_dir: Path) -> None:
        entry = harvest.parse_single_extension(sample_ext_dir, "extsDeprecated")
        assert entry["category"] == "Deprecated (omni.isaac.*)"
