"""Builds 4 conveyor belts in O shape + Franka + basket.

Uses pxr USD API directly (UsdGeom.Cube.Define / Xform.Define) for prim
creation -- omni.kit.commands.execute('CreatePrimWithDefaultXform') was
observed to silent-fail when the parent prim does not exist yet.
"""

from __future__ import annotations

import carb
import omni.kit.commands
import omni.usd
from pxr import Gf, Sdf, UsdGeom, UsdPhysics, UsdShade

# (path, position xyz, rotation_z_deg, velocity_dir for conveyor)
BELT_LAYOUT = [
    ("/World/Conveyors/Belt_N", (0.0, 1.3, 0.5), 0.0, (-1.0, 0.0, 0.0)),
    ("/World/Conveyors/Belt_W", (-1.3, 0.0, 0.5), 90.0, (0.0, -1.0, 0.0)),
    ("/World/Conveyors/Belt_S", (0.0, -1.3, 0.5), 180.0, (1.0, 0.0, 0.0)),
    ("/World/Conveyors/Belt_E", (1.3, 0.0, 0.5), 270.0, (0.0, 1.0, 0.0)),
]

FRANKA_USD = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd"
)

BASKET_PATH = "/World/Basket"
BASKET_POSITION = (0.6, 0.0, 0.0)


def build_scene() -> dict:
    stage = omni.usd.get_context().get_stage()
    summary = {"belts": [], "franka": None, "basket": None, "errors": []}

    if stage is None:
        summary["errors"].append("no stage")
        return summary

    # Ensure /World exists (always created by Kit but be defensive)
    if not stage.GetPrimAtPath("/World").IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path("/World"))

    # PhysicsScene + default PhysicsMaterial -- isaacsim.core.api.World.reset_async()
    # needs both; without them PickPlaceController init raises
    # "'NoneType' object has no attribute 'is_homogeneous'" on the default
    # physics material lookup.
    if not stage.GetPrimAtPath("/World/physicsScene").IsValid():
        scene = UsdPhysics.Scene.Define(stage, Sdf.Path("/World/physicsScene"))
        scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
        scene.CreateGravityMagnitudeAttr(9.81)
    mat_path = "/World/PhysicsMaterials/DefaultMaterial"
    if not stage.GetPrimAtPath(mat_path).IsValid():
        UsdShade.Material.Define(stage, Sdf.Path(mat_path))
        mat_api = UsdPhysics.MaterialAPI.Apply(stage.GetPrimAtPath(mat_path))
        mat_api.CreateDynamicFrictionAttr(0.5)
        mat_api.CreateStaticFrictionAttr(0.5)
        mat_api.CreateRestitutionAttr(0.0)

    # Parent group for conveyors
    UsdGeom.Xform.Define(stage, Sdf.Path("/World/Conveyors"))

    # 1. Conveyor belts
    for path, pos, rot, vel in BELT_LAYOUT:
        ok = _create_belt_simple(stage, path, pos, rot, vel)
        summary["belts"].append({"path": path, "ok": ok})
        if not ok:
            summary["errors"].append(f"belt {path} failed")

    # 2. Franka load
    try:
        omni.kit.commands.execute(
            "CreateReferenceCommand",
            usd_context=omni.usd.get_context(),
            path_to=Sdf.Path("/World/Franka"),
            asset_path=FRANKA_USD,
            instanceable=False,
        )
        summary["franka"] = "/World/Franka"
        carb.log_info("[conveyor_pick] Franka reference created")
    except Exception as exc:
        carb.log_warn(f"[conveyor_pick] Franka reference create failed: {exc}")
        summary["errors"].append(f"franka: {exc}")

    # 3. Basket — open box (just a thin Cube under Franka workspace)
    try:
        basket = UsdGeom.Cube.Define(stage, Sdf.Path(BASKET_PATH))
        basket.GetSizeAttr().Set(0.3)
        xform = UsdGeom.Xformable(basket)
        # Reset xformOps to known state
        xform.ClearXformOpOrder()
        translate_op = xform.AddTranslateOp()
        translate_op.Set(Gf.Vec3d(*BASKET_POSITION))
        # Visual only -- no RigidBody so static
        UsdPhysics.CollisionAPI.Apply(basket.GetPrim())
        basket.GetDisplayColorAttr().Set([Gf.Vec3f(0.4, 0.25, 0.1)])
        summary["basket"] = BASKET_PATH
        carb.log_info(f"[conveyor_pick] basket created at {BASKET_PATH}")
    except Exception as exc:
        carb.log_warn(f"[conveyor_pick] basket create failed: {exc}")
        summary["errors"].append(f"basket: {exc}")

    return summary


def _create_belt_simple(stage, path: str, pos, rot_deg: float, vel) -> bool:
    """Create a static cube belt at path with given pose. Records velocity in
    customData for diagnostics (no surface motion -- omni.physx.conveyor not
    relied upon). Returns True on success.
    """
    try:
        cube = UsdGeom.Cube.Define(stage, Sdf.Path(path))
        cube.GetSizeAttr().Set(1.0)
        prim = cube.GetPrim()
        xform = UsdGeom.Xformable(prim)
        xform.ClearXformOpOrder()
        xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
        xform.AddRotateXYZOp().Set(Gf.Vec3f(0.0, 0.0, float(rot_deg)))
        xform.AddScaleOp().Set(Gf.Vec3f(1.5, 0.4, 0.05))
        UsdPhysics.CollisionAPI.Apply(prim)
        # Subtle dark-grey color for visual contrast
        cube.GetDisplayColorAttr().Set([Gf.Vec3f(0.15, 0.15, 0.18)])
        # Stash intended velocity in customData so a later conveyor-physics
        # binding step (or operator inspection) can pick it up
        prim.SetCustomDataByKey("conveyor:velocity", Gf.Vec3f(*vel))
        return True
    except Exception as exc:
        carb.log_warn(f"[conveyor_pick] simple belt fallback failed for {path}: {exc}")
        return False
