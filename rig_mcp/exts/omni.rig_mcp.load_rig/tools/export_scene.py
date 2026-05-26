"""Headless build + export of the lift-rig scene (usd-core; no Kit runtime).

Run: .venv/Scripts/python.exe rig_mcp/exts/omni.rig_mcp.load_rig/tools/export_scene.py
"""
from __future__ import annotations

import pathlib
import sys

_EXT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EXT_ROOT))
sys.dont_write_bytecode = True

from pxr import Usd, UsdGeom, UsdPhysics  # noqa: E402

from omni.rig_mcp.load_rig import config, scene_builder  # noqa: E402


def _prim_paths(stage) -> set[str]:
    return {p.GetPath().pathString for p in stage.Traverse()}


def main() -> int:
    stage = Usd.Stage.CreateInMemory()
    info = scene_builder.build(stage)

    before = _prim_paths(stage)
    scene_builder.build(stage)
    after = _prim_paths(stage)
    assert before == after, f"not idempotent; diff={before ^ after}"

    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert stage.GetPrimAtPath(config.PHYSICS_SCENE).IsValid()

    # Prismatic lift joint with a linear drive.
    lift = stage.GetPrimAtPath(config.LIFT_JOINT)
    assert lift.IsA(UsdPhysics.PrismaticJoint), "LiftJoint not a PrismaticJoint"
    assert "PhysicsDriveAPI:linear" in lift.GetAppliedSchemas(), lift.GetAppliedSchemas()
    assert UsdPhysics.PrismaticJoint(lift).GetAxisAttr().Get() == "Z"

    # Revolute tilt joint with an angular drive.
    tilt = stage.GetPrimAtPath(config.TILT_JOINT)
    assert tilt.IsA(UsdPhysics.RevoluteJoint), "TiltJoint not a RevoluteJoint"
    assert "PhysicsDriveAPI:angular" in tilt.GetAppliedSchemas(), tilt.GetAppliedSchemas()

    # Rigid bodies + mass.
    for body in (config.CARRIAGE, config.FORK, config.PALLET, config.BOX):
        prim = stage.GetPrimAtPath(body)
        schemas = prim.GetAppliedSchemas()
        assert "PhysicsRigidBodyAPI" in schemas, (body, schemas)
        assert "PhysicsMassAPI" in schemas, (body, schemas)

    # Payload references real assets.
    for pay in config.PALLET, config.BOX:
        model = stage.GetPrimAtPath(pay + "/Model")
        assert model and model.GetReferences(), f"missing /Model reference under {pay}"

    out = _EXT_ROOT.parents[1] / "scenes" / "rig_scene.usd"
    out.parent.mkdir(parents=True, exist_ok=True)
    stage.GetRootLayer().Export(str(out))
    print(f"OK: physics scene + prismatic+revolute drives + {len(info['rigid_bodies'])} bodies, "
          f"idempotent -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
