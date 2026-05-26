"""Author the lift-rig scene into a USD stage. Idempotent. pxr lazy-imported.

Physics scene + ground + a 2-DOF lift rig (static base/column; rigid carriage on a
prismatic Z lift joint with a linear DriveAPI; rigid fork on a revolute Y tilt joint
with an angular DriveAPI) + a real pallet+box payload (RigidBody + MassAPI). Works
headless (usd-core) — PhysX-only schemas are not authored here (runtime adds them).
The rig geometry is an authored mechanism (R1 NOTE in rig_make.md); payload is real.
"""
from __future__ import annotations

from . import config

_MANAGED = (config.PHYSICS_SCENE, config.GROUND, config.RIG_ROOT, config.PAYLOAD_ROOT)


def clear(stage) -> None:
    for path in _MANAGED:
        if stage.GetPrimAtPath(path):
            stage.RemovePrim(path)


def _box(stage, path, size, translate):
    from pxr import UsdGeom, Gf

    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)  # unit cube; scale to full dimensions
    m = Gf.Matrix4d(1.0)
    m.SetScale(Gf.Vec3d(*size))
    m.SetTranslateOnly(Gf.Vec3d(*translate))
    cube.AddTransformOp().Set(m)
    return cube


def _referenced_payload(stage, path, url, translate, mass):
    from pxr import UsdGeom, UsdPhysics, Gf

    parent = UsdGeom.Xform.Define(stage, path)
    parent.AddTranslateOp().Set(Gf.Vec3d(*translate))
    UsdPhysics.RigidBodyAPI.Apply(parent.GetPrim())
    UsdPhysics.MassAPI.Apply(parent.GetPrim()).CreateMassAttr(mass)
    model = UsdGeom.Xform.Define(stage, path + "/Model")
    model.GetPrim().GetReferences().AddReference(url)
    return parent


def build(stage) -> dict:
    from pxr import UsdGeom, UsdPhysics, Gf

    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, config.WORLD)
    stage.SetDefaultPrim(world.GetPrim())

    clear(stage)

    scene = UsdPhysics.Scene.Define(stage, config.PHYSICS_SCENE)
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr(config.GRAVITY)

    ground = _box(stage, config.GROUND, config.GROUND_SIZE, (0.0, 0.0, -config.GROUND_SIZE[2] * 0.5))
    UsdPhysics.CollisionAPI.Apply(ground.GetPrim())

    UsdGeom.Xform.Define(stage, config.RIG_ROOT)

    base = _box(stage, config.BASE, config.BASE_SIZE, (0.0, 0.0, config.BASE_SIZE[2] * 0.5))
    UsdPhysics.CollisionAPI.Apply(base.GetPrim())

    column = _box(stage, config.COLUMN, config.COLUMN_SIZE, (0.0, 0.0, config.COLUMN_Z))
    UsdPhysics.CollisionAPI.Apply(column.GetPrim())

    carriage = _box(stage, config.CARRIAGE, config.CARRIAGE_SIZE, (config.CARRIAGE_X, 0.0, config.CARRIAGE_Z0))
    UsdPhysics.RigidBodyAPI.Apply(carriage.GetPrim())
    UsdPhysics.CollisionAPI.Apply(carriage.GetPrim())
    UsdPhysics.MassAPI.Apply(carriage.GetPrim()).CreateMassAttr(config.CARRIAGE_MASS)

    fork = _box(stage, config.FORK, config.FORK_SIZE, (config.CARRIAGE_X + config.FORK_X, 0.0, config.CARRIAGE_Z0))
    UsdPhysics.RigidBodyAPI.Apply(fork.GetPrim())
    UsdPhysics.CollisionAPI.Apply(fork.GetPrim())
    UsdPhysics.MassAPI.Apply(fork.GetPrim()).CreateMassAttr(config.FORK_MASS)

    # Prismatic lift: Column -> Carriage along Z.
    lift = UsdPhysics.PrismaticJoint.Define(stage, config.LIFT_JOINT)
    lift.CreateBody0Rel().SetTargets([config.COLUMN])
    lift.CreateBody1Rel().SetTargets([config.CARRIAGE])
    lift.CreateAxisAttr("Z")
    lift.CreateLowerLimitAttr(config.LIFT_LOWER)
    lift.CreateUpperLimitAttr(config.LIFT_UPPER)
    ld = UsdPhysics.DriveAPI.Apply(lift.GetPrim(), "linear")
    ld.CreateTargetPositionAttr(0.0)
    ld.CreateStiffnessAttr(config.LIFT_STIFFNESS)
    ld.CreateDampingAttr(config.LIFT_DAMPING)
    ld.CreateMaxForceAttr(config.LIFT_MAX_FORCE)

    # Revolute tilt: Carriage -> Fork about Y.
    tilt = UsdPhysics.RevoluteJoint.Define(stage, config.TILT_JOINT)
    tilt.CreateBody0Rel().SetTargets([config.CARRIAGE])
    tilt.CreateBody1Rel().SetTargets([config.FORK])
    tilt.CreateAxisAttr("Y")
    td = UsdPhysics.DriveAPI.Apply(tilt.GetPrim(), "angular")
    td.CreateTargetPositionAttr(0.0)
    td.CreateStiffnessAttr(config.TILT_STIFFNESS)
    td.CreateDampingAttr(config.TILT_DAMPING)

    # Real payload on the fork.
    UsdGeom.Xform.Define(stage, config.PAYLOAD_ROOT)
    fork_top_z = config.CARRIAGE_Z0 + config.FORK_SIZE[2] * 0.5
    _referenced_payload(
        stage, config.PALLET, config.PAYLOAD_PALLET_URL,
        (config.CARRIAGE_X + config.FORK_X, 0.0, fork_top_z + 0.05), config.PALLET_MASS,
    )
    _referenced_payload(
        stage, config.BOX, config.PAYLOAD_BOX_URL,
        (config.CARRIAGE_X + config.FORK_X, 0.0, fork_top_z + 0.30), config.BOX_MASS,
    )

    return {
        "physics_scene": config.PHYSICS_SCENE,
        "joints": [config.LIFT_JOINT, config.TILT_JOINT],
        "rigid_bodies": [config.CARRIAGE, config.FORK, config.PALLET, config.BOX],
        "payload": [config.PALLET, config.BOX],
    }
