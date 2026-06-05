"""Simulation module — play/pause/stop/status via Isaac Sim REST API."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.simulation import (
    ObservedEETarget,
    ObservedJointState,
    ObservedPrimState,
    SimulationSetTimeRequest,
    SimulationSetTimeResult,
    SimulationStatus,
    SimulationStepObserveRequest,
    SimulationStepObserveResult,
    SimulationStepRequest,
    SimulationStepResult,
    SimulationWaitUntilRequest,
    SimulationWaitUntilResult,
    StageWriteResult,
)
from omniverse_kit_mcp.types.stage import StageFileResult

logger = logging.getLogger(__name__)


class SimulationModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def play(self, meta: OperationMeta) -> ModuleResult[SimulationStatus]:
        return await self._control("play", meta)

    async def pause(self, meta: OperationMeta) -> ModuleResult[SimulationStatus]:
        return await self._control("pause", meta)

    async def stop(self, meta: OperationMeta) -> ModuleResult[SimulationStatus]:
        return await self._control("stop", meta)

    async def get_status(self, meta: OperationMeta) -> ModuleResult[SimulationStatus]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.simulation_status()
            return ok_result(_parse_status(raw), started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="SIMULATION_STATUS_ERROR"
            )

    # --- Phase G ---

    async def step(
        self,
        meta: OperationMeta,
        request: SimulationStepRequest,
    ) -> ModuleResult[SimulationStepResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.simulation_step({
                "frames": request.frames,
            })
            return ok_result(
                SimulationStepResult(
                    status=_parse_status(raw),
                    frames=int(raw.get("frames", request.frames)),
                    start_time=float(raw.get("start_time", 0.0)),
                    advance_mode=str(raw.get("advance_mode", "")),
                    was_playing=bool(raw.get("was_playing", False)),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="SIMULATION_STEP_ERROR",
            )

    async def step_observe(
        self,
        meta: OperationMeta,
        request: SimulationStepObserveRequest,
    ) -> ModuleResult[SimulationStepObserveResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.simulation_step_observe({
                "frames": request.frames,
                "observe_prims": list(request.observe_prims),
                "observe_joints": list(request.observe_joints),
                "observe_ee": [
                    {
                        "prim_path": spec.prim_path,
                        "end_effector_frame": spec.end_effector_frame,
                    }
                    for spec in request.observe_ee
                ],
            })
            return ok_result(
                SimulationStepObserveResult(
                    status=_parse_status(raw),
                    frames=int(raw.get("frames", request.frames)),
                    start_time=float(raw.get("start_time", 0.0)),
                    advance_mode=str(raw.get("advance_mode", "")),
                    was_playing=bool(raw.get("was_playing", False)),
                    prim_states=tuple(
                        _parse_prim_state(item) for item in raw.get("prim_states") or []
                    ),
                    joint_states=tuple(
                        _parse_joint_state(item)
                        for item in raw.get("joint_states") or []
                    ),
                    ee_states=tuple(
                        _parse_ee_state(item) for item in raw.get("ee_states") or []
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started,
                error_code="SIMULATION_STEP_OBSERVE_ERROR",
            )

    async def wait_until(
        self,
        meta: OperationMeta,
        request: SimulationWaitUntilRequest,
    ) -> ModuleResult[SimulationWaitUntilResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.simulation_wait_until({
                "until_time": request.until_time,
                "timeout_s": request.timeout_s,
            })
            return ok_result(
                SimulationWaitUntilResult(
                    status=_parse_status(raw),
                    until_time=float(raw.get("until_time", request.until_time)),
                    reached=bool(raw.get("reached", False)),
                    timed_out=bool(raw.get("timed_out", False)),
                    elapsed_s=float(raw.get("elapsed_s", 0.0)),
                    frames_waited=int(raw.get("frames_waited", 0)),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started,
                error_code="SIMULATION_WAIT_UNTIL_ERROR",
            )

    async def set_time(
        self,
        meta: OperationMeta,
        request: SimulationSetTimeRequest,
    ) -> ModuleResult[SimulationSetTimeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.simulation_set_time({
                "time_seconds": request.time_seconds,
            })
            return ok_result(
                SimulationSetTimeResult(
                    status=_parse_status(raw),
                    requested_time=float(raw.get("requested_time", request.time_seconds)),
                    previous_time=float(raw.get("previous_time", 0.0)),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="SIMULATION_SET_TIME_ERROR",
            )

    # --- Stage WRITE operations ---

    async def stage_load_usd(
        self,
        meta: OperationMeta,
        request: dict,
    ) -> ModuleResult[StageWriteResult]:
        started = int(time.time() * 1000)
        try:
            await self._ensure_timeline_stopped(meta)
            raw = await self._client.stage_load_usd(request)
            result = StageWriteResult(
                ok=raw.get("ok", True),
                prim_path=raw.get("prim_path", request.get("prim_path", "")),
                detail=f"type={raw.get('type_name', '?')}, children={raw.get('has_children', '?')}",
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="STAGE_LOAD_ERROR"
            )

    async def stage_set_property(
        self,
        meta: OperationMeta,
        request: dict,
    ) -> ModuleResult[StageWriteResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_set_property(request)
            result = StageWriteResult(
                ok=raw.get("ok", True),
                prim_path=raw.get("prim_path", request.get("prim_path", "")),
                detail=f"{raw.get('property_name', '?')}={raw.get('value', '?')}",
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="STAGE_PROPERTY_ERROR"
            )

    async def stage_set_semantic_label(
        self,
        meta: OperationMeta,
        request: dict,
    ) -> ModuleResult[StageWriteResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_set_semantic_label(request)
            result = StageWriteResult(
                ok=raw.get("ok", True),
                prim_path=raw.get("prim_path", request.get("prim_path", "")),
                detail=f"{raw.get('label_type', 'class')}={raw.get('label_class', '?')}",
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started,
                error_code="STAGE_SEMANTIC_LABEL_ERROR",
            )

    async def stage_create_prim(
        self,
        meta: OperationMeta,
        request: dict,
    ) -> ModuleResult[StageWriteResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_create_prim(request)
            result = StageWriteResult(
                ok=raw.get("ok", True),
                prim_path=raw.get("prim_path", request.get("prim_path", "")),
                detail=f"type={raw.get('prim_type', '?')}",
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="PRIM_CREATE_ERROR"
            )

    async def stage_delete_prim(
        self,
        meta: OperationMeta,
        prim_path: str,
    ) -> ModuleResult[StageWriteResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_delete_prim(prim_path)
            result = StageWriteResult(
                ok=raw.get("ok", True),
                prim_path=raw.get("prim_path", prim_path),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="PRIM_DELETE_ERROR"
            )

    # --- File operations (Phase B+) ---

    async def stage_save(
        self,
        meta: OperationMeta,
        path: str | None = None,
    ) -> ModuleResult[StageFileResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_save(path)
            return ok_result(
                StageFileResult(
                    ok=bool(raw.get("ok", False)),
                    path=raw.get("path"),
                    mode=raw.get("mode"),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="STAGE_SAVE_ERROR"
            )

    async def stage_open(
        self,
        meta: OperationMeta,
        url: str,
    ) -> ModuleResult[StageFileResult]:
        started = int(time.time() * 1000)
        try:
            await self._ensure_timeline_stopped(meta)
            raw = await self._client.stage_open(url)
            return ok_result(
                StageFileResult(
                    ok=bool(raw.get("ok", False)),
                    path=raw.get("root_layer") or raw.get("url"),
                    mode="open",
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="STAGE_OPEN_ERROR"
            )

    async def stage_new(
        self, meta: OperationMeta,
    ) -> ModuleResult[StageFileResult]:
        started = int(time.time() * 1000)
        try:
            await self._ensure_timeline_stopped(meta)
            raw = await self._client.stage_new()
            return ok_result(
                StageFileResult(
                    ok=bool(raw.get("ok", False)),
                    path=raw.get("root_layer"),
                    mode="new",
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="STAGE_NEW_ERROR"
            )

    # --- Internal ---

    async def _ensure_timeline_stopped(self, meta: OperationMeta) -> None:
        """Stop the timeline before a stage swap if it is playing.

        Replacing the stage (stage_new / stage_open / stage_load_usd) while the
        timeline is playing causes a 92s Kit event-loop hang (farm session).
        Stop is idempotent, so this is safe — but we gate on is_playing to avoid
        resetting time when already stopped/paused.
        """
        status = await self.get_status(meta)
        if status.ok and status.data is not None and status.data.is_playing:
            await self.stop(meta)

    async def _control(
        self, action: str, meta: OperationMeta
    ) -> ModuleResult[SimulationStatus]:
        started = int(time.time() * 1000)
        try:
            method = getattr(self._client, f"simulation_{action}")
            raw = await method()
            return ok_result(_parse_status(raw), started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="SIMULATION_CONTROL_ERROR"
            )


def _parse_status(raw: dict) -> SimulationStatus:
    return SimulationStatus(
        is_playing=raw.get("is_playing", False),
        is_stopped=raw.get("is_stopped", True),
        current_time=raw.get("current_time", 0.0),
        start_time=raw.get("start_time", 0.0),
        end_time=raw.get("end_time", 0.0),
        time_codes_per_second=raw.get("time_codes_per_second", 24.0),
    )


def _vec3(raw: object) -> tuple[float, float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        return None
    return (float(raw[0]), float(raw[1]), float(raw[2]))


def _quat(raw: object) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _parse_prim_state(raw: dict) -> ObservedPrimState:
    return ObservedPrimState(
        prim_path=str(raw.get("prim_path", "")),
        position=_vec3(raw.get("position")),
        orientation=_quat(raw.get("orientation")),
        linear_velocity=_vec3(raw.get("linear_velocity")),
        angular_velocity=_vec3(raw.get("angular_velocity")),
        has_rigid_body=bool(raw.get("has_rigid_body", False)),
        source=str(raw.get("source", "")),
        error=raw.get("error"),
    )


def _parse_joint_state(raw: dict) -> ObservedJointState:
    return ObservedJointState(
        prim_path=str(raw.get("prim_path", "")),
        positions=tuple(float(v) for v in raw.get("positions") or ()),
        dof_names=tuple(str(v) for v in raw.get("dof_names") or ()),
        source=str(raw.get("source", "")),
        error=raw.get("error"),
    )


def _parse_ee_state(raw: dict) -> ObservedEETarget:
    return ObservedEETarget(
        prim_path=str(raw.get("prim_path", "")),
        end_effector_frame=str(raw.get("end_effector_frame", "")),
        position=_vec3(raw.get("position")),
        orientation=_quat(raw.get("orientation")),
        source=str(raw.get("source", "")),
        error=raw.get("error"),
    )
