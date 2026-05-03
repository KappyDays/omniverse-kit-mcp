"""Material module — MDL enumeration / assign / bound readback (Phase F)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.material import (
    MaterialAssignMdlRequest,
    MaterialAssignMdlResult,
    MaterialGetBoundRequest,
    MaterialGetBoundResult,
    MaterialListMdlRequest,
    MaterialListMdlResult,
    MaterialMdlEntry,
)

logger = logging.getLogger(__name__)


class MaterialModule:
    """Enumerate MDL modules, assign MDL material to prims, read back bindings."""

    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def list_mdl(
        self, meta: OperationMeta, request: MaterialListMdlRequest,
    ) -> ModuleResult[MaterialListMdlResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.material_list_mdl(request.library)
            entries_raw = raw.get("entries") or []
            entries = tuple(
                MaterialMdlEntry(
                    name=str(e.get("name", "")),
                    url=str(e.get("url", "")),
                    library=str(e.get("library", request.library)),
                )
                for e in entries_raw
            )
            return ok_result(
                MaterialListMdlResult(
                    ok=bool(raw.get("ok", True)),
                    library=str(raw.get("library", request.library)),
                    count=int(raw.get("count", len(entries))),
                    entries=entries,
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="MATERIAL_LIST_MDL_ERROR",
            )

    async def assign_mdl(
        self, meta: OperationMeta, request: MaterialAssignMdlRequest,
    ) -> ModuleResult[MaterialAssignMdlResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.material_assign_mdl({
                "prim_path": request.prim_path,
                "mdl_url": request.mdl_url,
                "material_name": request.material_name,
            })
            return ok_result(
                MaterialAssignMdlResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=str(raw.get("prim_path", request.prim_path)),
                    material_prim_path=str(raw.get("material_prim_path", "")),
                    mdl_url=str(raw.get("mdl_url", request.mdl_url)),
                    material_name=str(
                        raw.get("material_name", request.material_name),
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="MATERIAL_ASSIGN_MDL_ERROR",
            )

    async def get_bound(
        self, meta: OperationMeta, request: MaterialGetBoundRequest,
    ) -> ModuleResult[MaterialGetBoundResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.material_get_bound(request.prim_path)
            return ok_result(
                MaterialGetBoundResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=str(raw.get("prim_path", request.prim_path)),
                    material_path=raw.get("material_path"),
                    binding_strength=raw.get("binding_strength"),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="MATERIAL_GET_BOUND_ERROR",
            )
