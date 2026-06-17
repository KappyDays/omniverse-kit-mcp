"""Robot service — USD load, joint control, async navigate (Phase B).

All omni.*/pxr.*/isaacsim.core.prims imports are lazy (inside functions)
per Extension API rule #7 so the module is safe to import outside Kit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)

_PICK_PLACE_PROGRESS_SAMPLE_INTERVAL_STEPS = 30
_PICK_PLACE_PROGRESS_SAMPLE_LIMIT = 32
_PICK_PLACE_FAR_CONTACT_BBOX_WIDTH_MULTIPLIER = 1.0
_PICK_PLACE_DIAGNOSTIC_OFFSET_STEP_LIMIT_M = 0.05


@dataclass(frozen=True)
class _OfficialFrankaPickPlaceClasses:
    pick_place_controller: Any
    parallel_gripper: Any
    single_articulation: Any


@dataclass(frozen=True)
class _FrankaParallelGripperSpec:
    end_effector_prim_name: str
    joint_prim_names: tuple[str, str]


@dataclass
class _FrankaPickPlaceDemoState:
    request: dict[str, Any]
    robot: Any
    gripper: Any
    controller: Any
    subscription: Any
    robot_description: str
    robot_prim_path: str
    object_prim_path: str
    target_position: list[float]
    object_initial_position: list[float]
    object_bbox_size: list[float]
    initial_joint_positions: Any
    picking_position: list[float]
    explicit_picking_position: bool
    end_effector_offset: Any
    end_effector_orientation: Any
    end_effector_initial_height: float
    diagnostics: dict[str, Any]
    max_steps: int
    position_tolerance: float
    lift_height_tolerance: float
    reset_on_play: bool
    status: str = "idle"
    steps: int = 0
    controller_event: int = 0
    done: bool = False
    placed: bool = False
    lifted: bool = False
    initial_object_position: list[float] | None = None
    final_object_position: list[float] | None = None
    last_object_bbox_center: list[float] | None = None
    final_distance: float = 0.0
    max_lift_delta: float = 0.0
    max_center_z: float = 0.0
    last_error: str | None = None
    last_timeline_time: float = 0.0
    event_tick_counts: dict[int, int] = field(default_factory=dict)
    event_first_steps: dict[int, int] = field(default_factory=dict)
    event_last_steps: dict[int, int] = field(default_factory=dict)
    progress_samples: list[dict[str, Any]] = field(default_factory=list)
    max_joint_delta_from_initial: float = 0.0
    max_action_joint_position_delta: float = 0.0
    action_joint_positions_seen: bool = False
    min_end_effector_distance_to_pick: float | None = None
    min_end_effector_distance_to_target: float | None = None
    min_end_effector_distance_to_object: float | None = None
    min_end_effector_xy_distance_to_object: float | None = None
    min_abs_end_effector_z_distance_to_object: float | None = None
    signed_end_effector_z_distance_at_min_abs_to_object: float | None = None
    end_effector_object_delta_at_min_distance: list[float] | None = None
    end_effector_object_delta_at_min_xy_distance: list[float] | None = None
    end_effector_object_delta_at_min_abs_z: list[float] | None = None
    min_end_effector_distance_to_object_during_closed_gripper: float | None = None
    min_end_effector_xy_distance_to_object_during_closed_gripper: float | None = None
    min_abs_end_effector_z_distance_to_object_during_closed_gripper: float | None = None
    signed_end_effector_z_distance_at_min_abs_during_closed_gripper: float | None = None
    end_effector_object_delta_at_min_distance_during_closed_gripper: list[float] | None = None
    end_effector_object_delta_at_min_xy_distance_during_closed_gripper: list[float] | None = None
    end_effector_object_delta_at_min_abs_z_during_closed_gripper: list[float] | None = None
    max_object_lift_delta_during_closed_gripper: float | None = None
    max_object_xy_motion_during_closed_gripper: float | None = None
    end_effector_pose_seen: bool = False
    gripper_aperture_seen: bool = False
    action_gripper_aperture_seen: bool = False
    gripper_closed_on_object_width_seen: bool = False
    min_gripper_aperture_m: float | None = None
    max_gripper_aperture_m: float | None = None
    min_action_gripper_aperture_m: float | None = None
    max_action_gripper_aperture_m: float | None = None
    min_gripper_object_width_margin_m: float | None = None
    min_action_gripper_object_width_margin_m: float | None = None
    playback_wrapper_refresh_count: int = 0


class RobotService:
    """Thin wrapper over SingleArticulation + USD payload load/transform.

    Navigate is implemented as a linear interpolation of ``xformOp:translate``
    dispatched to :class:`JobService` so the REST call returns a ``job_id``
    immediately without blocking the Kit event loop.
    """

    def __init__(self, job_service: Any) -> None:
        self._job_service = job_service
        self._pick_place_demo: _FrankaPickPlaceDemoState | None = None

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
        await _ensure_articulation_ready(art, prim_path)
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
        await _ensure_articulation_ready(art, prim_path)

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

    async def get_joint_config_static(self, prim_path: str) -> dict[str, Any]:
        """Read USD-authored joint metadata without touching SingleArticulation.

        This is a diagnostic fallback for hazardous profile triage. The returned
        joint order is USD traversal order, not guaranteed articulation DOF order,
        so callers must not feed these arrays into joint-position writes.
        """
        _assert_articulation(prim_path)
        usd_data = _read_static_usd_joint_config(prim_path)
        return {
            "ok": True,
            "prim_path": prim_path,
            "source": "usd_joint_prims_static",
            "static_only": True,
            "order_reliable": False,
            "dof_count": len(usd_data["dof_names"]),
            "dof_names": usd_data["dof_names"],
            "joint_types": usd_data["joint_types"],
            "stiffness": usd_data["stiffness"],
            "damping": usd_data["damping"],
            "max_force": usd_data["max_force"],
            "lower_limits": usd_data["lower_limits"],
            "upper_limits": usd_data["upper_limits"],
            "max_velocity": usd_data["max_velocity"],
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
        await _ensure_articulation_ready(art, prim_path)
        _apply_joint_positions(art, np.array(positions, dtype=np.float32))
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
        await _ensure_articulation_ready(art, prim_path)

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
        _apply_joint_positions(art, new_positions)

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
        await _ensure_articulation_ready(art, prim_path)
        warm = art.get_joint_positions()
        if warm is None:
            raise ValueError(
                f"IK warm-start failed — {prim_path} returned no joint positions"
            )

        solver_joint_names = _lula_solver_joint_names(solver)
        dof_names = tuple(str(v) for v in (getattr(art, "dof_names", None) or ()))
        arm_indices = _select_lula_articulation_joint_indices(
            dof_names=dof_names,
            solver_joint_names=solver_joint_names,
            robot_description=robot_description,
            warm_count=len(warm),
        )
        warm_arr = np.array(warm, dtype=np.float32)
        arm_warm = np.array([warm_arr[i] for i in arm_indices], dtype=np.float32)

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
        new_positions = warm_arr.copy()
        sol_arr = np.asarray(sol, dtype=np.float32).reshape(-1)
        for i, articulation_index in enumerate(arm_indices[: len(sol_arr)]):
            if articulation_index < len(new_positions):
                new_positions[articulation_index] = sol_arr[i]
        _apply_joint_positions(art, new_positions)

        return {
            "ok": True,
            "prim_path": prim_path,
            "target_pose": [float(v) for v in target_pose],
            "robot_description": robot_description,
            "end_effector_frame": ee_name,
            "lula_import_path": import_path,
            "ik_success": True,
            "solution": [float(v) for v in sol_arr.tolist()],
            "lula_joint_names": list(solver_joint_names),
            "articulation_joint_indices": [int(v) for v in arm_indices],
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

    async def run_franka_pick_place(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run Isaac Sim's official Franka PickPlaceController on an object.

        This endpoint deliberately does not move the object kinematically. The
        only object-side setup it performs is best-effort physics schema
        preparation so an existing prim can participate in contact. Success is
        based on controller completion plus bbox-based lift/place validation.
        """
        import numpy as np
        import omni.kit.app
        import omni.timeline

        robot_prim_path = str(request["robot_prim_path"])
        object_prim_path = str(request["object_prim_path"])
        target_position = [float(v) for v in request["target_position"]]
        if len(target_position) != 3:
            raise ValueError("target_position must be [x, y, z]")
        _assert_franka_family_pick_place_robot(
            request.get("robot_description", "Franka"),
            endpoint="robot/franka_pick_place",
        )

        max_steps = int(request.get("max_steps", 1800))
        position_tolerance = float(request.get("position_tolerance", 0.05))
        lift_height_tolerance = float(request.get("lift_height_tolerance", 0.03))
        picking_position_raw = request.get("picking_position")
        explicit_picking_position = (
            [float(v) for v in picking_position_raw]
            if picking_position_raw is not None
            else None
        )
        end_effector_initial_height = request.get("end_effector_initial_height")
        end_effector_offset_raw = request.get("end_effector_offset")
        end_effector_offset = (
            np.array([float(v) for v in end_effector_offset_raw], dtype=np.float32)
            if end_effector_offset_raw is not None
            else None
        )
        end_effector_orientation_raw = request.get("end_effector_orientation")
        end_effector_orientation = (
            np.array([float(v) for v in end_effector_orientation_raw], dtype=np.float32)
            if end_effector_orientation_raw is not None
            else None
        )
        events_dt = request.get("events_dt")
        if events_dt is not None:
            events_dt = [float(v) for v in events_dt]

        _assert_articulation(robot_prim_path)
        _assert_prim_exists(object_prim_path)
        _ensure_pickable_physics(object_prim_path)

        classes = _resolve_official_franka_pick_place_classes()
        robot = classes.single_articulation(robot_prim_path)
        await _ensure_articulation_ready(robot, robot_prim_path, max_frames=180)

        robot_description = str(request.get("robot_description", "Franka"))
        gripper = _create_franka_parallel_gripper(
            classes,
            robot,
            robot_prim_path,
            robot_description=robot_description,
        )
        try:
            robot.apply_action(gripper.forward(action="open"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("initial gripper open failed: %s", exc)

        initial_bbox = _compute_world_bbox(object_prim_path)
        initial_center = initial_bbox["center"]
        object_bbox_size = initial_bbox["size"]
        picking_position = explicit_picking_position or list(initial_center)
        picking_position_source = "explicit" if explicit_picking_position is not None else "bbox_center"
        resolved_hover_height = _resolve_franka_pick_place_hover_height(
            explicit_height=(
                float(end_effector_initial_height)
                if end_effector_initial_height is not None
                else None
            ),
            picking_z=float(picking_position[2]),
            target_z=float(target_position[2]),
        )
        hover_height_source = (
            "explicit"
            if end_effector_initial_height is not None
            else (
                "official_default"
                if math.isclose(resolved_hover_height, 0.3, rel_tol=0.0, abs_tol=1e-9)
                else "auto_above_pick_place"
            )
        )
        diagnostics = _build_franka_pick_place_diagnostics(
            object_bbox_size,
            picking_position_source=picking_position_source,
        )
        diagnostics["end_effector_initial_height"] = resolved_hover_height
        diagnostics["end_effector_initial_height_source"] = hover_height_source
        diagnostics["requested_pick_strategy"] = _franka_pick_place_strategy_diagnostics(
            picking_position_source=picking_position_source,
            picking_position=picking_position,
            object_initial_position=list(initial_center),
            target_position=target_position,
            end_effector_initial_height=resolved_hover_height,
            end_effector_initial_height_source=hover_height_source,
            end_effector_offset=end_effector_offset,
            end_effector_orientation=end_effector_orientation,
            events_dt=events_dt,
            max_steps=max_steps,
        )

        controller = _create_franka_pick_place_controller(
            classes=classes,
            robot=robot,
            gripper=gripper,
            hover_height=resolved_hover_height,
            events_dt=events_dt,
            robot_description=robot_description,
        )

        app = omni.kit.app.get_app()
        timeline = omni.timeline.get_timeline_interface()
        was_playing = bool(timeline.is_playing())
        if not was_playing:
            timeline.play()
            for _ in range(5):
                await app.next_update_async()

        max_center_z = initial_center[2]
        final_center = initial_center
        steps = 0
        done = False
        last_event = 0
        reason: str | None = None

        try:
            for steps in range(1, max_steps + 1):
                joints = robot.get_joint_positions()
                if joints is None:
                    reason = "Robot joint positions unavailable during pick-place"
                    break
                object_bbox = _compute_world_bbox(object_prim_path)
                object_center = object_bbox["center"]
                max_center_z = max(max_center_z, object_center[2])
                current_picking_position = (
                    picking_position
                    if explicit_picking_position is not None
                    else object_center
                )
                actions = controller.forward(
                    picking_position=np.array(current_picking_position, dtype=np.float32),
                    placing_position=np.array(target_position, dtype=np.float32),
                    current_joint_positions=np.asarray(joints, dtype=np.float32),
                    end_effector_offset=end_effector_offset,
                    end_effector_orientation=end_effector_orientation,
                )
                try:
                    robot.apply_action(actions)
                except Exception:
                    controller_obj = robot.get_articulation_controller()
                    controller_obj.apply_action(actions)
                last_event = int(controller.get_current_event())
                await app.next_update_async()
                if controller.is_done():
                    done = True
                    break

            final_bbox = _compute_world_bbox(object_prim_path)
            final_center = final_bbox["center"]
            final_distance = _distance3(final_center, target_position)
            max_lift_delta = max_center_z - initial_center[2]
            lifted = max_lift_delta >= lift_height_tolerance
            placed = final_distance <= position_tolerance
            ok = done and lifted and placed
            if reason is None and not ok:
                if not done:
                    reason = f"Official PickPlaceController did not finish within {max_steps} steps (event={last_event})"
                elif not lifted:
                    reason = (
                        "Object was not lifted by the gripper "
                        f"(max_lift_delta={max_lift_delta:.4f}m < {lift_height_tolerance:.4f}m)"
                    )
                elif not placed:
                    reason = (
                        "Object final bbox center is outside target tolerance "
                        f"(distance={final_distance:.4f}m > {position_tolerance:.4f}m)"
                    )
        finally:
            if not was_playing:
                timeline.pause()

        return {
            "ok": bool(ok),
            "robot_prim_path": robot_prim_path,
            "object_prim_path": object_prim_path,
            "target_position": target_position,
            "controller": (
                "isaacsim.robot.manipulators.examples.franka.controllers."
                "PickPlaceController"
            ),
            "gripper": "ParallelGripper",
            "uses_kinematic_carry": False,
            "steps": int(steps),
            "done": bool(done),
            "placed": bool(placed),
            "lifted": bool(lifted),
            "initial_object_position": [float(v) for v in initial_center],
            "final_object_position": [float(v) for v in final_center],
            "final_distance": float(final_distance),
            "max_lift_delta": float(max_lift_delta),
            "object_bbox_size": [float(v) for v in object_bbox_size],
            "picking_position": [float(v) for v in picking_position],
            "picking_position_source": picking_position_source,
            "end_effector_initial_height": float(resolved_hover_height),
            "end_effector_initial_height_source": hover_height_source,
            "end_effector_orientation": (
                [float(v) for v in end_effector_orientation.tolist()]
                if end_effector_orientation is not None
                else None
            ),
            "diagnostics": diagnostics,
            "reason": reason,
        }

    async def install_franka_pick_place_playback_demo(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Install a persistent playback-tick Franka pick/place demo.

        Unlike ``run_franka_pick_place``, this endpoint returns immediately
        after installing an update subscription. The controller advances only
        while the Kit timeline is playing, so Isaac Sim's GUI Play button and
        the MCP ``simulation_play`` tool both drive the same demo.
        """
        import numpy as np
        import omni.kit.app

        robot_prim_path = str(request.get("robot_prim_path", "/World/Franka"))
        object_prim_path = str(request.get("object_prim_path", "/World/PickCube"))
        target_position = [float(v) for v in request.get("target_position", [0.45, -0.35, 0.02575])]
        object_initial_position = [
            float(v) for v in request.get("object_initial_position", [0.3, 0.35, 0.02575])
        ]
        if len(target_position) != 3:
            raise ValueError("target_position must be [x, y, z]")
        if len(object_initial_position) != 3:
            raise ValueError("object_initial_position must be [x, y, z]")
        _assert_franka_family_pick_place_robot(
            request.get("robot_description", "Franka"),
            endpoint="franka_pick_place_demo",
        )

        self._clear_pick_place_demo_subscription()
        _assert_articulation(robot_prim_path)
        if bool(request.get("create_demo_scene", True)):
            _ensure_franka_pick_place_demo_scene(
                object_prim_path=object_prim_path,
                object_initial_position=object_initial_position,
                object_size=float(request.get("object_size", 0.04)),
                object_asset_url=request.get("object_asset_url"),
                grid_asset_url=request.get("grid_asset_url"),
            )
        _assert_prim_exists(object_prim_path)
        _ensure_pickable_physics(object_prim_path)

        classes = _resolve_official_franka_pick_place_classes()
        robot = classes.single_articulation(robot_prim_path)
        await _ensure_articulation_ready(robot, robot_prim_path, max_frames=180)

        initial_joints = robot.get_joint_positions()
        if initial_joints is None:
            raise ValueError("Robot joint positions unavailable while installing demo")
        initial_joints = np.asarray(initial_joints, dtype=np.float32).copy()

        robot_description = str(request.get("robot_description", "Franka"))
        gripper = _create_franka_parallel_gripper(
            classes,
            robot,
            robot_prim_path,
            robot_description=robot_description,
        )
        _open_franka_gripper(robot, gripper)

        _set_prim_world_translate(object_prim_path, object_initial_position)
        _zero_rigid_body_velocity(object_prim_path)
        initial_bbox = _compute_world_bbox(object_prim_path)
        object_bbox_size = initial_bbox["size"]
        picking_raw = request.get("picking_position")
        explicit_picking_position = picking_raw is not None
        picking_position = (
            [float(v) for v in picking_raw]
            if explicit_picking_position
            else list(initial_bbox["center"])
        )
        resolved_hover_height = _resolve_franka_pick_place_hover_height(
            explicit_height=(
                float(request["end_effector_initial_height"])
                if request.get("end_effector_initial_height") is not None
                else None
            ),
            picking_z=float(picking_position[2]),
            target_z=float(target_position[2]),
        )
        diagnostics = _build_franka_pick_place_diagnostics(
            object_bbox_size,
            picking_position_source="explicit" if explicit_picking_position else "bbox_center",
        )
        diagnostics["end_effector_initial_height"] = resolved_hover_height
        diagnostics["end_effector_initial_height_source"] = (
            "explicit"
            if request.get("end_effector_initial_height") is not None
            else (
                "official_default"
                if math.isclose(resolved_hover_height, 0.3, rel_tol=0.0, abs_tol=1e-9)
                else "auto_above_pick_place"
            )
        )
        diagnostics["playback_mode"] = "app_update_subscription"

        end_effector_offset_raw = request.get("end_effector_offset")
        end_effector_offset = (
            np.array([float(v) for v in end_effector_offset_raw], dtype=np.float32)
            if end_effector_offset_raw is not None
            else None
        )
        orientation_raw = request.get("end_effector_orientation")
        end_effector_orientation = (
            np.array([float(v) for v in orientation_raw], dtype=np.float32)
            if orientation_raw is not None
            else None
        )
        events_dt = request.get("events_dt")
        if events_dt is not None:
            events_dt = [float(v) for v in events_dt]
        diagnostics["requested_pick_strategy"] = _franka_pick_place_strategy_diagnostics(
            picking_position_source="explicit" if explicit_picking_position else "bbox_center",
            picking_position=picking_position,
            object_initial_position=object_initial_position,
            target_position=target_position,
            end_effector_initial_height=resolved_hover_height,
            end_effector_initial_height_source=diagnostics["end_effector_initial_height_source"],
            end_effector_offset=end_effector_offset,
            end_effector_orientation=end_effector_orientation,
            events_dt=events_dt,
            max_steps=int(request.get("max_steps", 1800)),
            reset_on_play=bool(request.get("reset_on_play", True)),
        )

        controller = _create_franka_pick_place_controller(
            classes=classes,
            robot=robot,
            gripper=gripper,
            hover_height=resolved_hover_height,
            events_dt=events_dt,
            robot_description=robot_description,
        )

        app = omni.kit.app.get_app()
        holder: dict[str, Any] = {}

        def _on_update(_event: Any) -> None:
            state = self._pick_place_demo
            if state is None or state.subscription is not holder.get("subscription"):
                return
            _tick_franka_pick_place_demo(state)

        subscription = app.get_update_event_stream().create_subscription_to_pop(
            _on_update,
            name="mcp_franka_pick_place_playback_demo",
        )
        holder["subscription"] = subscription
        self._pick_place_demo = _FrankaPickPlaceDemoState(
            request=dict(request),
            robot=robot,
            gripper=gripper,
            controller=controller,
            subscription=subscription,
            robot_description=robot_description,
            robot_prim_path=robot_prim_path,
            object_prim_path=object_prim_path,
            target_position=target_position,
            object_initial_position=object_initial_position,
            object_bbox_size=[float(v) for v in object_bbox_size],
            initial_joint_positions=initial_joints,
            picking_position=picking_position,
            explicit_picking_position=explicit_picking_position,
            end_effector_offset=end_effector_offset,
            end_effector_orientation=end_effector_orientation,
            end_effector_initial_height=resolved_hover_height,
            diagnostics=diagnostics,
            max_steps=int(request.get("max_steps", 1800)),
            position_tolerance=float(request.get("position_tolerance", 0.05)),
            lift_height_tolerance=float(request.get("lift_height_tolerance", 0.03)),
            reset_on_play=bool(request.get("reset_on_play", True)),
            initial_object_position=list(initial_bbox["center"]),
            final_object_position=list(initial_bbox["center"]),
            last_object_bbox_center=list(initial_bbox["center"]),
            max_center_z=float(initial_bbox["center"][2]),
        )
        return _franka_pick_place_demo_status(self._pick_place_demo)

    async def reset_pick_place_demo(self) -> dict[str, Any]:
        state = self._pick_place_demo
        if state is None:
            raise ValueError("No Franka pick/place playback demo is installed")
        _reset_franka_pick_place_demo_state(state)
        return _franka_pick_place_demo_status(state)

    async def get_pick_place_demo_status(self) -> dict[str, Any]:
        state = self._pick_place_demo
        if state is None:
            raise ValueError("No Franka pick/place playback demo is installed")
        return _franka_pick_place_demo_status(state)

    def _clear_pick_place_demo_subscription(self) -> None:
        state = self._pick_place_demo
        if state is not None:
            try:
                state.subscription = None
            except Exception:  # noqa: BLE001
                pass
        self._pick_place_demo = None

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


def _resolve_official_franka_pick_place_classes() -> _OfficialFrankaPickPlaceClasses:
    """Resolve Isaac Sim 5.1 official Franka PickPlace classes lazily."""
    controller_mod = importlib.import_module(
        "isaacsim.robot.manipulators.examples.franka.controllers.pick_place_controller"
    )
    gripper_mod = importlib.import_module(
        "isaacsim.robot.manipulators.grippers.parallel_gripper"
    )
    prims_mod = importlib.import_module("isaacsim.core.prims")
    return _OfficialFrankaPickPlaceClasses(
        pick_place_controller=controller_mod.PickPlaceController,
        parallel_gripper=gripper_mod.ParallelGripper,
        single_articulation=prims_mod.SingleArticulation,
    )


def _assert_prim_exists(prim_path: str) -> None:
    import omni.usd

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")


def _ensure_pickable_physics(prim_path: str) -> None:
    """Best-effort physical setup matching official DynamicCuboid assumptions.

    The official PickPlace task creates a dynamic cuboid, so arbitrary existing
    prims need at least RigidBodyAPI on the root and CollisionAPI on visible
    geometry. This helper authors schema only; it never edits object transform.
    """
    import omni.usd
    from pxr import Usd, UsdGeom, UsdPhysics

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")

    if not root.HasAPI(UsdPhysics.RigidBodyAPI):
        body = UsdPhysics.RigidBodyAPI.Apply(root)
        enabled = body.GetRigidBodyEnabledAttr()
        if enabled and enabled.IsValid():
            enabled.Set(True)

    applied_collision = False
    for prim in Usd.PrimRange(root):
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            applied_collision = True
            continue
        if prim.IsA(UsdGeom.Gprim):
            UsdPhysics.CollisionAPI.Apply(prim)
            applied_collision = True
    if not applied_collision and root.IsA(UsdGeom.Gprim):
        UsdPhysics.CollisionAPI.Apply(root)


def _compute_world_bbox(prim_path: str) -> dict[str, list[float]]:
    import omni.usd
    from pxr import Usd, UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")

    purposes = [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy]
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes)
    aligned = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    minimum = aligned.GetMin()
    maximum = aligned.GetMax()
    if aligned.IsEmpty():
        matrix = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        )
        translate = matrix.ExtractTranslation()
        center = [float(translate[0]), float(translate[1]), float(translate[2])]
        return {"min": center, "max": center, "center": center, "size": [0.0, 0.0, 0.0]}

    min_list = [float(minimum[0]), float(minimum[1]), float(minimum[2])]
    max_list = [float(maximum[0]), float(maximum[1]), float(maximum[2])]
    center = [
        (min_list[0] + max_list[0]) * 0.5,
        (min_list[1] + max_list[1]) * 0.5,
        (min_list[2] + max_list[2]) * 0.5,
    ]
    size = [
        max_list[0] - min_list[0],
        max_list[1] - min_list[1],
        max_list[2] - min_list[2],
    ]
    return {"min": min_list, "max": max_list, "center": center, "size": size}


def _build_franka_pick_place_diagnostics(
    bbox_size: list[float],
    *,
    picking_position_source: str,
) -> dict[str, Any]:
    """Compare a candidate object with the official Franka block examples."""
    official_block_size_m = 0.0515
    franka_nominal_gripper_width_m = 0.10
    low_object_height_warn_m = 0.025

    size = [float(v) for v in bbox_size]
    horizontal = size[:2]
    largest_horizontal = max(horizontal) if horizontal else 0.0
    height = size[2] if len(size) >= 3 else 0.0
    warnings: list[str] = []
    hints: list[str] = []

    if largest_horizontal > franka_nominal_gripper_width_m:
        warnings.append(
            "Object horizontal bbox is wider than the Franka gripper nominal opening "
            f"({largest_horizontal:.4f}m > {franka_nominal_gripper_width_m:.4f}m)."
        )
    if height < low_object_height_warn_m:
        warnings.append(
            "Object is flatter than the official block-stacking cube; "
            f"height {height:.4f}m can make the parallel fingers collide with the table "
            "or close without contact."
        )
    if picking_position_source != "explicit":
        hints.append(
            "Pass an explicit picking_position when the visual grasp point should differ "
            "from the world bbox center."
        )
    hints.append(
        "For official-example validation, use a DynamicCuboid-like block around "
        f"{official_block_size_m:.4f}m on each side."
    )

    return {
        "official_reference": "Isaac Sim Franka Cortex Block Stacking",
        "official_block_size_m": official_block_size_m,
        "franka_nominal_gripper_width_m": franka_nominal_gripper_width_m,
        "bbox_size": size,
        "picking_position_source": picking_position_source,
        "warnings": warnings,
        "hints": hints,
    }


def _franka_pick_place_strategy_diagnostics(
    *,
    picking_position_source: str,
    picking_position: object,
    object_initial_position: object,
    target_position: object,
    end_effector_initial_height: float,
    end_effector_initial_height_source: str,
    end_effector_offset: object | None,
    end_effector_orientation: object | None,
    events_dt: object | None,
    max_steps: int,
    reset_on_play: bool | None = None,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "picking_position_source": str(picking_position_source),
        "picking_position": _float_list_or_none(picking_position),
        "object_initial_position": _float_list_or_none(object_initial_position),
        "target_position": _float_list_or_none(target_position),
        "end_effector_initial_height": float(end_effector_initial_height),
        "end_effector_initial_height_source": str(end_effector_initial_height_source),
        "end_effector_offset": _float_list_or_none(end_effector_offset),
        "end_effector_orientation": _float_list_or_none(end_effector_orientation),
        "events_dt": _float_list_or_none(events_dt),
        "max_steps": int(max_steps),
    }
    if reset_on_play is not None:
        diagnostics["reset_on_play"] = bool(reset_on_play)
    return diagnostics


def _float_list_or_none(value: object | None) -> list[float] | None:
    if value is None:
        return None
    return [float(v) for v in value]  # type: ignore[union-attr]


def _finite_float_triplet_or_none(value: object | None) -> list[float] | None:
    values = _float_list_or_none(value)
    if values is None or len(values) < 3:
        return None
    triplet = [float(v) for v in values[:3]]
    if not all(math.isfinite(v) for v in triplet):
        return None
    return triplet


def _resolve_franka_pick_place_hover_height(
    *,
    explicit_height: float | None,
    picking_z: float,
    target_z: float,
) -> float:
    """Resolve PickPlaceController's absolute-world hover height.

    Isaac's official default is z=0.3m because the tutorial cube sits on the
    ground. For table-top tasks this absolute value can be below the object,
    so the MCP wrapper chooses a hover height above both pick and place z.
    """
    if explicit_height is not None:
        return float(explicit_height)
    return max(0.3, float(picking_z) + 0.25, float(target_z) + 0.25)


def _distance3(a: list[float], b: list[float]) -> float:
    return math.sqrt(
        (float(a[0]) - float(b[0])) ** 2
        + (float(a[1]) - float(b[1])) ** 2
        + (float(a[2]) - float(b[2])) ** 2
    )


def _ensure_franka_pick_place_demo_scene(
    *,
    object_prim_path: str,
    object_initial_position: list[float],
    object_size: float,
    object_asset_url: str | None,
    grid_asset_url: str | None,
) -> None:
    """Create the demo object, physics scene, grid reference, and light if missing."""
    import omni.usd
    from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdPhysics

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    if not stage.GetPrimAtPath("/World").IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path("/World"))
    if not stage.GetPrimAtPath("/World/PhysicsScene").IsValid():
        UsdPhysics.Scene.Define(stage, Sdf.Path("/World/PhysicsScene"))
    if not stage.GetPrimAtPath("/World/DemoLight").IsValid():
        light = UsdLux.DistantLight.Define(stage, Sdf.Path("/World/DemoLight"))
        light.CreateIntensityAttr().Set(3000.0)

    grid_path = "/World/FlatGrid"
    if not stage.GetPrimAtPath(grid_path).IsValid():
        if not grid_asset_url:
            raise ValueError("grid_asset_url is required when create_demo_scene=True")
        grid = UsdGeom.Xform.Define(stage, Sdf.Path(grid_path))
        grid.GetPrim().GetReferences().AddReference(str(grid_asset_url))

    _ensure_parent_xform(stage, object_prim_path)
    prim = stage.GetPrimAtPath(object_prim_path)
    if not prim.IsValid():
        if object_asset_url:
            prim = UsdGeom.Xform.Define(stage, Sdf.Path(object_prim_path)).GetPrim()
            prim.GetReferences().AddReference(str(object_asset_url))
        else:
            prim = _define_pick_place_demo_cube(stage, object_prim_path, object_size)
    _set_prim_world_translate(object_prim_path, object_initial_position)
    if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
        body = UsdPhysics.RigidBodyAPI.Apply(prim)
        body.CreateRigidBodyEnabledAttr(True)
    if not prim.HasAPI(UsdPhysics.CollisionAPI):
        UsdPhysics.CollisionAPI.Apply(prim)
    mass = UsdPhysics.MassAPI.Apply(prim)
    mass.CreateMassAttr().Set(0.05)
    prim.GetAttribute("physics:velocity").Set(Gf.Vec3f(0.0, 0.0, 0.0)) if prim.GetAttribute("physics:velocity").IsValid() else prim.CreateAttribute("physics:velocity", Sdf.ValueTypeNames.Vector3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))
    prim.GetAttribute("physics:angularVelocity").Set(Gf.Vec3f(0.0, 0.0, 0.0)) if prim.GetAttribute("physics:angularVelocity").IsValid() else prim.CreateAttribute("physics:angularVelocity", Sdf.ValueTypeNames.Vector3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))


def _define_pick_place_demo_cube(stage: Any, prim_path: str, object_size: float) -> Any:
    """Create a small rigid cube that fits the default Franka gripper opening."""
    from pxr import UsdGeom

    cube = UsdGeom.Cube.Define(stage, prim_path)
    cube.CreateSizeAttr(float(object_size))
    return cube.GetPrim()


def _create_franka_parallel_gripper(
    classes: _OfficialFrankaPickPlaceClasses,
    robot: Any,
    robot_prim_path: str,
    *,
    robot_description: str = "Franka",
) -> Any:
    import numpy as np

    gripper_spec = _franka_parallel_gripper_spec(robot_description)
    use_absolute_targets = str(robot_description or "").strip().lower() == "fr3"
    gripper = classes.parallel_gripper(
        end_effector_prim_path=f"{robot_prim_path}/{gripper_spec.end_effector_prim_name}",
        joint_prim_names=list(gripper_spec.joint_prim_names),
        joint_opened_positions=np.array([0.05, 0.05], dtype=np.float32),
        joint_closed_positions=np.array([0.0, 0.0], dtype=np.float32),
        action_deltas=None if use_absolute_targets else np.array([0.05, 0.05], dtype=np.float32),
    )
    _initialize_franka_parallel_gripper(gripper, robot)
    return gripper


def _initialize_franka_parallel_gripper(gripper: Any, robot: Any) -> None:
    cached_positions = robot.get_joint_positions()
    if cached_positions is not None:
        setattr(gripper, "_mcp_last_joint_positions", cached_positions)

    def _get_joint_positions_with_cache() -> Any:
        positions = robot.get_joint_positions()
        if positions is not None:
            setattr(gripper, "_mcp_last_joint_positions", positions)
            return positions
        return getattr(gripper, "_mcp_last_joint_positions", None)

    gripper.initialize(
        articulation_apply_action_func=robot.apply_action,
        get_joint_positions_func=_get_joint_positions_with_cache,
        set_joint_positions_func=robot.set_joint_positions,
        dof_names=list(robot.dof_names or []),
    )


def _franka_parallel_gripper_has_joint_indices(gripper: Any) -> bool:
    """Return whether Isaac's ParallelGripper has resolved articulation DOFs.

    Isaac Sim stores these as a private field, with a misspelled
    ``_joint_dof_indicies`` name in some releases. If the field is absent, treat
    the gripper as ready so compatible releases without that private cache keep
    working.
    """
    saw_index_cache = False
    for attr_name in ("_joint_dof_indicies", "_joint_dof_indices"):
        if not hasattr(gripper, attr_name):
            continue
        saw_index_cache = True
        value = getattr(gripper, attr_name)
        if value is None:
            return False
        try:
            if len(value) == 0:
                return False
        except TypeError:
            pass
    return True


def _ensure_franka_pick_place_demo_gripper_ready(
    state: _FrankaPickPlaceDemoState,
) -> bool:
    """Refresh demo gripper/controller wrappers after physics initializes.

    A Stop -> reset -> Play proof cycle can recreate the articulation/gripper
    while the timeline is stopped. On some Isaac Sim builds, ParallelGripper then
    keeps ``_joint_dof_indicies=None`` until physics is live, and the official
    PickPlaceController later fails inside ``gripper.forward("close")``. Once
    joint positions are available again, reinitializing the gripper is enough;
    if not, rebuild the wrapper/controller on the now-live articulation.
    """
    if _franka_parallel_gripper_has_joint_indices(state.gripper):
        return False

    try:
        _ensure_initialized(state.robot)
    except Exception as exc:  # noqa: BLE001
        logger.debug("demo articulation initialize before gripper refresh failed: %s", exc)
    try:
        _initialize_franka_parallel_gripper(state.gripper, state.robot)
    except Exception as exc:  # noqa: BLE001
        logger.debug("demo gripper reinitialize failed: %s", exc)

    if not _franka_parallel_gripper_has_joint_indices(state.gripper):
        classes = _resolve_official_franka_pick_place_classes()
        state.robot = classes.single_articulation(state.robot_prim_path)
        _ensure_initialized(state.robot)
        state.gripper = _create_franka_parallel_gripper(
            classes,
            state.robot,
            state.robot_prim_path,
            robot_description=state.robot_description,
        )
        events_dt = state.request.get("events_dt")
        if events_dt is not None:
            events_dt = [float(v) for v in events_dt]
        state.controller = _create_franka_pick_place_controller(
            classes=classes,
            robot=state.robot,
            gripper=state.gripper,
            hover_height=state.end_effector_initial_height,
            events_dt=events_dt,
            robot_description=state.robot_description,
        )

    if not _franka_parallel_gripper_has_joint_indices(state.gripper):
        raise RuntimeError("Franka playback gripper DOF indices are unavailable")

    state.playback_wrapper_refresh_count += 1
    state.diagnostics["playback_wrapper_refresh_count"] = state.playback_wrapper_refresh_count
    return True


def _create_franka_pick_place_controller(
    *,
    classes: _OfficialFrankaPickPlaceClasses,
    robot: Any,
    gripper: Any,
    hover_height: float,
    events_dt: list[float] | None,
    robot_description: str = "Franka",
) -> Any:
    if str(robot_description or "").strip().lower() == "fr3":
        return _create_fr3_pick_place_controller(
            name="mcp_gui_franka_pick_place_demo",
            robot=robot,
            gripper=gripper,
            hover_height=hover_height,
            events_dt=events_dt,
            robot_description=robot_description,
        )
    return classes.pick_place_controller(
        name="mcp_gui_franka_pick_place_demo",
        gripper=gripper,
        robot_articulation=robot,
        end_effector_initial_height=float(hover_height),
        events_dt=events_dt,
    )


def _franka_pick_place_default_events_dt() -> list[float]:
    return [0.008, 0.005, 1.0, 0.1, 0.05, 0.05, 0.0025, 1.0, 0.008, 0.08]


def _create_fr3_pick_place_controller(
    *,
    name: str,
    robot: Any,
    gripper: Any,
    hover_height: float,
    events_dt: list[float] | None,
    robot_description: str,
) -> Any:
    import isaacsim.robot.manipulators.controllers as manipulators_controllers
    import isaacsim.robot_motion.motion_generation as mg

    _, interface_config_loader, _ = _resolve_lula_modules()
    if interface_config_loader is None:
        raise ValueError("FR3 pick/place requires Isaac Sim Lula/RMPflow config loader")
    cfg = _resolve_lula_config(interface_config_loader, robot_description)
    rmp_flow = mg.lula.motion_policies.RmpFlow(**cfg)
    articulation_rmp = mg.ArticulationMotionPolicy(robot, rmp_flow, 1.0 / 60.0)
    cspace_controller = mg.MotionPolicyController(
        name=name + "_fr3_cspace_controller",
        articulation_motion_policy=articulation_rmp,
    )
    default_position, default_orientation = robot.get_world_pose()
    cspace_controller.get_motion_policy().set_robot_base_pose(
        robot_position=default_position,
        robot_orientation=default_orientation,
    )
    return manipulators_controllers.PickPlaceController(
        name=name,
        cspace_controller=cspace_controller,
        gripper=gripper,
        end_effector_initial_height=float(hover_height),
        events_dt=events_dt if events_dt is not None else _franka_pick_place_default_events_dt(),
    )


def _open_franka_gripper(robot: Any, gripper: Any) -> None:
    try:
        positions = robot.get_joint_positions()
        if positions is not None:
            setattr(gripper, "_mcp_last_joint_positions", positions)
        robot.apply_action(gripper.forward(action="open"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("demo gripper open failed: %s", exc)


def _set_prim_world_translate(prim_path: str, position: list[float]) -> None:
    import omni.usd
    from pxr import Gf, UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")
    attr = prim.GetAttribute("xformOp:translate")
    if not attr.IsValid():
        attr = UsdGeom.Xformable(prim).AddTranslateOp()
    attr.Set(Gf.Vec3d(float(position[0]), float(position[1]), float(position[2])))


def _set_prim_uniform_scale(prim: Any, scale: float) -> None:
    from pxr import Gf, UsdGeom

    attr = prim.GetAttribute("xformOp:scale")
    if not attr.IsValid():
        attr = UsdGeom.Xformable(prim).AddScaleOp()
    attr.Set(Gf.Vec3f(float(scale), float(scale), float(scale)))


def _zero_rigid_body_velocity(prim_path: str) -> None:
    import omni.usd
    from pxr import Gf, Sdf

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return
    for attr_name in ("physics:velocity", "physics:angularVelocity"):
        attr = prim.GetAttribute(attr_name)
        if not attr.IsValid():
            attr = prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Vector3f)
        attr.Set(Gf.Vec3f(0.0, 0.0, 0.0))


def _reset_franka_pick_place_demo_state(state: _FrankaPickPlaceDemoState) -> None:
    events_dt = state.request.get("events_dt")
    if events_dt is not None:
        events_dt = [float(v) for v in events_dt]
    classes = _resolve_official_franka_pick_place_classes()
    state.status = "resetting"
    state.steps = 0
    state.controller_event = 0
    state.done = False
    state.placed = False
    state.lifted = False
    state.final_distance = _distance3(state.object_initial_position, state.target_position)
    state.max_lift_delta = 0.0
    state.max_center_z = float(state.object_initial_position[2])
    state.last_error = None
    state.event_tick_counts.clear()
    state.event_first_steps.clear()
    state.event_last_steps.clear()
    state.progress_samples.clear()
    state.max_joint_delta_from_initial = 0.0
    state.max_action_joint_position_delta = 0.0
    state.action_joint_positions_seen = False
    state.min_end_effector_distance_to_pick = None
    state.min_end_effector_distance_to_target = None
    state.min_end_effector_distance_to_object = None
    state.min_end_effector_xy_distance_to_object = None
    state.min_abs_end_effector_z_distance_to_object = None
    state.signed_end_effector_z_distance_at_min_abs_to_object = None
    state.end_effector_object_delta_at_min_distance = None
    state.end_effector_object_delta_at_min_xy_distance = None
    state.end_effector_object_delta_at_min_abs_z = None
    state.min_end_effector_distance_to_object_during_closed_gripper = None
    state.min_end_effector_xy_distance_to_object_during_closed_gripper = None
    state.min_abs_end_effector_z_distance_to_object_during_closed_gripper = None
    state.signed_end_effector_z_distance_at_min_abs_during_closed_gripper = None
    state.end_effector_object_delta_at_min_distance_during_closed_gripper = None
    state.end_effector_object_delta_at_min_xy_distance_during_closed_gripper = None
    state.end_effector_object_delta_at_min_abs_z_during_closed_gripper = None
    state.max_object_lift_delta_during_closed_gripper = None
    state.max_object_xy_motion_during_closed_gripper = None
    state.end_effector_pose_seen = False
    state.gripper_aperture_seen = False
    state.action_gripper_aperture_seen = False
    state.gripper_closed_on_object_width_seen = False
    state.min_gripper_aperture_m = None
    state.max_gripper_aperture_m = None
    state.min_action_gripper_aperture_m = None
    state.max_action_gripper_aperture_m = None
    state.min_gripper_object_width_margin_m = None
    state.min_action_gripper_object_width_margin_m = None
    state.playback_wrapper_refresh_count = 0
    state.diagnostics.pop("playback_wrapper_refresh_count", None)
    _set_prim_world_translate(state.object_prim_path, state.object_initial_position)
    _zero_rigid_body_velocity(state.object_prim_path)
    try:
        state.robot = classes.single_articulation(state.robot_prim_path)
        _ensure_initialized(state.robot)
        state.gripper = _create_franka_parallel_gripper(
            classes,
            state.robot,
            state.robot_prim_path,
            robot_description=state.robot_description,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("demo reset wrapper recreation failed; reusing previous wrapper: %s", exc)
    _apply_joint_positions(state.robot, state.initial_joint_positions)
    _open_franka_gripper(state.robot, state.gripper)
    state.controller = _create_franka_pick_place_controller(
        classes=classes,
        robot=state.robot,
        gripper=state.gripper,
        hover_height=state.end_effector_initial_height,
        events_dt=events_dt,
        robot_description=state.robot_description,
    )
    bbox = _compute_world_bbox(state.object_prim_path)
    state.object_bbox_size = [float(v) for v in bbox["size"]]
    state.initial_object_position = list(bbox["center"])
    state.final_object_position = list(bbox["center"])
    state.last_object_bbox_center = list(bbox["center"])
    state.max_center_z = float(bbox["center"][2])
    if not state.explicit_picking_position:
        state.picking_position = list(bbox["center"])
    state.status = "idle"


def _tick_franka_pick_place_demo(state: _FrankaPickPlaceDemoState) -> None:
    import numpy as np
    import omni.timeline

    timeline = omni.timeline.get_timeline_interface()
    if not timeline.is_playing():
        try:
            state.last_timeline_time = float(timeline.get_current_time())
        except Exception:  # noqa: BLE001
            pass
        return

    try:
        current_time = float(timeline.get_current_time())
    except Exception:  # noqa: BLE001
        current_time = state.last_timeline_time

    if (
        state.reset_on_play
        and state.status in {"done", "failed"}
        and (current_time < state.last_timeline_time or current_time <= 0.05)
    ):
        _reset_franka_pick_place_demo_state(state)
        state.last_timeline_time = current_time
        return

    if state.status in {"done", "failed", "resetting"}:
        state.last_timeline_time = current_time
        return

    try:
        if state.steps >= state.max_steps:
            _refresh_franka_pick_place_demo_metrics(state)
            state.status = "failed"
            state.last_error = (
                "Official PickPlaceController did not finish within "
                f"{state.max_steps} playback ticks"
            )
            return

        joints = state.robot.get_joint_positions()
        if joints is None:
            try:
                _ensure_initialized(state.robot)
                joints = state.robot.get_joint_positions()
            except Exception as exc:  # noqa: BLE001
                state.last_error = f"Waiting for robot articulation after playback reset: {exc}"
                return
            if joints is None:
                state.last_error = "Waiting for robot articulation after playback reset"
                return
        if _ensure_franka_pick_place_demo_gripper_ready(state):
            joints = state.robot.get_joint_positions()
            if joints is None:
                state.last_error = "Waiting for robot articulation after playback gripper refresh"
                return
        state.last_error = None

        bbox = _compute_world_bbox(state.object_prim_path)
        object_center = list(bbox["center"])
        state.object_bbox_size = [float(v) for v in bbox["size"]]
        state.last_object_bbox_center = object_center
        state.max_center_z = max(state.max_center_z, float(object_center[2]))
        current_pick = state.picking_position if state.explicit_picking_position else object_center
        end_effector_position = _compute_franka_demo_end_effector_position(
            state.robot_prim_path,
            state.robot_description,
        )
        current_joints = np.asarray(joints, dtype=np.float32)
        setattr(state.gripper, "_mcp_last_joint_positions", current_joints)
        actions = state.controller.forward(
            picking_position=np.array(current_pick, dtype=np.float32),
            placing_position=np.array(state.target_position, dtype=np.float32),
            current_joint_positions=current_joints,
            end_effector_offset=state.end_effector_offset,
            end_effector_orientation=state.end_effector_orientation,
        )
        joint_progress = _franka_pick_place_demo_joint_progress(
            current_joint_positions=current_joints,
            initial_joint_positions=state.initial_joint_positions,
            actions=actions,
        )
        gripper_progress = _franka_pick_place_demo_gripper_progress(
            robot=state.robot,
            current_joint_positions=current_joints,
            actions=actions,
            robot_description=state.robot_description,
        )
        try:
            state.robot.apply_action(actions)
        except Exception:
            state.robot.get_articulation_controller().apply_action(actions)

        state.steps += 1
        state.controller_event = int(state.controller.get_current_event())
        state.status = "picking" if state.controller_event < 4 else "placing"
        _record_franka_pick_place_demo_progress(
            state,
            event=state.controller_event,
            step=state.steps,
            timeline_time=current_time,
            object_center=object_center,
            joint_progress=joint_progress,
            gripper_progress=gripper_progress,
            current_pick=[float(v) for v in current_pick],
            end_effector_position=end_effector_position,
        )

        if state.controller.is_done():
            _finish_franka_pick_place_demo(state)
    except Exception as exc:  # noqa: BLE001
        state.status = "failed"
        state.last_error = str(exc)
        logger.error("Franka pick/place playback tick failed: %s", exc, exc_info=True)
    finally:
        state.last_timeline_time = current_time


def _finish_franka_pick_place_demo(state: _FrankaPickPlaceDemoState) -> None:
    _refresh_franka_pick_place_demo_metrics(state)
    state.done = True
    if state.lifted and state.placed:
        state.status = "done"
        state.last_error = None
    elif not state.lifted:
        state.status = "failed"
        state.last_error = (
            "Object was not lifted by the gripper "
            f"(max_lift_delta={state.max_lift_delta:.4f}m < "
            f"{state.lift_height_tolerance:.4f}m)"
        )
    else:
        state.status = "failed"
        state.last_error = (
            "Object final bbox center is outside target tolerance "
            f"(distance={state.final_distance:.4f}m > "
            f"{state.position_tolerance:.4f}m)"
        )


def _refresh_franka_pick_place_demo_metrics(state: _FrankaPickPlaceDemoState) -> None:
    bbox = _compute_world_bbox(state.object_prim_path)
    final_center = list(bbox["center"])
    state.object_bbox_size = [float(v) for v in bbox["size"]]
    state.last_object_bbox_center = final_center
    initial_center = state.initial_object_position or state.object_initial_position
    state.final_object_position = final_center
    state.final_distance = _distance3(final_center, state.target_position)
    state.max_lift_delta = state.max_center_z - float(initial_center[2])
    state.lifted = state.max_lift_delta >= state.lift_height_tolerance
    state.placed = state.final_distance <= state.position_tolerance


def _record_franka_pick_place_demo_progress(
    state: _FrankaPickPlaceDemoState,
    *,
    event: int,
    step: int,
    timeline_time: float,
    object_center: list[float],
    joint_progress: dict[str, Any] | None = None,
    gripper_progress: dict[str, Any] | None = None,
    current_pick: list[float] | None = None,
    end_effector_position: list[float] | None = None,
) -> None:
    event = int(event)
    step = int(step)
    joint_progress = joint_progress or {}
    gripper_progress = gripper_progress or {}
    current_pick = current_pick or getattr(state, "picking_position", None) or object_center
    state.event_tick_counts[event] = state.event_tick_counts.get(event, 0) + 1
    state.event_first_steps.setdefault(event, step)
    state.event_last_steps[event] = step
    joint_delta = float(joint_progress.get("joint_delta_from_initial_max_abs", 0.0) or 0.0)
    action_delta = float(joint_progress.get("action_joint_position_delta_max_abs", 0.0) or 0.0)
    state.max_joint_delta_from_initial = max(
        float(getattr(state, "max_joint_delta_from_initial", 0.0)),
        joint_delta,
    )
    state.max_action_joint_position_delta = max(
        float(getattr(state, "max_action_joint_position_delta", 0.0)),
        action_delta,
    )
    if bool(joint_progress.get("action_joint_positions_present", False)):
        state.action_joint_positions_seen = True
    ee_distance_to_pick: float | None = None
    ee_distance_to_target: float | None = None
    ee_distance_to_object: float | None = None
    ee_xy_distance_to_object: float | None = None
    ee_z_delta_to_object: float | None = None
    ee_abs_z_distance_to_object: float | None = None
    ee_object_delta: list[float] | None = None
    if end_effector_position is not None:
        state.end_effector_pose_seen = True
        ee_object_delta = [
            float(end_effector_position[0]) - float(object_center[0]),
            float(end_effector_position[1]) - float(object_center[1]),
            float(end_effector_position[2]) - float(object_center[2]),
        ]
        ee_distance_to_pick = _distance3(end_effector_position, current_pick)
        ee_distance_to_target = _distance3(end_effector_position, state.target_position)
        ee_distance_to_object = _distance3(end_effector_position, object_center)
        ee_xy_distance_to_object = math.sqrt(
            (
                float(end_effector_position[0])
                - float(object_center[0])
            ) ** 2
            + (
                float(end_effector_position[1])
                - float(object_center[1])
            ) ** 2
        )
        ee_z_delta_to_object = float(end_effector_position[2]) - float(object_center[2])
        ee_abs_z_distance_to_object = abs(ee_z_delta_to_object)
        state.min_end_effector_distance_to_pick = _min_optional_distance(
            getattr(state, "min_end_effector_distance_to_pick", None),
            ee_distance_to_pick,
        )
        state.min_end_effector_distance_to_target = _min_optional_distance(
            getattr(state, "min_end_effector_distance_to_target", None),
            ee_distance_to_target,
        )
        state.min_end_effector_distance_to_object = _min_optional_distance(
            getattr(state, "min_end_effector_distance_to_object", None),
            ee_distance_to_object,
        )
        current_min_distance = getattr(state, "min_end_effector_distance_to_object", None)
        if current_min_distance is None or ee_distance_to_object <= float(current_min_distance):
            state.end_effector_object_delta_at_min_distance = (
                list(ee_object_delta) if ee_object_delta is not None else None
            )
        current_min_xy = getattr(state, "min_end_effector_xy_distance_to_object", None)
        if current_min_xy is None or ee_xy_distance_to_object <= float(current_min_xy):
            state.min_end_effector_xy_distance_to_object = ee_xy_distance_to_object
            state.end_effector_object_delta_at_min_xy_distance = (
                list(ee_object_delta) if ee_object_delta is not None else None
            )
        current_min_z = getattr(state, "min_abs_end_effector_z_distance_to_object", None)
        if current_min_z is None or ee_abs_z_distance_to_object <= float(current_min_z):
            state.min_abs_end_effector_z_distance_to_object = ee_abs_z_distance_to_object
            state.signed_end_effector_z_distance_at_min_abs_to_object = (
                ee_z_delta_to_object
            )
            state.end_effector_object_delta_at_min_abs_z = (
                list(ee_object_delta) if ee_object_delta is not None else None
            )
    gripper_aperture = _optional_float(gripper_progress.get("gripper_aperture_m"))
    action_gripper_aperture = _optional_float(
        gripper_progress.get("action_gripper_aperture_m")
    )
    object_width = _franka_pick_place_object_grasp_width_m(
        getattr(state, "object_bbox_size", [])
    )
    initial_center = state.initial_object_position or state.object_initial_position
    gripper_object_width_margin: float | None = None
    action_gripper_object_width_margin: float | None = None
    if gripper_aperture is not None:
        state.gripper_aperture_seen = True
        state.min_gripper_aperture_m = _min_optional_distance(
            getattr(state, "min_gripper_aperture_m", None),
            gripper_aperture,
        )
        state.max_gripper_aperture_m = _max_optional_distance(
            getattr(state, "max_gripper_aperture_m", None),
            gripper_aperture,
        )
        if object_width is not None:
            gripper_object_width_margin = gripper_aperture - object_width
            state.min_gripper_object_width_margin_m = _min_optional_distance(
                getattr(state, "min_gripper_object_width_margin_m", None),
                gripper_object_width_margin,
            )
            if gripper_object_width_margin <= 0.0:
                state.gripper_closed_on_object_width_seen = True
                object_lift_delta = float(object_center[2]) - float(initial_center[2])
                object_xy_motion = math.sqrt(
                    (float(object_center[0]) - float(initial_center[0])) ** 2
                    + (float(object_center[1]) - float(initial_center[1])) ** 2
                )
                state.max_object_lift_delta_during_closed_gripper = (
                    _max_optional_distance(
                        getattr(
                            state,
                            "max_object_lift_delta_during_closed_gripper",
                            None,
                        ),
                        object_lift_delta,
                    )
                )
                state.max_object_xy_motion_during_closed_gripper = (
                    _max_optional_distance(
                        getattr(
                            state,
                            "max_object_xy_motion_during_closed_gripper",
                            None,
                        ),
                        object_xy_motion,
                    )
                )
                if ee_distance_to_object is not None:
                    current_min_distance = getattr(
                        state,
                        "min_end_effector_distance_to_object_during_closed_gripper",
                        None,
                    )
                    if current_min_distance is None or ee_distance_to_object < float(
                        current_min_distance
                    ):
                        state.min_end_effector_distance_to_object_during_closed_gripper = (
                            ee_distance_to_object
                        )
                        state.end_effector_object_delta_at_min_distance_during_closed_gripper = (
                            list(ee_object_delta) if ee_object_delta is not None else None
                        )
                if ee_xy_distance_to_object is not None:
                    current_min_xy = getattr(
                        state,
                        "min_end_effector_xy_distance_to_object_during_closed_gripper",
                        None,
                    )
                    if current_min_xy is None or ee_xy_distance_to_object < float(
                        current_min_xy
                    ):
                        state.min_end_effector_xy_distance_to_object_during_closed_gripper = (
                            ee_xy_distance_to_object
                        )
                        state.end_effector_object_delta_at_min_xy_distance_during_closed_gripper = (
                            list(ee_object_delta) if ee_object_delta is not None else None
                        )
                if ee_abs_z_distance_to_object is not None:
                    current_min_z = getattr(
                        state,
                        "min_abs_end_effector_z_distance_to_object_during_closed_gripper",
                        None,
                    )
                    if current_min_z is None or ee_abs_z_distance_to_object < float(
                        current_min_z
                    ):
                        state.min_abs_end_effector_z_distance_to_object_during_closed_gripper = (
                            ee_abs_z_distance_to_object
                        )
                        state.signed_end_effector_z_distance_at_min_abs_during_closed_gripper = (
                            ee_z_delta_to_object
                        )
                        state.end_effector_object_delta_at_min_abs_z_during_closed_gripper = (
                            list(ee_object_delta) if ee_object_delta is not None else None
                        )
    if action_gripper_aperture is not None:
        state.action_gripper_aperture_seen = True
        state.min_action_gripper_aperture_m = _min_optional_distance(
            getattr(state, "min_action_gripper_aperture_m", None),
            action_gripper_aperture,
        )
        state.max_action_gripper_aperture_m = _max_optional_distance(
            getattr(state, "max_action_gripper_aperture_m", None),
            action_gripper_aperture,
        )
        if object_width is not None:
            action_gripper_object_width_margin = action_gripper_aperture - object_width
            state.min_action_gripper_object_width_margin_m = _min_optional_distance(
                getattr(state, "min_action_gripper_object_width_margin_m", None),
                action_gripper_object_width_margin,
            )

    last_sample = state.progress_samples[-1] if state.progress_samples else {}
    should_sample = (
        not state.progress_samples
        or int(last_sample.get("controller_event", -1)) != event
        or step % _PICK_PLACE_PROGRESS_SAMPLE_INTERVAL_STEPS == 0
    )
    if not should_sample:
        return

    sample = {
        "step": step,
        "controller_event": event,
        "timeline_time": float(timeline_time),
        "status": state.status,
        "object_center": [float(v) for v in object_center],
        "lift_delta": float(object_center[2]) - float(initial_center[2]),
        "distance_to_target": _distance3(object_center, state.target_position),
        "end_effector_position": (
            [float(v) for v in end_effector_position]
            if end_effector_position is not None
            else None
        ),
        "end_effector_distance_to_pick": ee_distance_to_pick,
        "end_effector_distance_to_target": ee_distance_to_target,
        "end_effector_distance_to_object": ee_distance_to_object,
        "end_effector_object_delta": ee_object_delta,
        "end_effector_xy_distance_to_object": ee_xy_distance_to_object,
        "end_effector_z_delta_to_object": ee_z_delta_to_object,
        "end_effector_abs_z_distance_to_object": ee_abs_z_distance_to_object,
        "gripper_joint_indices": [
            int(v) for v in (gripper_progress.get("gripper_joint_indices") or [])
        ],
        "gripper_joint_names": [
            str(v) for v in (gripper_progress.get("gripper_joint_names") or [])
        ],
        "gripper_joint_positions": [
            float(v) for v in (gripper_progress.get("gripper_joint_positions") or [])
        ],
        "gripper_aperture_m": gripper_aperture,
        "action_gripper_joint_positions": [
            float(v)
            for v in (gripper_progress.get("action_gripper_joint_positions") or [])
        ],
        "action_gripper_aperture_m": action_gripper_aperture,
        "gripper_object_width_m": object_width,
        "gripper_object_width_margin_m": gripper_object_width_margin,
        "gripper_closed_on_object_width": (
            gripper_object_width_margin is not None
            and gripper_object_width_margin <= 0.0
        ),
        "action_gripper_object_width_margin_m": action_gripper_object_width_margin,
        "joint_delta_from_initial_max_abs": joint_delta,
        "joint_delta_from_initial_l2": float(
            joint_progress.get("joint_delta_from_initial_l2", 0.0) or 0.0
        ),
        "action_joint_positions_present": bool(
            joint_progress.get("action_joint_positions_present", False)
        ),
        "action_joint_position_delta_max_abs": action_delta,
        "action_joint_position_delta_l2": float(
            joint_progress.get("action_joint_position_delta_l2", 0.0) or 0.0
        ),
        "action_joint_position_count": int(
            joint_progress.get("action_joint_position_count", 0) or 0
        ),
    }
    state.progress_samples.append(sample)
    if len(state.progress_samples) > _PICK_PLACE_PROGRESS_SAMPLE_LIMIT:
        del state.progress_samples[:-_PICK_PLACE_PROGRESS_SAMPLE_LIMIT]


def _franka_pick_place_demo_joint_progress(
    *,
    current_joint_positions: Any,
    initial_joint_positions: Any,
    actions: Any,
) -> dict[str, Any]:
    current = _float_sequence(current_joint_positions)
    initial = _float_sequence(initial_joint_positions)
    joint_deltas = _finite_abs_deltas(current, initial)
    joint_delta_max = max(joint_deltas) if joint_deltas else 0.0
    joint_delta_l2 = math.sqrt(sum(delta * delta for delta in joint_deltas))

    action_positions = _float_sequence(getattr(actions, "joint_positions", None))
    action_indices = _int_sequence(getattr(actions, "joint_indices", None))
    action_current = current
    if action_positions and action_indices and len(action_positions) == len(action_indices):
        action_current = [
            current[index]
            for index in action_indices
            if 0 <= index < len(current)
        ]
    action_deltas = _finite_abs_deltas(action_positions, action_current)
    action_delta_max = max(action_deltas) if action_deltas else 0.0
    action_delta_l2 = math.sqrt(sum(delta * delta for delta in action_deltas))

    return {
        "joint_delta_from_initial_max_abs": float(joint_delta_max),
        "joint_delta_from_initial_l2": float(joint_delta_l2),
        "joint_position_count": len(current),
        "action_joint_positions_present": bool(action_positions),
        "action_joint_position_count": len(action_positions),
        "action_joint_position_delta_max_abs": float(action_delta_max),
        "action_joint_position_delta_l2": float(action_delta_l2),
        "action_joint_indices_present": bool(action_indices),
    }


def _franka_pick_place_demo_gripper_progress(
    *,
    robot: Any,
    current_joint_positions: Any,
    actions: Any,
    robot_description: object,
) -> dict[str, Any]:
    try:
        current = _float_sequence(current_joint_positions)
        gripper_indices, gripper_names, index_source = _franka_gripper_joint_indices(
            robot=robot,
            robot_description=robot_description,
            joint_count=len(current),
        )
        gripper_positions = [
            current[index] for index in gripper_indices if 0 <= index < len(current)
        ]
        action_gripper_positions = _franka_action_gripper_positions(
            actions=actions,
            gripper_indices=gripper_indices,
            current_count=len(current),
        )
        gripper_aperture = _franka_gripper_aperture_m(gripper_positions)
        action_gripper_aperture = _franka_gripper_aperture_m(action_gripper_positions)
        return {
            "gripper_joint_indices": [int(v) for v in gripper_indices],
            "gripper_joint_names": [str(v) for v in gripper_names],
            "gripper_joint_index_source": index_source,
            "gripper_joint_positions": [float(v) for v in gripper_positions],
            "gripper_aperture_m": gripper_aperture,
            "action_gripper_joint_positions": [
                float(v) for v in action_gripper_positions
            ],
            "action_gripper_aperture_m": action_gripper_aperture,
        }
    except Exception:  # noqa: BLE001
        logger.debug("Franka pick/place gripper telemetry unavailable", exc_info=True)
        return {}


def _franka_gripper_joint_indices(
    *,
    robot: Any,
    robot_description: object,
    joint_count: int,
) -> tuple[list[int], list[str], str]:
    dof_names = tuple(str(v) for v in (getattr(robot, "dof_names", None) or ()))
    if dof_names:
        spec = _franka_parallel_gripper_spec(robot_description)
        indices: list[int] = []
        for wanted_name in spec.joint_prim_names:
            for index, dof_name in enumerate(dof_names):
                if index in indices:
                    continue
                if (
                    dof_name == wanted_name
                    or dof_name.endswith(f"/{wanted_name}")
                    or dof_name.endswith(f".{wanted_name}")
                    or wanted_name in dof_name
                ):
                    indices.append(index)
                    break
        if indices:
            return indices, [dof_names[index] for index in indices], "spec_dof_name"

        fallback_indices = [
            index
            for index, dof_name in enumerate(dof_names)
            if "finger" in dof_name.lower() or "gripper" in dof_name.lower()
        ]
        if fallback_indices:
            return (
                fallback_indices,
                [dof_names[index] for index in fallback_indices],
                "name_contains_gripper",
            )

    if joint_count >= 9:
        indices = [joint_count - 2, joint_count - 1]
        names = [
            dof_names[index] if index < len(dof_names) else f"joint_{index}"
            for index in indices
        ]
        return indices, names, "tail_pair_fallback"
    return [], [], "unavailable"


def _franka_action_gripper_positions(
    *,
    actions: Any,
    gripper_indices: list[int],
    current_count: int,
) -> list[float]:
    action_positions = _float_sequence(getattr(actions, "joint_positions", None))
    if not action_positions or not gripper_indices:
        return []
    action_indices = _int_sequence(getattr(actions, "joint_indices", None))
    if action_indices and len(action_indices) == len(action_positions):
        by_index = {
            index: action_positions[position_index]
            for position_index, index in enumerate(action_indices)
        }
        return [
            by_index[index]
            for index in gripper_indices
            if index in by_index
        ]
    if len(action_positions) == current_count:
        return [
            action_positions[index]
            for index in gripper_indices
            if 0 <= index < len(action_positions)
        ]
    return []


def _franka_gripper_aperture_m(joint_positions: list[float]) -> float | None:
    if not joint_positions:
        return None
    return float(sum(max(0.0, float(value)) for value in joint_positions))


def _franka_pick_place_object_grasp_width_m(
    object_bbox_size: list[float],
) -> float | None:
    if len(object_bbox_size) < 2:
        return None
    return max(float(object_bbox_size[0]), float(object_bbox_size[1]))


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _min_optional_distance(current: float | None, candidate: float) -> float:
    if current is None:
        return float(candidate)
    return min(float(current), float(candidate))


def _max_optional_distance(current: float | None, candidate: float) -> float:
    if current is None:
        return float(candidate)
    return max(float(current), float(candidate))


def _franka_pick_place_contact_window_diagnostics(
    state: _FrankaPickPlaceDemoState,
) -> dict[str, Any]:
    object_width = _franka_pick_place_object_grasp_width_m(
        getattr(state, "object_bbox_size", [])
    )
    object_bbox_size = [float(v) for v in getattr(state, "object_bbox_size", [])]
    object_bbox_half_diagonal = (
        math.sqrt(sum(float(v) ** 2 for v in object_bbox_size[:3])) / 2.0
        if len(object_bbox_size) >= 3
        else None
    )
    closed_seen = bool(getattr(state, "gripper_closed_on_object_width_seen", False))
    min_distance = getattr(
        state,
        "min_end_effector_distance_to_object_during_closed_gripper",
        None,
    )
    min_xy_distance = getattr(
        state,
        "min_end_effector_xy_distance_to_object_during_closed_gripper",
        None,
    )
    object_half_width = object_width / 2.0 if object_width is not None else None
    object_half_height = (
        float(object_bbox_size[2]) / 2.0 if len(object_bbox_size) >= 3 else None
    )
    xy_margin = (
        float(min_xy_distance) - float(object_half_width)
        if min_xy_distance is not None and object_half_width is not None
        else None
    )
    min_abs_z_distance = getattr(
        state,
        "min_abs_end_effector_z_distance_to_object_during_closed_gripper",
        None,
    )
    if (
        min_abs_z_distance is None
        and min_distance is not None
        and min_xy_distance is not None
    ):
        min_abs_z_distance = math.sqrt(
            max(float(min_distance) ** 2 - float(min_xy_distance) ** 2, 0.0)
        )
    signed_z_distance = getattr(
        state,
        "signed_end_effector_z_distance_at_min_abs_during_closed_gripper",
        None,
    )
    min_distance_delta = getattr(
        state,
        "end_effector_object_delta_at_min_distance_during_closed_gripper",
        None,
    )
    min_xy_delta = getattr(
        state,
        "end_effector_object_delta_at_min_xy_distance_during_closed_gripper",
        None,
    )
    min_abs_z_delta = getattr(
        state,
        "end_effector_object_delta_at_min_abs_z_during_closed_gripper",
        None,
    )
    z_margin = (
        float(min_abs_z_distance) - float(object_half_height)
        if min_abs_z_distance is not None and object_half_height is not None
        else None
    )
    bbox_sphere_margin = (
        float(min_distance) - float(object_bbox_half_diagonal)
        if min_distance is not None and object_bbox_half_diagonal is not None
        else None
    )
    far_distance_threshold = _franka_pick_place_far_contact_threshold(
        object_bbox_half_diagonal=object_bbox_half_diagonal,
        object_width=object_width,
    )
    distance_over_far_threshold = (
        float(min_distance) - float(far_distance_threshold)
        if min_distance is not None and far_distance_threshold is not None
        else None
    )
    closed_window_lift_delta = getattr(
        state,
        "max_object_lift_delta_during_closed_gripper",
        None,
    )
    closed_window_xy_motion = getattr(
        state,
        "max_object_xy_motion_during_closed_gripper",
        None,
    )
    lift_threshold = float(getattr(state, "lift_height_tolerance", 0.0) or 0.0)
    lift_threshold_met = (
        closed_window_lift_delta is not None
        and float(closed_window_lift_delta) >= lift_threshold
    )
    xy_aligned = xy_margin is not None and xy_margin <= 0.0
    z_aligned = z_margin is not None and z_margin <= 0.0
    inside_bbox_sphere = bbox_sphere_margin is not None and bbox_sphere_margin <= 0.0
    far_from_object = (
        closed_seen
        and distance_over_far_threshold is not None
        and distance_over_far_threshold > 0.0
    )
    dominant_far_axis = _dominant_axis_label(min_distance_delta)
    if not closed_seen:
        classification = "no_closed_gripper_width_window"
    elif min_distance is None or min_xy_distance is None:
        classification = "closed_gripper_width_window_missing_ee_distance"
    elif far_from_object:
        classification = "closed_gripper_width_window_far_from_object"
    elif not xy_aligned:
        classification = "closed_gripper_width_window_not_xy_aligned"
    elif inside_bbox_sphere:
        classification = "closed_gripper_width_window_inside_bbox_sphere"
    else:
        classification = "closed_gripper_width_window_xy_aligned_outside_bbox_sphere"
    if not closed_seen:
        axis_hint = "no_closed_gripper_width_window"
    elif min_distance is None or min_xy_distance is None:
        axis_hint = "missing_ee_distance"
    elif far_from_object:
        axis_hint = (
            f"{dominant_far_axis}_offset_far_from_object"
            if dominant_far_axis is not None
            else "far_from_object"
        )
    elif not xy_aligned:
        axis_hint = "xy_offset_outside_object_width"
    elif z_margin is not None and not z_aligned:
        axis_hint = "z_offset_outside_object_height"
    elif inside_bbox_sphere:
        axis_hint = "inside_object_bbox_sphere"
    else:
        axis_hint = "outside_object_bbox_sphere"
    correction_delta, correction_source = _franka_pick_place_alignment_correction(
        axis_hint=axis_hint,
        delta=min_distance_delta,
        xy_delta=min_xy_delta,
        z_delta=min_abs_z_delta,
        xy_margin=xy_margin,
        z_margin=z_margin,
        bbox_sphere_margin=bbox_sphere_margin,
    )
    offset_recommendation = _franka_pick_place_offset_recommendation(
        base_offset=getattr(state, "end_effector_offset", None),
        delta=correction_delta,
    )
    return {
        "classification": classification,
        "axis_hint": axis_hint,
        "diagnostic_end_effector_offset_delta_m": correction_delta,
        "diagnostic_end_effector_offset_delta_source": correction_source,
        **offset_recommendation,
        "gripper_closed_on_object_width_seen": closed_seen,
        "object_grasp_width_m": object_width,
        "object_half_height_m": object_half_height,
        "object_bbox_half_diagonal_m": object_bbox_half_diagonal,
        "min_end_effector_distance_to_object_during_closed_gripper": min_distance,
        "min_end_effector_xy_distance_to_object_during_closed_gripper": min_xy_distance,
        "min_abs_end_effector_z_distance_to_object_during_closed_gripper": (
            min_abs_z_distance
        ),
        "signed_end_effector_z_distance_at_min_abs_during_closed_gripper": (
            signed_z_distance
        ),
        "end_effector_object_delta_at_min_distance_during_closed_gripper": (
            _float_list_or_none(min_distance_delta)
        ),
        "end_effector_object_delta_at_min_xy_distance_during_closed_gripper": (
            _float_list_or_none(min_xy_delta)
        ),
        "end_effector_object_delta_at_min_abs_z_during_closed_gripper": (
            _float_list_or_none(min_abs_z_delta)
        ),
        "xy_aligned_during_closed_gripper": bool(xy_aligned),
        "z_aligned_during_closed_gripper": bool(z_aligned),
        "inside_object_bbox_sphere_during_closed_gripper": bool(inside_bbox_sphere),
        "far_from_object_during_closed_gripper": bool(far_from_object),
        "closed_gripper_far_distance_threshold_m": far_distance_threshold,
        "closed_gripper_distance_over_far_threshold_m": distance_over_far_threshold,
        "closed_gripper_xy_margin_to_object_half_width_m": xy_margin,
        "closed_gripper_z_margin_to_object_half_height_m": z_margin,
        "closed_gripper_distance_margin_to_object_bbox_sphere_m": bbox_sphere_margin,
        "max_object_lift_delta_during_closed_gripper": closed_window_lift_delta,
        "max_object_xy_motion_during_closed_gripper": closed_window_xy_motion,
        "lift_height_tolerance_m": lift_threshold,
        "lift_threshold_met_during_closed_gripper": bool(lift_threshold_met),
    }


def _franka_pick_place_approach_window_diagnostics(
    state: _FrankaPickPlaceDemoState,
) -> dict[str, Any]:
    object_width = _franka_pick_place_object_grasp_width_m(
        getattr(state, "object_bbox_size", [])
    )
    object_bbox_size = [float(v) for v in getattr(state, "object_bbox_size", [])]
    object_bbox_half_diagonal = (
        math.sqrt(sum(float(v) ** 2 for v in object_bbox_size[:3])) / 2.0
        if len(object_bbox_size) >= 3
        else None
    )
    object_half_width = object_width / 2.0 if object_width is not None else None
    object_half_height = (
        float(object_bbox_size[2]) / 2.0 if len(object_bbox_size) >= 3 else None
    )
    min_distance = getattr(state, "min_end_effector_distance_to_object", None)
    min_xy_distance = getattr(state, "min_end_effector_xy_distance_to_object", None)
    min_abs_z_distance = getattr(
        state,
        "min_abs_end_effector_z_distance_to_object",
        None,
    )
    signed_z_distance = getattr(
        state,
        "signed_end_effector_z_distance_at_min_abs_to_object",
        None,
    )
    min_distance_delta = getattr(
        state,
        "end_effector_object_delta_at_min_distance",
        None,
    )
    min_xy_delta = getattr(
        state,
        "end_effector_object_delta_at_min_xy_distance",
        None,
    )
    min_abs_z_delta = getattr(
        state,
        "end_effector_object_delta_at_min_abs_z",
        None,
    )
    xy_margin = (
        float(min_xy_distance) - float(object_half_width)
        if min_xy_distance is not None and object_half_width is not None
        else None
    )
    z_margin = (
        float(min_abs_z_distance) - float(object_half_height)
        if min_abs_z_distance is not None and object_half_height is not None
        else None
    )
    bbox_sphere_margin = (
        float(min_distance) - float(object_bbox_half_diagonal)
        if min_distance is not None and object_bbox_half_diagonal is not None
        else None
    )
    far_distance_threshold = _franka_pick_place_far_contact_threshold(
        object_bbox_half_diagonal=object_bbox_half_diagonal,
        object_width=object_width,
    )
    distance_over_far_threshold = (
        float(min_distance) - float(far_distance_threshold)
        if min_distance is not None and far_distance_threshold is not None
        else None
    )
    pose_seen = bool(getattr(state, "end_effector_pose_seen", False))
    xy_aligned = xy_margin is not None and xy_margin <= 0.0
    z_aligned = z_margin is not None and z_margin <= 0.0
    inside_bbox_sphere = bbox_sphere_margin is not None and bbox_sphere_margin <= 0.0
    far_from_object = (
        pose_seen
        and distance_over_far_threshold is not None
        and distance_over_far_threshold > 0.0
    )
    dominant_far_axis = _dominant_axis_label(min_distance_delta)
    if not pose_seen:
        classification = "no_end_effector_pose_samples"
    elif min_distance is None or min_xy_distance is None:
        classification = "approach_window_missing_ee_distance"
    elif far_from_object:
        classification = "approach_window_far_from_object"
    elif not xy_aligned:
        classification = "approach_window_not_xy_aligned"
    elif inside_bbox_sphere:
        classification = "approach_window_inside_bbox_sphere"
    else:
        classification = "approach_window_xy_aligned_outside_bbox_sphere"
    if not pose_seen:
        axis_hint = "no_end_effector_pose_samples"
    elif min_distance is None or min_xy_distance is None:
        axis_hint = "missing_ee_distance"
    elif far_from_object:
        axis_hint = (
            f"{dominant_far_axis}_offset_far_from_object"
            if dominant_far_axis is not None
            else "far_from_object"
        )
    elif not xy_aligned:
        axis_hint = "xy_offset_outside_object_width"
    elif z_margin is not None and not z_aligned:
        axis_hint = "z_offset_outside_object_height"
    elif inside_bbox_sphere:
        axis_hint = "inside_object_bbox_sphere"
    else:
        axis_hint = "outside_object_bbox_sphere"
    correction_delta, correction_source = _franka_pick_place_alignment_correction(
        axis_hint=axis_hint,
        delta=min_distance_delta,
        xy_delta=min_xy_delta,
        z_delta=min_abs_z_delta,
        xy_margin=xy_margin,
        z_margin=z_margin,
        bbox_sphere_margin=bbox_sphere_margin,
    )
    offset_recommendation = _franka_pick_place_offset_recommendation(
        base_offset=getattr(state, "end_effector_offset", None),
        delta=correction_delta,
    )
    return {
        "classification": classification,
        "axis_hint": axis_hint,
        "diagnostic_end_effector_offset_delta_m": correction_delta,
        "diagnostic_end_effector_offset_delta_source": correction_source,
        **offset_recommendation,
        "end_effector_pose_seen": pose_seen,
        "object_grasp_width_m": object_width,
        "object_half_height_m": object_half_height,
        "object_bbox_half_diagonal_m": object_bbox_half_diagonal,
        "min_end_effector_distance_to_object": min_distance,
        "min_end_effector_xy_distance_to_object": min_xy_distance,
        "min_abs_end_effector_z_distance_to_object": min_abs_z_distance,
        "signed_end_effector_z_distance_at_min_abs_to_object": signed_z_distance,
        "end_effector_object_delta_at_min_distance": _float_list_or_none(
            min_distance_delta
        ),
        "end_effector_object_delta_at_min_xy_distance": _float_list_or_none(
            min_xy_delta
        ),
        "end_effector_object_delta_at_min_abs_z": _float_list_or_none(
            min_abs_z_delta
        ),
        "xy_aligned_during_approach": bool(xy_aligned),
        "z_aligned_during_approach": bool(z_aligned),
        "inside_object_bbox_sphere_during_approach": bool(inside_bbox_sphere),
        "far_from_object_during_approach": bool(far_from_object),
        "approach_far_distance_threshold_m": far_distance_threshold,
        "approach_distance_over_far_threshold_m": distance_over_far_threshold,
        "approach_xy_margin_to_object_half_width_m": xy_margin,
        "approach_z_margin_to_object_half_height_m": z_margin,
        "approach_distance_margin_to_object_bbox_sphere_m": bbox_sphere_margin,
    }


def _franka_pick_place_far_contact_threshold(
    *,
    object_bbox_half_diagonal: float | None,
    object_width: float | None,
) -> float | None:
    if object_bbox_half_diagonal is None:
        return None
    width_margin = (
        _PICK_PLACE_FAR_CONTACT_BBOX_WIDTH_MULTIPLIER * float(object_width)
        if object_width is not None
        else 0.0
    )
    return float(object_bbox_half_diagonal) + width_margin


def _dominant_axis_label(delta: object | None) -> str | None:
    values = _float_list_or_none(delta)
    if values is None or len(values) < 3:
        return None
    axes = ("x", "y", "z")
    return axes[max(range(3), key=lambda index: abs(float(values[index])))]


def _franka_pick_place_alignment_correction(
    *,
    axis_hint: str,
    delta: object | None,
    xy_delta: object | None,
    z_delta: object | None,
    xy_margin: float | None,
    z_margin: float | None,
    bbox_sphere_margin: float | None,
) -> tuple[list[float] | None, str | None]:
    """Return minimal EE offset delta toward the observed object envelope."""
    delta_values = _float_list_or_none(delta)
    xy_values = _float_list_or_none(xy_delta) or delta_values
    z_values = _float_list_or_none(z_delta) or delta_values

    if axis_hint.startswith(("no_", "missing_")):
        return None, None
    if axis_hint == "inside_object_bbox_sphere":
        return None, None

    if axis_hint.startswith("z_offset") and z_margin is not None and z_margin > 0:
        if z_values is None or len(z_values) < 3:
            return None, None
        z_value = float(z_values[2])
        if not math.isfinite(z_value) or abs(z_value) <= 1e-12:
            return None, None
        return (
            [0.0, 0.0, -math.copysign(float(z_margin), z_value)],
            "z_margin_to_object_half_height",
        )

    if xy_margin is not None and xy_margin > 0 and xy_values is not None and len(xy_values) >= 2:
        x_value = float(xy_values[0])
        y_value = float(xy_values[1])
        xy_norm = math.hypot(x_value, y_value)
        if math.isfinite(xy_norm) and xy_norm > 1e-12:
            return (
                [
                    -(x_value / xy_norm) * float(xy_margin),
                    -(y_value / xy_norm) * float(xy_margin),
                    0.0,
                ],
                "xy_margin_to_object_half_width",
            )

    if z_margin is not None and z_margin > 0 and z_values is not None and len(z_values) >= 3:
        z_value = float(z_values[2])
        if math.isfinite(z_value) and abs(z_value) > 1e-12:
            return (
                [0.0, 0.0, -math.copysign(float(z_margin), z_value)],
                "z_margin_to_object_half_height",
            )

    if (
        bbox_sphere_margin is not None
        and bbox_sphere_margin > 0
        and delta_values is not None
        and len(delta_values) >= 3
    ):
        norm = math.sqrt(sum(float(value) ** 2 for value in delta_values[:3]))
        if math.isfinite(norm) and norm > 1e-12:
            return (
                [
                    -(float(value) / norm) * float(bbox_sphere_margin)
                    for value in delta_values[:3]
                ],
                "distance_margin_to_object_bbox_sphere",
            )

    return None, None


def _franka_pick_place_offset_recommendation(
    *,
    base_offset: object | None,
    delta: object | None,
) -> dict[str, Any]:
    """Build a bounded next-trial EE offset recommendation from diagnostics."""
    base_values = _finite_float_triplet_or_none(base_offset)
    delta_values = _finite_float_triplet_or_none(delta)
    if delta_values is None:
        return {
            "diagnostic_end_effector_offset_base_m": base_values,
            "diagnostic_end_effector_offset_applied_delta_m": None,
            "diagnostic_end_effector_offset_next_m": None,
            "diagnostic_end_effector_offset_delta_limited": False,
            "diagnostic_end_effector_offset_delta_limit_m": (
                _PICK_PLACE_DIAGNOSTIC_OFFSET_STEP_LIMIT_M
            ),
        }

    base_values = base_values or [0.0, 0.0, 0.0]

    raw_delta = [float(v) for v in delta_values]
    norm = math.sqrt(sum(v ** 2 for v in raw_delta))
    limited = False
    applied_delta = raw_delta
    if math.isfinite(norm) and norm > _PICK_PLACE_DIAGNOSTIC_OFFSET_STEP_LIMIT_M:
        scale = _PICK_PLACE_DIAGNOSTIC_OFFSET_STEP_LIMIT_M / norm
        applied_delta = [v * scale for v in raw_delta]
        limited = True

    return {
        "diagnostic_end_effector_offset_base_m": [float(v) for v in base_values],
        "diagnostic_end_effector_offset_applied_delta_m": applied_delta,
        "diagnostic_end_effector_offset_next_m": [
            float(base_values[index]) + float(applied_delta[index])
            for index in range(3)
        ],
        "diagnostic_end_effector_offset_delta_limited": limited,
        "diagnostic_end_effector_offset_delta_limit_m": (
            _PICK_PLACE_DIAGNOSTIC_OFFSET_STEP_LIMIT_M
        ),
    }


def _compute_franka_demo_end_effector_position(
    robot_prim_path: str,
    robot_description: object,
) -> list[float] | None:
    """Best-effort gripper-link position for pick/place playback diagnostics."""
    try:
        import omni.usd
        from pxr import Usd, UsdGeom

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return None
        robot_prim = stage.GetPrimAtPath(robot_prim_path)
        if not robot_prim.IsValid():
            return None

        ee_name = _franka_parallel_gripper_spec(robot_description).end_effector_prim_name
        ee_prim = stage.GetPrimAtPath(f"{robot_prim_path}/{ee_name}")
        if not ee_prim.IsValid():
            ee_prim = None
            for prim in Usd.PrimRange(robot_prim):
                if prim.GetName() == ee_name:
                    ee_prim = prim
                    break
        if ee_prim is None or not ee_prim.IsValid():
            return None

        matrix = UsdGeom.Xformable(ee_prim).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default(),
        )
        translate = matrix.ExtractTranslation()
        return [float(translate[0]), float(translate[1]), float(translate[2])]
    except Exception:  # noqa: BLE001
        logger.debug("Franka pick/place EE telemetry unavailable", exc_info=True)
        return None


def _float_sequence(value: Any) -> list[float]:
    return [float(v) for v in _flatten_sequence(value)]


def _int_sequence(value: Any) -> list[int]:
    return [int(v) for v in _flatten_sequence(value)]


def _flatten_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (str, bytes)):
        return [value]
    try:
        iterator = iter(value)
    except TypeError:
        return [value]

    flattened: list[Any] = []
    for item in iterator:
        flattened.extend(_flatten_sequence(item))
    return flattened


def _finite_abs_deltas(left: list[float], right: list[float]) -> list[float]:
    deltas: list[float] = []
    for l_value, r_value in zip(left, right, strict=False):
        if math.isfinite(l_value) and math.isfinite(r_value):
            deltas.append(abs(l_value - r_value))
    return deltas


def _franka_pick_place_demo_progress_diagnostics(
    state: _FrankaPickPlaceDemoState,
) -> dict[str, Any]:
    current_event = int(state.controller_event)
    return {
        "current_event": current_event,
        "current_event_ticks": int(state.event_tick_counts.get(current_event, 0)),
        "event_tick_counts": {
            str(event): int(count)
            for event, count in sorted(state.event_tick_counts.items())
        },
        "event_first_steps": {
            str(event): int(step)
            for event, step in sorted(state.event_first_steps.items())
        },
        "event_last_steps": {
            str(event): int(step)
            for event, step in sorted(state.event_last_steps.items())
        },
        "sample_interval_steps": _PICK_PLACE_PROGRESS_SAMPLE_INTERVAL_STEPS,
        "sample_limit": _PICK_PLACE_PROGRESS_SAMPLE_LIMIT,
        "max_joint_delta_from_initial": float(
            getattr(state, "max_joint_delta_from_initial", 0.0)
        ),
        "max_action_joint_position_delta": float(
            getattr(state, "max_action_joint_position_delta", 0.0)
        ),
        "action_joint_positions_seen": bool(
            getattr(state, "action_joint_positions_seen", False)
        ),
        "end_effector_pose_seen": bool(getattr(state, "end_effector_pose_seen", False)),
        "min_end_effector_distance_to_pick": getattr(
            state,
            "min_end_effector_distance_to_pick",
            None,
        ),
        "min_end_effector_distance_to_target": getattr(
            state,
            "min_end_effector_distance_to_target",
            None,
        ),
        "min_end_effector_distance_to_object": getattr(
            state,
            "min_end_effector_distance_to_object",
            None,
        ),
        "min_end_effector_xy_distance_to_object": getattr(
            state,
            "min_end_effector_xy_distance_to_object",
            None,
        ),
        "min_abs_end_effector_z_distance_to_object": getattr(
            state,
            "min_abs_end_effector_z_distance_to_object",
            None,
        ),
        "signed_end_effector_z_distance_at_min_abs_to_object": getattr(
            state,
            "signed_end_effector_z_distance_at_min_abs_to_object",
            None,
        ),
        "end_effector_object_delta_at_min_distance": getattr(
            state,
            "end_effector_object_delta_at_min_distance",
            None,
        ),
        "end_effector_object_delta_at_min_xy_distance": getattr(
            state,
            "end_effector_object_delta_at_min_xy_distance",
            None,
        ),
        "end_effector_object_delta_at_min_abs_z": getattr(
            state,
            "end_effector_object_delta_at_min_abs_z",
            None,
        ),
        "gripper_closed_on_object_width_seen": bool(
            getattr(state, "gripper_closed_on_object_width_seen", False)
        ),
        "min_end_effector_distance_to_object_during_closed_gripper": getattr(
            state,
            "min_end_effector_distance_to_object_during_closed_gripper",
            None,
        ),
        "min_end_effector_xy_distance_to_object_during_closed_gripper": getattr(
            state,
            "min_end_effector_xy_distance_to_object_during_closed_gripper",
            None,
        ),
        "min_abs_end_effector_z_distance_to_object_during_closed_gripper": getattr(
            state,
            "min_abs_end_effector_z_distance_to_object_during_closed_gripper",
            None,
        ),
        "signed_end_effector_z_distance_at_min_abs_during_closed_gripper": getattr(
            state,
            "signed_end_effector_z_distance_at_min_abs_during_closed_gripper",
            None,
        ),
        "end_effector_object_delta_at_min_distance_during_closed_gripper": getattr(
            state,
            "end_effector_object_delta_at_min_distance_during_closed_gripper",
            None,
        ),
        "end_effector_object_delta_at_min_xy_distance_during_closed_gripper": getattr(
            state,
            "end_effector_object_delta_at_min_xy_distance_during_closed_gripper",
            None,
        ),
        "end_effector_object_delta_at_min_abs_z_during_closed_gripper": getattr(
            state,
            "end_effector_object_delta_at_min_abs_z_during_closed_gripper",
            None,
        ),
        "max_object_lift_delta_during_closed_gripper": getattr(
            state,
            "max_object_lift_delta_during_closed_gripper",
            None,
        ),
        "max_object_xy_motion_during_closed_gripper": getattr(
            state,
            "max_object_xy_motion_during_closed_gripper",
            None,
        ),
        "gripper_aperture_seen": bool(getattr(state, "gripper_aperture_seen", False)),
        "action_gripper_aperture_seen": bool(
            getattr(state, "action_gripper_aperture_seen", False)
        ),
        "min_gripper_aperture_m": getattr(
            state,
            "min_gripper_aperture_m",
            None,
        ),
        "max_gripper_aperture_m": getattr(
            state,
            "max_gripper_aperture_m",
            None,
        ),
        "min_action_gripper_aperture_m": getattr(
            state,
            "min_action_gripper_aperture_m",
            None,
        ),
        "max_action_gripper_aperture_m": getattr(
            state,
            "max_action_gripper_aperture_m",
            None,
        ),
        "min_gripper_object_width_margin_m": getattr(
            state,
            "min_gripper_object_width_margin_m",
            None,
        ),
        "min_action_gripper_object_width_margin_m": getattr(
            state,
            "min_action_gripper_object_width_margin_m",
            None,
        ),
        "approach_window": _franka_pick_place_approach_window_diagnostics(state),
        "contact_window": _franka_pick_place_contact_window_diagnostics(state),
        "samples": list(state.progress_samples),
    }


def _franka_pick_place_demo_status(state: _FrankaPickPlaceDemoState) -> dict[str, Any]:
    bbox_center = list(
        state.last_object_bbox_center
        or state.final_object_position
        or state.initial_object_position
        or state.object_initial_position
    )
    bbox_size = [float(v) for v in state.object_bbox_size]
    object_fit = _evaluate_pick_object_fit(
        bbox_size,
        max_grasp_width_m=state.request.get("max_grasp_width_m"),
        fit_clearance_m=state.request.get("fit_clearance_m", 0.005),
    )
    final_position = state.final_object_position or bbox_center
    initial_position = state.initial_object_position or state.object_initial_position
    final_distance = (
        state.final_distance
        if state.done or state.status == "failed"
        else _distance3(bbox_center, state.target_position)
    )
    return {
        "ok": state.status != "failed",
        "status": state.status,
        "robot_prim_path": state.robot_prim_path,
        "object_prim_path": state.object_prim_path,
        "target_position": [float(v) for v in state.target_position],
        "uses_kinematic_carry": False,
        "steps": int(state.steps),
        "controller_event": int(state.controller_event),
        "done": bool(state.done),
        "placed": bool(state.placed),
        "lifted": bool(state.lifted),
        "initial_object_position": [float(v) for v in initial_position],
        "final_object_position": [float(v) for v in final_position],
        "final_distance": float(final_distance),
        "max_lift_delta": float(state.max_lift_delta),
        "object_bbox_center": [float(v) for v in bbox_center],
        "object_bbox_size": bbox_size,
        "object_fit_ok": bool(object_fit["ok"]),
        "object_fit_reason": object_fit["reason"],
        "object_fit_axis": object_fit["axis"],
        "object_fit_limit_m": object_fit["limit_m"],
        "object_fit_measured_m": object_fit["measured_m"],
        "picking_position": [float(v) for v in state.picking_position],
        "end_effector_initial_height": float(state.end_effector_initial_height),
        "diagnostics": {
            **dict(state.diagnostics),
            "object_fit": object_fit,
            "playback_progress": _franka_pick_place_demo_progress_diagnostics(state),
        },
        "last_error": state.last_error,
    }


def _evaluate_pick_object_fit(
    object_bbox_size: list[float],
    *,
    max_grasp_width_m: object,
    fit_clearance_m: object,
) -> dict[str, Any]:
    try:
        max_width = float(max_grasp_width_m) if max_grasp_width_m is not None else None
    except (TypeError, ValueError):
        max_width = None
    try:
        clearance = max(0.0, float(fit_clearance_m))
    except (TypeError, ValueError):
        clearance = 0.0

    if max_width is None:
        return {
            "ok": True,
            "reason": "No max grasp width metadata is available for this profile.",
            "axis": None,
            "limit_m": None,
            "measured_m": None,
        }

    xy_sizes = [
        ("x", float(object_bbox_size[0]) if len(object_bbox_size) > 0 else 0.0),
        ("y", float(object_bbox_size[1]) if len(object_bbox_size) > 1 else 0.0),
    ]
    axis, measured = max(xy_sizes, key=lambda item: item[1])
    limit = max(0.0, max_width - clearance)
    ok = measured <= limit
    return {
        "ok": bool(ok),
        "reason": (
            "Object bbox fits within gripper opening."
            if ok
            else "Object bbox exceeds gripper opening; collect evidence and do not run play validation."
        ),
        "axis": axis,
        "limit_m": float(limit),
        "measured_m": float(measured),
    }


async def _ensure_articulation_ready(
    articulation: Any,
    prim_path: str,
    *,
    max_frames: int = 90,
) -> None:
    """Wait until Isaac's articulation wrapper exposes live joint state."""
    import omni.kit.app  # lazy

    _ensure_physics_world()
    app = omni.kit.app.get_app()
    last_error: str | None = None

    for _frame in range(max_frames + 1):
        try:
            _ensure_initialized(articulation)
            positions = articulation.get_joint_positions()
            if positions is not None:
                return
            last_error = "get_joint_positions returned None"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        await app.next_update_async()

    raise ValueError(
        f"articulation at {prim_path} not ready after {max_frames} frames; "
        f"last_error={last_error or 'unknown'}"
    )


def _ensure_initialized(articulation: Any) -> None:
    """Defensive ``SingleArticulation.initialize()`` — safe to call twice.

    Kit articulation wrappers require initialize() before joint I/O even when the prim
    has a PhysxArticulationRoot. Re-initializing an already-initialized
    articulation is a no-op. Initialization failures are surfaced as a
    domain error instead of leaking Isaac internals such as ``link_names``.
    """
    prim_path = str(getattr(articulation, "prim_path", "") or "<unknown>")
    try:
        articulation.initialize()
    except Exception as exc:
        raise ValueError(
            f"articulation at {prim_path} not ready: initialize failed: {exc}"
        ) from exc

    ready, reason = _articulation_runtime_ready(articulation)
    if not ready:
        raise ValueError(f"articulation at {prim_path} not ready: {reason}")


def _articulation_runtime_ready(articulation: Any) -> tuple[bool, str]:
    try:
        dof_names = list(articulation.dof_names or [])
    except Exception as exc:  # noqa: BLE001
        return False, f"dof_names unavailable: {exc}"
    try:
        num_dof = int(articulation.num_dof or len(dof_names))
    except Exception as exc:  # noqa: BLE001
        return False, f"num_dof unavailable: {exc}"
    if num_dof <= 0:
        return False, "num_dof is 0"
    if not dof_names:
        return False, "dof_names is empty"
    return True, ""


def _ensure_physics_world() -> None:
    """Create/initialize an Isaac World so SingleArticulation can bind PhysX."""
    try:
        from isaacsim.core.api import World  # type: ignore[import-not-found]

        world = World.instance()
        if world is None:
            world = World(
                physics_dt=1.0 / 60.0,
                rendering_dt=1.0 / 60.0,
                stage_units_in_meters=1.0,
            )
        if getattr(world, "physics_sim_view", None) is None:
            world.initialize_physics()
    except ImportError:
        return
    except Exception as exc:  # noqa: BLE001
        logger.debug("World physics initialization failed: %s", exc)


def _apply_joint_positions(articulation: Any, positions: Any) -> None:
    """Apply joint targets through the controller when available."""
    try:
        from isaacsim.core.utils.types import ArticulationAction  # type: ignore[import-not-found]
    except ImportError:
        try:
            from omni.isaac.core.utils.types import ArticulationAction  # type: ignore[import-not-found]
        except ImportError:
            articulation.set_joint_positions(positions)
            return

    try:
        controller = articulation.get_articulation_controller()
        controller.apply_action(ArticulationAction(joint_positions=positions))
    except Exception as exc:  # noqa: BLE001
        logger.debug("articulation controller apply_action failed; using set_joint_positions: %s", exc)
        articulation.set_joint_positions(positions)


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


def _read_static_usd_joint_config(prim_path: str) -> dict[str, list]:
    """Read movable USD joint prim metadata without runtime articulation state.

    This intentionally excludes FixedJoint prims. The order follows
    ``Usd.PrimRange`` traversal and is diagnostic only.
    """
    import omni.usd
    from pxr import Usd

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")

    out = {
        "dof_names": [],
        "joint_types": [],
        "stiffness": [],
        "damping": [],
        "max_force": [],
        "lower_limits": [],
        "upper_limits": [],
        "max_velocity": [],
    }

    for p in Usd.PrimRange(root):
        type_name = str(p.GetTypeName())
        if not _is_static_usd_dof_joint_type(type_name):
            continue
        values = _read_usd_joint_config_values(p, type_name)
        out["dof_names"].append(str(p.GetName()))
        out["joint_types"].append(type_name)
        for key, value in values.items():
            out[key].append(value)

    return out


def _is_static_usd_dof_joint_type(type_name: str) -> bool:
    return type_name.endswith("Joint") and not type_name.endswith("FixedJoint")


def _read_usd_drive_config(prim_path: str, dof_names: list[str]) -> dict[str, list]:
    """Walk the articulation prim subtree and pull DriveAPI / limit attributes.

    Drive config + joint limits live on the joint prims themselves (UsdPhysics
    schema), independent of any runtime articulation wrapper. We match joint
    prims to *dof_names* by joint prim name so the returned arrays align with
    the articulation's DOF order. Joints not represented in *dof_names* are
    skipped; *dof_names* entries with no matching joint prim get zeros.
    """
    import omni.usd
    from pxr import Usd

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
        values = _read_usd_joint_config_values(p, type_name)
        for key, value in values.items():
            out[key][idx] = value

    return out


def _read_usd_joint_config_values(joint_prim: Any, type_name: str) -> dict[str, float]:
    from pxr import UsdPhysics

    values = {
        "stiffness": 0.0,
        "damping": 0.0,
        "max_force": 0.0,
        "lower_limits": 0.0,
        "upper_limits": 0.0,
        "max_velocity": 0.0,
    }

    # Drive API — angular for revolute/spherical, linear for prismatic.
    drive_token = "linear" if "Prismatic" in type_name else "angular"
    try:
        drive = UsdPhysics.DriveAPI.Get(joint_prim, drive_token)
        if drive:
            for attr_getter, key in (
                (drive.GetStiffnessAttr, "stiffness"),
                (drive.GetDampingAttr, "damping"),
                (drive.GetMaxForceAttr, "max_force"),
            ):
                attr = attr_getter()
                if attr and attr.IsValid():
                    val = attr.Get()
                    if val is not None:
                        values[key] = float(val)
    except Exception as exc:  # noqa: BLE001
        logger.debug("DriveAPI read failed for %s: %s", joint_prim.GetPath(), exc)

    # Position limits live directly on the joint prim.
    for attr_name, key in (
        ("physics:lowerLimit", "lower_limits"),
        ("physics:upperLimit", "upper_limits"),
    ):
        attr = joint_prim.GetAttribute(attr_name)
        if attr and attr.IsValid():
            val = attr.Get()
            if val is not None:
                values[key] = float(val)

    # Max joint velocity (PhysxJointAPI extension attribute).
    for vel_attr_name in ("physxJoint:maxJointVelocity", "physics:maxJointVelocity"):
        vel_attr = joint_prim.GetAttribute(vel_attr_name)
        if vel_attr and vel_attr.IsValid():
            val = vel_attr.Get()
            if val is not None:
                values["max_velocity"] = float(val)
                break

    return values


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


def _lula_solver_joint_names(solver: Any) -> tuple[str, ...]:
    """Best-effort joint order expected by a Lula kinematics solver."""
    for method_name in (
        "get_joint_names",
        "get_cspace_joint_names",
        "get_c_space_joint_names",
    ):
        method = getattr(solver, method_name, None)
        if method is None:
            continue
        try:
            names = method()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Lula solver joint-name read failed via %s: %s", method_name, exc)
            continue
        if names:
            return tuple(str(name) for name in names)
    return ()


def _select_lula_articulation_joint_indices(
    *,
    dof_names: tuple[str, ...],
    solver_joint_names: tuple[str, ...],
    robot_description: str,
    warm_count: int,
) -> tuple[int, ...]:
    """Map Lula c-space order to articulation DOF indices.

    Lula IK usually controls only the arm subset, while the live articulation can
    also expose grippers or mobile-base dummy joints. Name matching is preferred;
    family fallbacks preserve existing Franka behavior and keep hazardous
    profile triage honest when names are unavailable.
    """
    if solver_joint_names and dof_names:
        mapped = _map_lula_joint_names_to_articulation_indices(
            dof_names,
            solver_joint_names,
        )
        if len(mapped) == len(solver_joint_names):
            return mapped

    expected_count = _lula_expected_joint_count(
        robot_description=robot_description,
        solver_joint_names=solver_joint_names,
        warm_count=warm_count,
    )
    candidates = _lula_family_joint_index_candidates(
        dof_names=dof_names,
        robot_description=robot_description,
    )
    if expected_count > 0 and len(candidates) >= expected_count:
        return candidates[:expected_count]
    if candidates:
        return candidates
    return tuple(range(min(max(expected_count, 0) or warm_count, warm_count)))


def _map_lula_joint_names_to_articulation_indices(
    dof_names: tuple[str, ...],
    solver_joint_names: tuple[str, ...],
) -> tuple[int, ...]:
    exact = {_normalize_joint_name(name): i for i, name in enumerate(dof_names)}
    canonical: dict[str, int] = {}
    ambiguous: set[str] = set()
    for i, name in enumerate(dof_names):
        key = _canonical_lula_joint_name(name)
        if key in canonical:
            ambiguous.add(key)
        else:
            canonical[key] = i

    out: list[int] = []
    used: set[int] = set()
    for solver_name in solver_joint_names:
        exact_key = _normalize_joint_name(solver_name)
        idx = exact.get(exact_key)
        if idx is None:
            canonical_key = _canonical_lula_joint_name(solver_name)
            if canonical_key not in ambiguous:
                idx = canonical.get(canonical_key)
        if idx is None or idx in used:
            return ()
        out.append(idx)
        used.add(idx)
    return tuple(out)


def _lula_expected_joint_count(
    *,
    robot_description: str,
    solver_joint_names: tuple[str, ...],
    warm_count: int,
) -> int:
    if solver_joint_names:
        return len(solver_joint_names)
    description = _canonical_lula_joint_name(robot_description)
    if any(token in description for token in ("franka", "panda", "fr3", "rizon")):
        return min(7, warm_count)
    if any(
        token in description
        for token in (
            "ur",
            "rs007",
            "rs013",
            "rs025",
            "rs080",
            "kawasaki",
            "cobotta",
            "fanuc",
            "kuka",
            "techman",
        )
    ):
        return min(6, warm_count)
    return min(7, warm_count)


def _lula_family_joint_index_candidates(
    *,
    dof_names: tuple[str, ...],
    robot_description: str,
) -> tuple[int, ...]:
    if not dof_names:
        return ()

    description = _canonical_lula_joint_name(robot_description)
    if "ur" in description:
        ur_indices = tuple(
            i for i, name in enumerate(dof_names)
            if _canonical_lula_joint_name(name).startswith("urarm")
            and not _is_lula_non_arm_dof_name(name)
        )
        if ur_indices:
            return ur_indices

    if any(token in description for token in ("franka", "panda", "fr3", "rizon")):
        family_markers = ("panda", "fr3", "joint")
        indices = tuple(
            i for i, name in enumerate(dof_names)
            if any(marker in _canonical_lula_joint_name(name) for marker in family_markers)
            and not _is_lula_non_arm_dof_name(name)
        )
        if indices:
            return indices

    if any(token in description for token in ("rs007", "rs013", "rs025", "rs080", "kawasaki")):
        joint_indices = tuple(
            i for i, name in enumerate(dof_names)
            if _canonical_lula_joint_name(name).startswith("joint")
            and not _is_lula_non_arm_dof_name(name)
        )
        if joint_indices:
            return joint_indices

    return tuple(
        i for i, name in enumerate(dof_names)
        if not _is_lula_non_arm_dof_name(name)
    )


def _is_lula_non_arm_dof_name(name: str) -> bool:
    normalized = _canonical_lula_joint_name(name)
    markers = (
        "finger",
        "gripper",
        "dummybase",
        "mobilebase",
        "baseprismatic",
        "wheel",
        "caster",
    )
    return any(marker in normalized for marker in markers)


def _normalize_joint_name(name: str) -> str:
    return str(name or "").strip().lower()


def _canonical_lula_joint_name(name: str) -> str:
    normalized = _normalize_joint_name(name)
    for prefix in ("ur_arm_", "urarm_"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return "".join(ch for ch in normalized if ch.isalnum())


def _assert_franka_family_pick_place_robot(
    robot_description: object,
    *,
    endpoint: str,
) -> None:
    normalized = str(robot_description or "").strip().lower()
    if normalized in {"franka", "fr3"}:
        return
    raise ValueError(f"{endpoint} supports robot_description in ('Franka', 'FR3') only")


def _franka_parallel_gripper_spec(robot_description: object) -> _FrankaParallelGripperSpec:
    normalized = str(robot_description or "").strip().lower()
    if normalized == "fr3":
        return _FrankaParallelGripperSpec(
            end_effector_prim_name="fr3_rightfinger",
            joint_prim_names=("fr3_finger_joint1", "fr3_finger_joint2"),
        )
    return _FrankaParallelGripperSpec(
        end_effector_prim_name="panda_rightfinger",
        joint_prim_names=("panda_finger_joint1", "panda_finger_joint2"),
    )


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
        for candidate_name in _ee_pose_frame_candidate_names(frame_name):
            for prim in Usd.PrimRange(robot_prim):
                if prim.GetName() == candidate_name:
                    ee_prim = prim
                    frame_name = candidate_name
                    break
            if ee_prim is not None:
                break
    if ee_prim is None or not ee_prim.IsValid():
        tried = ", ".join(_ee_pose_frame_candidate_names(frame_name))
        raise ValueError(
            f"End-effector frame {frame_name!r} not found under {prim_path}; "
            f"tried: {tried}"
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


def _ee_pose_frame_candidate_names(frame_name: str) -> tuple[str, ...]:
    """Return USD prim names to try for an EE frame request.

    Lula frame names are sometimes fixed URDF frames rather than authored USD
    link prims. Keep this explicit and small so telemetry remains honest: the
    response reports the actual USD prim name that was used.
    """
    default_names = ("panda_hand", "right_gripper", "tool0", "ee_link")
    aliases = {
        "panda_hand": ("panda_rightfinger", "right_gripper"),
        "fr3_hand_tcp": ("fr3_rightfinger", "right_gripper"),
        "right_gripper": (
            "panda_rightfinger",
            "fr3_rightfinger",
            "onrobot_rg2_base_link",
        ),
        "tool0": (
            "ee_link",
            "wrist_3_link",
            "ur_arm_tool0",
            "ur_arm_ee_link",
            "ur_arm_wrist_3_link",
            "onrobot_rg2_base_link",
            "link5",
        ),
        "ee_link": (
            "tool0",
            "wrist_3_link",
            "ur_arm_tool0",
            "ur_arm_ee_link",
            "ur_arm_wrist_3_link",
            "onrobot_rg2_base_link",
            "link5",
        ),
        "ur_arm_tool0": (
            "ur_arm_ee_link",
            "ur_arm_wrist_3_link",
            "tool0",
            "ee_link",
            "wrist_3_link",
        ),
        "ur_arm_ee_link": (
            "ur_arm_tool0",
            "ur_arm_wrist_3_link",
            "tool0",
            "ee_link",
            "wrist_3_link",
        ),
        "ur_arm_wrist_3_link": (
            "ur_arm_tool0",
            "ur_arm_ee_link",
            "wrist_3_link",
            "tool0",
            "ee_link",
        ),
    }
    candidates: list[str] = []

    def add(name: str) -> None:
        if name and name not in candidates:
            candidates.append(name)

    add(frame_name)
    for alias in aliases.get(frame_name, ()):
        add(alias)
    for fallback in default_names:
        add(fallback)
    return tuple(candidates)


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
    ax, ay = a
    bx, by = b
    px, py = p
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
