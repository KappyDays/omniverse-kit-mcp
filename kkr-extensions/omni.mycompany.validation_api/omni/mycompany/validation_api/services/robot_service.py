"""Robot service — USD load, joint control, async navigate (Phase B).

All omni.*/pxr.*/isaacsim.core.prims imports are lazy (inside functions)
per Extension API rule #7 so the module is safe to import outside Kit.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RobotService:
    """Thin wrapper over SingleArticulation + USD payload load/transform.

    Navigate is implemented as a linear interpolation of ``xformOp:translate``
    dispatched to :class:`JobService` so the REST call returns a ``job_id``
    immediately without blocking the Kit event loop.
    """

    def __init__(self, job_service: Any) -> None:
        self._job_service = job_service

    async def load(self, request: dict[str, Any]) -> dict[str, Any]:
        """Load a USD robot asset into the stage at *prim_path*."""
        import asyncio
        import omni.kit.async_engine  # lazy
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Gf, UsdGeom

        usd_url: str = request["usd_url"].replace("\\", "/")
        prim_path: str = request["prim_path"]
        position: list[float] | None = request.get("position")
        rotation: list[float] | None = request.get("rotation")

        active_jobs = _active_job_ids(self._job_service)
        if active_jobs:
            raise ValueError(
                "robot/load requires all async jobs to be terminal before mutating "
                f"the stage. Active job_ids={active_jobs}. Poll /jobs/{{id}} or "
                "cancel the job before loading another robot."
            )

        async def _main_loop_impl():
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()
            if stage is None:
                raise RuntimeError("No USD stage available")

            timeline_was_playing = await _stop_timeline_if_playing()
            _ensure_parent_xform(stage, prim_path)

            omni.kit.commands.execute(
                "CreatePayloadCommand",
                usd_context=ctx,
                path_to=prim_path,
                asset_path=usd_url,
                # Robot payloads need runtime traversal and articulation writes.
                # Payload avoids the Isaac 6.0 reference crash; non-instanceable
                # keeps articulated child prims editable and discoverable.
                instanceable=False,
            )

            await _wait_stage_loading()

            prim = stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                raise RuntimeError(f"Prim not found at {prim_path} after loading")

            if position is not None:
                attr = prim.GetAttribute("xformOp:translate")
                if attr.IsValid():
                    attr.Set(Gf.Vec3d(*position))
                else:
                    UsdGeom.Xformable(prim).AddTranslateOp().Set(Gf.Vec3d(*position))
            if rotation is not None:
                rot_attr = prim.GetAttribute("xformOp:rotateXYZ")
                if rot_attr.IsValid():
                    rot_attr.Set(Gf.Vec3f(*rotation))
                else:
                    UsdGeom.Xformable(prim).AddRotateXYZOp().Set(Gf.Vec3f(*rotation))

            return prim, timeline_was_playing

        future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
        prim, timeline_was_playing = await asyncio.wrap_future(future)
        has_articulation = _has_articulation_api(prim)

        return {
            "ok": True,
            "prim_path": prim_path,
            "usd_url": usd_url,
            "type_name": str(prim.GetTypeName()),
            "has_articulation": has_articulation,
            "timeline_was_playing": timeline_was_playing,
        }

    async def get_joint_positions(self, prim_path: str) -> dict[str, Any]:
        """Return the current joint positions of an articulation.

        Raises ``ValueError`` (→ HTTP 400) if the prim lacks a PhysX
        articulation API. ``SingleArticulation`` itself would silently
        return ``None`` / empty data, which hides broken scenarios — surface
        the mismatch at the REST boundary instead.

        The wrapper needs an explicit ``initialize()`` call
        once PhysX has populated the articulation view (usually after one
        simulation play tick). We call it defensively here so callers don't
        have to orchestrate the init themselves.
        """
        from isaacsim.core.prims import SingleArticulation  # lazy

        _assert_articulation(prim_path)
        art = SingleArticulation(prim_path)
        _ensure_initialized(art)
        positions = art.get_joint_positions()
        if positions is None:
            raise ValueError(
                f"SingleArticulation.get_joint_positions returned None for {prim_path} — "
                "articulation present but not ready. Run simulation_play at least "
                "once to let PhysX populate the articulation view."
            )
        positions_list = (
            positions.tolist() if hasattr(positions, "tolist") else list(positions)
        )
        return {
            "ok": True,
            "prim_path": prim_path,
            "positions": [float(p) for p in positions_list],
        }

    async def get_joint_config(self, prim_path: str) -> dict[str, Any]:
        """Read joint drive config + limits + max velocity per DOF.

        Symmetric readback for ``set_joint_positions`` — exposes drive
        stiffness/damping/max_force, position lower/upper limits, and
        max joint velocities. Useful for IK / drive_physics debugging
        when set_joint_positions or set_ee_target produce unexpected
        motion (drive too soft, target outside limits, velocity capped).

        Tries ``SingleArticulation.dof_properties`` first (numpy structured
        array on builds that expose it). Falls back to per-
        joint ``UsdPhysics.DriveAPI`` introspection — which is always
        available because drive config is encoded directly on the joint
        prims regardless of the articulation wrapper version.
        """
        from isaacsim.core.prims import SingleArticulation  # lazy

        _assert_articulation(prim_path)
        art = SingleArticulation(prim_path)
        _ensure_initialized(art)

        dof_names = list(art.dof_names or [])
        num_dof = int(art.num_dof or len(dof_names))

        # Source 1: dof_properties (preferred — single readback)
        props_source = "dof_properties"
        stiffness: list[float] = [0.0] * num_dof
        damping: list[float] = [0.0] * num_dof
        max_force: list[float] = [0.0] * num_dof
        lower_limits: list[float] = [0.0] * num_dof
        upper_limits: list[float] = [0.0] * num_dof
        max_velocity: list[float] = [0.0] * num_dof
        joint_types: list[str] = ["unknown"] * num_dof

        props = None
        try:
            props = art.dof_properties
        except Exception as exc:  # noqa: BLE001
            logger.debug("dof_properties read failed (falling back to USD): %s", exc)

        if props is not None:
            try:
                for i in range(num_dof):
                    record = props[i]
                    stiffness[i] = float(_props_get(record, "stiffness", 0.0))
                    damping[i] = float(_props_get(record, "damping", 0.0))
                    max_force[i] = float(_props_get(record, "maxEffort", 0.0))
                    lower_limits[i] = float(_props_get(record, "lower", 0.0))
                    upper_limits[i] = float(_props_get(record, "upper", 0.0))
                    max_velocity[i] = float(_props_get(record, "maxVelocity", 0.0))
                # joint_types: dof_properties exposes driveMode (Position /
                # Velocity / Force), not joint kind (Revolute / Prismatic / ...).
                # Walk USD to read the actual joint type tokens.
                try:
                    joint_types = _read_usd_joint_types(prim_path, dof_names)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("joint_types USD read failed (keeping 'unknown'): %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.debug("dof_properties parse failed (falling back to USD): %s", exc)
                props = None

        # Source 2: USD UsdPhysics.DriveAPI per joint prim (always-available fallback)
        if props is None:
            props_source = "usd_drive_api"
            usd_data = _read_usd_drive_config(prim_path, dof_names)
            stiffness = usd_data["stiffness"]
            damping = usd_data["damping"]
            max_force = usd_data["max_force"]
            lower_limits = usd_data["lower_limits"]
            upper_limits = usd_data["upper_limits"]
            max_velocity = usd_data["max_velocity"]
            joint_types = usd_data["joint_types"]

        return {
            "ok": True,
            "prim_path": prim_path,
            "source": props_source,
            "dof_count": num_dof,
            "dof_names": dof_names,
            "joint_types": joint_types,
            "stiffness": stiffness,
            "damping": damping,
            "max_force": max_force,
            "lower_limits": lower_limits,
            "upper_limits": upper_limits,
            "max_velocity": max_velocity,
        }

    async def set_joint_positions(
        self, prim_path: str, positions: list[float]
    ) -> dict[str, Any]:
        """Set joint positions — requires a prim with PhysxArticulationRoot.

        Auto-calls ``SingleArticulation.initialize()`` so the articulation
        view is populated before ``set_joint_positions``; on Kit builds
        this is mandatory (earlier 4.x tolerated a missing init).
        """
        import numpy as np  # lazy
        from isaacsim.core.prims import SingleArticulation

        _assert_articulation(prim_path)
        art = SingleArticulation(prim_path)
        _ensure_initialized(art)
        art.set_joint_positions(np.array(positions, dtype=np.float32))
        return {
            "ok": True,
            "prim_path": prim_path,
            "positions_count": len(positions),
        }

    async def navigate_to(
        self,
        prim_path: str,
        target: list[float],
        duration_s: float,
    ) -> dict[str, Any]:
        """Dispatch a linear-interpolation move as an async Job.

        The job is completed when ``xformOp:translate`` reaches *target*.
        Returns ``{job_id}`` so the caller can poll ``GET /jobs/{id}``.
        """
        if len(target) != 3:
            raise ValueError("target must be a 3-element [x, y, z] list")

        def _factory(update_progress):
            return _navigate_coro(prim_path, list(target), duration_s, update_progress)

        job_id = self._job_service.start_job(_factory)
        return {
            "ok": True,
            "job_id": job_id,
            "prim_path": prim_path,
            "target": list(target),
        }

    async def gripper_control(
        self,
        prim_path: str,
        action: str,
        target: float | None = None,
    ) -> dict[str, Any]:
        """Open / close / set gripper joints on an articulation (Phase G).

        Auto-detects gripper joints by matching ``finger`` or ``gripper``
        substrings against ``SingleArticulation.dof_names``. Applies the
        action only to those DOFs — non-gripper DOFs keep their current
        value (read back before write).

        For ``open`` / ``close`` the extension reads joint limits via
        ``art.get_dof_limits`` (if exposed). When limits are unavailable
        (generic articulation without per-DOF bounds), falls back to the
        Franka-default 0.04 / 0.0 pair. ``action="set"`` requires a
        *target* argument and writes it verbatim.
        """
        import numpy as np  # lazy
        from isaacsim.core.prims import SingleArticulation

        if action not in ("open", "close", "set"):
            raise ValueError("action must be open|close|set")
        if action == "set" and target is None:
            raise ValueError("action='set' requires a target value")

        _assert_articulation(prim_path)
        art = SingleArticulation(prim_path)
        _ensure_initialized(art)

        dof_names = list(art.dof_names or [])
        gripper_idx = [
            i for i, n in enumerate(dof_names)
            if "finger" in str(n).lower() or "gripper" in str(n).lower()
        ]
        if not gripper_idx:
            raise ValueError(
                f"No gripper joints found on {prim_path} — DOF names: {dof_names!r}"
            )

        # Resolve target per action
        if action == "set":
            target_value = float(target)  # type: ignore[arg-type]
        else:
            lower, upper = _read_dof_limits(art, gripper_idx)
            if action == "open":
                target_value = upper if upper is not None else 0.04
            else:  # close
                target_value = lower if lower is not None else 0.0

        # Read current, overwrite gripper DOFs, write back
        current = art.get_joint_positions()
        if current is None:
            raise ValueError(
                f"get_joint_positions returned None on {prim_path} — "
                "run simulation_play once so PhysX populates the articulation."
            )
        new_positions = np.array(current, dtype=np.float32).copy()
        for i in gripper_idx:
            new_positions[i] = target_value
        art.set_joint_positions(new_positions)

        return {
            "ok": True,
            "prim_path": prim_path,
            "action": action,
            "target_value": float(target_value),
            "gripper_joint_names": [str(dof_names[i]) for i in gripper_idx],
            "gripper_joint_indices": gripper_idx,
            "dof_count": len(dof_names),
        }

    async def set_ee_target(
        self,
        prim_path: str,
        target_pose: list[float],
        robot_description: str = "Franka",
        end_effector_frame: str | None = None,
    ) -> dict[str, Any]:
        """Solve IK for *target_pose* and write the resulting joint positions.

        target_pose is ``[x, y, z, qw, qx, qy, qz]`` (scalar-first quat).
        Uses Lula IK — Franka ships with a built-in config, generic
        articulations (UR / custom) without a config raise HTTP 400 so
        scenarios skip them cleanly.
        """
        import numpy as np  # lazy

        if len(target_pose) != 7:
            raise ValueError("target_pose must be [x, y, z, qw, qx, qy, qz]")

        _assert_articulation(prim_path)

        # Resolve Lula imports from the Isaac Sim 6.0 namespace.
        LulaKinematicsSolver, interface_config_loader, import_path = _resolve_lula_modules()
        if LulaKinematicsSolver is None or interface_config_loader is None:
            raise ValueError(
                "IK solver unavailable — isaacsim.robot_motion.motion_generation.lula "
                "not importable. Skip IK tools."
            )

        # Lula config for the selected robot description. Keep both loader
        # method names because the local 6.0 bundle still exposes the shorter
        # variant while historical fixtures cover the longer one.
        try:
            cfg = _resolve_lula_config(interface_config_loader, robot_description)
        except Exception as exc:
            raise ValueError(
                f"No Lula motion policy config for robot_description={robot_description!r}. "
                f"Supported: Franka, FR3. Original error: {exc}"
            ) from exc

        urdf_path = cfg.get("urdf_path")
        desc_path = cfg.get("robot_description_path")
        default_ee = cfg.get("end_effector_frame_name") or "right_gripper"
        ee_name = end_effector_frame or default_ee

        solver = LulaKinematicsSolver(desc_path, urdf_path)
        solver.set_robot_base_pose(
            np.array([0.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0, 0.0]),
        )

        from isaacsim.core.prims import SingleArticulation  # lazy
        art = SingleArticulation(prim_path)
        _ensure_initialized(art)
        warm = art.get_joint_positions()
        if warm is None:
            raise ValueError(
                f"IK warm-start failed — {prim_path} returned no joint positions"
            )

        # Lula's Franka solver expects 7 arm DOFs (no gripper). Trim warm state.
        arm_warm = np.array(warm, dtype=np.float32)[:7]

        target_pos = np.array(target_pose[:3], dtype=np.float32)
        target_quat = np.array(target_pose[3:], dtype=np.float32)

        try:
            sol, success = solver.compute_inverse_kinematics(
                frame_name=ee_name,
                target_position=target_pos,
                target_orientation=target_quat,
                warm_start=arm_warm,
            )
        except Exception as exc:
            raise ValueError(
                f"Lula IK solve raised — target_pose may be unreachable. Cause: {exc}"
            ) from exc

        if not success or sol is None:
            raise ValueError(
                f"Lula IK did not converge for target pose {target_pose!r} "
                f"on {prim_path} (ee={ee_name}). Consider relaxing orientation."
            )

        # Merge solution (arm DOFs) with current gripper values
        new_positions = np.array(warm, dtype=np.float32).copy()
        sol_arr = np.asarray(sol, dtype=np.float32).reshape(-1)
        for i in range(min(len(sol_arr), len(new_positions))):
            new_positions[i] = sol_arr[i]
        art.set_joint_positions(new_positions)

        return {
            "ok": True,
            "prim_path": prim_path,
            "target_pose": [float(v) for v in target_pose],
            "robot_description": robot_description,
            "end_effector_frame": ee_name,
            "lula_import_path": import_path,
            "ik_success": True,
            "solution": [float(v) for v in sol_arr.tolist()],
        }

    async def get_ee_pose(
        self,
        prim_path: str,
        end_effector_frame: str | None = None,
    ) -> dict[str, Any]:
        """Read a robot end-effector world pose from the live USD stage.

        This deliberately reads the articulated link transform after PhysX
        has advanced instead of solving another IK problem. It is meant for
        controller telemetry: "where is the hand now?".
        """
        return _compute_ee_pose(prim_path, end_effector_frame)

    async def navigate_path(
        self,
        prim_path: str,
        points: list[list[float]],
        duration_s: float,
    ) -> dict[str, Any]:
        """Follow a multi-waypoint path (e.g. NavMesh result) via linear interp
        per segment. Segment duration is weighted by segment length so speed
        stays constant across the full path.

        For NavMesh-aware robot nav: call ``/navigation/query_path`` first and
        pass its ``points`` directly. Returns a single ``job_id`` for the whole
        traversal.

        **Precondition**: timeline must be **playing** — per project rule
        "모든 Robot 관련 동작은 물리 시뮬레이션 활성화 상태에서만 검증" (see root
        CLAUDE.md). Raises ``ValueError`` (→ HTTP 400) if timeline is stopped /
        paused so callers cannot silently skip physics. Caller must explicitly
        `simulation_play` before navigate_path.
        """
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        if not timeline.is_playing():
            raise ValueError(
                "robot/navigate_path requires simulation to be playing. "
                "Call /simulation/play before navigate_path so PhysX can tick "
                "wheels/articulation + collision."
            )

        if len(points) < 2:
            raise ValueError("points must contain at least 2 waypoints")
        for p in points:
            if len(p) != 3:
                raise ValueError("each waypoint must be [x, y, z]")
        if duration_s <= 0:
            raise ValueError("duration_s must be > 0")

        def _factory(update_progress):
            return _navigate_path_coro(prim_path, [list(p) for p in points],
                                        float(duration_s), update_progress)

        job_id = self._job_service.start_job(_factory)
        return {
            "ok": True,
            "job_id": job_id,
            "prim_path": prim_path,
            "num_waypoints": len(points),
            "duration_s": duration_s,
        }

    async def drive_physics(self, request: dict[str, Any]) -> dict[str, Any]:
        """Drive a wheel-based articulation along ``waypoints`` via
        DifferentialController + Pure Pursuit (spec §8.2). Physics-based
        — writes ``joint_velocities`` to PhysX articulation. Returns Job
        ``{job_id}``; poll ``/jobs/{id}``. Requires timeline playing (R2).
        """
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        if not timeline.is_playing():
            raise ValueError(
                "robot/drive_physics requires simulation to be playing. "
                "Call /simulation/play first so PhysX can tick wheel joints."
            )

        prim_path = request["prim_path"]
        waypoints = request["waypoints"]
        if len(waypoints) < 2:
            raise ValueError("waypoints must contain at least 2 points")
        # Accept 2D [x, y] (ground plane) or 3D [x, y, z]; pad z=0 for 2D so a
        # caller passing [[x, y], ...] gets a clear behaviour instead of a cryptic
        # "list index out of range" downstream.
        norm_wps: list[list[float]] = []
        for p in waypoints:
            if len(p) == 2:
                norm_wps.append([float(p[0]), float(p[1]), 0.0])
            elif len(p) == 3:
                norm_wps.append([float(p[0]), float(p[1]), float(p[2])])
            else:
                raise ValueError("each waypoint must be [x, y] or [x, y, z]")
        waypoints = norm_wps

        _assert_articulation(prim_path)

        kwargs = dict(
            prim_path=prim_path,
            waypoints=[list(p) for p in waypoints],
            max_linear=float(request.get("max_linear", 1.0)),
            max_angular=float(request.get("max_angular", 1.2)),
            wheel_radius=float(request.get("wheel_radius", 0.14)),
            wheel_base=float(request.get("wheel_base", 0.413)),
            arrival_tol=float(request.get("arrival_tolerance", 0.3)),
            timeout_s=float(request.get("timeout_s", 60.0)),
            lookahead=float(request.get("lookahead", 0.8)),
        )

        def _factory(update_progress):
            return _drive_physics_coro(update_progress=update_progress, **kwargs)

        job_id = self._job_service.start_job(_factory)
        return {
            "ok": True,
            "job_id": job_id,
            "prim_path": prim_path,
        }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _navigate_coro(
    prim_path: str,
    target: list[float],
    duration_s: float,
    update_progress,
) -> dict[str, Any]:
    """Linear interpolation of xformOp:translate over ``duration_s`` seconds."""
    import omni.kit.app  # lazy
    import omni.usd
    from pxr import Gf, UsdGeom

    app = omni.kit.app.get_app()
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise RuntimeError(f"Prim not found at {prim_path}")

    attr = prim.GetAttribute("xformOp:translate")
    if not attr.IsValid():
        attr = UsdGeom.Xformable(prim).AddTranslateOp()

    start_raw = attr.Get()
    start = (
        [float(start_raw[0]), float(start_raw[1]), float(start_raw[2])]
        if start_raw is not None else [0.0, 0.0, 0.0]
    )
    target_vec = [float(v) for v in target]

    steps = max(1, int(max(duration_s, 0.0) * 60))
    start_time = time.monotonic()
    for i in range(1, steps + 1):
        t = i / steps
        current = [
            start[0] + (target_vec[0] - start[0]) * t,
            start[1] + (target_vec[1] - start[1]) * t,
            start[2] + (target_vec[2] - start[2]) * t,
        ]
        attr.Set(Gf.Vec3d(*current))
        update_progress(t)
        await app.next_update_async()

    elapsed_s = time.monotonic() - start_time
    return {
        "final_position": target_vec,
        "steps": steps,
        "elapsed_s": elapsed_s,
    }


async def _navigate_path_coro(
    prim_path: str,
    points: list[list[float]],
    duration_s: float,
    update_progress,
) -> dict[str, Any]:
    """Follow multi-waypoint path. Segment durations weighted by XY length
    so linear speed is roughly constant even when segment lengths vary."""
    import math
    import omni.kit.app  # lazy
    import omni.usd
    from pxr import Gf, UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise RuntimeError(f"Prim not found at {prim_path}")
    attr = prim.GetAttribute("xformOp:translate")
    if not attr.IsValid():
        attr = UsdGeom.Xformable(prim).AddTranslateOp()

    # Compute XY distances + total
    seg_lengths: list[float] = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        seg_lengths.append(math.hypot(b[0] - a[0], b[1] - a[1]))
    total = sum(seg_lengths) or 1.0

    app = omni.kit.app.get_app()
    start_time = time.monotonic()
    total_steps = 0
    for seg_idx, seg_len in enumerate(seg_lengths):
        a = points[seg_idx]
        b = points[seg_idx + 1]
        seg_duration = max(duration_s * (seg_len / total), 0.05)
        steps = max(1, int(seg_duration * 60))
        for i in range(1, steps + 1):
            t = i / steps
            cur = (
                a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * t,
                a[2] + (b[2] - a[2]) * t,
            )
            attr.Set(Gf.Vec3d(*cur))
            cumulative = (sum(seg_lengths[:seg_idx]) + seg_len * t) / total
            update_progress(cumulative)
            await app.next_update_async()
        total_steps += steps

    return {
        "final_position": points[-1],
        "num_waypoints": len(points),
        "total_steps": total_steps,
        "path_length": total,
        "elapsed_s": time.monotonic() - start_time,
    }


async def _wait_stage_loading(max_frames: int = 300) -> None:
    import omni.kit.app  # lazy

    app = omni.kit.app.get_app()
    for _ in range(max_frames):
        await app.next_update_async()
        if not _is_stage_loading():
            return


def _is_stage_loading() -> bool:
    try:
        from isaacsim.core.experimental.utils.stage import is_stage_loading
        return is_stage_loading()
    except ImportError:
        try:
            import omni.usd
            ctx = omni.usd.get_context()
            _, files_loaded, total_files = ctx.get_stage_loading_status()
            return total_files > 0 and files_loaded < total_files
        except Exception:
            return False


def _ensure_parent_xform(stage: Any, prim_path: str) -> None:
    """Define missing parent Xforms before CreatePayloadCommand.

    Kit can otherwise return success while leaving nested paths such as
    ``/World/Robot/Jetbot`` uncreated.
    """
    from pxr import Sdf, UsdGeom

    parts = [part for part in prim_path.split("/") if part]
    if len(parts) <= 1:
        return

    current = ""
    for part in parts[:-1]:
        current = f"{current}/{part}"
        if not stage.GetPrimAtPath(current).IsValid():
            UsdGeom.Xform.Define(stage, Sdf.Path(current))


def _active_job_ids(job_service: Any) -> tuple[str, ...]:
    active = getattr(job_service, "active_job_ids", None)
    if callable(active):
        return tuple(str(job_id) for job_id in active())

    jobs = getattr(job_service, "_jobs", {})
    if not isinstance(jobs, dict):
        return ()
    return tuple(
        str(job_id)
        for job_id, entry in jobs.items()
        if isinstance(entry, dict) and entry.get("status") in {"pending", "running"}
    )


async def _stop_timeline_if_playing(max_frames: int = 10) -> bool:
    """Stop timeline before robot payload load.

    Isaac Sim 6.0 can crash in PhysX/primdata when a new articulated payload is
    added while physics is ticking. Stop is idempotent and mirrors stage-write
    play-guard behavior.
    """
    import omni.kit.app
    import omni.timeline

    timeline = omni.timeline.get_timeline_interface()
    if not timeline.is_playing():
        return False

    timeline.stop()
    app = omni.kit.app.get_app()
    for _ in range(max_frames):
        await app.next_update_async()
        if not timeline.is_playing():
            break
    return True


def _has_articulation_api(prim: Any) -> bool:
    """Return True if *prim* (or any descendant) has PhysxArticulationAPI applied.

    Uses ``Usd.PrimRange`` so deeply-nested articulation roots (e.g. Franka's
    ``/World/Robot/panda_link0``) are detected — a previous direct-children
    scan gave false negatives on real robot USDs.
    """
    try:
        from pxr import Usd

        for p in Usd.PrimRange(prim):
            schemas = p.GetAppliedSchemas()
            for s in schemas:
                if "ArticulationRoot" in s or "ArticulationAPI" in s:
                    return True
        return False
    except Exception:
        return False


def _ensure_initialized(articulation: Any) -> None:
    """Defensive ``SingleArticulation.initialize()`` — safe to call twice.

    Kit articulation wrappers require initialize() before joint I/O even when the prim
    has a PhysxArticulationRoot. Re-initializing an already-initialized
    articulation is a no-op (no exception). Any other error is logged but
    not raised — the subsequent get/set call will surface a useful error.
    """
    try:
        articulation.initialize()
    except Exception as exc:
        logger.debug("SingleArticulation.initialize() raised (non-fatal): %s", exc)


def _props_get(record: Any, key: str, default: Any) -> Any:
    """Read *key* from a dof_properties record (numpy structured / dict / namedtuple).

    Isaac Sim 5.x exposes `dof_properties` as a numpy structured array on
    PhysX builds, but lighter test stubs return a list of dicts. Try both.
    Returns *default* when the key is missing or read raises.
    """
    try:
        return record[key]
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    try:
        return getattr(record, key)
    except AttributeError:
        return default


def _read_usd_joint_types(prim_path: str, dof_names: list[str]) -> list[str]:
    """Walk articulation subtree → joint type per DOF (UsdPhysics joint kind).

    ``dof_properties.driveMode`` is the *drive* type (Position/Velocity/Force),
    not the joint *kind*. The joint kind (RevoluteJoint / PrismaticJoint /
    SphericalJoint / FixedJoint) lives on the joint prim's USD type — we walk
    the articulation subtree to read it. Joints whose names don't match
    *dof_names* (and dof_names without a matching joint) yield ``"unknown"``.
    """
    import omni.usd
    from pxr import Usd

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return ["unknown"] * len(dof_names)
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        return ["unknown"] * len(dof_names)

    name_to_idx = {name: i for i, name in enumerate(dof_names)}
    out = ["unknown"] * len(dof_names)
    for p in Usd.PrimRange(root):
        type_name = str(p.GetTypeName())
        if not type_name.endswith("Joint"):
            continue
        idx = name_to_idx.get(p.GetName())
        if idx is not None:
            out[idx] = type_name
    return out


def _read_usd_drive_config(prim_path: str, dof_names: list[str]) -> dict[str, list]:
    """Walk the articulation prim subtree and pull DriveAPI / limit attributes.

    Drive config + joint limits live on the joint prims themselves (UsdPhysics
    schema), independent of any runtime articulation wrapper. We match joint
    prims to *dof_names* by joint prim name so the returned arrays align with
    the articulation's DOF order. Joints not represented in *dof_names* are
    skipped; *dof_names* entries with no matching joint prim get zeros.
    """
    import omni.usd
    from pxr import Usd, UsdPhysics

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")

    name_to_idx = {name: i for i, name in enumerate(dof_names)}
    n = len(dof_names)
    out = {
        "stiffness": [0.0] * n,
        "damping": [0.0] * n,
        "max_force": [0.0] * n,
        "lower_limits": [0.0] * n,
        "upper_limits": [0.0] * n,
        "max_velocity": [0.0] * n,
        "joint_types": ["unknown"] * n,
    }

    for p in Usd.PrimRange(root):
        type_name = str(p.GetTypeName())
        if not type_name.endswith("Joint"):
            continue
        idx = name_to_idx.get(p.GetName())
        if idx is None:
            continue
        out["joint_types"][idx] = type_name

        # Drive API — angular for revolute/spherical, linear for prismatic.
        drive_token = "linear" if type_name == "PrismaticJoint" else "angular"
        try:
            drive = UsdPhysics.DriveAPI.Get(p, drive_token)
            if drive:
                stiff_attr = drive.GetStiffnessAttr()
                damp_attr = drive.GetDampingAttr()
                force_attr = drive.GetMaxForceAttr()
                if stiff_attr and stiff_attr.IsValid():
                    val = stiff_attr.Get()
                    if val is not None:
                        out["stiffness"][idx] = float(val)
                if damp_attr and damp_attr.IsValid():
                    val = damp_attr.Get()
                    if val is not None:
                        out["damping"][idx] = float(val)
                if force_attr and force_attr.IsValid():
                    val = force_attr.Get()
                    if val is not None:
                        out["max_force"][idx] = float(val)
        except Exception as exc:  # noqa: BLE001
            logger.debug("DriveAPI read failed for %s: %s", p.GetPath(), exc)

        # Position limits live directly on the joint prim
        for attr_name, key in (
            ("physics:lowerLimit", "lower_limits"),
            ("physics:upperLimit", "upper_limits"),
        ):
            attr = p.GetAttribute(attr_name)
            if attr and attr.IsValid():
                val = attr.Get()
                if val is not None:
                    out[key][idx] = float(val)

        # Max joint velocity (PhysxJointAPI extension attribute)
        for vel_attr_name in ("physxJoint:maxJointVelocity", "physics:maxJointVelocity"):
            vel_attr = p.GetAttribute(vel_attr_name)
            if vel_attr and vel_attr.IsValid():
                val = vel_attr.Get()
                if val is not None:
                    out["max_velocity"][idx] = float(val)
                    break

    return out


def _read_dof_limits(art: Any, indices: list[int]) -> tuple[float | None, float | None]:
    """Return (min_lower, max_upper) across *indices* in the articulation.

    Kit exposes DOF limits inconsistently across code paths —
    ``SingleArticulation.get_dof_limits`` on some builds returns a numpy
    array shaped ``(num_dof, 2)``; on others the limits live on
    ``dof_properties``. We try both and fall back to ``(None, None)``
    — the caller then uses Franka defaults.
    """
    try:
        limits = art.get_dof_limits()
    except Exception:
        limits = None

    if limits is not None:
        try:
            # Expect shape (num_dof, 2) → (lower, upper)
            import numpy as np  # lazy
            arr = np.asarray(limits)
            lowers = [float(arr[i, 0]) for i in indices]
            uppers = [float(arr[i, 1]) for i in indices]
            return (min(lowers), max(uppers))
        except Exception:
            pass

    # Fallback to dof_properties if available
    try:
        props = art.dof_properties  # numpy structured array in some builds
        lowers = [float(props[i]["lower"]) for i in indices]
        uppers = [float(props[i]["upper"]) for i in indices]
        return (min(lowers), max(uppers))
    except Exception:
        return (None, None)


def _resolve_lula_modules() -> tuple[Any, Any, str]:
    """Resolve Isaac Sim 6.0 Lula modules.

    Returns ``(None, None, "")`` when the supported ``isaacsim.*`` namespace
    is unavailable so the caller can raise a user-facing 400.
    """
    try:
        from isaacsim.robot_motion.motion_generation.lula import (  # type: ignore[import-not-found]
            LulaKinematicsSolver,
        )
        from isaacsim.robot_motion.motion_generation import (  # type: ignore[import-not-found]
            interface_config_loader,
        )
        return LulaKinematicsSolver, interface_config_loader, "isaacsim.robot_motion"
    except ImportError:
        return None, None, ""


def _resolve_lula_config(
    interface_config_loader: Any,
    robot_description: str,
) -> dict[str, Any]:
    """Resolve a Lula/RMPflow config across Isaac Sim loader API variants."""
    errors: list[str] = []
    for robot_name in _lula_robot_name_candidates(robot_description):
        for method_name in (
            "load_supported_motion_policy_config",
            "load_supported_robot_motion_policy_configs",
        ):
            method = getattr(interface_config_loader, method_name, None)
            if method is None:
                continue
            try:
                cfg = method(robot_name, "RMPflow")
            except Exception as exc:  # noqa: BLE001 - report all attempted APIs
                errors.append(f"{method_name}({robot_name!r}): {exc}")
                continue
            if cfg:
                return dict(cfg)
            errors.append(f"{method_name}({robot_name!r}) returned no config")

    joined = "; ".join(errors) if errors else "no supported loader API found"
    raise ValueError(joined)


def _lula_robot_name_candidates(robot_description: str) -> tuple[str, ...]:
    raw = str(robot_description or "").strip()
    aliases = {
        "franka": ("Franka",),
        "franka_panda": ("Franka",),
        "panda": ("Franka",),
        "fr3": ("FR3",),
    }
    candidates = [raw] if raw else []
    candidates.extend(aliases.get(raw.lower(), ()))

    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return tuple(unique or ["Franka"])


def _assert_articulation(prim_path: str) -> None:
    """Raise ValueError if *prim_path* has no PhysxArticulationRoot/API applied."""
    import omni.usd

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")
    if not _has_articulation_api(prim):
        raise ValueError(
            f"Prim at {prim_path} has no PhysX articulation API — "
            "joint control requires a robot with ArticulationRoot. "
            "Use continueOnFailure: true in scenarios where optional."
        )


def _compute_ee_pose(
    prim_path: str,
    end_effector_frame: str | None = None,
) -> dict[str, Any]:
    """Return end-effector world pose by reading the current USD link transform."""
    import omni.usd
    from pxr import Gf, Usd, UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    robot_prim = stage.GetPrimAtPath(prim_path)
    if not robot_prim.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")
    if not _has_articulation_api(robot_prim):
        raise ValueError(f"Prim at {prim_path} has no PhysX articulation API")

    frame_name = end_effector_frame or "panda_hand"
    ee_prim = None
    if frame_name.startswith("/"):
        candidate = stage.GetPrimAtPath(frame_name)
        if candidate.IsValid():
            ee_prim = candidate
    else:
        for prim in Usd.PrimRange(robot_prim):
            if prim.GetName() == frame_name:
                ee_prim = prim
                break
        if ee_prim is None:
            for fallback in ("panda_hand", "right_gripper", "tool0", "ee_link"):
                for prim in Usd.PrimRange(robot_prim):
                    if prim.GetName() == fallback:
                        ee_prim = prim
                        frame_name = fallback
                        break
                if ee_prim is not None:
                    break
    if ee_prim is None or not ee_prim.IsValid():
        raise ValueError(
            f"End-effector frame {frame_name!r} not found under {prim_path}"
        )

    matrix = UsdGeom.Xformable(ee_prim).ComputeLocalToWorldTransform(
        Usd.TimeCode.Default(),
    )
    translate = matrix.ExtractTranslation()
    rotation = matrix.ExtractRotation()
    quat = rotation.GetQuat() if hasattr(rotation, "GetQuat") else Gf.Quatd(1.0)
    imag = quat.GetImaginary()
    return {
        "ok": True,
        "prim_path": prim_path,
        "end_effector_frame": frame_name,
        "position": [float(translate[0]), float(translate[1]), float(translate[2])],
        "orientation": [
            float(quat.GetReal()),
            float(imag[0]),
            float(imag[1]),
            float(imag[2]),
        ],
        "source": "usd_world_transform",
    }


# ---------------------------------------------------------------------------
# Drive Physics — Pure Pursuit + DifferentialController (spec §8.2)
# ---------------------------------------------------------------------------

async def _drive_physics_coro(
    *,
    prim_path: str,
    waypoints: list[list[float]],
    max_linear: float,
    max_angular: float,
    wheel_radius: float,
    wheel_base: float,
    arrival_tol: float,
    timeout_s: float,
    lookahead: float,
    update_progress,
) -> dict[str, Any]:
    """Pure Pursuit + DifferentialController async loop. Spec §8.2.

    Always zeros wheel joint_velocities on exit (cancel/timeout/exception).
    """
    import math
    import numpy as np

    import carb  # lazy
    import omni.kit.app

    from isaacsim.robot.wheeled_robots.controllers.differential_controller import (
        DifferentialController,
    )
    from isaacsim.core.utils.types import ArticulationAction

    from isaacsim.core.prims import SingleArticulation

    art = SingleArticulation(prim_path)
    try:
        art.initialize()
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[drive_physics] art.initialize() failed (may be already inited): {exc}")

    dof_names = list(art.dof_names or [])
    left_idx, right_idx = _resolve_wheel_dofs(dof_names)
    if left_idx is None or right_idx is None:
        raise ValueError(
            f"Wheel DOF not resolvable. dof_names={dof_names}. "
            "Expected substrings: wheel_left/right or joint_wheel_left/right."
        )

    num_dof = int(art.num_dof)
    ctrl = DifferentialController(
        name=f"drive_physics_{prim_path.replace('/', '_')}",
        wheel_radius=wheel_radius,
        wheel_base=wheel_base,
    )

    path_2d = [(float(p[0]), float(p[1])) for p in waypoints]
    total_path_len = sum(
        math.hypot(path_2d[i + 1][0] - path_2d[i][0], path_2d[i + 1][1] - path_2d[i][1])
        for i in range(len(path_2d) - 1)
    )

    app = omni.kit.app.get_app()
    start_time = time.monotonic()
    ticks = 0
    reached = False
    final_distance = float("inf")

    try:
        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > timeout_s:
                break

            pos, orient = art.get_world_pose()
            pos_xy = (float(pos[0]), float(pos[1]))
            goal_xy = path_2d[-1]
            d_goal = math.hypot(goal_xy[0] - pos_xy[0], goal_xy[1] - pos_xy[1])
            final_distance = d_goal
            if d_goal < arrival_tol:
                reached = True
                break

            # Pure Pursuit target
            tx, ty = _pure_pursuit_target(pos_xy, path_2d, lookahead)
            dx, dy = tx - pos_xy[0], ty - pos_xy[1]
            yaw = _quat_yaw_wxyz(orient)
            yaw_err = _wrap_pi(math.atan2(dy, dx) - yaw)

            # Pure Pursuit linear/angular split — 사용자 fix (2026-04-23):
            # 이전 lin = max_linear * (1 - |yaw_err|/π) 가 너무 강한 감쇄로
            # robot 이 향하는 방향 != target 방향이면 in-place spin (제자리 회전).
            # 새 정책:
            #   - yaw_err 작음 (<30°): full max_linear (직진 우선)
            #   - 중간 (30°~90°): cos 기반 부드러운 감쇄
            #   - 큼 (>90°): 최소 0.2 m/s 보장 + 회전
            yaw_abs = abs(yaw_err)
            if yaw_abs < math.radians(30):
                lin_scale = 1.0
            elif yaw_abs < math.radians(90):
                lin_scale = max(0.3, math.cos(yaw_abs))
            else:
                lin_scale = 0.2
            lin = max_linear * lin_scale
            ang = float(np.clip(2.0 * yaw_err, -max_angular, max_angular))

            # ctrl.forward([lin, ang]) returns an ArticulationAction with
            # joint_velocities populated on current builds; historical builds
            # returned a 2-element numpy array. Handle both shapes.
            wv = ctrl.forward([lin, ang])
            if hasattr(wv, "joint_velocities") and wv.joint_velocities is not None:
                jv = np.asarray(wv.joint_velocities, dtype=np.float32)
            else:
                jv = np.asarray(wv, dtype=np.float32)
            vels = np.zeros(num_dof, dtype=np.float32)
            # forward() yields [left_wheel_rad_s, right_wheel_rad_s]
            vels[left_idx] = float(jv.flat[0])
            vels[right_idx] = float(jv.flat[1])
            art.apply_action(ArticulationAction(joint_velocities=vels))

            ticks += 1
            if total_path_len > 1e-6:
                prog = max(0.0, min(1.0, 1.0 - d_goal / total_path_len))
                update_progress(prog)
            await app.next_update_async()
    finally:
        # Always brake wheels on exit
        try:
            zeros = np.zeros(num_dof, dtype=np.float32)
            art.apply_action(ArticulationAction(joint_velocities=zeros))
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[drive_physics] failed to zero wheels on exit: {exc}")

    return {
        "reached": reached,
        "final_distance_m": final_distance,
        "elapsed_s": time.monotonic() - start_time,
        "ticks": ticks,
        "dof_names": dof_names,
        "left_wheel_idx": left_idx,
        "right_wheel_idx": right_idx,
    }


def _resolve_wheel_dofs(dof_names: list[str]) -> tuple[int | None, int | None]:
    """Find left / right wheel DOF indices by name substring scan."""
    low = [n.lower() for n in dof_names]
    def _find(patterns: list[str]) -> int | None:
        for p in patterns:
            for i, n in enumerate(low):
                if p in n:
                    return i
        return None
    return (
        _find(["wheel_left", "left_wheel", "joint_wheel_left"]),
        _find(["wheel_right", "right_wheel", "joint_wheel_right"]),
    )


def _pure_pursuit_target(
    pos_xy: tuple[float, float],
    path_2d: list[tuple[float, float]],
    lookahead: float,
) -> tuple[float, float]:
    """Find a point on `path_2d` that is ~`lookahead` ahead of `pos_xy`."""
    import math
    if len(path_2d) < 2:
        return path_2d[-1]
    # Nearest segment
    best_i, best_d = 0, float("inf")
    for i in range(len(path_2d) - 1):
        d = _seg_dist(pos_xy, path_2d[i], path_2d[i + 1])
        if d < best_d:
            best_d, best_i = d, i
    # Walk forward until cumulative distance >= lookahead
    remaining = lookahead
    cur = pos_xy
    for j in range(best_i, len(path_2d) - 1):
        ax, ay = path_2d[j]
        bx, by = path_2d[j + 1]
        sx, sy = bx - ax, by - ay
        seg_len = math.hypot(sx, sy)
        if seg_len < 1e-6:
            continue
        ux, uy = sx / seg_len, sy / seg_len
        if remaining <= seg_len:
            sx0, sy0 = (cur[0], cur[1]) if j == best_i else (ax, ay)
            return (sx0 + ux * remaining, sy0 + uy * remaining)
        remaining -= seg_len
        cur = (bx, by)
    return path_2d[-1]


def _seg_dist(p, a, b) -> float:
    import math
    ax, ay = a; bx, by = b; px, py = p
    abx, aby = bx - ax, by - ay
    ab_sq = abx * abx + aby * aby
    if ab_sq < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / ab_sq))
    cx, cy = ax + t * abx, ay + t * aby
    return math.hypot(px - cx, py - cy)


def _quat_yaw_wxyz(q) -> float:
    """Extract yaw from quaternion. Accepts [w,x,y,z] tuple or carb/Gf quat."""
    import math
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    siny = 2.0 * (w * z + x * y)
    cosy = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny, cosy)


def _wrap_pi(a: float) -> float:
    import math
    return (a + math.pi) % (2.0 * math.pi) - math.pi
