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

    def test_fallback_on_toml_decode_error(self, tmp_path: Path) -> None:
        """TOML 이중 선언 등 파싱 실패 시 raw 텍스트 우회로 Error 카테고리가 되지 않는다."""
        ext_dir = tmp_path / "omni.anim.broken-1.0.0"
        (ext_dir / "config").mkdir(parents=True)
        (ext_dir / "config" / "extension.toml").write_text(
            "[package]\nversion = \"1.0.0\"\ntitle = \"Broken TOML\"\ndescription = \"duplicate section test\"\n\n"
            "[package]\ndescription = \"duplicate — invalid TOML\"\n",
            encoding="utf-8",
        )
        entry = harvest.parse_single_extension(ext_dir, "extscache")
        assert entry["category"] != "Error"
        assert entry["version"] == "1.0.0"
        assert entry["title"] == "Broken TOML"
        assert entry["enrichment_status"] == "bootstrap"

    def test_fallback_extracts_dependencies(self, tmp_path: Path) -> None:
        """raw fallback이 [dependencies] 섹션도 올바르게 추출한다."""
        ext_dir = tmp_path / "omni.broken.deps-2.0.0"
        (ext_dir / "config").mkdir(parents=True)
        (ext_dir / "config" / "extension.toml").write_text(
            "[package]\nversion = \"2.0.0\"\ntitle = \"Deps Test\"\n\n"
            "[package]\ntitle = \"duplicate\"\n\n"
            "[dependencies]\n\"omni.kit.core\" = {}\n\"omni.physx\" = {}\n",
            encoding="utf-8",
        )
        entry = harvest.parse_single_extension(ext_dir, "extscache")
        assert "omni.kit.core" in entry["dependencies"]
        assert "omni.physx" in entry["dependencies"]


@pytest.fixture
def fake_isaac_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """최소 isaac-sim 디렉토리 구조 (3 source + 각 2 ext)."""
    root = tmp_path / "isaac_sim"
    for source_dir, exts in {
        "exts": ["isaacsim.core.api", "isaacsim.robot.manipulators"],
        "extscache": [
            "omni.physx-107.3.26+107.3.3.wx64.r.cp311.u353",
            "omni.anim.people-0.7.9+107.3.3",
        ],
        "extsDeprecated": ["omni.isaac.franka", "omni.isaac.cortex"],
    }.items():
        for ext_name in exts:
            ext_dir = root / source_dir / ext_name
            (ext_dir / "config").mkdir(parents=True)
            (ext_dir / "config" / "extension.toml").write_text(
                f'''
[package]
version = "1.0.0"
title = "{ext_name}"
description = "Fake description for {ext_name}."

[dependencies]
''',
                encoding="utf-8",
            )
    return root


class TestBootstrap:
    def test_produces_all_entries(
        self, fake_isaac_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(harvest, "ISAAC_SIM_ROOT", fake_isaac_root)
        catalog_json = tmp_path / "extensions.json"
        progress_json = tmp_path / "harvest-progress.json"
        monkeypatch.setattr(harvest, "CATALOG_JSON", catalog_json)
        monkeypatch.setattr(harvest, "PROGRESS_JSON", progress_json)

        harvest.bootstrap(resume=False)

        data = json.loads(catalog_json.read_text(encoding="utf-8"))
        assert data["metadata"]["total_extensions"] == 6
        assert data["metadata"]["source_counts"] == {
            "exts": 2, "extscache": 2, "extsDeprecated": 2, "extsInternal": 0
        }
        names = sorted(e["name"] for e in data["extensions"])
        assert names == sorted([
            "isaacsim.core.api",
            "isaacsim.robot.manipulators",
            "omni.physx",
            "omni.anim.people",
            "omni.isaac.franka",
            "omni.isaac.cortex",
        ])
        assert [e["name"] for e in data["extensions"]] == sorted(names)
        cortex_entry = next(e for e in data["extensions"] if e["name"] == "omni.isaac.cortex")
        assert cortex_entry["category"] == "Deprecated (omni.isaac.*)"

    def test_resume_preserves_existing_entries(
        self, fake_isaac_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(harvest, "ISAAC_SIM_ROOT", fake_isaac_root)
        catalog_json = tmp_path / "extensions.json"
        progress_json = tmp_path / "harvest-progress.json"
        monkeypatch.setattr(harvest, "CATALOG_JSON", catalog_json)
        monkeypatch.setattr(harvest, "PROGRESS_JSON", progress_json)

        harvest.bootstrap(resume=False)
        first = json.loads(catalog_json.read_text(encoding="utf-8"))
        for e in first["extensions"]:
            if e["name"] == "isaacsim.core.api":
                e["mcp_extension_idea"] = "manual-test-marker"
                e["enrichment_status"] = "enriched"
        catalog_json.write_text(
            json.dumps(first, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

        harvest.bootstrap(resume=True)
        second = json.loads(catalog_json.read_text(encoding="utf-8"))
        api_entry = next(e for e in second["extensions"] if e["name"] == "isaacsim.core.api")
        assert api_entry["mcp_extension_idea"] == "manual-test-marker"
        assert api_entry["enrichment_status"] == "enriched"

    def test_progress_marked_complete(
        self, fake_isaac_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(harvest, "ISAAC_SIM_ROOT", fake_isaac_root)
        catalog_json = tmp_path / "extensions.json"
        progress_json = tmp_path / "harvest-progress.json"
        monkeypatch.setattr(harvest, "CATALOG_JSON", catalog_json)
        monkeypatch.setattr(harvest, "PROGRESS_JSON", progress_json)

        harvest.bootstrap(resume=False)

        prog = json.loads(progress_json.read_text(encoding="utf-8"))
        assert prog["phases"]["bootstrap"]["status"] == "complete"
        assert prog["phases"]["bootstrap"]["processed"] == 6
        assert prog["total_extensions"] == 6
