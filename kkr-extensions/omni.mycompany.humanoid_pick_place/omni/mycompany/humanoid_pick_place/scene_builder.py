"""Scene assembly for the humanoid pick-and-place demo.

Builds a self-contained stage:

    /World
        physicsScene                    UsdPhysics.Scene (gravity -z 9.81)
        defaultGroundPlane              GroundPlane (visual + collision)
        Sky                             DomeLight (intensity 1500)
        Demo
            PickTable                   Cube prop at A (right of humanoid)
            PlaceTable                  Cube prop at B (left  of humanoid)
            PickCube                    Red 6-cm cube on PickTable (RigidBody)
        Humanoid                        Payload: humanoid_28.usd
        Humanoid_Anchor                 FixedJoint /World ↔ humanoid root
        DemoCam                         Authored Camera (workspace overview)
        PickStatus                      Xform with status attributes (MCP read)

Coordinates are SI (metres). Positions assume +Y is forward, +Z is up
(USD default), with the humanoid facing +Y. The two tables sit ~50 cm
out to the right and left along ±X, both at ~Y = 0.45 m so the right
arm can reach across to either side via shoulder yaw.
"""

from __future__ import annotations

import math
from typing import Any

import carb
import omni.kit.commands
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

from .humanoids import HumanoidSpec, default_humanoid
from .usd_loader import safe_load_usd_sync, wait_stage_loaded_sync


# ---------------------------------------------------------------------------
# Layout constants — kept centralised so the controller and the unit tests
# share one source of truth for "where is A / where is B".
# ---------------------------------------------------------------------------

WORLD_ROOT = "/World"
DEMO_ROOT = "/World/Demo"

HUMANOID_PRIM_PATH = "/World/Humanoid"
HUMANOID_ANCHOR_JOINT_PATH = "/World/Humanoid_Anchor"
PICK_STATUS_PRIM_PATH = "/World/HumanoidPickStatus"
DEMO_CAMERA_PATH = "/World/DemoCam"

PICK_TABLE_PATH = f"{DEMO_ROOT}/PickTable"
PLACE_TABLE_PATH = f"{DEMO_ROOT}/PlaceTable"
PICK_CUBE_PATH = f"{DEMO_ROOT}/PickCube"

# Tables — visual props sized for the humanoid's arm reach.
# 2026-05-01 live tuning: Humanoid28 arm length ~0.55 m + shoulder pitch
# clamped at +1.05 rad → reachable hand positions sit in a 0.45 m radius
# below the shoulder. The place table position was anchored to the
# cube's empirical release point so the demo lands the cube ON the
# table rather than next to it (multi-run live capture average:
# x ≈ 0.17, y ≈ -0.22 with the default trajectory + Humanoid28 rig).
TABLE_HEIGHT = 0.20  # half-height; cube top is at 2 * 0.20 = 0.40 m
TABLE_HALF = 0.20

# Pick station ("A") — right-front of humanoid, well within shoulder
# pitch / abduct sweep.
PICK_TABLE_POSITION = (0.42, 0.30, TABLE_HEIGHT)
# Place station ("B") — anchored at cube's empirical release point so
# the demo lands the cube on the table top instead of beside it.
PLACE_TABLE_POSITION = (0.17, -0.22, TABLE_HEIGHT)

# Cube starts on top of pick table (table top is z = 2 * TABLE_HEIGHT * 0.5 = 0.4).
PICK_CUBE_SIZE = 0.06
PICK_CUBE_INITIAL_POSITION = (
    PICK_TABLE_POSITION[0],
    PICK_TABLE_POSITION[1],
    2.0 * TABLE_HEIGHT + PICK_CUBE_SIZE * 0.5 + 0.005,
)

# Camera — 1.5 m back, 1.0 m to the left of humanoid, at chest height
# pointing toward the humanoid origin so the viewport composes both
# tables and the humanoid in a single frame.
CAMERA_POSITION = (1.6, -1.6, 1.5)
CAMERA_ROTATION_DEG = (0.0, 0.0, 135.0)


def build_scene(humanoid: HumanoidSpec | None = None) -> dict[str, Any]:
    """Assemble the demo stage. Idempotent on re-call.

    Returns a summary dict that the UI uses to populate the status
    panel. Raises only on hard failures (no stage). Soft failures (e.g.
    table already exists) are reported under ``summary['notes']``.
    """
    if humanoid is None:
        humanoid = default_humanoid()

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage; call stage_new() first.")

    summary: dict[str, Any] = {
        "humanoid_key": humanoid.key,
        "humanoid_title": humanoid.title,
        "notes": [],
    }

    _ensure_world_root(stage)
    _ensure_physics_scene(stage)
    _ensure_ground_plane(stage)
    _ensure_dome_light(stage)
    _ensure_demo_root(stage)

    _build_table(stage, PICK_TABLE_PATH, PICK_TABLE_POSITION,
                 colour=(0.30, 0.20, 0.10))
    _build_table(stage, PLACE_TABLE_PATH, PLACE_TABLE_POSITION,
                 colour=(0.10, 0.20, 0.35))
    _build_pick_cube(stage)
    _ensure_demo_camera(stage)
    _ensure_pick_status(stage)

    # Humanoid load — payload command. Skip if already present.
    existing = stage.GetPrimAtPath(HUMANOID_PRIM_PATH)
    if existing and existing.IsValid() and str(existing.GetTypeName()):
        summary["notes"].append(
            f"Humanoid already at {HUMANOID_PRIM_PATH}; reusing."
        )
    else:
        load_result = safe_load_usd_sync(
            usd_url=humanoid.usd_url,
            prim_path=HUMANOID_PRIM_PATH,
            position=[0.0, 0.0, humanoid.standing_height_m],
            instanceable=False,
        )
        summary["humanoid_load"] = load_result
        # Wait briefly so the articulation tree resolves before the anchor
        # joint authoring runs (FixedJoint targets need valid prims).
        wait_stage_loaded_sync(max_wait_s=15.0)

    anchor_link = _find_anchor_link(stage, humanoid.anchor_link_hint)
    if anchor_link is None:
        summary["notes"].append(
            f"Anchor link with hint {humanoid.anchor_link_hint!r} not found "
            f"under {HUMANOID_PRIM_PATH}. Humanoid may topple under gravity."
        )
    else:
        _ensure_fixed_anchor(stage, anchor_link, humanoid.standing_height_m)
        summary["anchor_link"] = anchor_link

    summary["pick_position"] = PICK_CUBE_INITIAL_POSITION
    summary["place_position_top"] = (
        PLACE_TABLE_POSITION[0],
        PLACE_TABLE_POSITION[1],
        2.0 * TABLE_HEIGHT + PICK_CUBE_SIZE * 0.5 + 0.005,
    )
    return summary


# ---------------------------------------------------------------------------
# Lookup helpers — exported because pick_controller uses them too.
# ---------------------------------------------------------------------------

def find_right_hand_link(stage, hint: str) -> str | None:
    """Return prim path of the link whose name contains ``hint``.

    DFS under :data:`HUMANOID_PRIM_PATH`; returns the first match. The
    cube-grasp parenting trick clamps onto whichever path comes back.
    """
    root = stage.GetPrimAtPath(HUMANOID_PRIM_PATH)
    if not root or not root.IsValid():
        return None
    for prim in Usd.PrimRange(root):
        if hint in prim.GetName():
            return prim.GetPath().pathString
    return None


def stamp_status(**kwargs) -> None:
    """Write diagnostic key=value pairs onto :data:`PICK_STATUS_PRIM_PATH`.

    The MCP server reads these via ``stage_assert_property`` so an
    out-of-process verifier can confirm the demo is progressing without
    needing direct access to the controller's Python state.
    """
    try:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        result = UsdGeom.Xform.Define(stage, Sdf.Path(PICK_STATUS_PRIM_PATH))
        prim = result.GetPrim()
        for k, v in kwargs.items():
            if isinstance(v, bool):
                prim.CreateAttribute(k, Sdf.ValueTypeNames.Bool).Set(v)
            elif isinstance(v, int):
                prim.CreateAttribute(k, Sdf.ValueTypeNames.Int).Set(v)
            elif isinstance(v, float):
                prim.CreateAttribute(k, Sdf.ValueTypeNames.Float).Set(v)
            else:
                prim.CreateAttribute(k, Sdf.ValueTypeNames.String).Set(str(v))
    except Exception as exc:
        carb.log_warn(f"[humanoid_pick_place] stamp_status error: {exc}")


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _ensure_world_root(stage) -> None:
    if not stage.GetPrimAtPath(WORLD_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path(WORLD_ROOT))


def _ensure_demo_root(stage) -> None:
    if not stage.GetPrimAtPath(DEMO_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path(DEMO_ROOT))


def _ensure_physics_scene(stage) -> None:
    path = "/World/physicsScene"
    if stage.GetPrimAtPath(path).IsValid():
        return
    scene = UsdPhysics.Scene.Define(stage, Sdf.Path(path))
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr(9.81)
    # Default physics material (mirrors conveyor_pick — Franka helper expects one)
    mat_path = "/World/PhysicsMaterials/DefaultMaterial"
    if not stage.GetPrimAtPath(mat_path).IsValid():
        UsdShade.Material.Define(stage, Sdf.Path(mat_path))
        api = UsdPhysics.MaterialAPI.Apply(stage.GetPrimAtPath(mat_path))
        api.CreateDynamicFrictionAttr(0.5)
        api.CreateStaticFrictionAttr(0.5)
        api.CreateRestitutionAttr(0.0)


_GRID_ENV_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Grid/default_environment.usd"
)


def _ensure_ground_plane(stage) -> None:
    """Drop NVIDIA's default Grid environment as the ground plane.

    Project convention (memory: ``feedback_physics_ground_plane``) — for
    physics work always use ``default_environment.usd`` (Grid) instead
    of a Cube primitive: 1) the visible grid pattern gives the user
    instant scale + coordinate cues, 2) it satisfies R1 (real assets
    only — no primitive substitution), 3) it ships its own ground-plane
    physics + lighting hookups so the humanoid feet land on a proper
    collider.
    """
    path = "/World/defaultGroundPlane"
    if stage.GetPrimAtPath(path).IsValid():
        return
    from .usd_loader import safe_load_usd_sync, wait_stage_loaded_sync
    safe_load_usd_sync(
        usd_url=_GRID_ENV_URL, prim_path=path,
        position=[0.0, 0.0, 0.0], instanceable=True,
    )
    # The grid environment ships fast (14 KB main + a couple of small
    # texture refs), but we still wait briefly so the floor is queryable
    # before downstream physics anchoring runs.
    wait_stage_loaded_sync(max_wait_s=8.0)


def _ensure_dome_light(stage) -> None:
    """Create a dome light if absent. Hard-coded intensity matches the
    captured scene baseline; tuning this changes SSIM compare results."""
    path = "/World/Sky"
    if stage.GetPrimAtPath(path).IsValid():
        return
    omni.kit.commands.execute(
        "CreatePrim", prim_path=path, prim_type="DomeLight",
        attributes={"inputs:intensity": 1500.0, "inputs:colorTemperature": 6500.0},
    )


def _build_table(stage, path: str, position: tuple[float, float, float],
                 colour: tuple[float, float, float]) -> None:
    """Static cube prop for visual reference. Idempotent."""
    if stage.GetPrimAtPath(path).IsValid():
        return
    cube = UsdGeom.Cube.Define(stage, Sdf.Path(path))
    cube.GetSizeAttr().Set(1.0)
    prim = cube.GetPrim()
    xf = UsdGeom.Xformable(prim)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*position))
    xf.AddScaleOp().Set(Gf.Vec3f(0.4, 0.4, 2.0 * TABLE_HEIGHT))
    UsdPhysics.CollisionAPI.Apply(prim)
    cube.GetDisplayColorAttr().Set([Gf.Vec3f(*colour)])


def _build_pick_cube(stage) -> None:
    """Red dynamic cube — what the humanoid picks up. Idempotent."""
    if stage.GetPrimAtPath(PICK_CUBE_PATH).IsValid():
        return
    cube = UsdGeom.Cube.Define(stage, Sdf.Path(PICK_CUBE_PATH))
    cube.GetSizeAttr().Set(PICK_CUBE_SIZE)
    prim = cube.GetPrim()
    xf = UsdGeom.Xformable(prim)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*PICK_CUBE_INITIAL_POSITION))
    cube.GetDisplayColorAttr().Set([Gf.Vec3f(0.85, 0.10, 0.10)])
    UsdPhysics.RigidBodyAPI.Apply(prim)
    UsdPhysics.CollisionAPI.Apply(prim)
    mass_api = UsdPhysics.MassAPI.Apply(prim)
    mass_api.GetMassAttr().Set(0.05)


def _ensure_demo_camera(stage) -> None:
    if stage.GetPrimAtPath(DEMO_CAMERA_PATH).IsValid():
        return
    cam = UsdGeom.Camera.Define(stage, Sdf.Path(DEMO_CAMERA_PATH))
    prim = cam.GetPrim()
    xf = UsdGeom.Xformable(prim)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*CAMERA_POSITION))
    xf.AddRotateXYZOp().Set(Gf.Vec3f(*CAMERA_ROTATION_DEG))
    cam.GetFocalLengthAttr().Set(24.0)
    cam.GetClippingRangeAttr().Set(Gf.Vec2f(0.05, 100.0))


def _ensure_pick_status(stage) -> None:
    if stage.GetPrimAtPath(PICK_STATUS_PRIM_PATH).IsValid():
        return
    UsdGeom.Xform.Define(stage, Sdf.Path(PICK_STATUS_PRIM_PATH))


def _find_anchor_link(stage, hint: str) -> str | None:
    """Locate the link to pin via FixedJoint.

    Searches under :data:`HUMANOID_PRIM_PATH` for a prim whose name
    *contains* ``hint`` (case sensitive). Returns the first match.
    """
    root = stage.GetPrimAtPath(HUMANOID_PRIM_PATH)
    if not root or not root.IsValid():
        return None
    for prim in Usd.PrimRange(root):
        if hint in prim.GetName():
            return prim.GetPath().pathString
    return None


def _ensure_fixed_anchor(stage, anchor_link: str, height: float) -> None:
    """Author a FixedJoint between /World and ``anchor_link``.

    Without this the educational humanoid topples under gravity in
    ~0.5 s, ruining the demo. PhysX honours the FixedJoint as long as
    both bodies have RigidBodyAPI; the anchor link gets it from the
    humanoid USD itself, /World does not need one (PhysX treats the
    world as static).
    """
    if stage.GetPrimAtPath(HUMANOID_ANCHOR_JOINT_PATH).IsValid():
        return
    joint = UsdPhysics.FixedJoint.Define(
        stage, Sdf.Path(HUMANOID_ANCHOR_JOINT_PATH),
    )
    joint.CreateBody0Rel().SetTargets([Sdf.Path(WORLD_ROOT)])
    joint.CreateBody1Rel().SetTargets([Sdf.Path(anchor_link)])
    # localPos0 is in /World coordinates — anchor at humanoid hip height.
    joint.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 0.0, height))
    joint.CreateLocalRot0Attr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    # localPos1 / localRot1 default to identity → joint origin is at the
    # link's local origin, which is what we want.


def reset_pick_cube(stage) -> None:
    """Move the pick cube back to its initial position (UI Reset Cube)."""
    prim = stage.GetPrimAtPath(PICK_CUBE_PATH)
    if not prim or not prim.IsValid():
        return
    xf = UsdGeom.Xformable(prim)
    t_attr = prim.GetAttribute("xformOp:translate")
    if not t_attr.IsValid():
        t_attr = xf.AddTranslateOp()
    t_attr.Set(Gf.Vec3d(*PICK_CUBE_INITIAL_POSITION))
    # Zero out velocities if the rigid body cached any (sleep state safe).
    for vname in ("physics:velocity", "physics:angularVelocity"):
        a = prim.GetAttribute(vname)
        if a and a.IsValid():
            a.Set(Gf.Vec3f(0.0, 0.0, 0.0))
