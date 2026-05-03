"""Job module — polls async job status from the Extension (Phase B)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.job import JobStatus

logger = logging.getLogger(__name__)


class JobModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def status(
        self,
        meta: OperationMeta,
        job_id: str,
    ) -> ModuleResult[JobStatus]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.job_status(job_id)
            return ok_result(_parse_status(raw, job_id), started_ms=started)
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="JOB_STATUS_ERROR")

    async def cancel(
        self,
        meta: OperationMeta,
        job_id: str,
    ) -> ModuleResult[JobStatus]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.job_cancel(job_id)
            return ok_result(_parse_status(raw, job_id), started_ms=started)
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="JOB_CANCEL_ERROR")


def _parse_status(raw: dict, job_id: str) -> JobStatus:
    return JobStatus(
        job_id=raw.get("job_id", job_id),
        status=raw.get("status", "unknown"),
        progress=float(raw.get("progress", 0.0)),
        result=raw.get("result"),
        error=raw.get("error"),
        created_at_epoch_ms=int(raw.get("created_at_epoch_ms", 0)),
        updated_at_epoch_ms=int(raw.get("updated_at_epoch_ms", 0)),
        raw=raw,
    )
