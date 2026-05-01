"""Physics service — UsdPhysics APIs + PhysX visualization (Phase F).

Implements rigid-body, collider, material, joint, scene, and debug
visualization operations via ``UsdPhysics`` schemas + ``carb.settings``
toggles. omni.*/pxr imports are lazy per API rule #7.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Mapping from visualization mode → carb.settings key(s).
# Values are tuples so the "all off" path can reset every key before toggling
# the target one back on.
_VIZ_SETTINGS: dict[str, tuple[str, ...]] = {
    "collision": ("/physics/visualizationCollisionMesh",),
    "joint": (
        "/physics/visualizationSimulationOutput",
        "/physics/visualizationJoints",
    ),
    "mass": ("/physics/visualizationMassProperties",),
}


class PhysicsService:
    """Rigid body / collider / joint / scene / viz operations on the active Stage."""

    # ------------------------------------------------------------------
    # Rigid body
    # ------------------------------------------------------------------

    async def apply_rigid_body(self, request: dict[str, Any]) -> dict[str, Any]:
        import omni.usd
        from pxr import UsdPhysics

        prim_path = request["prim_path"]
        mass = float(request.get("mass", 1.0))
        dynamic = bool(request.get("dynamic", True))

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim {prim_path!r} not found")

        rb = UsdPhysics.RigidBodyAPI.Apply(prim)
        rb.CreateRigidBodyEnabledAttr().Set(dynamic)

        mass_api = UsdPhysics.MassAPI.Apply(prim)
        mass_api.CreateMassAttr().Set(mass)

        return {
            "ok": True,
            "prim_path": prim_path,
            "mass": mass,
            "dynamic": dynamic,
            "applied_apis": ["PhysicsRigidBodyAPI", "PhysicsMassAPI"],
        }

    async def get_rigid_body_state(self, prim_path: str) -> dict[str, Any]:
        """Read PhysX runtime state of a rigid body — vel / mass / com.

        Symmetric readback for ``apply_rigid_body``. Tries the
        ``isaacsim.core.prims.SingleRigidPrim`` runtime wrapper first
        (live PhysX state — populated after ``simulation.play``). Falls
        back to ``UsdPhysics`` schema attributes (initial state on USD
        only — velocities reflect authored values, not the live PhysX
        readout, but mass/COM are always available).

        Returns ``source`` field reporting which path won (``physx_runtime``
        or ``usd_initial``) so the caller can tell whether the velocities
        are live or stale.
        """
        import omni.usd
        from pxr import UsdPhysics

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim {prim_path!r} not found")
        if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            raise ValueError(
                f"Prim at {prim_path} has no UsdPhysics.RigidBodyAPI applied — "
                "call physics_apply_rigid_body first."
            )

        linear_vel = [0.0, 0.0, 0.0]
        angular_vel = [0.0, 0.0, 0.0]
        com = [0.0, 0.0, 0.0]
        mass = 0.0
        is_kinematic = False
        is_enabled = True
        source = "physx_runtime"

        # Source 1: PhysX runtime via SingleRigidPrim (live readout).
        # `source` reflects the *velocity* origin (the only field that meaningfully
        # changes between pre-play USD-initial and post-play runtime). Mass/COM are
        # tracked separately so we can supplement from USD MassAPI on builds where
        # SingleRigidPrim lacks `get_mass`/`get_com` or returns None.
        runtime_ok = False
        mass_filled = False
        com_filled = False
        try:
            from isaacsim.core.prims import SingleRigidPrim  # type: ignore[import-not-found]

            rp = SingleRigidPrim(prim_path)
            try:
                rp.initialize()
            except Exception as exc:  # noqa: BLE001
                logger.debug("SingleRigidPrim.initialize() failed (non-fatal): %s", exc)

            try:
                lv = rp.get_linear_velocity()
                if lv is not None:
                    linear_vel = [float(v) for v in (lv.tolist() if hasattr(lv, "tolist") else lv)]
                av = rp.get_angular_velocity()
                if av is not None:
                    angular_vel = [float(v) for v in (av.tolist() if hasattr(av, "tolist") else av)]
                m = rp.get_mass() if hasattr(rp, "get_mass") else None
                if m is not None:
                    mass = float(m)
                    mass_filled = True
                if hasattr(rp, "get_com"):
                    c = rp.get_com()
                    if c is not None:
                        com = [float(v) for v in (c.tolist() if hasattr(c, "tolist") else c)]
                        com_filled = True
                runtime_ok = True
            except Exception as exc:  # noqa: BLE001
                logger.debug("SingleRigidPrim runtime read failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.debug("SingleRigidPrim unavailable (falling back to USD): %s", exc)

        if not runtime_ok:
            source = "usd_initial"
            # Velocity attributes (initial state — set on USD before play)
            for attr_name, target in (
                ("physics:velocity", linear_vel),
                ("physics:angularVelocity", angular_vel),
            ):
                attr = prim.GetAttribute(attr_name)
                if attr and attr.IsValid():
                    val = attr.Get()
                    if val is not None:
                        target[:] = [float(v) for v in val]

        # Mass + COM: USD MassAPI is authoritative for static mass. Always
        # supplement when runtime didn't fill (older builds without get_mass /
        # get_com on SingleRigidPrim, or runtime returned None).
        if (not mass_filled or not com_filled) and prim.HasAPI(UsdPhysics.MassAPI):
            mass_api = UsdPhysics.MassAPI(prim)
            if not mass_filled:
                m_attr = mass_api.GetMassAttr()
                if m_attr and m_attr.IsValid():
                    val = m_attr.Get()
                    if val is not None:
                        mass = float(val)
            if not com_filled:
                com_attr = mass_api.GetCenterOfMassAttr()
                if com_attr and com_attr.IsValid():
                    val = com_attr.Get()
                    if val is not None:
                        com = [float(v) for v in val]

        # Common: read enabled + kinematic flags from USD (always authoritative)
        rb_api = UsdPhysics.RigidBodyAPI(prim)
        enabled_attr = rb_api.GetRigidBodyEnabledAttr()
        if enabled_attr and enabled_attr.IsValid():
            val = enabled_attr.Get()
            if val is not None:
                is_enabled = bool(val)
        kinematic_attr = rb_api.GetKinematicEnabledAttr()
        if kinematic_attr and kinematic_attr.IsValid():
            val = kinematic_attr.Get()
            if val is not None:
                is_kinematic = bool(val)

        return {
            "ok": True,
            "prim_path": prim_path,
            "source": source,
            "linear_velocity": linear_vel,
            "angular_velocity": angular_vel,
            "mass": mass,
            "center_of_mass": com,
            "is_kinematic": is_kinematic,
            "is_enabled": is_enabled,
        }

    # ------------------------------------------------------------------
    # Collider
    # ------------------------------------------------------------------

    async def apply_collider(self, request: dict[str, Any]) -> dict[str, Any]:
        import omni.usd
        from pxr import UsdPhysics

        prim_path = request["prim_path"]
        approximation = request.get("approximation", "convexHull")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim {prim_path!r} not found")

        UsdPhysics.CollisionAPI.Apply(prim)
        applied = ["PhysicsCollisionAPI"]

        # MeshCollisionAPI only applies to mesh-based prims; for primitive
        # shapes (Cube/Sphere/...) the approximation is implicit so we skip.
        if prim.IsA("UsdGeom.Mesh") or prim.GetTypeName() == "Mesh":
            mesh_api = UsdPhysics.MeshCollisionAPI.Apply(prim)
            mesh_api.CreateApproximationAttr().Set(approximation)
            applied.append("PhysicsMeshCollisionAPI")

        return {
            "ok": True,
            "prim_path": prim_path,
            "approximation": approximation,
            "applied_apis": applied,
        }

    # ------------------------------------------------------------------
    # Material
    # ------------------------------------------------------------------

    async def apply_material(self, request: dict[str, Any]) -> dict[str, Any]:
        import omni.usd
        from pxr import Sdf, UsdPhysics, UsdShade

        prim_path = request["prim_path"]
        friction = float(request.get("friction", 0.5))
        restitution = float(request.get("restitution", 0.0))
        density = float(request.get("density", 1000.0))
        requested_name = request.get("material_name")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim {prim_path!r} not found")

        suffix = requested_name or _hash_suffix(prim_path, friction, restitution, density)
        material_path = f"/World/PhysicsMaterials/M_{suffix}"
        stage.DefinePrim("/World/PhysicsMaterials", "Scope")
        mat_prim = stage.DefinePrim(Sdf.Path(material_path), "Material")
        mat_api = UsdPhysics.MaterialAPI.Apply(mat_prim)
        mat_api.CreateStaticFrictionAttr().Set(friction)
        mat_api.CreateDynamicFrictionAttr().Set(friction)
        mat_api.CreateRestitutionAttr().Set(restitution)
        mat_api.CreateDensityAttr().Set(density)

        mat = UsdShade.Material(mat_prim)
        binding_api = UsdShade.MaterialBindingAPI.Apply(prim)
        binding_api.Bind(
            mat,
            bindingStrength=UsdShade.Tokens.strongerThanDescendants,
            materialPurpose="physics",
        )

        return {
            "ok": True,
            "prim_path": prim_path,
            "material_prim_path": material_path,
            "friction": friction,
            "restitution": restitution,
            "density": density,
        }

    # ------------------------------------------------------------------
    # Joint
    # ------------------------------------------------------------------

    async def create_joint(self, request: dict[str, Any]) -> dict[str, Any]:
        import omni.usd
        from pxr import Gf, Sdf, UsdPhysics

        joint_type = request["joint_type"]
        body_a = request["body_a"]
        body_b = request["body_b"]
        anchor = request.get("anchor") or [0.0, 0.0, 0.0]
        axis = request.get("axis") or [0.0, 0.0, 1.0]
        requested_path = request.get("joint_prim_path")

        TYPE_MAP = {
            "Fixed": UsdPhysics.FixedJoint,
            "Revolute": UsdPhysics.RevoluteJoint,
            "Prismatic": UsdPhysics.PrismaticJoint,
            "Spherical": UsdPhysics.SphericalJoint,
        }
        if joint_type not in TYPE_MAP:
            raise ValueError(
                f"joint_type must be one of {sorted(TYPE_MAP)}, got {joint_type!r}"
            )

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        for p in (body_a, body_b):
            if not stage.GetPrimAtPath(p).IsValid():
                raise ValueError(f"Body prim {p!r} not found")

        stage.DefinePrim("/World/PhysicsJoints", "Scope")
        joint_path = requested_path or _auto_joint_path(stage, joint_type)
        joint = TYPE_MAP[joint_type].Define(stage, Sdf.Path(joint_path))

        joint.CreateBody0Rel().SetTargets([Sdf.Path(body_a)])
        joint.CreateBody1Rel().SetTargets([Sdf.Path(body_b)])
        joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*anchor))
        joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))

        if joint_type in ("Revolute", "Prismatic"):
            axis_token = _axis_token(axis)
            axis_attr = joint.GetPrim().GetAttribute("physics:axis")
            if not axis_attr.IsValid():
                axis_attr = joint.CreateAxisAttr()
            axis_attr.Set(axis_token)

        return {
            "ok": True,
            "joint_prim_path": joint_path,
            "joint_type": joint_type,
            "body_a": body_a,
            "body_b": body_b,
        }

    # ------------------------------------------------------------------
    # Scene
    # ------------------------------------------------------------------

    async def set_scene(self, request: dict[str, Any]) -> dict[str, Any]:
        import carb.settings
        import omni.usd
        from pxr import Gf, Sdf, UsdPhysics

        gravity = request.get("gravity") or [0.0, 0.0, -9.81]
        timestep = float(request.get("timestep", 1.0 / 60.0))
        solver_iter_pos = int(request.get("solver_iter_pos", 4))
        solver_iter_vel = int(request.get("solver_iter_vel", 1))
        scene_path = request.get("scene_prim_path", "/World/PhysicsScene")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        stage.DefinePrim("/World", "Xform")
        scene = UsdPhysics.Scene.Define(stage, Sdf.Path(scene_path))
        direction = Gf.Vec3f(*gravity)
        magnitude = float(direction.GetLength())
        if magnitude > 0:
            normalized = direction / magnitude
        else:
            normalized = Gf.Vec3f(0.0, 0.0, -1.0)
        scene.CreateGravityDirectionAttr().Set(normalized)
        scene.CreateGravityMagnitudeAttr().Set(magnitude)

        time_steps_per_second = int(round(1.0 / timestep)) if timestep > 0 else 60
        settings = carb.settings.get_settings()
        settings.set("/physics/timeStepsPerSecond", time_steps_per_second)
        settings.set("/physics/solverPositionIterations", solver_iter_pos)
        settings.set("/physics/solverVelocityIterations", solver_iter_vel)

        return {
            "ok": True,
            "scene_prim_path": scene_path,
            "gravity": [float(v) for v in gravity],
            "gravity_magnitude": magnitude,
            "timestep": timestep,
            "time_steps_per_second": time_steps_per_second,
            "solver_iter_pos": solver_iter_pos,
            "solver_iter_vel": solver_iter_vel,
        }

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    async def visualize(self, request: dict[str, Any]) -> dict[str, Any]:
        import carb.settings

        mode = request["mode"]
        if mode not in ("collision", "joint", "mass", "off"):
            raise ValueError(
                "mode must be one of {collision, joint, mass, off}"
            )

        settings = carb.settings.get_settings()
        active: list[str] = []
        # Always clear every managed key first — acts as the "off" path.
        for keys in _VIZ_SETTINGS.values():
            for key in keys:
                settings.set(key, False)
        if mode != "off":
            for key in _VIZ_SETTINGS[mode]:
                settings.set(key, True)
                active.append(key)

        return {
            "ok": True,
            "mode": mode,
            "active_settings": active,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_suffix(*parts: Any) -> str:
    import hashlib

    token = "|".join(str(p) for p in parts)
    return hashlib.sha1(token.encode("utf-8")).hexdigest()[:10]


def _auto_joint_path(stage: Any, joint_type: str) -> str:
    import time
    suffix = f"{joint_type}_{int(time.time() * 1000) % 1_000_000}"
    return f"/World/PhysicsJoints/{suffix}"


def _axis_token(axis: list[float]) -> str:
    ax, ay, az = (abs(axis[0]), abs(axis[1]), abs(axis[2]))
    if ax >= ay and ax >= az:
        return "X"
    if ay >= ax and ay >= az:
        return "Y"
    return "Z"
