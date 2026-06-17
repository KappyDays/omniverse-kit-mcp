from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_robot_service_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "kkr-extensions"
        / "omni.mycompany.validation_api"
        / "omni"
        / "mycompany"
        / "validation_api"
        / "services"
        / "robot_service.py"
    )
    spec = importlib.util.spec_from_file_location("robot_service_static_joint_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_static_usd_dof_joint_type_accepts_movable_joint_variants():
    robot_service = _load_robot_service_module()

    assert robot_service._is_static_usd_dof_joint_type("RevoluteJoint")
    assert robot_service._is_static_usd_dof_joint_type("PhysicsRevoluteJoint")
    assert robot_service._is_static_usd_dof_joint_type("PrismaticJoint")
    assert robot_service._is_static_usd_dof_joint_type("PhysicsPrismaticJoint")
    assert not robot_service._is_static_usd_dof_joint_type("FixedJoint")
    assert not robot_service._is_static_usd_dof_joint_type("PhysicsFixedJoint")
    assert not robot_service._is_static_usd_dof_joint_type("Xform")
