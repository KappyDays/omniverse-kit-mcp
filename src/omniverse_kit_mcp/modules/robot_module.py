"""Robot module — USD load, joint control, async navigate (Phase B)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, fail_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.robot import (
    JointConfig,
    JointPositions,
    JointPositionsSetRequest,
    JointPositionsSetResult,
    RobotDrivePhysicsRequest,
    RobotDrivePhysicsResult,
    RobotEEPose,
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
    RobotSetEETargetRequest,
    RobotSetEETargetResult,
)

logger = logging.getLogger(__name__)


class RobotModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

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
