"""Robot module — USD load, joint control, async navigate (Phase B)."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

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
    RobotArmProfile,
    RobotArmProfileProbeRequest,
    RobotArmProfileProbeResult,
    RobotArmProfilesProbeRequest,
    RobotArmProfilesProbeResult,
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
    RobotProbeCheck,
    RobotSetEETargetRequest,
    RobotSetEETargetResult,
)

logger = logging.getLogger(__name__)

_DEFAULT_DEMO_GRID_CATALOG_PATH = "Grid/default_environment.usd"
_PROBE_ROOT = "/World/MCPProbe"
_PROBE_NUDGE_DELTA = 0.01
_PROBE_NUDGE_TOLERANCE = 1e-4
_PROBE_NUDGE_MIN_PROGRESS_RATIO = 0.25
_PROBE_NUDGE_SETTLE_FRAMES = 5
_PROBE_IK_DEFAULT_TARGET_POSE = (0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0)
_PROBE_IK_RELAXED_Z_TARGET_POSE = (0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0)
_PROBE_IK_KAWASAKI_RELAXED_TARGET_POSE = _PROBE_IK_RELAXED_Z_TARGET_POSE
_PROBE_IK_KAWASAKI_RS080N_RELAXED_FORWARD_TARGET_POSE = (
    0.7,
    0.0,
    0.5,
    0.0,
    0.0,
    1.0,
    0.0,
)
_PROBE_IK_KUKA_FORWARD_HIGH_IDENTITY_TARGET_POSE = (
    1.5,
    0.0,
    1.2,
    1.0,
    0.0,
    0.0,
    0.0,
)
_PROBE_TIMEOUT_CLEANUP_TIMEOUT_S = 3.0
_PROBE_BATCH_CLEANUP_RESERVE_S = 2 * _PROBE_TIMEOUT_CLEANUP_TIMEOUT_S + 2.0
_PROBE_PHASE_OPERATION_TIMEOUT_S = 20.0
_PICK_PLACE_STATUS_FALLBACK_TOOL_ORDER = (
    "simulation_get_status",
    "robot_get_pick_place_demo_status",
    "extension_capture_logs",
)
_PICK_PLACE_UNSUPPORTED_FALLBACK_TOOL_ORDER = (
    "robot_list_arm_profiles",
    "robot_probe_arm_profile",
    "robot_install_pick_place_playback_demo",
)
_ROBOT_LOAD_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "stage_capture_snapshot",
    "official_asset_search",
    "asset_search",
    "robot_load",
    "extension_capture_logs",
)
_ROBOT_GRIPPER_CONTROL_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "stage_capture_snapshot",
    "robot_gripper_control",
    "extension_capture_logs",
)
_ROBOT_SET_EE_TARGET_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "stage_capture_snapshot",
    "robot_get_joint_config_static",
    "robot_set_ee_target",
    "extension_capture_logs",
)
_PROBE_UNSAFE_TIMEOUT_CLEANUP_PHASES = {
    "simulation_play",
    "warmup_step",
    "safe_nudge",
}
_KNOWN_DYNAMIC_TIMEOUT_PROFILE_REASONS = {
    # Direct live dynamic timeout evidence is recorded in
    # docs/artifacts/robot-pickplace/robot-arm-mcp-probe-matrix-2026-06-15.md.
    # Batch-aborted rows are intentionally not included here until isolated
    # dynamic probes prove the same hazard profile-by-profile.
    "dofbot": "warmup_step timed out after load/articulation/play and degraded the host",
    "lite6": "dynamic profile-only probe timed out and degraded the host",
    "lite6_gripper": "isolated dynamic profile-only probe timed out during warmup_step and degraded the host",
    "openarm_bimanual": "isolated dynamic profile-only probe timed out during warmup_step and degraded the host",
    "openarm_unimanual": "dynamic profile-only probe timed out and degraded the host",
    "so101_new_calib": "dynamic profile-only probe timed out and degraded the host",
    "uf850": "isolated dynamic profile-only probe timed out during warmup_step and degraded the host",
    "ur3": "dynamic IK-only probe timed out and degraded the host",
    "ur5": "dynamic IK-only probe timed out and degraded the host",
    "ur20": "dynamic profile-only probe timed out and degraded the host",
    "xarm6": "isolated dynamic profile-only probe timed out during warmup_step and degraded the host",
    "xarm7": "isolated dynamic profile-only probe timed out during warmup_step and degraded the host",
}
_KNOWN_PICK_PLACE_BLOCKER_PROFILE_REASONS = {
    # Direct live playback blocker evidence is recorded in
    # docs/artifacts/robot-pickplace/robot-arm-mcp-probe-matrix-2026-06-15.md.
    # These rows are about manipulation playback proof only; they do not change
    # probe-level MCP controllability claims.
    "franka_panda": (
        "profile-selected playback repeatability proof failed on cycle 2: "
        "the cache-fix rerun avoided the prior ParallelGripper NoneType crash "
        "but failed with insufficient lift for durable proof"
    ),
    "factory_franka": (
        "direct Franka-family playback trials reached no durable lift/place proof, "
        "and a deeper combined-Z offset trial degraded simulation/status/log calls"
    ),
}
_PROBE_PROGRESS: ContextVar[dict[str, Any] | None] = ContextVar(
    "robot_probe_progress",
    default=None,
)
_GRIPPER_UNSUPPORTED_MARKERS = (
    "no gripper",
    "gripper joint",
    "unsupported",
    "not supported",
)
_IK_UNSUPPORTED_MARKERS = (
    "no lula",
    "motion policy config",
    "solver unavailable",
    "not importable",
    "skip ik",
    "unsupported",
    "not supported",
)
_PROBE_NUDGE_EXCLUDED_JOINT_NAME_MARKERS = (
    "finger",
    "gripper",
    "wheel",
    "caster",
    "dummy_base",
    "base_prismatic",
    "base_revolute",
    "base_x",
    "base_y",
    "base_theta",
    "odom",
)
_EE_POSE_UNSUPPORTED_MARKERS = (
    "end-effector",
    "end effector",
    "ee pose",
    "frame",
    "link",
    "unsupported",
    "not supported",
    "not found",
)


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
            known_dynamic_timeout_reasons = {
                profile.profile_name: reason
                for profile in profiles
                if (reason := _known_dynamic_timeout_reason(profile.profile_name))
                is not None
            }
            known_pick_place_blocker_reasons = {
                profile.profile_name: reason
                for profile in profiles
                if (
                    reason := _known_pick_place_blocker_reason(profile.profile_name)
                )
                is not None
            }
            static_only_probe_profiles = tuple(known_dynamic_timeout_reasons.keys())
            dynamic_probe_profiles = tuple(
                profile.profile_name
                for profile in profiles
                if profile.profile_name not in known_dynamic_timeout_reasons
            )
            recommended_probe_mode_by_profile = {
                profile.profile_name: (
                    "static_only_known_dynamic_timeout"
                    if profile.profile_name in known_dynamic_timeout_reasons
                    else "dynamic_with_bounded_timeouts"
                )
                for profile in profiles
            }
            recommended_probe_mode_reasons = {
                profile.profile_name: (
                    known_dynamic_timeout_reasons[profile.profile_name]
                    if profile.profile_name in known_dynamic_timeout_reasons
                    else (
                        "No durable live dynamic-timeout evidence is registered; "
                        "schedule dynamic checks with bounded per-profile and "
                        "batch timeouts."
                    )
                )
                for profile in profiles
            }
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
                    known_dynamic_timeout_profiles=tuple(
                        known_dynamic_timeout_reasons.keys()
                    ),
                    known_dynamic_timeout_profile_reasons=known_dynamic_timeout_reasons,
                    dynamic_probe_recommended_profiles=dynamic_probe_profiles,
                    static_only_probe_recommended_profiles=static_only_probe_profiles,
                    recommended_probe_mode_by_profile=(
                        recommended_probe_mode_by_profile
                    ),
                    recommended_probe_mode_reasons=recommended_probe_mode_reasons,
                    known_pick_place_blocker_profiles=tuple(
                        known_pick_place_blocker_reasons.keys()
                    ),
                    known_pick_place_blocker_profile_reasons=(
                        known_pick_place_blocker_reasons
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
                    diagnostics=(
                        dict(raw["diagnostics"])
                        if isinstance(raw.get("diagnostics"), dict)
                        else {}
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            error_code = (
                "CAPABILITY_NOT_SUPPORTED"
                if getattr(exc, "error_code", None) == "CAPABILITY_NOT_SUPPORTED"
                else "ROBOT_LOAD_ERROR"
            )
            data = RobotLoadResult(
                ok=False,
                prim_path=request.prim_path,
                usd_url=request.usd_url,
                type_name="",
                has_articulation=False,
                diagnostics=_robot_load_error_diagnostics(
                    request=request,
                    upstream_error_code=error_code,
                    upstream_message=str(exc),
                ),
            )
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code=error_code,
                data=data,
            )

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
                _joint_config_from_raw(raw, prim_path),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="ROBOT_GET_JOINT_CONFIG_ERROR"
            )

    async def get_joint_config_static(
        self,
        meta: OperationMeta,
        prim_path: str,
    ) -> ModuleResult[JointConfig]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.robot_get_joint_config_static(prim_path)
            return ok_result(
                _joint_config_from_raw(raw, prim_path),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_GET_STATIC_JOINT_CONFIG_ERROR",
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
                    diagnostics=(
                        dict(raw["diagnostics"])
                        if isinstance(raw.get("diagnostics"), dict)
                        else {}
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            error_code = "ROBOT_GRIPPER_CONTROL_ERROR"
            data = RobotGripperControlResult(
                prim_path=request.prim_path,
                action=request.action,
                target_value=float(request.target or 0.0),
                gripper_joint_names=(),
                gripper_joint_indices=(),
                dof_count=0,
                diagnostics=_robot_gripper_control_error_diagnostics(
                    request=request,
                    upstream_error_code=error_code,
                    upstream_message=str(exc),
                ),
            )
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code=error_code,
                data=data,
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
                    diagnostics=(
                        dict(raw["diagnostics"])
                        if isinstance(raw.get("diagnostics"), dict)
                        else {}
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            error_code = "ROBOT_SET_EE_TARGET_ERROR"
            data = RobotSetEETargetResult(
                prim_path=request.prim_path,
                target_pose=request.target_pose,
                robot_description=request.robot_description,
                end_effector_frame=request.end_effector_frame or "",
                lula_import_path="",
                ik_success=False,
                solution=(),
                diagnostics=_robot_set_ee_target_error_diagnostics(
                    request=request,
                    upstream_error_code=error_code,
                    upstream_message=str(exc),
                ),
            )
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code=error_code,
                data=data,
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

    async def probe_arm_profile(
        self,
        meta: OperationMeta,
        request: RobotArmProfileProbeRequest,
    ) -> ModuleResult[RobotArmProfileProbeResult]:
        started = int(time.time() * 1000)
        profile = get_robot_arm_profile(request.profile_name)
        if profile is None:
            return error_result(
                f"Unknown robot arm profile: {request.profile_name}",
                started_ms=started,
                error_code="ROBOT_PROBE_UNKNOWN_PROFILE",
            )

        prim_path = request.prim_path or _default_probe_prim_path(profile.profile_name)
        known_timeout_reason = _known_dynamic_timeout_reason(profile.profile_name)
        static_only_known_timeout = (
            request.dynamic_checks
            and request.static_only_for_known_dynamic_timeouts
            and known_timeout_reason is not None
        )
        if request.timeout_s is not None and request.timeout_s > 0:
            progress: dict[str, Any] = {
                "last_phase": "start",
                "completed_checks": [],
                "deadline_monotonic": time.monotonic() + request.timeout_s,
                "profile_name": profile.profile_name,
                "prim_path": prim_path,
            }
            progress_token = _PROBE_PROGRESS.set(progress)
            inner_request = RobotArmProfileProbeRequest(
                profile_name=request.profile_name,
                prim_path=prim_path,
                reset_stage=request.reset_stage,
                safe_nudge=request.safe_nudge,
                cleanup=request.cleanup,
                dynamic_checks=request.dynamic_checks,
                static_only_for_known_dynamic_timeouts=(
                    request.static_only_for_known_dynamic_timeouts
                ),
                timeout_s=None,
            )
            try:
                return await asyncio.wait_for(
                    self.probe_arm_profile(meta, inner_request),
                    timeout=request.timeout_s,
                )
            except asyncio.TimeoutError:
                checks = {
                    "probe_timeout": _probe_timeout_check(
                        timeout_s=request.timeout_s,
                        timeout_kind="single_profile",
                        progress=progress,
                    )
                }
                timeout_cleanup = await self._cleanup_after_probe_timeout(
                    prim_path,
                    cleanup=request.cleanup,
                    progress=progress,
                )
                checks.update(timeout_cleanup)
                result = _build_probe_result(profile, prim_path, checks)
                return ok_result(result, started_ms=started)
            finally:
                _PROBE_PROGRESS.reset(progress_token)

        checks: dict[str, RobotProbeCheck] = {}
        joint_config: JointConfig | None = None
        joint_positions: JointPositions | None = None
        effective_dynamic_checks = (
            request.dynamic_checks and not static_only_known_timeout
        )

        if request.reset_stage:
            _set_probe_phase("stage_reset_stop")
            checks["stage_reset_stop"] = await _probe_call(
                "stage_reset_stop",
                self._client.simulation_stop,
            )
            _mark_probe_check_complete("stage_reset_stop")
            if not checks["stage_reset_stop"].ok:
                result = _build_probe_result(profile, prim_path, checks)
                return ok_result(result, started_ms=started)
            _set_probe_phase("stage_reset")
            checks["stage_reset"] = await _probe_call("stage_reset", self._client.stage_new)
            _mark_probe_check_complete("stage_reset")
            if not checks["stage_reset"].ok:
                result = _build_probe_result(profile, prim_path, checks)
                return ok_result(result, started_ms=started)

        _set_probe_phase("load")
        load_check, load_raw = await _probe_raw_call(
            "load",
            self._client.robot_load,
            {
                "usd_url": profile.asset_url,
                "prim_path": prim_path,
                "position": None,
                "rotation": None,
            },
        )
        if load_raw:
            load_check = _with_probe_evidence(
                load_check,
                {
                    "prim_path": load_raw.get("prim_path", prim_path),
                    "has_articulation": bool(load_raw.get("has_articulation", False)),
                    "type_name": str(load_raw.get("type_name", "unknown")),
                },
            )
        checks["load"] = load_check
        _mark_probe_check_complete("load")
        checks["articulation"] = _probe_check(
            ok=bool(load_raw and load_raw.get("has_articulation", False)),
            skipped=not bool(load_raw),
            error_code=None if load_raw else "ROBOT_PROBE_LOAD_MISSING",
            message=(
                "PhysX articulation detected"
                if bool(load_raw and load_raw.get("has_articulation", False))
                else "Loaded profile has no detected PhysX articulation"
            ),
            evidence={"prim_path": prim_path},
        )
        _mark_probe_check_complete("articulation")
        if not checks["load"].ok or not checks["articulation"].ok:
            if request.cleanup:
                _set_probe_phase("cleanup")
                checks["cleanup"] = await _probe_call(
                    "cleanup",
                    self._client.stage_delete_prim,
                    prim_path,
                )
                _mark_probe_check_complete("cleanup")
            result = _build_probe_result(profile, prim_path, checks)
            return ok_result(result, started_ms=started)

        if not effective_dynamic_checks:
            _set_probe_phase("static_joint_config")
            static_joint_config_result = await self.get_joint_config_static(meta, prim_path)
            checks["static_joint_config"] = _static_joint_config_probe_check(
                static_joint_config_result
            )
            _mark_probe_check_complete("static_joint_config")
            checks.update(_dynamic_checks_disabled_checks())
            if request.cleanup:
                _set_probe_phase("cleanup")
                checks["cleanup"] = await _probe_call(
                    "cleanup",
                    self._client.stage_delete_prim,
                    prim_path,
                )
                _mark_probe_check_complete("cleanup")
            result = _build_probe_result(profile, prim_path, checks)
            if static_only_known_timeout and known_timeout_reason is not None:
                result = _mark_static_only_known_timeout_result(
                    result,
                    profile,
                    reason=known_timeout_reason,
                )
            return ok_result(result, started_ms=started)

        _set_probe_phase("simulation_play")
        checks["simulation_play"] = await _probe_call(
            "simulation_play",
            self._client.simulation_play,
            timeout_s=_probe_phase_operation_timeout_s(),
        )
        _mark_probe_check_complete("simulation_play")
        if not checks["simulation_play"].ok:
            cleanup_checks = await self._cleanup_after_probe_phase_failure(
                prim_path,
                cleanup=request.cleanup,
                timed_out=_probe_check_timed_out(checks["simulation_play"]),
            )
            checks.update(cleanup_checks)
            result = _build_probe_result(profile, prim_path, checks)
            return ok_result(result, started_ms=started)

        _set_probe_phase("warmup_step")
        checks["warmup_step"] = await _probe_call(
            "warmup_step",
            self._client.simulation_step,
            {"frames": 1},
            timeout_s=_probe_phase_operation_timeout_s(),
        )
        _mark_probe_check_complete("warmup_step")
        if not checks["warmup_step"].ok:
            cleanup_checks = await self._cleanup_after_probe_phase_failure(
                prim_path,
                cleanup=request.cleanup,
                timed_out=_probe_check_timed_out(checks["warmup_step"]),
            )
            checks.update(cleanup_checks)
            result = _build_probe_result(profile, prim_path, checks)
            return ok_result(result, started_ms=started)

        _set_probe_phase("joint_config")
        joint_config_result = await self.get_joint_config(meta, prim_path)
        if joint_config_result.ok and joint_config_result.data is not None:
            joint_config = joint_config_result.data
            checks["joint_config"] = _probe_check(
                ok=True,
                skipped=False,
                error_code=None,
                message="Joint config read succeeded",
                evidence={
                    "dof_count": joint_config.dof_count,
                    "source": joint_config.source,
                    "dof_names": list(joint_config.dof_names),
                },
            )
        else:
            checks["joint_config"] = _module_result_probe_check(
                joint_config_result,
                "Joint config read failed",
            )
        _mark_probe_check_complete("joint_config")

        _set_probe_phase("joint_read")
        joint_positions_result = await self.get_joint_positions(meta, prim_path)
        if joint_positions_result.ok and joint_positions_result.data is not None:
            joint_positions = joint_positions_result.data
            checks["joint_read"] = _probe_check(
                ok=True,
                skipped=False,
                error_code=None,
                message="Joint position read succeeded",
                evidence={"positions_count": len(joint_positions.positions)},
            )
        else:
            checks["joint_read"] = _module_result_probe_check(
                joint_positions_result,
                "Joint position read failed",
            )
        _mark_probe_check_complete("joint_read")

        if request.safe_nudge:
            _set_probe_phase("safe_nudge")
            checks["safe_nudge"] = await self._probe_safe_nudge(
                meta,
                prim_path,
                joint_config,
                joint_positions,
            )
        else:
            checks["safe_nudge"] = _probe_check(
                ok=True,
                skipped=True,
                error_code=None,
                message="Safe nudge disabled by request",
            )
        _mark_probe_check_complete("safe_nudge")

        if _profile_has_gripper_probe_candidate(profile):
            _set_probe_phase("gripper")
            checks["gripper"] = await self._probe_gripper(meta, prim_path)
        else:
            checks["gripper"] = _probe_check(
                ok=True,
                skipped=True,
                error_code=None,
                message="Profile has no built-in gripper candidate for joint probing",
                evidence={
                    "unsupported": True,
                    "capability": "gripper",
                    "gripper_kind": profile.gripper_kind,
                    "built_in_gripper": profile.built_in_gripper,
                },
            )
        _mark_probe_check_complete("gripper")

        if profile.robot_description:
            _set_probe_phase("ik")
            checks["ik"] = await self._probe_ik(meta, prim_path, profile)
        else:
            checks["ik"] = _probe_check(
                ok=True,
                skipped=True,
                error_code=None,
                message="Profile has no robot_description for Lula IK probing",
                evidence={
                    "unsupported": True,
                    "capability": "ik",
                    "robot_description": None,
                },
            )
        _mark_probe_check_complete("ik")

        ik_end_effector_frame = _probe_ik_end_effector_frame(checks["ik"])
        _set_probe_phase("ee_pose")
        checks["ee_pose"] = await self._probe_ee_pose(
            meta,
            prim_path,
            profile,
            ik_end_effector_frame=ik_end_effector_frame,
        )
        _mark_probe_check_complete("ee_pose")

        _set_probe_phase("simulation_stop")
        checks["simulation_stop"] = await _probe_call(
            "simulation_stop",
            self._client.simulation_stop,
        )
        _mark_probe_check_complete("simulation_stop")

        if request.cleanup:
            _set_probe_phase("cleanup")
            checks["cleanup"] = await _probe_call(
                "cleanup",
                self._client.stage_delete_prim,
                prim_path,
            )
            _mark_probe_check_complete("cleanup")

        result = _build_probe_result(profile, prim_path, checks)
        return ok_result(result, started_ms=started)

    async def probe_arm_profiles(
        self,
        meta: OperationMeta,
        request: RobotArmProfilesProbeRequest,
    ) -> ModuleResult[RobotArmProfilesProbeResult]:
        started = int(time.time() * 1000)
        try:
            profiles = _select_probe_profiles(request.profile_names)
            if request.status_filter:
                allowed = {status.lower() for status in request.status_filter}
                profiles = [
                    profile for profile in profiles
                    if _profile_is_unknown(profile)
                    or str(getattr(profile, "support_status", "")).lower() in allowed
                ]
            if request.family_filter:
                allowed = {family.lower() for family in request.family_filter}
                profiles = [
                    profile for profile in profiles
                    if _profile_is_unknown(profile)
                    or str(getattr(profile, "family", "")).lower() in allowed
                ]
            if request.limit is not None:
                profiles = profiles[:max(0, request.limit)]

            batch_deadline = (
                time.monotonic() + request.batch_timeout_s
                if request.batch_timeout_s is not None and request.batch_timeout_s > 0
                else None
            )
            results: list[RobotArmProfileProbeResult] = []
            for index, profile in enumerate(profiles):
                if _profile_is_unknown(profile):
                    results.append(_build_unknown_profile_result(profile))
                    continue
                profile_timeout_s = request.per_profile_timeout_s
                profile_dynamic_checks = request.dynamic_checks
                known_timeout_reason = _known_dynamic_timeout_reason(profile.profile_name)
                static_only_known_timeout = (
                    request.dynamic_checks
                    and request.static_only_for_known_dynamic_timeouts
                    and known_timeout_reason is not None
                )
                if static_only_known_timeout:
                    profile_dynamic_checks = False
                if batch_deadline is not None:
                    remaining_s = batch_deadline - time.monotonic()
                    if remaining_s <= _PROBE_BATCH_CLEANUP_RESERVE_S:
                        results.extend(
                            _build_batch_timeout_results(
                                profiles[index:],
                                timeout_s=request.batch_timeout_s,
                                remaining_s=max(0.0, remaining_s),
                            )
                        )
                        break
                    reserved_remaining_s = remaining_s - _PROBE_BATCH_CLEANUP_RESERVE_S
                    profile_timeout_s = (
                        min(profile_timeout_s, reserved_remaining_s)
                        if profile_timeout_s is not None and profile_timeout_s > 0
                        else reserved_remaining_s
                    )
                try:
                    probe = await self.probe_arm_profile(
                        meta,
                        RobotArmProfileProbeRequest(
                            profile_name=profile.profile_name,
                            reset_stage=request.reset_stage_per_profile,
                            safe_nudge=request.safe_nudge,
                            cleanup=request.cleanup,
                            dynamic_checks=profile_dynamic_checks,
                            timeout_s=profile_timeout_s,
                        ),
                    )
                except Exception as exc:
                    checks = {
                        "probe": _probe_check(
                            ok=False,
                            skipped=False,
                            error_code="ROBOT_PROBE_PROFILE_ERROR",
                            message=str(exc),
                            evidence={
                                "exception_type": type(exc).__name__,
                                "batch_profile": profile.profile_name,
                                "hard_failure": True,
                            },
                        )
                    }
                    results.append(
                        _build_probe_result(
                            profile,
                            _default_probe_prim_path(profile.profile_name),
                            checks,
                        )
                    )
                    continue
                if probe.data is not None:
                    profile_result = _mark_batch_timeout_result(probe.data, profile)
                    if static_only_known_timeout and known_timeout_reason is not None:
                        profile_result = _mark_static_only_known_timeout_result(
                            profile_result,
                            profile,
                            reason=known_timeout_reason,
                        )
                    results.append(profile_result)
                    abort_reason = _batch_abort_reason_after_probe_result(profile_result)
                    if abort_reason is not None:
                        results.extend(
                            _build_batch_aborted_results(
                                profiles[index + 1:],
                                blocked_by_profile=profile.profile_name,
                                reason=abort_reason,
                                checks=profile_result.checks,
                            )
                        )
                        break
                elif not probe.ok:
                    checks = {
                        "probe": _probe_check(
                            ok=False,
                            skipped=False,
                            error_code=probe.error_code or "ROBOT_PROBE_PROFILE_ERROR",
                            message=probe.message or "Profile probe failed",
                            evidence={
                                "batch_profile": profile.profile_name,
                                "hard_failure": True,
                                "returned_status": str(
                                    getattr(probe.status, "value", probe.status)
                                ),
                            },
                        )
                    }
                    results.append(
                        _build_probe_result(
                            profile,
                            _default_probe_prim_path(profile.profile_name),
                            checks,
                        )
                    )
                else:
                    checks = {
                        "probe": _probe_check(
                            ok=False,
                            skipped=False,
                            error_code="ROBOT_PROBE_PROFILE_EMPTY_RESULT",
                            message=(
                                "Profile probe returned ok=true without a "
                                "result payload"
                            ),
                            evidence={
                                "batch_profile": profile.profile_name,
                                "hard_failure": True,
                                "contract_violation": "ok_without_data",
                            },
                        )
                    }
                    results.append(
                        _build_probe_result(
                            profile,
                            _default_probe_prim_path(profile.profile_name),
                            checks,
                        )
                    )

            summary = _probe_batch_summary(results)
            return ok_result(
                RobotArmProfilesProbeResult(
                    count=len(results),
                    requested_count=len(profiles),
                    profile_names=request.profile_names,
                    status_filter=request.status_filter,
                    family_filter=request.family_filter,
                    mcp_controllability_counts=summary[
                        "mcp_controllability_counts"
                    ],
                    mcp_controllability_profiles=summary[
                        "mcp_controllability_profiles"
                    ],
                    probe_capability_level_name_counts=summary[
                        "probe_capability_level_name_counts"
                    ],
                    probe_capability_level_name_profiles=summary[
                        "probe_capability_level_name_profiles"
                    ],
                    pick_place_validation_status_counts=summary[
                        "pick_place_validation_status_counts"
                    ],
                    pick_place_validation_status_profiles=summary[
                        "pick_place_validation_status_profiles"
                    ],
                    unsupported_capability_counts=summary[
                        "unsupported_capability_counts"
                    ],
                    timed_out_profiles=summary["timed_out_profiles"],
                    batch_timeout_profiles=summary["batch_timeout_profiles"],
                    batch_aborted_profiles=summary["batch_aborted_profiles"],
                    blocked_profiles=summary["blocked_profiles"],
                    hard_failure_profiles=summary["hard_failure_profiles"],
                    lifecycle_recovery_profiles=summary[
                        "lifecycle_recovery_profiles"
                    ],
                    unsupported_capability_profiles=summary[
                        "unsupported_capability_profiles"
                    ],
                    ik_target_failure_profiles=summary[
                        "ik_target_failure_profiles"
                    ],
                    static_metadata_profiles=summary["static_metadata_profiles"],
                    known_dynamic_timeout_routed_profiles=summary[
                        "known_dynamic_timeout_routed_profiles"
                    ],
                    dynamic_joint_control_profiles=summary[
                        "dynamic_joint_control_profiles"
                    ],
                    results=tuple(results),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_PROBE_ARM_PROFILES_ERROR",
            )

    async def _probe_safe_nudge(
        self,
        meta: OperationMeta,
        prim_path: str,
        joint_config: JointConfig | None,
        joint_positions: JointPositions | None,
    ) -> RobotProbeCheck:
        if joint_config is None or joint_positions is None:
            return _probe_check(
                ok=False,
                skipped=True,
                error_code="ROBOT_PROBE_NUDGE_PREREQ_MISSING",
                message="Safe nudge skipped because joint config or positions are unavailable",
            )
        candidate = _choose_safe_nudge_joint(joint_config, joint_positions.positions)
        if candidate is None:
            return _probe_check(
                ok=True,
                skipped=True,
                error_code=None,
                message="No bounded non-gripper joint available for safe nudge",
                evidence={"dof_count": joint_config.dof_count},
            )

        idx, target = candidate
        original = tuple(joint_positions.positions)
        nudged = list(original)
        nudged[idx] = target
        set_result = await self.set_joint_positions(
            meta,
            JointPositionsSetRequest(prim_path=prim_path, positions=tuple(nudged)),
        )
        settle = await _probe_call(
            "safe_nudge_settle_step",
            self._client.simulation_step,
            {"frames": _PROBE_NUDGE_SETTLE_FRAMES},
        )
        readback = await self.get_joint_positions(meta, prim_path)
        restore = await self.set_joint_positions(
            meta,
            JointPositionsSetRequest(prim_path=prim_path, positions=original),
        )
        restore_settle = await _probe_call(
            "safe_nudge_restore_step",
            self._client.simulation_step,
            {"frames": _PROBE_NUDGE_SETTLE_FRAMES},
        )

        readback_value = None
        original_value = float(original[idx])
        target_value = float(target)
        command_delta = target_value - original_value
        movement_delta = None
        target_error = None
        progress_ratio = None
        moved_toward_target = False
        if readback.data is not None and len(readback.data.positions) > idx:
            readback_value = readback.data.positions[idx]
            readback_float = float(readback_value)
            movement_delta = readback_float - original_value
            target_error = readback_float - target_value
            if abs(command_delta) > _PROBE_NUDGE_TOLERANCE:
                progress_ratio = abs(movement_delta) / abs(command_delta)
                moved_toward_target = (
                    movement_delta * command_delta > 0
                    and progress_ratio >= _PROBE_NUDGE_MIN_PROGRESS_RATIO
                )
        readback_ok = (
            readback_value is not None
            and target_error is not None
            and abs(target_error) <= _PROBE_NUDGE_TOLERANCE
        )
        nudge_ok = readback_ok or moved_toward_target
        ok = (
            set_result.ok
            and settle.ok
            and readback.ok
            and restore.ok
            and restore_settle.ok
            and nudge_ok
        )
        if readback_ok:
            message = "Safe joint nudge reached commanded target"
        elif moved_toward_target:
            message = "Safe joint nudge moved toward commanded target"
        else:
            message = "Safe joint nudge did not move toward commanded target"
        return _probe_check(
            ok=ok,
            skipped=False,
            error_code=None if ok else "ROBOT_PROBE_SAFE_NUDGE_FAILED",
            message=message,
            evidence={
                "joint_index": idx,
                "joint_name": joint_config.dof_names[idx] if len(joint_config.dof_names) > idx else "",
                "original": original[idx],
                "target": target,
                "readback": readback_value,
                "command_delta": command_delta,
                "movement_delta": movement_delta,
                "target_error": target_error,
                "progress_ratio": progress_ratio,
                "min_progress_ratio": _PROBE_NUDGE_MIN_PROGRESS_RATIO,
                "readback_ok": readback_ok,
                "moved_toward_target": moved_toward_target,
                "restored": restore.ok,
                "settled": settle.ok,
                "restore_settled": restore_settle.ok,
                "settle_frames": _PROBE_NUDGE_SETTLE_FRAMES,
            },
        )

    async def _probe_gripper(
        self,
        meta: OperationMeta,
        prim_path: str,
    ) -> RobotProbeCheck:
        result = await self.gripper_control(
            meta,
            RobotGripperControlRequest(prim_path=prim_path, action="open"),
        )
        if result.ok and result.data is not None:
            return _probe_check(
                ok=True,
                skipped=False,
                error_code=None,
                message="Gripper open command succeeded",
                evidence={
                    "gripper_joint_names": list(result.data.gripper_joint_names),
                    "gripper_joint_indices": list(result.data.gripper_joint_indices),
                    "target_value": result.data.target_value,
                },
            )
        return _capability_probe_check(
            result,
            "Gripper command unsupported or failed",
            capability="gripper",
            unsupported_markers=_GRIPPER_UNSUPPORTED_MARKERS,
        )

    async def _probe_ik(
        self,
        meta: OperationMeta,
        prim_path: str,
        profile: object,
    ) -> RobotProbeCheck:
        robot_description = str(getattr(profile, "robot_description", "") or "")
        attempts: list[dict[str, Any]] = []
        last_result: ModuleResult[RobotSetEETargetResult] | None = None
        first_non_unsupported_result: ModuleResult[RobotSetEETargetResult] | None = None
        for label, target_pose, end_effector_frame in _profile_probe_ik_targets(profile):
            result = await self.set_ee_target(
                meta,
                RobotSetEETargetRequest(
                    prim_path=prim_path,
                    target_pose=target_pose,
                    robot_description=robot_description,
                    end_effector_frame=end_effector_frame,
                ),
            )
            attempts.append(
                _probe_ik_attempt_evidence(
                    label=label,
                    target_pose=target_pose,
                    requested_end_effector_frame=end_effector_frame,
                    result=result,
                ),
            )
            last_result = result
            if (
                first_non_unsupported_result is None
                and not _module_result_looks_unsupported(
                    result,
                    _IK_UNSUPPORTED_MARKERS,
                )
            ):
                first_non_unsupported_result = result
            if result.ok and result.data is not None:
                return _probe_check(
                    ok=True,
                    skipped=False,
                    error_code=None,
                    message="Lula IK target command succeeded",
                    evidence={
                        "robot_description": result.data.robot_description,
                        "end_effector_frame": result.data.end_effector_frame,
                        "solution_count": len(result.data.solution),
                        "target_pose": list(result.data.target_pose),
                        "selected_target_label": label,
                        "requested_end_effector_frame": end_effector_frame,
                        "attempted_targets": attempts,
                    },
                )

        assert last_result is not None
        classification_result = first_non_unsupported_result or last_result
        check = _capability_probe_check(
            classification_result,
            "Lula IK target command unsupported or failed",
            capability="ik",
            unsupported_markers=_IK_UNSUPPORTED_MARKERS,
        )
        return _with_probe_evidence(check, {"attempted_targets": attempts})

    async def _probe_ee_pose(
        self,
        meta: OperationMeta,
        prim_path: str,
        profile: object,
        *,
        ik_end_effector_frame: str | None = None,
    ) -> RobotProbeCheck:
        attempted_frames: list[str | None] = []
        failed_attempts: list[dict[str, Any]] = []
        last_result: ModuleResult[RobotEEPose] | None = None
        first_non_unsupported_result: ModuleResult[RobotEEPose] | None = None
        for frame in _profile_probe_ee_frames(
            profile,
            ik_end_effector_frame=ik_end_effector_frame,
        ):
            attempted_frames.append(frame)
            result = await self.get_ee_pose(meta, prim_path, frame)
            last_result = result
            if (
                first_non_unsupported_result is None
                and not _module_result_looks_unsupported(
                    result,
                    _EE_POSE_UNSUPPORTED_MARKERS,
                )
            ):
                first_non_unsupported_result = result
            if result.ok and result.data is not None:
                return _probe_check(
                    ok=True,
                    skipped=False,
                    error_code=None,
                    message="End-effector pose read succeeded",
                    evidence={
                        "end_effector_frame": result.data.end_effector_frame,
                        "requested_frame": frame,
                        "attempted_frames": list(attempted_frames),
                        "position": list(result.data.position),
                        "source": result.data.source,
                    },
                )
            failed_attempts.append(
                {
                    "requested_frame": frame,
                    "error_code": result.error_code,
                    "message": result.message,
                }
            )
        if last_result is None:
            return _probe_check(
                ok=True,
                skipped=True,
                error_code="ROBOT_PROBE_EE_POSE_NO_FRAME_CANDIDATES",
                message="End-effector pose read skipped because no frame candidates were available",
                evidence={"attempted_frames": []},
            )
        classification_result = first_non_unsupported_result or last_result
        check = _capability_probe_check(
            classification_result,
            "End-effector pose read unsupported or failed",
            capability="ee_pose",
            unsupported_markers=_EE_POSE_UNSUPPORTED_MARKERS,
        )
        return _with_probe_evidence(
            check,
            {
                "attempted_frames": list(attempted_frames),
                "attempts": failed_attempts,
            },
        )

    async def _cleanup_after_probe_timeout(
        self,
        prim_path: str,
        *,
        cleanup: bool,
        progress: dict[str, Any] | None = None,
    ) -> dict[str, RobotProbeCheck]:
        if _probe_timeout_cleanup_should_defer(progress):
            phase = str((progress or {}).get("last_phase", "unknown"))
            return _deferred_timeout_cleanup_checks(
                cleanup=cleanup,
                reason="unsafe_after_timed_out_dynamic_phase",
                last_phase=phase,
            )
        checks: dict[str, RobotProbeCheck] = {}
        checks["simulation_stop"] = await _probe_timeout_cleanup_call(
            "simulation_stop",
            self._client.simulation_stop,
        )
        if cleanup:
            checks["cleanup"] = await _probe_timeout_cleanup_call(
                "cleanup",
                self._client.stage_delete_prim,
                prim_path,
            )
        return checks

    async def _cleanup_after_probe_phase_failure(
        self,
        prim_path: str,
        *,
        cleanup: bool,
        timed_out: bool,
    ) -> dict[str, RobotProbeCheck]:
        if timed_out:
            return _deferred_timeout_cleanup_checks(
                cleanup=cleanup,
                reason="unsafe_after_phase_operation_timeout",
                last_phase=str((_PROBE_PROGRESS.get() or {}).get("last_phase", "unknown")),
            )

        checks: dict[str, RobotProbeCheck] = {}
        _set_probe_phase("simulation_stop")
        checks["simulation_stop"] = await _probe_call(
            "simulation_stop",
            self._client.simulation_stop,
        )
        _mark_probe_check_complete("simulation_stop")
        if cleanup:
            _set_probe_phase("cleanup")
            checks["cleanup"] = await _probe_call(
                "cleanup",
                self._client.stage_delete_prim,
                prim_path,
            )
            _mark_probe_check_complete("cleanup")
        return checks

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

        Only profiles with durable live proof are routed to an executable
        adapter. Candidate/IK/profile-only records return an explicit
        unsupported status rather than launching a risky unvalidated playback
        path.
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
            if request.create_demo_scene:
                robot_raw = await self._client.robot_load({
                    "usd_url": profile.asset_url,
                    "prim_path": request.robot_prim_path,
                    "position": None,
                    "rotation": None,
                })
                if not bool(robot_raw.get("ok", True)):
                    return error_result(
                        f"Failed to load robot profile asset for {profile.profile_name}",
                        started_ms=started,
                        error_code="ROBOT_PICK_PLACE_PROFILE_LOAD_ERROR",
                    )
                if not bool(robot_raw.get("has_articulation", True)):
                    return error_result(
                        f"Loaded robot profile asset has no articulation: {profile.profile_name}",
                        started_ms=started,
                        error_code="ROBOT_PICK_PLACE_PROFILE_LOAD_ERROR",
                    )
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
                profile=profile,
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
        timeout_s: float | None = 10.0,
    ) -> ModuleResult[RobotFrankaPickPlaceDemoStatus]:
        started = int(time.time() * 1000)
        try:
            status_call = self._client.robot_get_pick_place_demo_status()
            raw = (
                await asyncio.wait_for(status_call, timeout=timeout_s)
                if timeout_s is not None and timeout_s > 0
                else await status_call
            )
            status = _parse_pick_place_demo_status(raw)
            if status.status == "failed":
                return fail_result(
                    status.last_error or "Franka pick-place demo failed",
                    started_ms=started,
                    error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED",
                    data=status,
                )
            return ok_result(status, started_ms=started)
        except (asyncio.TimeoutError, TimeoutError):
            timeout_label = f"{timeout_s:g}s" if timeout_s is not None else "the caller limit"
            message = f"Franka pick-place demo status timed out after {timeout_label}"
            return error_result(
                message,
                started_ms=started,
                error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT",
                data=_pick_place_demo_status_error_data(
                    reason="pick_place_demo_status_timeout",
                    error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT",
                    message=message,
                    timeout_s=timeout_s,
                ),
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_ERROR",
                data=_pick_place_demo_status_error_data(
                    reason="pick_place_demo_status_error",
                    error_code="ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_ERROR",
                    message=str(exc),
                    timeout_s=timeout_s,
                ),
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


def _pick_place_demo_status_error_data(
    *,
    reason: str,
    error_code: str,
    message: str,
    timeout_s: float | None,
) -> RobotFrankaPickPlaceDemoStatus:
    status = "timeout" if reason.endswith("_timeout") else "error"
    diagnostics: dict[str, Any] = {
        "reason": reason,
        "upstream_error_code": error_code,
        "upstream_message": message,
        "timeout_s": timeout_s,
        "suggested_next": [
            "Check simulation_get_status before treating the proof loop as valid.",
            "Retry robot_get_pick_place_demo_status with a short timeout to "
            "confirm the status endpoint recovers.",
            "Capture WARN/ERROR logs if the status endpoint keeps timing out "
            "or raising errors.",
        ],
        "fallback_tool_order": list(_PICK_PLACE_STATUS_FALLBACK_TOOL_ORDER),
    }
    return RobotFrankaPickPlaceDemoStatus(
        ok=False,
        status=status,
        robot_prim_path="",
        object_prim_path="",
        target_position=(0.0, 0.0, 0.0),
        uses_kinematic_carry=False,
        steps=0,
        controller_event=0,
        done=False,
        placed=False,
        lifted=False,
        initial_object_position=(0.0, 0.0, 0.0),
        final_object_position=(0.0, 0.0, 0.0),
        final_distance=0.0,
        max_lift_delta=0.0,
        object_bbox_center=(0.0, 0.0, 0.0),
        object_bbox_size=(0.0, 0.0, 0.0),
        object_fit_ok=False,
        object_fit_reason=None,
        object_fit_axis=None,
        object_fit_limit_m=None,
        object_fit_measured_m=None,
        picking_position=(0.0, 0.0, 0.0),
        end_effector_initial_height=0.0,
        diagnostics=diagnostics,
        last_error=message,
    )


def _robot_load_error_diagnostics(
    *,
    request: RobotLoadRequest,
    upstream_error_code: str,
    upstream_message: str,
) -> dict[str, Any]:
    return {
        "reason": "robot_load_error",
        "upstream_error_code": upstream_error_code,
        "upstream_message": upstream_message,
        "usd_url": request.usd_url,
        "prim_path": request.prim_path,
        "position": list(request.position) if request.position else None,
        "rotation": list(request.rotation) if request.rotation else None,
        "suggested_next": [
            "Run simulation_get_status to confirm the app is responsive and no async job is blocking stage mutation.",
            "Run stage_capture_snapshot to check whether the target prim already exists or was partially created.",
            "Verify the robot USD URL with official_asset_search, official_asset_verify, or asset_search before retrying robot_load.",
        ],
        "fallback_tool_order": list(_ROBOT_LOAD_FALLBACK_TOOL_ORDER),
    }


def _robot_gripper_control_error_diagnostics(
    *,
    request: RobotGripperControlRequest,
    upstream_error_code: str,
    upstream_message: str,
) -> dict[str, Any]:
    return {
        "reason": "robot_gripper_control_error",
        "upstream_error_code": upstream_error_code,
        "upstream_message": upstream_message,
        "prim_path": request.prim_path,
        "action": request.action,
        "target": request.target,
        "suggested_next": [
            "Run simulation_get_status to confirm the timeline is playing before retrying gripper control.",
            "Run stage_capture_snapshot and robot_get_joint_config_static to confirm the robot prim and gripper joints.",
            "Capture WARN/ERROR logs if the robot prim and gripper joints look correct but control still fails.",
        ],
        "fallback_tool_order": list(_ROBOT_GRIPPER_CONTROL_FALLBACK_TOOL_ORDER),
    }


def _robot_set_ee_target_error_diagnostics(
    *,
    request: RobotSetEETargetRequest,
    upstream_error_code: str,
    upstream_message: str,
) -> dict[str, Any]:
    return {
        "reason": "robot_set_ee_target_error",
        "upstream_error_code": upstream_error_code,
        "upstream_message": upstream_message,
        "prim_path": request.prim_path,
        "target_pose": list(request.target_pose),
        "robot_description": request.robot_description,
        "end_effector_frame": request.end_effector_frame,
        "suggested_next": [
            "Run simulation_get_status and stage_capture_snapshot before retrying IK control.",
            "Run robot_get_joint_config_static to confirm the prim is an articulated arm profile with controllable joints.",
            "Retry robot_set_ee_target only after correcting robot_description, end_effector_frame, or target pose.",
        ],
        "fallback_tool_order": list(_ROBOT_SET_EE_TARGET_FALLBACK_TOOL_ORDER),
    }


def _default_probe_prim_path(profile_name: str) -> str:
    sanitized = "".join(ch if ch.isalnum() else "_" for ch in profile_name)
    return f"{_PROBE_ROOT}/{sanitized}"


def _select_probe_profiles(profile_names: tuple[str, ...] | None) -> list[RobotArmProfile]:
    if profile_names is None:
        return list(builtin_robot_arm_profiles())
    return [
        get_robot_arm_profile(profile_name) or _unknown_robot_arm_profile(profile_name)
        for profile_name in profile_names
    ]


def _unknown_robot_arm_profile(profile_name: str) -> RobotArmProfile:
    normalized = profile_name.strip() or "<empty>"
    return RobotArmProfile(
        profile_name=normalized,
        display_name=normalized,
        vendor="",
        family="unknown",
        asset_url="",
        robot_description=None,
        robot_description_aliases=(),
        gripper_kind="unknown",
        built_in_gripper=False,
        controller_strategy="unknown_profile",
        support_status="unknown",
        support_reason="No built-in Isaac Sim robot arm profile matched this name.",
        evidence=(),
    )


def _profile_is_unknown(profile: object) -> bool:
    return str(getattr(profile, "support_status", "")) == "unknown"


def _build_unknown_profile_result(profile: RobotArmProfile) -> RobotArmProfileProbeResult:
    checks = {
        "probe": _probe_check(
            ok=False,
            skipped=False,
            error_code="ROBOT_PROBE_UNKNOWN_PROFILE",
            message=f"Unknown robot arm profile: {profile.profile_name}",
            evidence={
                "profile_name": profile.profile_name,
                "hard_failure": True,
                "requested_profile_found": False,
            },
        )
    }
    return _build_probe_result(
        profile,
        _default_probe_prim_path(profile.profile_name),
        checks,
    )


def _probe_check(
    *,
    ok: bool,
    skipped: bool,
    error_code: str | None,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> RobotProbeCheck:
    return RobotProbeCheck(
        ok=ok,
        skipped=skipped,
        error_code=error_code,
        message=message,
        evidence=evidence or {},
    )


def _with_probe_evidence(
    check: RobotProbeCheck,
    evidence: dict[str, Any],
) -> RobotProbeCheck:
    merged = dict(check.evidence)
    merged.update(evidence)
    return RobotProbeCheck(
        ok=check.ok,
        skipped=check.skipped,
        error_code=check.error_code,
        message=check.message,
        evidence=merged,
    )


async def _probe_call(
    name: str,
    func: Callable[..., Awaitable[dict[str, Any]]],
    *args: Any,
    timeout_s: float | None = None,
    **kwargs: Any,
) -> RobotProbeCheck:
    check, _raw = await _probe_raw_call(name, func, *args, timeout_s=timeout_s, **kwargs)
    return check


async def _probe_raw_call(
    name: str,
    func: Callable[..., Awaitable[dict[str, Any]]],
    *args: Any,
    timeout_s: float | None = None,
    **kwargs: Any,
) -> tuple[RobotProbeCheck, dict[str, Any] | None]:
    try:
        call = func(*args, **kwargs)
        raw = (
            await asyncio.wait_for(call, timeout=timeout_s)
            if timeout_s is not None and timeout_s > 0
            else await call
        )
        ok = bool(raw.get("ok", True))
        return (
            _probe_check(
                ok=ok,
                skipped=False,
                error_code=None if ok else f"ROBOT_PROBE_{name.upper()}_FAILED",
                message=f"{name} succeeded" if ok else f"{name} returned ok=false",
                evidence=dict(raw),
            ),
            raw,
        )
    except asyncio.TimeoutError:
        timeout_label = timeout_s if timeout_s is not None else 0.0
        return (
            _probe_check(
                ok=False,
                skipped=False,
                error_code=f"ROBOT_PROBE_{name.upper()}_TIMEOUT",
                message=f"{name} timed out after {timeout_label:.1f}s",
                evidence={
                    "timeout_s": timeout_label,
                    "timeout_kind": "phase_operation",
                    "hard_failure": False,
                },
            ),
            None,
        )
    except Exception as exc:
        return (
            _probe_check(
                ok=False,
                skipped=False,
                error_code=f"ROBOT_PROBE_{name.upper()}_ERROR",
                message=str(exc),
                evidence={
                    "exception_type": type(exc).__name__,
                    "hard_failure": True,
                },
            ),
            None,
        )


def _module_result_probe_check(result: ModuleResult[Any], fallback_message: str) -> RobotProbeCheck:
    return _probe_check(
        ok=False,
        skipped=False,
        error_code=result.error_code,
        message=result.message or fallback_message,
    )


def _mark_probe_unsupported(
    check: RobotProbeCheck,
    *,
    capability: str,
) -> RobotProbeCheck:
    evidence = dict(check.evidence)
    evidence.update({"unsupported": True, "capability": capability})
    return RobotProbeCheck(
        ok=False,
        skipped=True,
        error_code=check.error_code,
        message=check.message,
        evidence=evidence,
    )


def _module_result_looks_unsupported(
    result: ModuleResult[Any],
    unsupported_markers: tuple[str, ...],
) -> bool:
    if result.error_code == "CAPABILITY_NOT_SUPPORTED":
        return True
    haystack = f"{result.error_code or ''} {result.message or ''}".lower()
    return any(marker in haystack for marker in unsupported_markers)


def _capability_probe_check(
    result: ModuleResult[Any],
    fallback_message: str,
    *,
    capability: str,
    unsupported_markers: tuple[str, ...],
) -> RobotProbeCheck:
    check = _module_result_probe_check(result, fallback_message)
    if _module_result_looks_unsupported(result, unsupported_markers):
        return _mark_probe_unsupported(check, capability=capability)
    return check


def _set_probe_phase(phase: str) -> None:
    progress = _PROBE_PROGRESS.get()
    if progress is None:
        return
    progress["last_phase"] = phase


def _mark_probe_check_complete(name: str) -> None:
    progress = _PROBE_PROGRESS.get()
    if progress is None:
        return
    completed = progress.setdefault("completed_checks", [])
    if isinstance(completed, list):
        completed.append(name)


def _probe_timeout_check(
    *,
    timeout_s: float,
    timeout_kind: str,
    progress: dict[str, Any] | None = None,
) -> RobotProbeCheck:
    evidence: dict[str, Any] = {
        "timeout_s": timeout_s,
        "timeout_kind": timeout_kind,
        "hard_failure": False,
    }
    if progress is not None:
        completed = progress.get("completed_checks", [])
        evidence.update(
            {
                "last_phase": str(progress.get("last_phase", "unknown")),
                "completed_checks": list(completed) if isinstance(completed, list) else [],
                "profile_name": str(progress.get("profile_name", "")),
                "prim_path": str(progress.get("prim_path", "")),
            }
        )
    return _probe_check(
        ok=False,
        skipped=False,
        error_code="ROBOT_PROBE_PROFILE_TIMEOUT",
        message=f"Profile probe timed out after {timeout_s:.1f}s",
        evidence=evidence,
    )


def _probe_phase_operation_timeout_s() -> float:
    timeout_s = _PROBE_PHASE_OPERATION_TIMEOUT_S
    progress = _PROBE_PROGRESS.get()
    if progress is None:
        return timeout_s
    deadline = progress.get("deadline_monotonic")
    if not isinstance(deadline, (int, float)):
        return timeout_s
    remaining_s = float(deadline) - time.monotonic() - _PROBE_BATCH_CLEANUP_RESERVE_S
    return min(timeout_s, max(0.001, remaining_s))


def _probe_check_timed_out(check: RobotProbeCheck) -> bool:
    return bool(check.error_code and check.error_code.endswith("_TIMEOUT"))


def _probe_check_requires_lifecycle_recovery(check: RobotProbeCheck) -> bool:
    cleanup_timeout_codes = {
        "ROBOT_PROBE_SIMULATION_STOP_TIMEOUT",
        "ROBOT_PROBE_CLEANUP_TIMEOUT",
    }
    return bool(
        check.evidence.get("requires_lifecycle_recovery")
        or (check.error_code and check.error_code.endswith("_DEFERRED"))
        or check.error_code in cleanup_timeout_codes
    )


def _first_blocking_phase_timeout(
    checks: dict[str, RobotProbeCheck],
) -> tuple[str, RobotProbeCheck] | None:
    for name, check in checks.items():
        if (
            _probe_check_timed_out(check)
            and check.evidence.get("timeout_kind") == "phase_operation"
        ):
            return name, check
    return None


def _first_blocking_phase_failure(
    checks: dict[str, RobotProbeCheck],
) -> tuple[str, RobotProbeCheck] | None:
    for name in ("simulation_play", "warmup_step"):
        check = checks.get(name)
        if (
            check is not None
            and not check.ok
            and not check.skipped
            and not _probe_check_timed_out(check)
        ):
            return name, check
    return None


def _profile_error_check(checks: dict[str, RobotProbeCheck]) -> RobotProbeCheck | None:
    check = checks.get("probe")
    if check is not None and not check.ok:
        return check
    return None


def _probe_result_is_blocked(checks: dict[str, RobotProbeCheck]) -> bool:
    return (
        "probe_batch_aborted" in checks
        or "probe_batch_timeout" in checks
        or "probe_timeout" in checks
        or _profile_error_check(checks) is not None
        or _first_blocking_phase_timeout(checks) is not None
        or _first_blocking_phase_failure(checks) is not None
    )


def _probe_timeout_cleanup_should_defer(progress: dict[str, Any] | None) -> bool:
    if progress is None:
        return False
    phase = str(progress.get("last_phase", ""))
    return phase in _PROBE_UNSAFE_TIMEOUT_CLEANUP_PHASES


def _deferred_timeout_cleanup_checks(
    *,
    cleanup: bool,
    reason: str,
    last_phase: str,
) -> dict[str, RobotProbeCheck]:
    checks = {
        "simulation_stop": _probe_deferred_cleanup_check(
            "simulation_stop",
            reason=reason,
            last_phase=last_phase,
        )
    }
    if cleanup:
        checks["cleanup"] = _probe_deferred_cleanup_check(
            "cleanup",
            reason=reason,
            last_phase=last_phase,
        )
    return checks


def _probe_deferred_cleanup_check(
    name: str,
    *,
    reason: str,
    last_phase: str,
) -> RobotProbeCheck:
    return _probe_check(
        ok=False,
        skipped=True,
        error_code=f"ROBOT_PROBE_{name.upper()}_DEFERRED",
        message=(
            f"{name} deferred after {last_phase} timeout; "
            "lifecycle recovery is required before more live probes"
        ),
        evidence={
            "deferred": True,
            "reason": reason,
            "last_phase": last_phase,
            "requires_lifecycle_recovery": True,
        },
    )


def _joint_config_from_raw(raw: dict[str, Any], prim_path: str) -> JointConfig:
    return JointConfig(
        prim_path=str(raw.get("prim_path", prim_path)),
        source=str(raw.get("source", "unknown")),
        dof_count=int(raw.get("dof_count", 0)),
        dof_names=tuple(str(n) for n in raw.get("dof_names", ())),
        joint_types=tuple(str(t) for t in raw.get("joint_types", ())),
        stiffness=_float_tuple(raw.get("stiffness", ())),
        damping=_float_tuple(raw.get("damping", ())),
        max_force=_float_tuple(raw.get("max_force", ())),
        lower_limits=_float_tuple(raw.get("lower_limits", ())),
        upper_limits=_float_tuple(raw.get("upper_limits", ())),
        max_velocity=_float_tuple(raw.get("max_velocity", ())),
        static_only=bool(raw.get("static_only", False)),
        order_reliable=bool(raw.get("order_reliable", True)),
    )


def _float_tuple(values: Any) -> tuple[float, ...]:
    out: list[float] = []
    for value in values or ():
        try:
            out.append(float(value) if value is not None else 0.0)
        except (TypeError, ValueError):
            out.append(0.0)
    return tuple(out)


def _static_joint_config_probe_check(
    result: ModuleResult[JointConfig],
) -> RobotProbeCheck:
    if result.ok and result.data is not None:
        config = result.data
        return _probe_check(
            ok=True,
            skipped=False,
            error_code=None,
            message="Static USD joint metadata read succeeded",
            evidence={
                "dof_count": config.dof_count,
                "source": config.source,
                "dof_names": list(config.dof_names),
                "static_only": config.static_only,
                "order_reliable": config.order_reliable,
                "dynamic_checks": False,
                "probe_scope": "load_articulation_static_metadata",
            },
        )
    return _probe_check(
        ok=True,
        skipped=True,
        error_code="ROBOT_PROBE_STATIC_JOINT_CONFIG_UNAVAILABLE",
        message="Static USD joint metadata unavailable; dynamic checks remain disabled",
        evidence={
            "dynamic_checks": False,
            "probe_scope": "load_articulation_only",
            "upstream_error_code": result.error_code,
            "upstream_message": result.message,
        },
    )


def _dynamic_checks_disabled_checks() -> dict[str, RobotProbeCheck]:
    return {
        name: _dynamic_checks_disabled_check(name)
        for name in (
            "simulation_play",
            "warmup_step",
            "joint_config",
            "joint_read",
            "safe_nudge",
            "gripper",
            "ik",
            "ee_pose",
        )
    }


def _dynamic_checks_disabled_check(name: str) -> RobotProbeCheck:
    return _probe_check(
        ok=False,
        skipped=True,
        error_code="ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED",
        message=f"{name} skipped because dynamic_checks=false",
        evidence={
            "dynamic_checks": False,
            "probe_scope": "load_articulation_static_metadata",
        },
    )


def _probe_batch_timeout_check(
    *,
    timeout_s: float | None,
    remaining_s: float,
) -> RobotProbeCheck:
    timeout_label = f"{timeout_s:.1f}s" if timeout_s is not None else "the batch"
    return _probe_check(
        ok=False,
        skipped=True,
        error_code="ROBOT_PROBE_BATCH_TIMEOUT",
        message=f"Batch timeout budget {timeout_label} reached before this profile was started",
        evidence={
            "timeout_s": timeout_s,
            "remaining_s": remaining_s,
            "timeout_kind": "batch_total",
        },
    )


async def _probe_timeout_cleanup_call(
    name: str,
    func: Callable[..., Awaitable[dict[str, Any]]],
    *args: Any,
    **kwargs: Any,
) -> RobotProbeCheck:
    try:
        return await asyncio.wait_for(
            _probe_call(name, func, *args, **kwargs),
            timeout=_PROBE_TIMEOUT_CLEANUP_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        return _probe_check(
            ok=False,
            skipped=False,
            error_code=f"ROBOT_PROBE_{name.upper()}_TIMEOUT",
            message=(
                f"{name} timed out after "
                f"{_PROBE_TIMEOUT_CLEANUP_TIMEOUT_S:.1f}s during timeout cleanup"
            ),
            evidence={"timeout_s": _PROBE_TIMEOUT_CLEANUP_TIMEOUT_S},
        )


def _profile_has_gripper_probe_candidate(profile: object) -> bool:
    gripper_kind = str(getattr(profile, "gripper_kind", "none")).lower()
    return bool(getattr(profile, "built_in_gripper", False)) or gripper_kind not in {
        "none",
        "unknown",
    }


def _probe_ik_end_effector_frame(check: RobotProbeCheck) -> str | None:
    if check.skipped or not check.ok:
        return None
    value = check.evidence.get("end_effector_frame")
    if not value:
        return None
    return str(value)


def _profile_probe_ik_targets(
    profile: object,
) -> tuple[tuple[str, tuple[float, float, float, float, float, float, float], str | None], ...]:
    targets: list[
        tuple[str, tuple[float, float, float, float, float, float, float], str | None]
    ] = [("default", _PROBE_IK_DEFAULT_TARGET_POSE, None)]

    family = str(getattr(profile, "family", "") or "").lower()
    profile_name = str(getattr(profile, "profile_name", "") or "").lower()
    if family == "kawasaki":
        targets.append((
            "kawasaki_relaxed_orientation",
            _PROBE_IK_KAWASAKI_RELAXED_TARGET_POSE,
            None,
        ))
        if profile_name == "kawasaki_rs080n":
            targets.append((
                "kawasaki_rs080n_relaxed_forward",
                _PROBE_IK_KAWASAKI_RS080N_RELAXED_FORWARD_TARGET_POSE,
                None,
            ))
    elif family in {"denso", "kuka"}:
        targets.append((
            "relaxed_orientation",
            _PROBE_IK_RELAXED_Z_TARGET_POSE,
            None,
        ))
        if family == "kuka":
            targets.append((
                "kuka_forward_high_identity",
                _PROBE_IK_KUKA_FORWARD_HIGH_IDENTITY_TARGET_POSE,
                None,
            ))

    return tuple(targets)


def _probe_ik_attempt_evidence(
    *,
    label: str,
    target_pose: tuple[float, float, float, float, float, float, float],
    requested_end_effector_frame: str | None,
    result: ModuleResult[RobotSetEETargetResult],
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "label": label,
        "target_pose": list(target_pose),
        "requested_end_effector_frame": requested_end_effector_frame,
        "ok": bool(result.ok),
        "error_code": result.error_code,
    }
    if result.message:
        evidence["message"] = result.message
    if result.data is not None:
        evidence["end_effector_frame"] = result.data.end_effector_frame
        evidence["solution_count"] = len(result.data.solution)
    return evidence


def _profile_probe_ee_frames(
    profile: object,
    *,
    ik_end_effector_frame: str | None = None,
) -> tuple[str | None, ...]:
    frames: list[str | None] = []

    def add(frame: str | None) -> None:
        if frame is not None:
            frame = str(frame).strip()
            if not frame:
                return
        if frame not in frames:
            frames.append(frame)

    for frame in getattr(profile, "end_effector_frame_candidates", ()) or ():
        add(frame)
    add(ik_end_effector_frame)

    robot_description = str(getattr(profile, "robot_description", "") or "").lower()
    if robot_description == "fr3":
        add("fr3_rightfinger")
    elif robot_description == "franka":
        add("panda_rightfinger")
    add(None)
    return tuple(frames)


def _choose_safe_nudge_joint(
    config: JointConfig,
    positions: tuple[float, ...],
) -> tuple[int, float] | None:
    for idx, current in enumerate(positions):
        name = config.dof_names[idx].lower() if len(config.dof_names) > idx else ""
        if not _is_safe_nudge_joint_name_candidate(name):
            continue
        lower = config.lower_limits[idx] if len(config.lower_limits) > idx else -3.14
        upper = config.upper_limits[idx] if len(config.upper_limits) > idx else 3.14
        if upper <= lower:
            continue
        delta = min(_PROBE_NUDGE_DELTA, (upper - lower) * 0.05)
        target = current + delta
        if target > upper:
            target = current - delta
        target = max(lower, min(upper, target))
        if abs(target - current) <= _PROBE_NUDGE_TOLERANCE:
            continue
        return idx, target
    return None


def _is_safe_nudge_joint_name_candidate(name: str) -> bool:
    if not name:
        return True
    normalized = name.lower()
    return not any(
        marker in normalized
        for marker in _PROBE_NUDGE_EXCLUDED_JOINT_NAME_MARKERS
    )


def _build_probe_result(
    profile: object,
    prim_path: str,
    checks: dict[str, RobotProbeCheck],
) -> RobotArmProfileProbeResult:
    recommended = _recommended_next_status(profile, checks)
    critical_names = ("load", "articulation", "joint_config", "joint_read", "safe_nudge")
    critical_checks = [checks.get(name, _missing_probe_check()) for name in critical_names]
    overall_ok = all(
        check.ok or check.skipped for check in critical_checks
    ) and not any(
        check.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
        for check in critical_checks
    )
    controllability, controllability_reason = _mcp_controllability(checks)
    capability_level, capability_name, capability_reason = _probe_capability_level(checks)
    (
        probe_proves_pick_place,
        pick_place_status,
        pick_place_reason,
    ) = _probe_pick_place_validation_boundary(profile)
    return RobotArmProfileProbeResult(
        profile_name=str(getattr(profile, "profile_name", "")),
        display_name=str(getattr(profile, "display_name", "")),
        family=str(getattr(profile, "family", "")),
        asset_url=str(getattr(profile, "asset_url", "")),
        prim_path=prim_path,
        support_status=str(getattr(profile, "support_status", "")),
        controller_strategy=str(getattr(profile, "controller_strategy", "")),
        recommended_next_status=recommended,
        overall_ok=overall_ok,
        mcp_controllability=controllability,
        mcp_controllability_reason=controllability_reason,
        probe_capability_level=capability_level,
        probe_capability_level_name=capability_name,
        probe_capability_level_reason=capability_reason,
        probe_proves_pick_place=probe_proves_pick_place,
        pick_place_validation_status=pick_place_status,
        pick_place_validation_reason=pick_place_reason,
        checks=checks,
    )


def _probe_pick_place_validation_boundary(
    profile: object,
) -> tuple[bool, str, str]:
    profile_name = str(getattr(profile, "profile_name", ""))
    support_status = str(getattr(profile, "support_status", ""))
    known_blocker_reason = _known_pick_place_blocker_reason(profile_name)
    if known_blocker_reason is not None:
        return (
            False,
            "known_pick_place_blocker",
            (
                "Known pick/place playback blocker: "
                f"{known_blocker_reason}. Probe evidence does not validate "
                "pick/place."
            ),
        )
    if support_status == "validated_pick_place":
        return (
            False,
            "catalog_validated_pick_place",
            (
                "Catalog support_status is validated_pick_place from durable "
                "live proof; this probe row is capability evidence and is not "
                "new pick/place validation."
            ),
        )
    return (
        False,
        "not_validated_by_probe",
        (
            "Probe evidence covers MCP controllability only. Durable live "
            "grasp, lift, and place proof is required before "
            "validated_pick_place."
        ),
    )


def _probe_batch_summary(
    results: list[RobotArmProfileProbeResult],
) -> dict[str, Any]:
    controllability_counts: dict[str, int] = {}
    controllability_profiles: dict[str, list[str]] = {}
    capability_name_counts: dict[str, int] = {}
    capability_name_profiles: dict[str, list[str]] = {}
    pick_place_validation_status_counts: dict[str, int] = {}
    pick_place_validation_status_profiles: dict[str, list[str]] = {}
    unsupported_capability_counts: dict[str, int] = {}
    timed_out_profiles: list[str] = []
    batch_timeout_profiles: list[str] = []
    batch_aborted_profiles: list[str] = []
    blocked_profiles: list[str] = []
    hard_failure_profiles: list[str] = []
    lifecycle_recovery_profiles: list[str] = []
    unsupported_capability_profiles: list[str] = []
    ik_target_failure_profiles: list[str] = []
    static_metadata_profiles: list[str] = []
    known_dynamic_timeout_routed_profiles: list[str] = []
    dynamic_joint_control_profiles: list[str] = []

    for result in results:
        controllability_counts[result.mcp_controllability] = (
            controllability_counts.get(result.mcp_controllability, 0) + 1
        )
        controllability_profiles.setdefault(result.mcp_controllability, []).append(
            result.profile_name
        )
        capability_name_counts[result.probe_capability_level_name] = (
            capability_name_counts.get(result.probe_capability_level_name, 0) + 1
        )
        capability_name_profiles.setdefault(
            result.probe_capability_level_name,
            [],
        ).append(result.profile_name)
        pick_place_validation_status_counts[result.pick_place_validation_status] = (
            pick_place_validation_status_counts.get(
                result.pick_place_validation_status, 0
            )
            + 1
        )
        pick_place_validation_status_profiles.setdefault(
            result.pick_place_validation_status,
            [],
        ).append(result.profile_name)
        if _probe_result_has_timeout_evidence(result):
            timed_out_profiles.append(result.profile_name)
        if _probe_result_has_batch_timeout_evidence(result):
            batch_timeout_profiles.append(result.profile_name)
        if _probe_result_has_batch_abort_evidence(result):
            batch_aborted_profiles.append(result.profile_name)
        if result.mcp_controllability.startswith("blocked_"):
            blocked_profiles.append(result.profile_name)
        if _probe_result_has_hard_failure_evidence(result):
            hard_failure_profiles.append(result.profile_name)
        if _probe_result_requires_lifecycle_recovery(result):
            lifecycle_recovery_profiles.append(result.profile_name)
        if _probe_result_has_unsupported_capability_evidence(result):
            unsupported_capability_profiles.append(result.profile_name)
            for capability in _probe_result_unsupported_capabilities(result):
                unsupported_capability_counts[capability] = (
                    unsupported_capability_counts.get(capability, 0) + 1
                )
        if _probe_result_has_ik_target_failure_evidence(result):
            ik_target_failure_profiles.append(result.profile_name)
        if result.mcp_controllability == "static_load_articulation_metadata":
            static_metadata_profiles.append(result.profile_name)
        if _probe_result_has_known_dynamic_timeout_policy(result):
            known_dynamic_timeout_routed_profiles.append(result.profile_name)
        if result.mcp_controllability == "dynamic_joint_control":
            dynamic_joint_control_profiles.append(result.profile_name)

    return {
        "mcp_controllability_counts": controllability_counts,
        "mcp_controllability_profiles": {
            status: tuple(profiles)
            for status, profiles in controllability_profiles.items()
        },
        "probe_capability_level_name_counts": capability_name_counts,
        "probe_capability_level_name_profiles": {
            status: tuple(profiles)
            for status, profiles in capability_name_profiles.items()
        },
        "pick_place_validation_status_counts": pick_place_validation_status_counts,
        "pick_place_validation_status_profiles": {
            status: tuple(profiles)
            for status, profiles in pick_place_validation_status_profiles.items()
        },
        "unsupported_capability_counts": unsupported_capability_counts,
        "timed_out_profiles": tuple(timed_out_profiles),
        "batch_timeout_profiles": tuple(batch_timeout_profiles),
        "batch_aborted_profiles": tuple(batch_aborted_profiles),
        "blocked_profiles": tuple(blocked_profiles),
        "hard_failure_profiles": tuple(hard_failure_profiles),
        "lifecycle_recovery_profiles": tuple(lifecycle_recovery_profiles),
        "unsupported_capability_profiles": tuple(unsupported_capability_profiles),
        "ik_target_failure_profiles": tuple(ik_target_failure_profiles),
        "static_metadata_profiles": tuple(static_metadata_profiles),
        "known_dynamic_timeout_routed_profiles": tuple(
            known_dynamic_timeout_routed_profiles
        ),
        "dynamic_joint_control_profiles": tuple(dynamic_joint_control_profiles),
    }


def _probe_result_has_timeout_evidence(result: RobotArmProfileProbeResult) -> bool:
    return any(
        _probe_check_timed_out(check)
        or check.evidence.get("timeout_kind") in {"batch_total", "batch_per_profile"}
        for check in result.checks.values()
    )


def _probe_result_has_batch_timeout_evidence(
    result: RobotArmProfileProbeResult,
) -> bool:
    return "probe_batch_timeout" in result.checks


def _probe_result_has_batch_abort_evidence(
    result: RobotArmProfileProbeResult,
) -> bool:
    return "probe_batch_aborted" in result.checks


def _probe_result_has_hard_failure_evidence(result: RobotArmProfileProbeResult) -> bool:
    return any(check.evidence.get("hard_failure") is True for check in result.checks.values())


def _probe_result_requires_lifecycle_recovery(
    result: RobotArmProfileProbeResult,
) -> bool:
    return any(
        _probe_check_requires_lifecycle_recovery(check)
        for check in result.checks.values()
    )


def _probe_result_has_unsupported_capability_evidence(
    result: RobotArmProfileProbeResult,
) -> bool:
    return any(
        check.skipped and check.evidence.get("unsupported") is True
        for check in result.checks.values()
    )


def _probe_result_unsupported_capabilities(
    result: RobotArmProfileProbeResult,
) -> tuple[str, ...]:
    capabilities: list[str] = []
    for check in result.checks.values():
        if not (check.skipped and check.evidence.get("unsupported") is True):
            continue
        capability = str(check.evidence.get("capability") or "unknown")
        if capability not in capabilities:
            capabilities.append(capability)
    return tuple(capabilities)


def _probe_result_has_ik_target_failure_evidence(
    result: RobotArmProfileProbeResult,
) -> bool:
    check = result.checks.get("ik")
    if check is None or check.skipped or check.ok:
        return False
    if check.evidence.get("unsupported") is True:
        return False
    attempts = check.evidence.get("attempted_targets")
    if not isinstance(attempts, list) or not attempts:
        return False
    return any(
        isinstance(attempt, dict)
        and attempt.get("ok") is False
        and not _ik_attempt_looks_unsupported(attempt)
        for attempt in attempts
    )


def _ik_attempt_looks_unsupported(attempt: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(attempt.get(key, "")).lower()
        for key in ("error_code", "message")
    )
    return any(marker in haystack for marker in _IK_UNSUPPORTED_MARKERS)


def _probe_result_has_known_dynamic_timeout_policy(
    result: RobotArmProfileProbeResult,
) -> bool:
    return any(
        check.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD"
        for check in result.checks.values()
    )


def _known_dynamic_timeout_reason(profile_name: str) -> str | None:
    return _KNOWN_DYNAMIC_TIMEOUT_PROFILE_REASONS.get(profile_name)


def _known_pick_place_blocker_reason(profile_name: str) -> str | None:
    return _KNOWN_PICK_PLACE_BLOCKER_PROFILE_REASONS.get(profile_name)


def _mark_static_only_known_timeout_result(
    result: RobotArmProfileProbeResult,
    profile: object,
    *,
    reason: str,
) -> RobotArmProfileProbeResult:
    checks = dict(result.checks)
    checks["dynamic_probe_policy"] = _probe_check(
        ok=False,
        skipped=True,
        error_code="ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD",
        message=(
            "Dynamic checks were routed to static-only mode because this "
            "profile has durable live dynamic-timeout evidence"
        ),
        evidence={
            "profile_name": result.profile_name,
            "dynamic_checks_requested": True,
            "dynamic_checks_effective": False,
            "reason": reason,
            "evidence_artifact": (
                "docs/artifacts/robot-pickplace/"
                "robot-arm-mcp-probe-matrix-2026-06-15.md"
            ),
            "probe_scope": "load_articulation_static_metadata",
        },
    )
    return _build_probe_result(profile, result.prim_path, checks)


def _mark_batch_timeout_result(
    result: RobotArmProfileProbeResult,
    profile: object,
) -> RobotArmProfileProbeResult:
    timeout_check = result.checks.get("probe_timeout")
    if timeout_check is None:
        return result
    checks = dict(result.checks)
    checks["probe_timeout"] = _with_probe_evidence(
        timeout_check,
        {
            "timeout_kind": "batch_per_profile",
            "batch_profile": result.profile_name,
        },
    )
    return _build_probe_result(profile, result.prim_path, checks)


def _batch_abort_reason_after_probe_result(result: RobotArmProfileProbeResult) -> str | None:
    cleanup_checks = (
        result.checks.get("simulation_stop"),
        result.checks.get("cleanup"),
    )
    for check in cleanup_checks:
        if check is None or check.ok:
            continue
        if _probe_check_timed_out(check):
            return "profile_timeout_cleanup_failed"
        if _probe_check_requires_lifecycle_recovery(check):
            return "profile_timeout_cleanup_deferred"
    return None


def _build_batch_timeout_results(
    profiles: list[object],
    *,
    timeout_s: float | None,
    remaining_s: float,
) -> list[RobotArmProfileProbeResult]:
    results: list[RobotArmProfileProbeResult] = []
    for profile in profiles:
        prim_path = _default_probe_prim_path(str(getattr(profile, "profile_name", "")))
        checks = {
            "probe_batch_timeout": _probe_batch_timeout_check(
                timeout_s=timeout_s,
                remaining_s=remaining_s,
            )
        }
        results.append(_build_probe_result(profile, prim_path, checks))
    return results


def _build_batch_aborted_results(
    profiles: list[object],
    *,
    blocked_by_profile: str,
    reason: str,
    checks: dict[str, RobotProbeCheck],
) -> list[RobotArmProfileProbeResult]:
    failed_checks = {
        name: {
            "error_code": check.error_code,
            "message": check.message,
        }
        for name, check in checks.items()
        if not check.ok and check.error_code is not None
    }
    results: list[RobotArmProfileProbeResult] = []
    for profile in profiles:
        prim_path = _default_probe_prim_path(str(getattr(profile, "profile_name", "")))
        result_checks = {
            "probe_batch_aborted": _probe_check(
                ok=False,
                skipped=True,
                error_code="ROBOT_PROBE_BATCH_ABORTED",
                message=(
                    "Batch probe aborted because a previous timed-out profile "
                    "left cleanup unhealthy"
                ),
                evidence={
                    "timeout_kind": "batch_unhealthy",
                    "blocked_by_profile": blocked_by_profile,
                    "reason": reason,
                    "failed_checks": failed_checks,
                },
            )
        }
        results.append(_build_probe_result(profile, prim_path, result_checks))
    return results


def _recommended_next_status(
    profile: object,
    checks: dict[str, RobotProbeCheck],
) -> str:
    current = str(getattr(profile, "support_status", "profile_only"))
    if current == "validated_pick_place":
        return "validated_pick_place"
    if _probe_result_is_blocked(checks):
        return current
    load_ok = checks.get("load", _missing_probe_check()).ok
    articulation_ok = checks.get("articulation", _missing_probe_check()).ok
    joint_ok = checks.get("joint_config", _missing_probe_check()).ok and checks.get(
        "joint_read", _missing_probe_check()
    ).ok
    critical_ok = load_ok and articulation_ok and joint_ok
    if not critical_ok:
        return "profile_only"
    gripper_check = checks.get("gripper", _missing_probe_check(skipped=True))
    gripper_ok = gripper_check.ok and not gripper_check.skipped
    ik_check = checks.get("ik", _missing_probe_check(skipped=True))
    ik_ok = ik_check.ok and not ik_check.skipped
    if current == "candidate_pick_place":
        return "candidate_pick_place"
    if gripper_ok and ik_ok:
        return "candidate_pick_place"
    if ik_ok:
        return "ik_only"
    return "profile_only"


def _mcp_controllability(checks: dict[str, RobotProbeCheck]) -> tuple[str, str]:
    if "probe_batch_aborted" in checks:
        return (
            "blocked_batch_abort",
            "Batch row was not dynamically probed because an earlier profile left cleanup unhealthy.",
        )
    if "probe_batch_timeout" in checks:
        return (
            "blocked_batch_timeout",
            "Batch timeout was reached before this profile could be dynamically probed.",
        )
    if "probe_timeout" in checks:
        return (
            "blocked_timeout",
            "Profile probe timed out before completing dynamic MCP controllability evidence.",
        )
    profile_error = _profile_error_check(checks)
    if profile_error is not None:
        return (
            "blocked_profile_error",
            (
                "Profile probe raised or returned an error before completing "
                f"dynamic MCP controllability evidence: {profile_error.message}"
            ),
        )
    blocking_timeout = _first_blocking_phase_timeout(checks)
    if blocking_timeout is not None:
        name, check = blocking_timeout
        return (
            "blocked_timeout",
            (
                f"Profile probe phase '{name}' timed out before completing "
                "dynamic MCP controllability evidence: "
                f"{check.message}"
            ),
        )
    blocking_failure = _first_blocking_phase_failure(checks)
    if blocking_failure is not None:
        name, check = blocking_failure
        return (
            "blocked_phase_error",
            (
                f"Profile probe phase '{name}' failed before completing "
                "dynamic MCP controllability evidence: "
                f"{check.message}"
            ),
        )

    load_ok = checks.get("load", _missing_probe_check()).ok
    articulation_ok = checks.get("articulation", _missing_probe_check()).ok
    if not load_ok or not articulation_ok:
        return (
            "blocked_load_or_articulation",
            "Profile did not prove load plus articulation readiness.",
        )

    joint_config = checks.get("joint_config", _missing_probe_check())
    joint_read = checks.get("joint_read", _missing_probe_check())
    if (
        joint_config.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
        or joint_read.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
    ):
        static_joint_config = checks.get("static_joint_config")
        if (
            static_joint_config is not None
            and static_joint_config.ok
            and not static_joint_config.skipped
        ):
            return (
                "static_load_articulation_metadata",
                "Load/articulation and static USD joint metadata were recorded, but dynamic joint read/write was intentionally skipped.",
            )
        return (
            "load_articulation_only",
            "Load/articulation were recorded, but dynamic joint read/write was intentionally skipped.",
        )
    if not joint_config.ok or not joint_read.ok:
        return (
            "load_articulation_only",
            "Profile loaded with articulation, but dynamic joint config/read did not both succeed.",
        )

    safe_nudge = checks.get("safe_nudge", _missing_probe_check())
    if safe_nudge.ok and not safe_nudge.skipped:
        return (
            "dynamic_joint_control",
            "Dynamic load, articulation, joint read, and safe joint nudge succeeded.",
        )
    if safe_nudge.skipped:
        return (
            "dynamic_joint_read_only",
            "Dynamic load, articulation, and joint read succeeded; safe joint nudge was skipped.",
        )
    return (
        "dynamic_joint_read_only",
        "Dynamic load, articulation, and joint read succeeded, but safe joint nudge did not prove write/control.",
    )


def _probe_capability_level(checks: dict[str, RobotProbeCheck]) -> tuple[int, str, str]:
    """Return the probe-evidence level from the handoff matrix, capped below Level 7."""
    if "probe_batch_aborted" in checks:
        return (
            0,
            "blocked_batch_abort",
            "Profile exists, but this batch row was not probed because an earlier profile left cleanup unhealthy.",
        )
    if "probe_batch_timeout" in checks:
        return (
            0,
            "blocked_batch_timeout",
            "Profile exists, but the batch timeout was reached before this profile could be probed.",
        )
    if "probe_timeout" in checks:
        return (
            0,
            "blocked_timeout",
            "Profile exists, but the probe timed out before completing stronger capability evidence.",
        )
    profile_error = _profile_error_check(checks)
    if profile_error is not None:
        return (
            0,
            "blocked_profile_error",
            (
                "Profile exists, but the probe raised or returned an error "
                f"before stronger capability evidence could be recorded: {profile_error.message}"
            ),
        )
    blocking_timeout = _first_blocking_phase_timeout(checks)
    if blocking_timeout is not None:
        name, check = blocking_timeout
        return (
            0,
            "blocked_timeout",
            (
                f"Profile exists, but probe phase '{name}' timed out before "
                f"stronger capability evidence could be recorded: {check.message}"
            ),
        )
    blocking_failure = _first_blocking_phase_failure(checks)
    if blocking_failure is not None:
        name, check = blocking_failure
        return (
            0,
            "blocked_phase_error",
            (
                f"Profile exists, but probe phase '{name}' failed before "
                f"stronger capability evidence could be recorded: {check.message}"
            ),
        )

    load = checks.get("load", _missing_probe_check())
    if not load.ok:
        return (
            0,
            "profile_exists_only",
            "Profile is known, but asset load was not proven.",
        )

    articulation = checks.get("articulation", _missing_probe_check())
    if not articulation.ok:
        return (
            1,
            "asset_load_only",
            "Asset load was proven, but PhysX articulation readiness was not proven.",
        )

    joint_config = checks.get("joint_config", _missing_probe_check())
    joint_read = checks.get("joint_read", _missing_probe_check())
    dynamic_disabled = (
        joint_config.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
        or joint_read.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
    )
    if dynamic_disabled:
        static_joint_config = checks.get("static_joint_config")
        if (
            static_joint_config is not None
            and static_joint_config.ok
            and not static_joint_config.skipped
        ):
            return (
                1,
                "load_articulation_static_metadata",
                "Load/articulation and static USD joint metadata were recorded; dynamic joint read/write was intentionally skipped.",
            )
        return (
            1,
            "load_articulation_only",
            "Load/articulation were recorded; dynamic joint read/write was intentionally skipped.",
        )
    if not joint_config.ok or not joint_read.ok:
        return (
            1,
            "load_articulation_only",
            "Load/articulation were proven, but dynamic joint config/read did not both succeed.",
        )

    safe_nudge = checks.get("safe_nudge", _missing_probe_check())
    if not safe_nudge.ok or safe_nudge.skipped:
        return (
            2,
            "dynamic_joint_read",
            "Dynamic articulation joint config/read succeeded, but safe joint write/control was not proven.",
        )

    gripper = checks.get("gripper", _missing_probe_check(skipped=True))
    ik = checks.get("ik", _missing_probe_check(skipped=True))
    ee_pose = checks.get("ee_pose", _missing_probe_check(skipped=True))
    gripper_ok = gripper.ok and not gripper.skipped
    ik_ok = ik.ok and not ik.skipped
    ee_pose_ok = ee_pose.ok and not ee_pose.skipped
    if ik_ok or ee_pose_ok:
        return (
            5,
            "ik_or_ee_telemetry",
            "Dynamic joint control plus IK and/or EE-pose telemetry succeeded; this is still not pick/place validation.",
        )
    if gripper_ok:
        return (
            4,
            "gripper_control",
            "Dynamic joint control plus gripper control succeeded; this is still not pick/place validation.",
        )
    return (
        3,
        "dynamic_joint_control",
        "Dynamic joint read/write via safe nudge succeeded; higher manipulation surfaces were unsupported or not proven.",
    )


def _missing_probe_check(skipped: bool = False) -> RobotProbeCheck:
    return _probe_check(
        ok=False,
        skipped=skipped,
        error_code="ROBOT_PROBE_CHECK_MISSING",
        message="Probe check was not run",
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
    if getattr(profile, "support_status", None) != "validated_pick_place":
        return False
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
    profile: object | None = None,
) -> RobotFrankaPickPlaceDemoStatus:
    resolved_profile_name = profile_name or request.profile_name
    playback_route = (
        "unknown_profile"
        if profile is None and support_status == "unsupported"
        else "blocked_unvalidated_profile"
    )
    known_blocker_reason = _known_pick_place_blocker_reason(resolved_profile_name)
    diagnostics: dict[str, Any] = {
        "unsupported": True,
        "reason": "pick_place_profile_unsupported",
        "requested_profile": request.profile_name,
        "resolved_profile": resolved_profile_name,
        "support_status": support_status,
        "support_reason": support_reason,
        "controller_strategy": controller_strategy,
        "playback_route": playback_route,
        "adapter_ready": False,
        "known_pick_place_blocker": known_blocker_reason is not None,
        "known_pick_place_blocker_reason": known_blocker_reason,
        "target_status": "validated_pick_place",
        "required_support_status": "validated_pick_place",
        "validated_pick_place_requires": "durable_live_pick_place_proof",
        "probe_success_is_pick_place_validation": False,
        "mcp_controllability_is_pick_place_validation": False,
        "mcp_controllability_required": (
            "profile-specific robot_probe_arm_profile or robot_probe_arm_profiles evidence"
        ),
        "suggested_next": [
            "Call robot_list_arm_profiles and choose a "
            "support_status=validated_pick_place profile before installing playback.",
            "Use robot_probe_arm_profile only for controllability evidence; "
            "probe success is not pick/place validation.",
            "Keep this unsupported result as blocker evidence unless durable "
            "live pick/place proof is added.",
        ],
        "fallback_tool_order": list(_PICK_PLACE_UNSUPPORTED_FALLBACK_TOOL_ORDER),
    }
    if profile is not None:
        diagnostics.update({
            "profile_family": getattr(profile, "family", None),
            "robot_description": getattr(profile, "robot_description", None),
            "gripper_kind": getattr(profile, "gripper_kind", None),
            "built_in_gripper": getattr(profile, "built_in_gripper", None),
        })
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
        object_fit_reason="Profile has no active validated pick/place adapter.",
        object_fit_axis=None,
        object_fit_limit_m=None,
        object_fit_measured_m=None,
        picking_position=request.picking_position or request.object_initial_position,
        end_effector_initial_height=request.end_effector_initial_height or 0.0,
        diagnostics=diagnostics,
        profile_name=resolved_profile_name,
        support_status=support_status,
        support_reason=support_reason,
        controller_strategy=controller_strategy,
        last_error=None,
    )
