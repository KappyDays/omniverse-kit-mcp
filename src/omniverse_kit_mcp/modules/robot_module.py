"""Robot module — USD load, joint control, async navigate (Phase B)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.asset_module import resolve_catalog_asset_url
from omniverse_kit_mcp.modules.base import error_result, fail_result, ok_result
from omniverse_kit_mcp.robot_arm_profiles import (
    builtin_robot_arm_profiles,
    get_robot_arm_profile,
)
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.robot import (
    JointConfig,
    JointPositions,
    JointPositionsSetRequest,
    JointPositionsSetResult,
    RobotArmProfilesResult,
    RobotDrivePhysicsRequest,
    RobotDrivePhysicsResult,
    RobotEEPose,
    RobotFrankaPickPlaceDemoRequest,
    RobotFrankaPickPlaceDemoStatus,
    RobotFrankaPickPlaceRequest,
    RobotFrankaPickPlaceResult,
    RobotGripperControlRequest,
    RobotGripperControlResult,
    RobotLoadRequest,
    RobotLoadResult,
    RobotNavigatePathRequest,
    RobotNavigatePathResult,
    RobotNavigateRequest,
    RobotNavigateResult,
    RobotPickPlaceDemoRequest,
    RobotSetEETargetRequest,
    RobotSetEETargetResult,
)

logger = logging.getLogger(__name__)

_DEFAULT_DEMO_GRID_CATALOG_PATH = "Grid/default_environment.usd"


class RobotModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def list_arm_profiles(
        self,
        meta: OperationMeta,
    ) -> ModuleResult[RobotArmProfilesResult]:
        started = int(time.time() * 1000)
        try:
            profiles = builtin_robot_arm_profiles()
            return ok_result(
                RobotArmProfilesResult(
                    count=len(profiles),
                    validated_pick_place_profiles=tuple(
                        profile.profile_name
                        for profile in profiles
                        if profile.support_status == "validated_pick_place"
                    ),
                    candidate_pick_place_profiles=tuple(
                        profile.profile_name
                        for profile in profiles
                        if profile.support_status == "candidate_pick_place"
                    ),
                    motion_policy_profiles=tuple(
                        profile.profile_name
                        for profile in profiles
                        if profile.robot_description is not None
                    ),
                    profile_only_profiles=tuple(
                        profile.profile_name
                        for profile in profiles
                        if profile.support_status == "profile_only"
                    ),
                    profiles=profiles,
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_LIST_ARM_PROFILES_ERROR",
            )

    async def load(
        self,
        meta: OperationMeta,
        request: RobotLoadRequest,
    ) -> ModuleResult[RobotLoadResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_load({
                "usd_url": request.usd_url,
                "prim_path": request.prim_path,
                "position": list(request.position) if request.position else None,
                "rotation": list(request.rotation) if request.rotation else None,
            })
            return ok_result(
                RobotLoadResult(
                    ok=raw.get("ok", True),
                    prim_path=raw.get("prim_path", request.prim_path),
                    usd_url=raw.get("usd_url", request.usd_url),
                    type_name=raw.get("type_name", "unknown"),
                    has_articulation=raw.get("has_articulation", False),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(str(exc), started_ms=started, exc=exc, error_code="ROBOT_LOAD_ERROR")

    async def get_joint_positions(
        self,
        meta: OperationMeta,
        prim_path: str,
    ) -> ModuleResult[JointPositions]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_get_joint_positions(prim_path)
            positions = tuple(float(p) for p in raw.get("positions", []))
            return ok_result(
                JointPositions(
                    prim_path=raw.get("prim_path", prim_path),
                    positions=positions,
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_GET_JOINTS_ERROR"
            )

    async def get_joint_config(
        self,
        meta: OperationMeta,
        prim_path: str,
    ) -> ModuleResult[JointConfig]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_get_joint_config(prim_path)
            return ok_result(
                JointConfig(
                    prim_path=str(raw.get("prim_path", prim_path)),
                    source=str(raw.get("source", "unknown")),
                    dof_count=int(raw.get("dof_count", 0)),
                    dof_names=tuple(str(n) for n in raw.get("dof_names", ())),
                    joint_types=tuple(str(t) for t in raw.get("joint_types", ())),
                    stiffness=tuple(float(v) for v in raw.get("stiffness", ())),
                    damping=tuple(float(v) for v in raw.get("damping", ())),
                    max_force=tuple(float(v) for v in raw.get("max_force", ())),
                    lower_limits=tuple(float(v) for v in raw.get("lower_limits", ())),
                    upper_limits=tuple(float(v) for v in raw.get("upper_limits", ())),
                    max_velocity=tuple(float(v) for v in raw.get("max_velocity", ())),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_GET_JOINT_CONFIG_ERROR"
            )

    async def set_joint_positions(
        self,
        meta: OperationMeta,
        request: JointPositionsSetRequest,
    ) -> ModuleResult[JointPositionsSetResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_set_joint_positions({
                "prim_path": request.prim_path,
                "positions": list(request.positions),
            })
            return ok_result(
                JointPositionsSetResult(
                    prim_path=raw.get("prim_path", request.prim_path),
                    positions_count=int(raw.get("positions_count", len(request.positions))),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_SET_JOINTS_ERROR"
            )

    async def navigate_to(
        self,
        meta: OperationMeta,
        request: RobotNavigateRequest,
    ) -> ModuleResult[RobotNavigateResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_navigate({
                "prim_path": request.prim_path,
                "target": list(request.target),
                "duration_s": request.duration_s,
            })
            return ok_result(
                RobotNavigateResult(
                    job_id=raw["job_id"],
                    prim_path=raw.get("prim_path", request.prim_path),
                    target=tuple(raw.get("target", list(request.target))),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_NAVIGATE_ERROR"
            )

    async def navigate_path(
        self,
        meta: OperationMeta,
        request: RobotNavigatePathRequest,
    ) -> ModuleResult[RobotNavigatePathResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_navigate_path({
                "prim_path": request.prim_path,
                "points": [list(p) for p in request.waypoints],
                "duration_s": request.duration_s,
            })
            return ok_result(
                RobotNavigatePathResult(
                    job_id=raw["job_id"],
                    prim_path=raw.get("prim_path", request.prim_path),
                    num_waypoints=int(raw.get("num_waypoints", len(request.waypoints))),
                    duration_s=float(raw.get("duration_s", request.duration_s)),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_NAVIGATE_PATH_ERROR",
            )

    async def gripper_control(
        self,
        meta: OperationMeta,
        request: RobotGripperControlRequest,
    ) -> ModuleResult[RobotGripperControlResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_gripper_control({
                "prim_path": request.prim_path,
                "action": request.action,
                "target": request.target,
            })
            return ok_result(
                RobotGripperControlResult(
                    prim_path=raw.get("prim_path", request.prim_path),
                    action=str(raw.get("action", request.action)),
                    target_value=float(raw.get("target_value", request.target or 0.0)),
                    gripper_joint_names=tuple(raw.get("gripper_joint_names", ())),
                    gripper_joint_indices=tuple(
                        int(i) for i in raw.get("gripper_joint_indices", ())
                    ),
                    dof_count=int(raw.get("dof_count", 0)),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_GRIPPER_CONTROL_ERROR",
            )

    async def set_ee_target(
        self,
        meta: OperationMeta,
        request: RobotSetEETargetRequest,
    ) -> ModuleResult[RobotSetEETargetResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_set_ee_target({
                "prim_path": request.prim_path,
                "target_pose": list(request.target_pose),
                "robot_description": request.robot_description,
                "end_effector_frame": request.end_effector_frame,
            })
            pose = raw.get("target_pose", list(request.target_pose))
            return ok_result(
                RobotSetEETargetResult(
                    prim_path=raw.get("prim_path", request.prim_path),
                    target_pose=tuple(float(v) for v in pose),  # type: ignore[arg-type]
                    robot_description=str(
                        raw.get("robot_description", request.robot_description),
                    ),
                    end_effector_frame=str(raw.get("end_effector_frame", "")),
                    lula_import_path=str(raw.get("lula_import_path", "")),
                    ik_success=bool(raw.get("ik_success", False)),
                    solution=tuple(float(v) for v in raw.get("solution", ())),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_SET_EE_TARGET_ERROR",
            )

    async def get_ee_pose(
        self,
        meta: OperationMeta,
        prim_path: str,
        end_effector_frame: str | None = None,
    ) -> ModuleResult[RobotEEPose]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_get_ee_pose(
                prim_path=prim_path,
                end_effector_frame=end_effector_frame,
            )
            position = raw.get("position", (0.0, 0.0, 0.0))
            orientation = raw.get("orientation", (1.0, 0.0, 0.0, 0.0))
            return ok_result(
                RobotEEPose(
                    prim_path=str(raw.get("prim_path", prim_path)),
                    end_effector_frame=str(
                        raw.get("end_effector_frame", end_effector_frame or ""),
                    ),
                    position=tuple(float(v) for v in position),  # type: ignore[arg-type]
                    orientation=tuple(float(v) for v in orientation),  # type: ignore[arg-type]
                    source=str(raw.get("source", "")),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="ROBOT_GET_EE_POSE_ERROR",
            )

    async def drive_physics(
        self,
        meta: OperationMeta,
        request: RobotDrivePhysicsRequest,
    ) -> ModuleResult[RobotDrivePhysicsResult]:
        """Drive a wheel-based articulation along ``waypoints`` via
        DifferentialController + Pure Pursuit (spec §8.2). Returns Job
        ``{job_id}``; poll ``job_status``. Requires timeline playing (R2).
        """
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_drive_physics({
                "prim_path": request.prim_path,
                "waypoints": [list(p) for p in request.waypoints],
                "max_linear": request.max_linear,
                "max_angular": request.max_angular,
                "wheel_radius": request.wheel_radius,
                "wheel_base": request.wheel_base,
                "arrival_tolerance": request.arrival_tolerance,
                "timeout_s": request.timeout_s,
                "lookahead": request.lookahead,
            })
            if not raw.get("ok", False):
                return error_result(
                    raw.get("reason", "drive_physics failed"),
                    started_ms=started,
                    error_code="ROBOT_DRIVE_PHYSICS_ERROR",
                )
            return ok_result(
                RobotDrivePhysicsResult(
                    ok=True,
                    job_id=str(raw.get("job_id", "")),
                    prim_path=raw.get("prim_path", request.prim_path),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_DRIVE_PHYSICS_ERROR",
            )

    async def run_franka_pick_place(
        self,
        meta: OperationMeta,
        request: RobotFrankaPickPlaceRequest,
    ) -> ModuleResult[RobotFrankaPickPlaceResult]:
        """Run Isaac Sim's official Franka PickPlaceController against an object."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_run_franka_pick_place({
                "robot_prim_path": request.robot_prim_path,
                "object_prim_path": request.object_prim_path,
                "target_position": list(request.target_position),
                "robot_description": request.robot_description,
                "picking_position": (
                    list(request.picking_position)
                    if request.picking_position is not None
                    else None
                ),
                "end_effector_initial_height": request.end_effector_initial_height,
                "end_effector_offset": (
                    list(request.end_effector_offset)
                    if request.end_effector_offset is not None
                    else None
                ),
                "end_effector_orientation": (
                    list(request.end_effector_orientation)
                    if request.end_effector_orientation is not None
                    else None
                ),
                "events_dt": list(request.events_dt) if request.events_dt is not None else None,
                "max_steps": request.max_steps,
                "position_tolerance": request.position_tolerance,
                "lift_height_tolerance": request.lift_height_tolerance,
            })
            result = RobotFrankaPickPlaceResult(
                ok=bool(raw.get("ok", False)),
                robot_prim_path=str(raw.get("robot_prim_path", request.robot_prim_path)),
                object_prim_path=str(raw.get("object_prim_path", request.object_prim_path)),
                target_position=tuple(
                    float(v) for v in raw.get("target_position", request.target_position)
                ),  # type: ignore[arg-type]
                controller=str(raw.get("controller", "")),
                gripper=str(raw.get("gripper", "")),
                uses_kinematic_carry=bool(raw.get("uses_kinematic_carry", True)),
                steps=int(raw.get("steps", 0)),
                done=bool(raw.get("done", False)),
                placed=bool(raw.get("placed", False)),
                lifted=bool(raw.get("lifted", False)),
                initial_object_position=tuple(
                    float(v) for v in raw.get("initial_object_position", (0.0, 0.0, 0.0))
                ),  # type: ignore[arg-type]
                final_object_position=tuple(
                    float(v) for v in raw.get("final_object_position", (0.0, 0.0, 0.0))
                ),  # type: ignore[arg-type]
                final_distance=float(raw.get("final_distance", 0.0)),
                max_lift_delta=float(raw.get("max_lift_delta", 0.0)),
                object_bbox_size=tuple(
                    float(v) for v in raw.get("object_bbox_size", (0.0, 0.0, 0.0))
                ),  # type: ignore[arg-type]
                picking_position=tuple(
                    float(v) for v in raw.get("picking_position", request.picking_position or (0.0, 0.0, 0.0))
                ),  # type: ignore[arg-type]
                picking_position_source=str(raw.get("picking_position_source", "unknown")),
                end_effector_initial_height=float(
                    raw.get("end_effector_initial_height", request.end_effector_initial_height or 0.0)
                ),
                end_effector_initial_height_source=str(
                    raw.get("end_effector_initial_height_source", "unknown")
                ),
                end_effector_orientation=(
                    tuple(float(v) for v in raw["end_effector_orientation"])
                    if raw.get("end_effector_orientation") is not None
                    else None
                ),  # type: ignore[arg-type]
                diagnostics=dict(raw.get("diagnostics", {})),
                reason=(
                    str(raw.get("reason"))
                    if raw.get("reason") is not None
                    else None
                ),
            )
            if not result.ok:
                return fail_result(
                    result.reason or "Franka pick-place physical validation failed",
                    started_ms=started,
                    error_code="ROBOT_FRANKA_PICK_PLACE_FAILED",
                    data=result,
                )
            return ok_result(result, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_FRANKA_PICK_PLACE_ERROR",
            )

    async def install_franka_pick_place_playback_demo(
        self,
        meta: OperationMeta,
        request: RobotFrankaPickPlaceDemoRequest,
    ) -> ModuleResult[RobotFrankaPickPlaceDemoStatus]:
        """Install a playback-tick Franka pick/place demo controlled by GUI Play."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_install_franka_pick_place_playback_demo({
                "robot_prim_path": request.robot_prim_path,
                "object_prim_path": request.object_prim_path,
                "target_position": list(request.target_position),
                "object_initial_position": list(request.object_initial_position),
                "object_size": request.object_size,
                "object_asset_url": request.object_asset_url,
                "max_grasp_width_m": request.max_grasp_width_m,
                "fit_clearance_m": request.fit_clearance_m,
                "grid_asset_url": request.grid_asset_url
                or resolve_catalog_asset_url("environments", _DEFAULT_DEMO_GRID_CATALOG_PATH),
                "robot_description": request.robot_description,
                "picking_position": (
                    list(request.picking_position)
                    if request.picking_position is not None
                    else None
                ),
                "end_effector_initial_height": request.end_effector_initial_height,
                "end_effector_offset": (
                    list(request.end_effector_offset)
                    if request.end_effector_offset is not None
                    else None
                ),
                "end_effector_orientation": (
                    list(request.end_effector_orientation)
                    if request.end_effector_orientation is not None
                    else None
                ),
                "events_dt": list(request.events_dt) if request.events_dt is not None else None,
                "max_steps": request.max_steps,
                "position_tolerance": request.position_tolerance,
                "lift_height_tolerance": request.lift_height_tolerance,
                "create_demo_scene": request.create_demo_scene,
                "reset_on_play": request.reset_on_play,
            })
            status = _parse_pick_place_demo_status(raw, request)
            if status.status == "failed":
                return fail_result(
                    status.last_error or "Franka pick-place demo failed",
                    started_ms=started,
                    error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED",
                    data=status,
                )
            return ok_result(status, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_INSTALL_ERROR",
            )

    async def install_pick_place_playback_demo(
        self,
        meta: OperationMeta,
        request: RobotPickPlaceDemoRequest,
    ) -> ModuleResult[RobotFrankaPickPlaceDemoStatus]:
        """Install a profile-selected pick/place playback demo.

        Only profiles with live proof are routed to an executable adapter.
        Candidate/IK/profile-only records return an explicit unsupported status
        rather than pretending pick/place support exists.
        """
        started = int(time.time() * 1000)
        profile = get_robot_arm_profile(request.profile_name)
        if profile is None:
            return ok_result(
                _unsupported_pick_place_demo_status(
                    request=request,
                    support_reason=f"Unknown robot arm profile: {request.profile_name}",
                ),
                started_ms=started,
            )

        if _uses_franka_pick_place_adapter(profile):
            franka_result = await self.install_franka_pick_place_playback_demo(
                meta,
                RobotFrankaPickPlaceDemoRequest(
                    robot_prim_path=request.robot_prim_path,
                    object_prim_path=request.object_prim_path,
                    target_position=request.target_position,
                    object_initial_position=request.object_initial_position,
                    object_size=request.object_size,
                    object_asset_url=request.object_asset_url,
                    grid_asset_url=request.grid_asset_url,
                    max_grasp_width_m=profile.max_grasp_width_m,
                    fit_clearance_m=profile.fit_clearance_m,
                    robot_description=profile.robot_description or "Franka",
                    picking_position=request.picking_position,
                    end_effector_initial_height=request.end_effector_initial_height,
                    end_effector_offset=request.end_effector_offset,
                    end_effector_orientation=request.end_effector_orientation,
                    events_dt=request.events_dt,
                    max_steps=request.max_steps,
                    position_tolerance=request.position_tolerance,
                    lift_height_tolerance=request.lift_height_tolerance,
                    create_demo_scene=request.create_demo_scene,
                    reset_on_play=request.reset_on_play,
                ),
            )
            if franka_result.data is None:
                return franka_result
            profiled_status = _with_profile_status(franka_result.data, profile)
            if not franka_result.ok:
                return fail_result(
                    franka_result.message or "Profile pick-place demo failed",
                    started_ms=started,
                    error_code=franka_result.error_code,
                    data=profiled_status,
                )
            return ok_result(profiled_status, started_ms=started)

        return ok_result(
            _unsupported_pick_place_demo_status(
                request=request,
                profile_name=profile.profile_name,
                support_status=profile.support_status,
                support_reason=profile.support_reason,
                controller_strategy=profile.controller_strategy,
            ),
            started_ms=started,
        )

    async def reset_pick_place_demo(
        self,
        meta: OperationMeta,
    ) -> ModuleResult[RobotFrankaPickPlaceDemoStatus]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_reset_pick_place_demo()
            return ok_result(_parse_pick_place_demo_status(raw), started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_RESET_ERROR",
            )

    async def get_pick_place_demo_status(
        self,
        meta: OperationMeta,
    ) -> ModuleResult[RobotFrankaPickPlaceDemoStatus]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_get_pick_place_demo_status()
            status = _parse_pick_place_demo_status(raw)
            if status.status == "failed":
                return fail_result(
                    status.last_error or "Franka pick-place demo failed",
                    started_ms=started,
                    error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED",
                    data=status,
                )
            return ok_result(status, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_ERROR",
            )


def _parse_pick_place_demo_status(
    raw: dict,
    request: RobotFrankaPickPlaceDemoRequest | None = None,
) -> RobotFrankaPickPlaceDemoStatus:
    target_default = request.target_position if request else (0.0, 0.0, 0.0)
    initial_default = request.object_initial_position if request else (0.0, 0.0, 0.0)
    bbox = raw.get("object_bbox", {}) if isinstance(raw.get("object_bbox"), dict) else {}
    diagnostics = dict(raw.get("diagnostics", {}))
    fit_info = diagnostics.get("object_fit", {})
    if not isinstance(fit_info, dict):
        fit_info = {}
    return RobotFrankaPickPlaceDemoStatus(
        ok=bool(raw.get("ok", raw.get("status") != "failed")),
        status=str(raw.get("status", "idle")),
        robot_prim_path=str(raw.get("robot_prim_path", request.robot_prim_path if request else "")),
        object_prim_path=str(raw.get("object_prim_path", request.object_prim_path if request else "")),
        target_position=tuple(
            float(v) for v in raw.get("target_position", target_default)
        ),  # type: ignore[arg-type]
        uses_kinematic_carry=bool(raw.get("uses_kinematic_carry", True)),
        steps=int(raw.get("steps", 0)),
        controller_event=int(raw.get("controller_event", 0)),
        done=bool(raw.get("done", False)),
        placed=bool(raw.get("placed", False)),
        lifted=bool(raw.get("lifted", False)),
        initial_object_position=tuple(
            float(v) for v in raw.get("initial_object_position", initial_default)
        ),  # type: ignore[arg-type]
        final_object_position=tuple(
            float(v) for v in raw.get("final_object_position", raw.get("object_bbox_center", initial_default))
        ),  # type: ignore[arg-type]
        final_distance=float(raw.get("final_distance", 0.0)),
        max_lift_delta=float(raw.get("max_lift_delta", 0.0)),
        object_bbox_center=tuple(
            float(v) for v in raw.get("object_bbox_center", bbox.get("center", initial_default))
        ),  # type: ignore[arg-type]
        object_bbox_size=tuple(
            float(v) for v in raw.get("object_bbox_size", bbox.get("size", (0.0, 0.0, 0.0)))
        ),  # type: ignore[arg-type]
        object_fit_ok=bool(raw.get("object_fit_ok", fit_info.get("ok", True))),
        object_fit_reason=(
            str(raw.get("object_fit_reason", fit_info.get("reason")))
            if raw.get("object_fit_reason", fit_info.get("reason")) is not None
            else None
        ),
        object_fit_axis=(
            str(raw.get("object_fit_axis", fit_info.get("axis")))
            if raw.get("object_fit_axis", fit_info.get("axis")) is not None
            else None
        ),
        object_fit_limit_m=(
            float(raw.get("object_fit_limit_m", fit_info.get("limit_m")))
            if raw.get("object_fit_limit_m", fit_info.get("limit_m")) is not None
            else None
        ),
        object_fit_measured_m=(
            float(raw.get("object_fit_measured_m", fit_info.get("measured_m")))
            if raw.get("object_fit_measured_m", fit_info.get("measured_m")) is not None
            else None
        ),
        picking_position=tuple(
            float(v) for v in raw.get("picking_position", initial_default)
        ),  # type: ignore[arg-type]
        end_effector_initial_height=float(raw.get("end_effector_initial_height", 0.0)),
        diagnostics=diagnostics,
        profile_name=(
            str(raw.get("profile_name"))
            if raw.get("profile_name") is not None
            else None
        ),
        support_status=(
            str(raw.get("support_status"))
            if raw.get("support_status") is not None
            else None
        ),
        support_reason=(
            str(raw.get("support_reason"))
            if raw.get("support_reason") is not None
            else None
        ),
        controller_strategy=(
            str(raw.get("controller_strategy"))
            if raw.get("controller_strategy") is not None
            else None
        ),
        last_error=(
            str(raw.get("last_error"))
            if raw.get("last_error") is not None
            else None
        ),
    )


def _with_profile_status(
    status: RobotFrankaPickPlaceDemoStatus,
    profile: object,
) -> RobotFrankaPickPlaceDemoStatus:
    return RobotFrankaPickPlaceDemoStatus(
        ok=status.ok,
        status=status.status,
        robot_prim_path=status.robot_prim_path,
        object_prim_path=status.object_prim_path,
        target_position=status.target_position,
        uses_kinematic_carry=status.uses_kinematic_carry,
        steps=status.steps,
        controller_event=status.controller_event,
        done=status.done,
        placed=status.placed,
        lifted=status.lifted,
        initial_object_position=status.initial_object_position,
        final_object_position=status.final_object_position,
        final_distance=status.final_distance,
        max_lift_delta=status.max_lift_delta,
        object_bbox_center=status.object_bbox_center,
        object_bbox_size=status.object_bbox_size,
        object_fit_ok=status.object_fit_ok,
        object_fit_reason=status.object_fit_reason,
        object_fit_axis=status.object_fit_axis,
        object_fit_limit_m=status.object_fit_limit_m,
        object_fit_measured_m=status.object_fit_measured_m,
        picking_position=status.picking_position,
        end_effector_initial_height=status.end_effector_initial_height,
        diagnostics=status.diagnostics,
        profile_name=getattr(profile, "profile_name", None),
        support_status=getattr(profile, "support_status", None),
        support_reason=getattr(profile, "support_reason", None),
        controller_strategy=getattr(profile, "controller_strategy", None),
        last_error=status.last_error,
    )


def _uses_franka_pick_place_adapter(profile: object) -> bool:
    return getattr(profile, "controller_strategy", None) in {
        "official_franka_pick_place",
        "same_family_franka_candidate",
    }


def _unsupported_pick_place_demo_status(
    request: RobotPickPlaceDemoRequest,
    profile_name: str | None = None,
    support_status: str = "unsupported",
    support_reason: str = "Profile has no validated pick/place adapter.",
    controller_strategy: str | None = None,
) -> RobotFrankaPickPlaceDemoStatus:
    return RobotFrankaPickPlaceDemoStatus(
        ok=False,
        status="unsupported",
        robot_prim_path=request.robot_prim_path,
        object_prim_path=request.object_prim_path,
        target_position=request.target_position,
        uses_kinematic_carry=False,
        steps=0,
        controller_event=0,
        done=False,
        placed=False,
        lifted=False,
        initial_object_position=request.object_initial_position,
        final_object_position=request.object_initial_position,
        final_distance=0.0,
        max_lift_delta=0.0,
        object_bbox_center=request.object_initial_position,
        object_bbox_size=(0.0, 0.0, 0.0),
        object_fit_ok=False,
        object_fit_reason="Profile has no validated pick/place fit metadata.",
        object_fit_axis=None,
        object_fit_limit_m=None,
        object_fit_measured_m=None,
        picking_position=request.picking_position or request.object_initial_position,
        end_effector_initial_height=request.end_effector_initial_height or 0.0,
        diagnostics={
            "unsupported": True,
            "requested_profile": request.profile_name,
        },
        profile_name=profile_name or request.profile_name,
        support_status=support_status,
        support_reason=support_reason,
        controller_strategy=controller_strategy,
        last_error=None,
    )
