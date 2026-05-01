"""Periodic spawn of dynamic colored cubes on the conveyor.

Task 6 fold-ins:
    * **Alternating zone** — successive ``spawn_cube`` calls toggle between
      the Robot A side (``-X``) and the Robot B side (``+X``) so both
      arms see fresh cubes within their reachable zone. The previous
      4-segment uniform-random distribution starved one robot when RNG
      streak-clustered.
    * **Friction material** — cubes get a ``UsdPhysics.MaterialAPI``-backed
      physics material (``staticFriction=1.0`` / ``dynamicFriction=0.9``)
      so the SurfaceGripper can hold them without the cube spinning out.
    * **list_cubes()** — exposes ``[{path, pos, vel}, ...]`` for the
      ``PickPlaceWorker`` predictive tracker. ``vel`` is read from the
      ``physics:velocity`` attribute on each cube's ``RigidBodyAPI``;
      until the timeline plays a tick the velocity stays at zero, which
      degenerates the lookahead to stationary IK (safe).
    * **get_spawn_count** — total spawns since module init, surfaced to
      the UI metrics label so the operator can see throughput.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import carb


_SOURCE = "omni.userext.pickplace"

CUBE_ROOT = "/World/Cubes"
CUBE_SIZE = 0.05
CUBE_MASS = 0.05  # lighter cubes are easier for the gripper to lift cleanly

# Spawn coords — initial placeholder values. Real values are set at build
# time via :func:`set_spawn_zones` from the SceneBuilder which knows the
# measured loop AABB (v5: ㅁ-shape NVIDIA ConveyorBuilder).
SPAWN_Z = 0.45  # belt top + 5 cm slack — overwritten by set_spawn_zones
_ZONE_A_X_CENTER = 0.0
_ZONE_B_X_CENTER = 0.0
_ZONE_A_Y = 0.0
_ZONE_B_Y = 0.0
# Tight jitter so cubes land on belt center (avoid roller-edge slip).
_ZONE_X_JITTER = 0.04
_ZONE_Y_JITTER = 0.04


def set_spawn_zones(zone_a: tuple[float, float, float],
                    zone_b: tuple[float, float, float]) -> None:
    """Update spawn-zone centers from measured loop geometry.

    Called by :class:`scene_builder.SceneBuilder` after the conveyor loop
    is built and the per-straight world AABB is known. ``zone_a`` is the
    Franka_A side STRAIGHT center, ``zone_b`` the Franka_B side STRAIGHT
    center; both are ``(x, y, z_top)`` tuples. SPAWN_Z is set to
    ``max(z_top) + 0.05`` for a small free-fall onto the surface plane.
    """
    global _ZONE_A_X_CENTER, _ZONE_A_Y, _ZONE_B_X_CENTER, _ZONE_B_Y, SPAWN_Z
    _ZONE_A_X_CENTER, _ZONE_A_Y, az = zone_a
    _ZONE_B_X_CENTER, _ZONE_B_Y, bz = zone_b
    SPAWN_Z = float(max(az, bz)) + 0.05
    carb.log_info(
        f"[{_SOURCE}] spawn zones updated: "
        f"A=({_ZONE_A_X_CENTER:.3f},{_ZONE_A_Y:.3f}), "
        f"B=({_ZONE_B_X_CENTER:.3f},{_ZONE_B_Y:.3f}), Z={SPAWN_Z:.3f}"
    )

# Module physics-material singleton — created lazily on the first cube
# spawn so the stage already exists.
_FRICTION_MATERIAL_PATH = "/World/Physics/Materials/CubeFriction"
_FRICTION_STATIC = 1.0
_FRICTION_DYNAMIC = 0.9

DEFAULT_PALETTE = [
    (0.95, 0.30, 0.30),
    (0.30, 0.85, 0.45),
    (0.30, 0.55, 0.95),
    (0.95, 0.85, 0.20),
    (0.85, 0.40, 0.85),
    (0.20, 0.85, 0.85),
]


@dataclass
class CubeRecord:
    prim_path: str
    spawned_t: float
    color: tuple[float, float, float]


# ---------------------------------------------------------------------------
# Module-level state — alternating cursor + total counter
# ---------------------------------------------------------------------------

# Alternating zone cursor; toggled inside spawn_cube() each call.
_next_zone: str = "A"
# Cumulative spawn count surfaced to the UI metrics label (get_spawn_count()).
_total_spawned: int = 0
# Per-spawn simulation_time stamps — used by Task 9 in-flight grace logic
# (compute_metric.spawn_times). Codex pass 7 F3: previously the spawner only
# tracked a counter, so dump.spawn_times was always None and the in-flight
# correction silently degenerated to eligible==spawned.
_spawn_times: list[float] = []


def reset_state() -> None:
    """Reset alternating cursor + spawn counter — called from on_reset()."""
    global _next_zone, _total_spawned
    _next_zone = "A"
    _total_spawned = 0
    _spawn_times.clear()


def get_spawn_count() -> int:
    """Total cubes spawned since the last :func:`reset_state` call."""
    return _total_spawned


def get_spawn_times() -> list[float]:
    """Return a copy of per-cube simulation_time stamps in spawn order.

    Length matches :func:`get_spawn_count`. Used by ``_on_dump_state`` to
    persist ``spawn_times`` in state_dump.json — required by Task 9
    ``compute_metric`` in-flight grace correction (Codex pass 7 F3).
    """
    return list(_spawn_times)


def ensure_cube_root() -> None:
    import omni.usd
    from pxr import UsdGeom

    stage = omni.usd.get_context().get_stage()
    if not stage.GetPrimAtPath(CUBE_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, CUBE_ROOT)


def _ensure_friction_material():
    """Create (or return) a shared physics material with friction tuned for
    the SurfaceGripper grip. Best-effort — schemas vary across Kit / USD
    versions; on import failure we silently skip and let downstream cubes
    inherit the default 0.5/0.5 friction.
    """
    import omni.usd
    from pxr import Sdf, UsdGeom, UsdPhysics, UsdShade

    stage = omni.usd.get_context().get_stage()
    mat_path = Sdf.Path(_FRICTION_MATERIAL_PATH)
    existing = stage.GetPrimAtPath(mat_path)
    if existing.IsValid():
        return UsdShade.Material(existing)

    # Make sure parent xforms exist before creating the material prim.
    for parent in ("/World/Physics", "/World/Physics/Materials"):
        if not stage.GetPrimAtPath(parent).IsValid():
            UsdGeom.Scope.Define(stage, parent)

    mat = UsdShade.Material.Define(stage, mat_path)
    UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    api = UsdPhysics.MaterialAPI(mat.GetPrim())
    try:
        api.CreateStaticFrictionAttr(_FRICTION_STATIC)
        api.CreateDynamicFrictionAttr(_FRICTION_DYNAMIC)
        api.CreateRestitutionAttr(0.0)
    except Exception as exc:
        carb.log_warn(f"[{_SOURCE}] friction material attr setup failed: {exc!r}")
    return mat


def _bind_friction_material(prim) -> None:
    """Bind the shared friction material to a cube prim's collision API."""
    try:
        from pxr import UsdShade
        mat = _ensure_friction_material()
        if mat is None:
            return
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(
            mat,
            bindingStrength=UsdShade.Tokens.strongerThanDescendants,
            materialPurpose="physics",
        )
    except Exception as exc:
        carb.log_warn(f"[{_SOURCE}] bind friction material failed: {exc!r}")


def spawn_cube(simulation_time: float) -> CubeRecord:
    """Spawn a single dynamic cube alternating between Robot A / B zones."""
    import omni.usd
    from pxr import Gf, Sdf, UsdGeom, UsdPhysics, PhysxSchema

    global _next_zone, _total_spawned

    ensure_cube_root()
    stage = omni.usd.get_context().get_stage()

    color = random.choice(DEFAULT_PALETTE)
    if _next_zone == "A":
        x = _ZONE_A_X_CENTER + random.uniform(-_ZONE_X_JITTER, _ZONE_X_JITTER)
        y = _ZONE_A_Y + random.uniform(-_ZONE_Y_JITTER, _ZONE_Y_JITTER)
    else:
        x = _ZONE_B_X_CENTER + random.uniform(-_ZONE_X_JITTER, _ZONE_X_JITTER)
        y = _ZONE_B_Y + random.uniform(-_ZONE_Y_JITTER, _ZONE_Y_JITTER)
    # Toggle for next call.
    _next_zone = "B" if _next_zone == "A" else "A"

    name_suffix = int(simulation_time * 1000)
    cube_path = f"{CUBE_ROOT}/cube_{name_suffix:08d}"

    if stage.GetPrimAtPath(cube_path).IsValid():
        return CubeRecord(prim_path=cube_path, spawned_t=simulation_time, color=color)

    cube = UsdGeom.Cube.Define(stage, cube_path)
    cube.GetSizeAttr().Set(1.0)
    prim = cube.GetPrim()

    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(x, y, SPAWN_Z))
    xform.AddScaleOp().Set(Gf.Vec3f(CUBE_SIZE, CUBE_SIZE, CUBE_SIZE))

    cube.GetDisplayColorAttr().Set([Gf.Vec3f(*color)])

    UsdPhysics.RigidBodyAPI.Apply(prim)
    UsdPhysics.CollisionAPI.Apply(prim)
    UsdPhysics.MassAPI.Apply(prim)
    PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
    PhysxSchema.PhysxCollisionAPI.Apply(prim)

    mass_attr = prim.GetAttribute("physics:mass")
    if not mass_attr.IsValid():
        mass_attr = prim.CreateAttribute("physics:mass", Sdf.ValueTypeNames.Float)
    mass_attr.Set(CUBE_MASS)

    # Apply the shared friction material so the SurfaceGripper holds firmly.
    _bind_friction_material(prim)

    _total_spawned += 1
    _spawn_times.append(float(simulation_time))
    carb.log_info(
        f"[{_SOURCE}] cube #{_total_spawned} ({_next_zone if _next_zone == 'A' else 'B'} next) "
        f"at ({x:.2f}, {y:.2f}, {SPAWN_Z:.2f}) → {cube_path}"
    )
    return CubeRecord(prim_path=cube_path, spawned_t=simulation_time, color=color)


def list_active_cubes() -> list[str]:
    import omni.usd

    stage = omni.usd.get_context().get_stage()
    cube_root_prim = stage.GetPrimAtPath(CUBE_ROOT)
    if not cube_root_prim.IsValid():
        return []
    return [str(p.GetPath()) for p in cube_root_prim.GetChildren() if p.IsValid()]


def get_cube_position(prim_path: str) -> tuple[float, float, float] | None:
    import omni.usd
    from pxr import UsdGeom

    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return None
    xformable = UsdGeom.Xformable(prim)
    world_xform = xformable.ComputeLocalToWorldTransform(0.0)
    t = world_xform.ExtractTranslation()
    return (float(t[0]), float(t[1]), float(t[2]))


def get_cube_velocity(prim_path: str) -> tuple[float, float, float]:
    """Read ``physics:velocity`` (linear) from the cube's RigidBodyAPI.

    Returns ``(0.0, 0.0, 0.0)`` until the timeline plays a tick — Physx
    populates the velocity attr only while the simulation is running.
    The predictive tracker tolerates zero velocity (lookahead degenerates
    to stationary IK).
    """
    import omni.usd
    from pxr import UsdPhysics

    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return (0.0, 0.0, 0.0)
    rbody = UsdPhysics.RigidBodyAPI(prim)
    if not rbody:
        return (0.0, 0.0, 0.0)
    try:
        attr = rbody.GetVelocityAttr()
        if attr is None or not attr.IsValid():
            return (0.0, 0.0, 0.0)
        v = attr.Get()
        if v is None:
            return (0.0, 0.0, 0.0)
        return (float(v[0]), float(v[1]), float(v[2]))
    except Exception:
        return (0.0, 0.0, 0.0)


def list_cubes() -> list[dict]:
    """Return ``[{path, pos, vel}, ...]`` for every active cube.

    Used by ``PickPlaceWorkshopExtension._collect_cubes`` to build the
    payload for ``PickPlaceWorker.tick(now, cubes)``. Velocity comes
    from the rigid-body physics:velocity attribute (zero before the
    timeline plays — predictive tracker degenerates safely).
    """
    out: list[dict] = []
    for path in list_active_cubes():
        pos = get_cube_position(path)
        if pos is None:
            continue
        vel = get_cube_velocity(path)
        out.append({"path": path, "pos": pos, "vel": vel})
    return out


def remove_cube(prim_path: str) -> None:
    import omni.usd
    import omni.kit.commands

    stage = omni.usd.get_context().get_stage()
    if not stage.GetPrimAtPath(prim_path).IsValid():
        return
    omni.kit.commands.execute("DeletePrims", paths=[prim_path])


def clear_all_cubes() -> None:
    import omni.usd
    import omni.kit.commands

    stage = omni.usd.get_context().get_stage()
    cube_root_prim = stage.GetPrimAtPath(CUBE_ROOT)
    if not cube_root_prim.IsValid():
        return
    paths = [str(p.GetPath()) for p in cube_root_prim.GetChildren()]
    if paths:
        omni.kit.commands.execute("DeletePrims", paths=paths)
