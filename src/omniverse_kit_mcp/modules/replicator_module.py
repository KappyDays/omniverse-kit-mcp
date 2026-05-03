"""Replicator (SDG) module — writer / randomizer / trigger (Phase H)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.replicator import (
    ReplicatorCreateWriterRequest,
    ReplicatorCreateWriterResult,
    ReplicatorRegisterRandomizerRequest,
    ReplicatorRegisterRandomizerResult,
    ReplicatorTriggerOnceRequest,
    ReplicatorTriggerOnceResult,
    ReplicatorTriggerOnTimeRequest,
    ReplicatorTriggerOnTimeResult,
)

logger = logging.getLogger(__name__)


class ReplicatorModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def create_writer(
        self, meta: OperationMeta, request: ReplicatorCreateWriterRequest,
    ) -> ModuleResult[ReplicatorCreateWriterResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.replicator_create_writer({
                "writer_type": request.writer_type,
                "output_dir": request.output_dir,
                "rgb": request.rgb,
                "depth": request.depth,
                "semantic_segmentation": request.semantic_segmentation,
            })
            result = ReplicatorCreateWriterResult(
                ok=bool(raw.get("ok", True)),
                writer_id=str(raw.get("writer_id", "")),
                writer_type=str(raw.get("writer_type", request.writer_type)),
                output_dir=str(raw.get("output_dir", request.output_dir)),
                channels=dict(raw.get("channels") or {}),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="REPLICATOR_CREATE_WRITER_ERROR",
            )

    async def register_randomizer(
        self, meta: OperationMeta,
        request: ReplicatorRegisterRandomizerRequest,
    ) -> ModuleResult[ReplicatorRegisterRandomizerResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.replicator_register_randomizer({
                "type": request.type,
                "target": request.target,
                "config": dict(request.config),
            })
            result = ReplicatorRegisterRandomizerResult(
                ok=bool(raw.get("ok", True)),
                randomizer_id=str(raw.get("randomizer_id", "")),
                type=str(raw.get("type", request.type)),
                target=str(raw.get("target", request.target)),
                config=dict(raw.get("config") or {}),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="REPLICATOR_REGISTER_RANDOMIZER_ERROR",
            )

    async def trigger_once(
        self, meta: OperationMeta, request: ReplicatorTriggerOnceRequest,
    ) -> ModuleResult[ReplicatorTriggerOnceResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.replicator_trigger_once({
                "num_frames": request.num_frames,
            })
            result = ReplicatorTriggerOnceResult(
                ok=bool(raw.get("ok", True)),
                num_frames=int(raw.get("num_frames", request.num_frames)),
                frames_ran=int(raw.get("frames_ran", 0)),
                writer_count=int(raw.get("writer_count", 0)),
                randomizer_count=int(raw.get("randomizer_count", 0)),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="REPLICATOR_TRIGGER_ONCE_ERROR",
            )

    async def trigger_on_time(
        self, meta: OperationMeta, request: ReplicatorTriggerOnTimeRequest,
    ) -> ModuleResult[ReplicatorTriggerOnTimeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.replicator_trigger_on_time({
                "interval_s": request.interval_s,
            })
            result = ReplicatorTriggerOnTimeResult(
                ok=bool(raw.get("ok", True)),
                trigger_id=str(raw.get("trigger_id", "")),
                interval_s=float(raw.get("interval_s", request.interval_s)),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="REPLICATOR_TRIGGER_ON_TIME_ERROR",
            )
