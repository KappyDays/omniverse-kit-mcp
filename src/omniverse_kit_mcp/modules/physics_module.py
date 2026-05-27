"""Physics module — UsdPhysics rigid body / collider / material / joint / scene / viz (Phase F)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.physics import (
    PhysicsApplyColliderRequest,
    PhysicsApplyColliderResult,
    PhysicsApplyMaterialRequest,
    PhysicsApplyMaterialResult,
    PhysicsApplyRigidBodyRequest,
    PhysicsApplyRigidBodyResult,
    PhysicsCreateJointRequest,
    PhysicsCreateJointResult,
    PhysicsRigidBodyState,
    PhysicsSetJointDriveRequest,
    PhysicsSetJointDriveResult,
    PhysicsSetSceneRequest,
    PhysicsSetSceneResult,
    PhysicsVisualizeRequest,
    PhysicsVisualizeResult,
)

logger = logging.getLogger(__name__)


class PhysicsModule:
    """Apply rigid bodies / colliders / materials / joints / physics scene / viz."""

    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def apply_rigid_body(
        self, meta: OperationMeta, request: PhysicsApplyRigidBodyRequest,
    ) -> ModuleResult[PhysicsApplyRigidBodyResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_apply_rigid_body({
                "prim_path": request.prim_path,
                "mass": request.mass,
                "dynamic": request.dynamic,
            })
            return ok_result(
                PhysicsApplyRigidBodyResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=str(raw.get("prim_path", request.prim_path)),
                    mass=float(raw.get("mass", request.mass)),
                    dynamic=bool(raw.get("dynamic", request.dynamic)),
                    applied_apis=tuple(raw.get("applied_apis") or ()),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_APPLY_RIGID_BODY_ERROR",
            )

    async def get_rigid_body_state(
        self, meta: OperationMeta, prim_path: str,
    ) -> ModuleResult[PhysicsRigidBodyState]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_get_rigid_body_state(prim_path)
            lv = raw.get("linear_velocity") or [0.0, 0.0, 0.0]
            av = raw.get("angular_velocity") or [0.0, 0.0, 0.0]
            com = raw.get("center_of_mass") or [0.0, 0.0, 0.0]
            return ok_result(
                PhysicsRigidBodyState(
                    prim_path=str(raw.get("prim_path", prim_path)),
                    source=str(raw.get("source", "unknown")),
                    linear_velocity=(float(lv[0]), float(lv[1]), float(lv[2])),
                    angular_velocity=(float(av[0]), float(av[1]), float(av[2])),
                    mass=float(raw.get("mass", 0.0)),
                    center_of_mass=(float(com[0]), float(com[1]), float(com[2])),
                    is_kinematic=bool(raw.get("is_kinematic", False)),
                    is_enabled=bool(raw.get("is_enabled", True)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_GET_RIGID_BODY_STATE_ERROR",
            )

    async def apply_collider(
        self, meta: OperationMeta, request: PhysicsApplyColliderRequest,
    ) -> ModuleResult[PhysicsApplyColliderResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_apply_collider({
                "prim_path": request.prim_path,
                "approximation": request.approximation,
            })
            return ok_result(
                PhysicsApplyColliderResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=str(raw.get("prim_path", request.prim_path)),
                    approximation=str(raw.get("approximation", request.approximation)),
                    applied_apis=tuple(raw.get("applied_apis") or ()),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_APPLY_COLLIDER_ERROR",
            )

    async def apply_material(
        self, meta: OperationMeta, request: PhysicsApplyMaterialRequest,
    ) -> ModuleResult[PhysicsApplyMaterialResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_apply_material({
                "prim_path": request.prim_path,
                "friction": request.friction,
                "restitution": request.restitution,
                "density": request.density,
                "material_name": request.material_name,
            })
            return ok_result(
                PhysicsApplyMaterialResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=str(raw.get("prim_path", request.prim_path)),
                    material_prim_path=str(raw.get("material_prim_path", "")),
                    friction=float(raw.get("friction", request.friction)),
                    restitution=float(raw.get("restitution", request.restitution)),
                    density=float(raw.get("density", request.density)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_APPLY_MATERIAL_ERROR",
            )

    async def create_joint(
        self, meta: OperationMeta, request: PhysicsCreateJointRequest,
    ) -> ModuleResult[PhysicsCreateJointResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_create_joint({
                "joint_type": request.joint_type,
                "body_a": request.body_a,
                "body_b": request.body_b,
                "anchor": list(request.anchor),
                "axis": list(request.axis),
                "joint_prim_path": request.joint_prim_path,
            })
            return ok_result(
                PhysicsCreateJointResult(
                    ok=bool(raw.get("ok", True)),
                    joint_prim_path=str(raw.get("joint_prim_path", "")),
                    joint_type=str(raw.get("joint_type", request.joint_type)),
                    body_a=str(raw.get("body_a", request.body_a)),
                    body_b=str(raw.get("body_b", request.body_b)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_CREATE_JOINT_ERROR",
            )

    async def set_joint_drive(
        self, meta: OperationMeta, request: PhysicsSetJointDriveRequest,
    ) -> ModuleResult[PhysicsSetJointDriveResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_set_joint_drive({
                "joint_prim_path": request.joint_prim_path,
                "drive_type": request.drive_type,
                "target_position": request.target_position,
                "target_velocity": request.target_velocity,
                "stiffness": request.stiffness,
                "damping": request.damping,
                "max_force": request.max_force,
            })
            mf = raw.get("max_force", request.max_force)
            return ok_result(
                PhysicsSetJointDriveResult(
                    ok=bool(raw.get("ok", True)),
                    joint_prim_path=str(raw.get("joint_prim_path", request.joint_prim_path)),
                    drive_type=str(raw.get("drive_type", request.drive_type)),
                    target_position=float(raw.get("target_position", request.target_position)),
                    target_velocity=float(raw.get("target_velocity", request.target_velocity)),
                    stiffness=float(raw.get("stiffness", request.stiffness)),
                    damping=float(raw.get("damping", request.damping)),
                    max_force=None if mf is None else float(mf),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_SET_JOINT_DRIVE_ERROR",
            )

    async def set_scene(
        self, meta: OperationMeta, request: PhysicsSetSceneRequest,
    ) -> ModuleResult[PhysicsSetSceneResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_set_scene({
                "gravity": list(request.gravity),
                "timestep": request.timestep,
                "solver_iter_pos": request.solver_iter_pos,
                "solver_iter_vel": request.solver_iter_vel,
                "scene_prim_path": request.scene_prim_path,
            })
            gravity_raw = raw.get("gravity") or list(request.gravity)
            return ok_result(
                PhysicsSetSceneResult(
                    ok=bool(raw.get("ok", True)),
                    scene_prim_path=str(
                        raw.get("scene_prim_path", request.scene_prim_path),
                    ),
                    gravity=(
                        float(gravity_raw[0]),
                        float(gravity_raw[1]),
                        float(gravity_raw[2]),
                    ),
                    gravity_magnitude=float(raw.get("gravity_magnitude", 0.0)),
                    timestep=float(raw.get("timestep", request.timestep)),
                    time_steps_per_second=int(raw.get("time_steps_per_second", 60)),
                    solver_iter_pos=int(raw.get("solver_iter_pos", request.solver_iter_pos)),
                    solver_iter_vel=int(raw.get("solver_iter_vel", request.solver_iter_vel)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_SET_SCENE_ERROR",
            )

    async def visualize(
        self, meta: OperationMeta, request: PhysicsVisualizeRequest,
    ) -> ModuleResult[PhysicsVisualizeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.physics_visualize({"mode": request.mode})
            return ok_result(
                PhysicsVisualizeResult(
                    ok=bool(raw.get("ok", True)),
                    mode=str(raw.get("mode", request.mode)),
                    active_settings=tuple(raw.get("active_settings") or ()),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="PHYSICS_VISUALIZE_ERROR",
            )
