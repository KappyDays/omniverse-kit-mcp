"""Lakehouse module — query only (no inject/cleanup per interview spec)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.lakehouse_client import LakehouseClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.lakehouse import (
    LakehouseQueryRequest,
    LakehouseQueryResult,
    LakehouseRow,
)

logger = logging.getLogger(__name__)


class LakehouseModule:
    def __init__(self, client: LakehouseClient) -> None:
        self._client = client

    async def query(
        self, meta: OperationMeta, request: LakehouseQueryRequest
    ) -> ModuleResult[LakehouseQueryResult]:
        started = int(time.time() * 1000)
        try:
            payload: dict = {"limit": request.limit}
            if request.sql is not None:
                payload["sql"] = request.sql
            if request.target is not None:
                payload["target"] = {
                    "namespace": request.target.namespace,
                    "dataset": request.target.dataset,
                }
                if request.target.table:
                    payload["target"]["table"] = request.target.table
                if request.target.version:
                    payload["target"]["version"] = request.target.version
            if request.filters:
                payload["filters"] = request.filters

            raw = await self._client.query(payload)
            rows = tuple(
                LakehouseRow(values=r.get("values", r) if isinstance(r, dict) else {"_value": r})
                for r in raw.get("rows", [])
            )
            result = LakehouseQueryResult(
                row_count=raw.get("row_count", len(rows)),
                rows=rows,
                schema=raw.get("schema", {}),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="LAKEHOUSE_QUERY_ERROR")
