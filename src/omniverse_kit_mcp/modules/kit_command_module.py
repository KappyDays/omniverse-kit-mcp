"""KitCommandModule — thin wrapper for omni.kit.commands.execute.

Common profile (Isaac + USD Composer). Module-level retry/timeout handled
by the shared IsaacRestClient.
"""

from __future__ import annotations

import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.kit_command import (
    KitCommandExecuteRequest,
    KitCommandExecuteResult,
    KitPythonExecRequest,
    KitPythonExecResult,
)


class KitCommandModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def execute(
        self,
        meta: OperationMeta,
        request: KitCommandExecuteRequest,
    ) -> ModuleResult[KitCommandExecuteResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.kit_command_execute(
                name=request.name,
                payload=request.payload,
                expect_undo=request.expect_undo,
            )
            data = KitCommandExecuteResult.from_raw(raw)
            if not data.succeeded:
                return error_result(
                    data.message or f"Command {request.name} failed",
                    started_ms=started,
                    error_code=data.error or "KIT_COMMAND_FAILED",
                )
            return ok_result(data, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="KIT_COMMAND_EXEC_ERROR",
            )

    async def python_run(
        self,
        meta: OperationMeta,
        request: KitPythonExecRequest,
    ) -> ModuleResult[KitPythonExecResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.kit_python_run(
                code=request.code,
                return_keys=list(request.return_keys),
            )
            data = KitPythonExecResult.from_raw(raw)
            if not data.ok:
                return error_result(
                    data.error or "Python script raised",
                    started_ms=started,
                    error_code="KIT_PYTHON_EXEC_ERROR",
                )
            return ok_result(data, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="KIT_PYTHON_EXEC_ERROR",
            )
