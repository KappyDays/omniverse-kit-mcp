"""Character module — USD load, animation playback, pose control, async navigate (Phase C)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.character import (
    CharacterLoadCrowdMember,
    CharacterLoadCrowdRequest,
    CharacterLoadCrowdResult,
    CharacterLoadRequest,
    CharacterLoadResult,
    CharacterNavigateRequest,
    CharacterNavigateResult,
    CharacterPlayAnimationRequest,
    CharacterPlayAnimationResult,
    CharacterPlayAnimationVariantRequest,
    CharacterPlayAnimationVariantResult,
    CharacterSetPositionRequest,
    CharacterSetPositionResult,
    CharacterState,
    CharacterStopAnimationRequest,
    CharacterStopAnimationResult,
)
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta

logger = logging.getLogger(__name__)


class CharacterModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def load(
        self,
        meta: OperationMeta,
        request: CharacterLoadRequest,
    ) -> ModuleResult[CharacterLoadResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_load({
                "usd_url": request.usd_url,
                "prim_path": request.prim_path,
                "position": list(request.position) if request.position else None,
                "yaw": request.yaw,
            })
            return ok_result(
                CharacterLoadResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=raw.get("prim_path", request.prim_path or ""),
                    skel_root_path=raw.get("skel_root_path", ""),
                    sanitized_prim_path=raw.get("sanitized_prim_path", raw.get("prim_path", "")),
                    has_skeleton=bool(raw.get("has_skeleton", False)),
                    anim_graph_bound=bool(raw.get("anim_graph_bound", False)),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="CHARACTER_LOAD_ERROR"
            )

    async def play_animation(
        self,
        meta: OperationMeta,
        request: CharacterPlayAnimationRequest,
    ) -> ModuleResult[CharacterPlayAnimationResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_play_animation({
                "prim_path": request.prim_path,
                "animation_name": request.animation_name,
                "speed": request.speed,
                "target_position": list(request.target_position) if request.target_position else None,
            })
            return ok_result(
                CharacterPlayAnimationResult(
                    prim_path=raw.get("prim_path", request.prim_path),
                    action=raw.get("action", request.animation_name),
                    speed=float(raw.get("speed", request.speed)),
                    bound_graph=raw.get("bound_graph", ""),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="CHARACTER_PLAY_ANIMATION_ERROR"
            )

    async def set_position(
        self,
        meta: OperationMeta,
        request: CharacterSetPositionRequest,
    ) -> ModuleResult[CharacterSetPositionResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_set_position({
                "prim_path": request.prim_path,
                "position": list(request.position),
                "orientation": list(request.orientation) if request.orientation else None,
            })
            if "position" not in raw or "orientation" not in raw:
                raise KeyError(
                    "Extension /character/set_position response missing "
                    "required 'position' / 'orientation' field"
                )
            return ok_result(
                CharacterSetPositionResult(
                    prim_path=raw.get("prim_path", request.prim_path),
                    position=tuple(raw["position"]),  # type: ignore[arg-type]
                    orientation=tuple(raw["orientation"]),  # type: ignore[arg-type]
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="CHARACTER_SET_POSITION_ERROR"
            )

    async def stop_animation(
        self,
        meta: OperationMeta,
        request: CharacterStopAnimationRequest,
    ) -> ModuleResult[CharacterStopAnimationResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_stop_animation({
                "prim_path": request.prim_path,
            })
            return ok_result(
                CharacterStopAnimationResult(
                    prim_path=raw.get("prim_path", request.prim_path),
                    action=raw.get("action", "Idle"),
                    speed=float(raw.get("speed", 0.0)),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="CHARACTER_STOP_ANIMATION_ERROR"
            )

    async def navigate_to(
        self,
        meta: OperationMeta,
        request: CharacterNavigateRequest,
    ) -> ModuleResult[CharacterNavigateResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_navigate({
                "prim_path": request.prim_path,
                "target": list(request.target),
                "speed": request.speed,
            })
            return ok_result(
                CharacterNavigateResult(
                    job_id=raw["job_id"],
                    prim_path=raw.get("prim_path", request.prim_path),
                    target=tuple(raw.get("target", list(request.target))),  # type: ignore[arg-type]
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="CHARACTER_NAVIGATE_ERROR"
            )

    async def play_animation_variant(
        self,
        meta: OperationMeta,
        request: CharacterPlayAnimationVariantRequest,
    ) -> ModuleResult[CharacterPlayAnimationVariantResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_play_animation_variant({
                "prim_path": request.prim_path,
                "variant": request.variant,
                "speed": request.speed,
                "target_position": (
                    list(request.target_position) if request.target_position else None
                ),
                "dispatch_mode": request.dispatch_mode,
            })
            variables_raw = raw.get("variables_set") or {}
            variables_tuple = tuple(str(k) for k in variables_raw.keys()) if isinstance(
                variables_raw, dict
            ) else tuple(str(v) for v in variables_raw)
            return ok_result(
                CharacterPlayAnimationVariantResult(
                    prim_path=raw.get("prim_path", request.prim_path),
                    variant=str(raw.get("variant", request.variant)),
                    base_action=str(raw.get("base_action", request.variant)),
                    speed=float(raw.get("speed", request.speed)),
                    variables_set=variables_tuple,
                    bound_graph=str(raw.get("bound_graph", "")),
                    dispatch_mode=str(raw.get("dispatch_mode", request.dispatch_mode)),
                    behavior_task_id=(
                        int(raw["behavior_task_id"])
                        if raw.get("behavior_task_id") is not None
                        else None
                    ),
                    behavior_task_name=raw.get("behavior_task_name"),
                    behavior_task_status=raw.get("behavior_task_status"),
                    behavior_task_running=(
                        bool(raw["behavior_task_running"])
                        if raw.get("behavior_task_running") is not None
                        else None
                    ),
                    task_error=raw.get("task_error"),
                    skel_animation_path=raw.get("skel_animation_path"),
                    skel_annotation_path=raw.get("skel_annotation_path"),
                    skel_animation_start=(
                        float(raw["skel_animation_start"])
                        if raw.get("skel_animation_start") is not None
                        else None
                    ),
                    skel_animation_end=(
                        float(raw["skel_animation_end"])
                        if raw.get("skel_animation_end") is not None
                        else None
                    ),
                    skel_seek_time_seconds=(
                        float(raw["skel_seek_time_seconds"])
                        if raw.get("skel_seek_time_seconds") is not None
                        else None
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started,
                error_code="CHARACTER_PLAY_ANIMATION_VARIANT_ERROR",
            )

    async def load_crowd(
        self,
        meta: OperationMeta,
        request: CharacterLoadCrowdRequest,
    ) -> ModuleResult[CharacterLoadCrowdResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_load_crowd({
                "count": request.count,
                "layout": request.layout,
                "spacing": request.spacing,
                "base_name": request.base_name,
                "center": list(request.center),
                "usd_url": request.usd_url,
            })
            loaded_raw = raw.get("loaded") or []
            members = tuple(
                CharacterLoadCrowdMember(
                    index=int(m.get("index", i)),
                    prim_path=m.get("prim_path"),
                    position=tuple(float(x) for x in m.get("position", (0.0, 0.0, 0.0))),  # type: ignore[arg-type]
                    error=m.get("error"),
                )
                for i, m in enumerate(loaded_raw)
            )
            center_raw = raw.get("center") or list(request.center)
            return ok_result(
                CharacterLoadCrowdResult(
                    count=int(raw.get("count", request.count)),
                    success_count=int(raw.get("success_count", 0)),
                    layout=str(raw.get("layout", request.layout)),
                    spacing=float(raw.get("spacing", request.spacing)),
                    base_name=str(raw.get("base_name", request.base_name)),
                    center=tuple(float(c) for c in center_raw),  # type: ignore[arg-type]
                    usd_url=str(raw.get("usd_url", "")),
                    loaded=members,
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="CHARACTER_LOAD_CROWD_ERROR",
            )

    async def get_state(
        self,
        meta: OperationMeta,
        prim_path: str,
    ) -> ModuleResult[CharacterState]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.character_get_state(prim_path)
            missing = [k for k in ("position", "rotation", "action", "is_navigating") if k not in raw]
            if missing:
                raise KeyError(
                    f"Extension /character/state response missing required fields: {missing}"
                )
            return ok_result(
                CharacterState(
                    prim_path=raw.get("prim_path", prim_path),
                    position=tuple(raw["position"]),  # type: ignore[arg-type]
                    rotation=tuple(raw["rotation"]),  # type: ignore[arg-type]
                    action=raw["action"],
                    is_navigating=bool(raw["is_navigating"]),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="CHARACTER_GET_STATE_ERROR"
            )
