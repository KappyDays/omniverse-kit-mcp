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
