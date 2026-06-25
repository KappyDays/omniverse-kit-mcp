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

_SIMULATION_STATUS_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "kit_app_start",
    "simulation_get_status",
    "extension_capture_logs",
)
_SIMULATION_CONTROL_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "{tool_name}",
    "extension_capture_logs",
)
_SIMULATION_STEP_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "simulation_step",
    "extension_capture_logs",
)
_SIMULATION_STEP_OBSERVE_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "simulation_step_observe",
    "extension_capture_logs",
)
_SIMULATION_WAIT_UNTIL_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "simulation_wait_until",
    "extension_capture_logs",
)
_SIMULATION_SET_TIME_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "simulation_set_time",
    "extension_capture_logs",
)
_STAGE_LOAD_USD_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "content_browse",
    "official_asset_search",
    "asset_search",
    "stage_load_usd",
    "extension_capture_logs",
)
_STAGE_WRITE_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "stage_capture_snapshot",
    "simulation_get_status",
    "{tool_name}",
    "extension_capture_logs",
)
_STAGE_FILE_FALLBACK_TOOL_ORDER = (
    "mcp_runtime_info",
    "simulation_get_status",
    "{tool_name}",
    "extension_capture_logs",
)


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
            error_code = "SIMULATION_STATUS_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                exc=exc,
                data=_simulation_status_error_data(
                    error_code=error_code,
                    message=str(exc),
                ),
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
                    diagnostics=(
                        dict(raw["diagnostics"])
                        if isinstance(raw.get("diagnostics"), dict)
                        else {}
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            error_code = "SIMULATION_STEP_ERROR"
            diagnostics = _simulation_step_error_diagnostics(
                request=request,
                error_code=error_code,
                message=str(exc),
            )
            data = SimulationStepResult(
                status=_simulation_error_status(diagnostics=diagnostics),
                frames=request.frames,
                start_time=0.0,
                advance_mode="",
                was_playing=False,
                diagnostics=diagnostics,
            )
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                exc=exc,
                data=data,
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
                    diagnostics=(
                        dict(raw["diagnostics"])
                        if isinstance(raw.get("diagnostics"), dict)
                        else {}
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            error_code = "SIMULATION_STEP_OBSERVE_ERROR"
            diagnostics = _simulation_step_observe_error_diagnostics(
                request=request,
                error_code=error_code,
                message=str(exc),
            )
            data = SimulationStepObserveResult(
                status=_simulation_error_status(diagnostics=diagnostics),
                frames=request.frames,
                start_time=0.0,
                advance_mode="",
                was_playing=False,
                diagnostics=diagnostics,
            )
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                exc=exc,
                data=data,
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
                    diagnostics=(
                        dict(raw["diagnostics"])
                        if isinstance(raw.get("diagnostics"), dict)
                        else {}
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            error_code = "SIMULATION_WAIT_UNTIL_ERROR"
            diagnostics = _simulation_wait_until_error_diagnostics(
                request=request,
                error_code=error_code,
                message=str(exc),
            )
            data = SimulationWaitUntilResult(
                status=_simulation_error_status(diagnostics=diagnostics),
                until_time=request.until_time,
                reached=False,
                timed_out=False,
                elapsed_s=0.0,
                frames_waited=0,
                diagnostics=diagnostics,
            )
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                exc=exc,
                data=data,
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
                    diagnostics=(
                        dict(raw["diagnostics"])
                        if isinstance(raw.get("diagnostics"), dict)
                        else {}
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            error_code = "SIMULATION_SET_TIME_ERROR"
            diagnostics = _simulation_set_time_error_diagnostics(
                request=request,
                error_code=error_code,
                message=str(exc),
            )
            data = SimulationSetTimeResult(
                status=_simulation_error_status(diagnostics=diagnostics),
                requested_time=request.time_seconds,
                previous_time=0.0,
                diagnostics=diagnostics,
            )
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                exc=exc,
                data=data,
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
            error_code = "STAGE_LOAD_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                data=_stage_write_error_data(
                    request=request,
                    tool_name="stage_load_usd",
                    reason="stage_load_usd_error",
                    error_code=error_code,
                    message=str(exc),
                    fallback_tool_order=_STAGE_LOAD_USD_FALLBACK_TOOL_ORDER,
                ),
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
            error_code = "STAGE_PROPERTY_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                data=_stage_write_error_data(
                    request=request,
                    tool_name="stage_set_property",
                    reason="stage_set_property_error",
                    error_code=error_code,
                    message=str(exc),
                    fallback_tool_order=_stage_tool_fallback_order(
                        "stage_set_property"
                    ),
                ),
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
            error_code = "STAGE_SEMANTIC_LABEL_ERROR"
            return error_result(
                str(exc), started_ms=started,
                error_code=error_code,
                data=_stage_write_error_data(
                    request=request,
                    tool_name="stage_set_semantic_label",
                    reason="stage_set_semantic_label_error",
                    error_code=error_code,
                    message=str(exc),
                    fallback_tool_order=_stage_tool_fallback_order(
                        "stage_set_semantic_label"
                    ),
                ),
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
            error_code = "PRIM_CREATE_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                data=_stage_write_error_data(
                    request=request,
                    tool_name="stage_create_prim",
                    reason="stage_create_prim_error",
                    error_code=error_code,
                    message=str(exc),
                    fallback_tool_order=_stage_tool_fallback_order(
                        "stage_create_prim"
                    ),
                ),
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
            error_code = "PRIM_DELETE_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                data=_stage_write_error_data(
                    request={"prim_path": prim_path},
                    tool_name="stage_delete_prim",
                    reason="stage_delete_prim_error",
                    error_code=error_code,
                    message=str(exc),
                    fallback_tool_order=_stage_tool_fallback_order(
                        "stage_delete_prim"
                    ),
                ),
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
            error_code = "STAGE_SAVE_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                data=_stage_file_error_data(
                    path=path,
                    mode="save",
                    tool_name="stage_save",
                    reason="stage_save_error",
                    error_code=error_code,
                    message=str(exc),
                ),
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
            error_code = "STAGE_OPEN_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                data=_stage_file_error_data(
                    path=url,
                    mode="open",
                    tool_name="stage_open",
                    reason="stage_open_error",
                    error_code=error_code,
                    message=str(exc),
                ),
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
            error_code = "STAGE_NEW_ERROR"
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                data=_stage_file_error_data(
                    path=None,
                    mode="new",
                    tool_name="stage_new",
                    reason="stage_new_error",
                    error_code=error_code,
                    message=str(exc),
                ),
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
            error_code = "SIMULATION_CONTROL_ERROR"
            diagnostics = _simulation_control_error_diagnostics(
                action=action,
                error_code=error_code,
                message=str(exc),
            )
            return error_result(
                str(exc),
                started_ms=started,
                error_code=error_code,
                exc=exc,
                data=_simulation_error_status(diagnostics=diagnostics),
            )


def _parse_status(raw: dict) -> SimulationStatus:
    return SimulationStatus(
        is_playing=raw.get("is_playing", False),
        is_stopped=raw.get("is_stopped", True),
        current_time=raw.get("current_time", 0.0),
        start_time=raw.get("start_time", 0.0),
        end_time=raw.get("end_time", 0.0),
        time_codes_per_second=raw.get("time_codes_per_second", 24.0),
        timeline_settled=raw.get("timeline_settled"),
        timeline_settle_updates=raw.get("timeline_settle_updates"),
        diagnostics=(
            dict(raw["diagnostics"])
            if isinstance(raw.get("diagnostics"), dict)
            else {}
        ),
    )


def _simulation_status_error_data(
    *, error_code: str, message: str
) -> SimulationStatus:
    return SimulationStatus(
        is_playing=False,
        is_stopped=False,
        current_time=0.0,
        start_time=0.0,
        end_time=0.0,
        time_codes_per_second=0.0,
        diagnostics={
            "reason": "simulation_status_error",
            "upstream_error_code": error_code,
            "upstream_message": message,
            "suggested_next": [
                "Call mcp_runtime_info to confirm the MCP worker is attached to the intended app.",
                "Use kit_app_start only if no compatible Kit/Isaac worker is running.",
                "Capture WARN/ERROR logs if simulation_get_status keeps failing.",
            ],
            "fallback_tool_order": list(_SIMULATION_STATUS_FALLBACK_TOOL_ORDER),
        },
    )


def _simulation_control_error_diagnostics(
    *,
    action: str,
    error_code: str,
    message: str,
) -> dict[str, object]:
    tool_name = f"simulation_{action}"
    return {
        "reason": "simulation_control_error",
        "upstream_error_code": error_code,
        "upstream_message": message,
        "action": action,
        "tool_name": tool_name,
        "suggested_next": [
            "Run simulation_get_status to confirm the timeline endpoint is responsive.",
            f"Retry {tool_name} once after checking status if the app is healthy.",
            "Capture WARN/ERROR logs if timeline control keeps failing.",
        ],
        "fallback_tool_order": [
            tool_name if item == "{tool_name}" else item
            for item in _SIMULATION_CONTROL_FALLBACK_TOOL_ORDER
        ],
    }


def _simulation_error_status(
    *, diagnostics: dict[str, object],
) -> SimulationStatus:
    return SimulationStatus(
        is_playing=False,
        is_stopped=False,
        current_time=0.0,
        start_time=0.0,
        end_time=0.0,
        time_codes_per_second=0.0,
        diagnostics=dict(diagnostics),
    )


def _simulation_step_error_diagnostics(
    *,
    request: SimulationStepRequest,
    error_code: str,
    message: str,
) -> dict[str, object]:
    return {
        "reason": "simulation_step_error",
        "upstream_error_code": error_code,
        "upstream_message": message,
        "frames": request.frames,
        "suggested_next": [
            "Run simulation_get_status to confirm the timeline and REST endpoint are responsive.",
            "Retry simulation_step with fewer frames if the status endpoint is healthy.",
            "Capture WARN/ERROR logs if simulation_step keeps failing or timing out.",
        ],
        "fallback_tool_order": list(_SIMULATION_STEP_FALLBACK_TOOL_ORDER),
    }


def _simulation_step_observe_error_diagnostics(
    *,
    request: SimulationStepObserveRequest,
    error_code: str,
    message: str,
) -> dict[str, object]:
    return {
        "reason": "simulation_step_observe_error",
        "upstream_error_code": error_code,
        "upstream_message": message,
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
        "suggested_next": [
            "Run simulation_get_status to confirm the timeline and REST endpoint are responsive.",
            "Retry simulation_step_observe with fewer frames or fewer observe targets.",
            "Capture WARN/ERROR logs if synchronized observation keeps failing.",
        ],
        "fallback_tool_order": list(_SIMULATION_STEP_OBSERVE_FALLBACK_TOOL_ORDER),
    }


def _simulation_wait_until_error_diagnostics(
    *,
    request: SimulationWaitUntilRequest,
    error_code: str,
    message: str,
) -> dict[str, object]:
    return {
        "reason": "simulation_wait_until_error",
        "upstream_error_code": error_code,
        "upstream_message": message,
        "until_time": request.until_time,
        "timeout_s": request.timeout_s,
        "suggested_next": [
            "Run simulation_get_status to confirm the timeline is playing and advancing.",
            "Retry simulation_wait_until with a nearer until_time or shorter timeout_s to isolate timeline responsiveness.",
            "Capture WARN/ERROR logs if the timeline status is healthy but wait_until still fails.",
        ],
        "fallback_tool_order": list(_SIMULATION_WAIT_UNTIL_FALLBACK_TOOL_ORDER),
    }


def _simulation_set_time_error_diagnostics(
    *,
    request: SimulationSetTimeRequest,
    error_code: str,
    message: str,
) -> dict[str, object]:
    return {
        "reason": "simulation_set_time_error",
        "upstream_error_code": error_code,
        "upstream_message": message,
        "time_seconds": request.time_seconds,
        "suggested_next": [
            "Run simulation_get_status to confirm the timeline endpoint is responsive.",
            "Retry simulation_set_time with a small non-negative time to isolate seek responsiveness.",
            "Capture WARN/ERROR logs if timeline seek keeps failing.",
        ],
        "fallback_tool_order": list(_SIMULATION_SET_TIME_FALLBACK_TOOL_ORDER),
    }


def _stage_write_error_data(
    *,
    request: dict,
    tool_name: str,
    reason: str,
    error_code: str,
    message: str,
    fallback_tool_order: tuple[str, ...] | list[str],
) -> StageWriteResult:
    prim_path = str(request.get("prim_path") or "")
    diagnostics = _stage_operation_error_diagnostics(
        request=request,
        tool_name=tool_name,
        reason=reason,
        error_code=error_code,
        message=message,
        fallback_tool_order=fallback_tool_order,
    )
    return StageWriteResult(
        ok=False,
        prim_path=prim_path,
        detail=message,
        diagnostics=diagnostics,
    )


def _stage_file_error_data(
    *,
    path: str | None,
    mode: str,
    tool_name: str,
    reason: str,
    error_code: str,
    message: str,
) -> StageFileResult:
    diagnostics = _stage_operation_error_diagnostics(
        request={"path": path, "mode": mode},
        tool_name=tool_name,
        reason=reason,
        error_code=error_code,
        message=message,
        fallback_tool_order=_stage_file_fallback_order(tool_name),
    )
    return StageFileResult(
        ok=False,
        path=path,
        mode=mode,
        diagnostics=diagnostics,
    )


def _stage_operation_error_diagnostics(
    *,
    request: dict,
    tool_name: str,
    reason: str,
    error_code: str,
    message: str,
    fallback_tool_order: tuple[str, ...] | list[str],
) -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "reason": reason,
        "tool_name": tool_name,
        "upstream_error_code": error_code,
        "upstream_message": message,
        "suggested_next": _stage_operation_suggested_next(reason, tool_name),
        "fallback_tool_order": list(fallback_tool_order),
    }
    for key in (
        "usd_url",
        "prim_path",
        "property_name",
        "prim_type",
        "label_type",
        "label_class",
        "path",
        "mode",
    ):
        if key in request:
            diagnostics[key] = request.get(key)
    return diagnostics


def _stage_tool_fallback_order(tool_name: str) -> list[str]:
    return [
        tool_name if item == "{tool_name}" else item
        for item in _STAGE_WRITE_FALLBACK_TOOL_ORDER
    ]


def _stage_file_fallback_order(tool_name: str) -> list[str]:
    return [
        tool_name if item == "{tool_name}" else item
        for item in _STAGE_FILE_FALLBACK_TOOL_ORDER
    ]


def _stage_operation_suggested_next(
    reason: str,
    tool_name: str,
) -> list[str]:
    if reason == "stage_load_usd_error":
        return [
            "Run simulation_get_status to confirm the Kit worker is responsive before retrying the load.",
            "Verify the USD URL with content_browse or rerun official_asset_search / asset_search instead of substituting a primitive.",
            "Capture WARN/ERROR logs if stage_load_usd keeps failing or timing out.",
        ]
    if reason == "stage_open_error":
        return [
            "Run simulation_get_status to confirm the Kit worker is responsive before retrying the stage open.",
            "Verify the scene URL or path before retrying stage_open.",
            "Capture WARN/ERROR logs if stage_open keeps failing or timing out.",
        ]
    return [
        "Run stage_capture_snapshot and simulation_get_status to confirm the target prim and timeline state.",
        f"Retry {tool_name} once after confirming the target state.",
        "Capture WARN/ERROR logs if the stage operation keeps failing.",
    ]


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
