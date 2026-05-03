"""Asset module — read-only catalog listing against the Extension (Phase B+)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.asset import AssetCategory, AssetItem, AssetListResult
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta

logger = logging.getLogger(__name__)


class AssetModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def list(
        self,
        meta: OperationMeta,
        category: str | None = None,
        subpath: str = "",
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> ModuleResult[AssetListResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.asset_list(
                category=category,
                subpath=subpath,
                recursive=recursive,
                max_depth=max_depth,
                max_entries=max_entries,
            )
            return ok_result(_parse_list(raw), started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="ASSET_LIST_ERROR"
            )


def _parse_list(raw: dict) -> AssetListResult:
    categories = tuple(
        AssetCategory(name=c["name"], url=c["url"])
        for c in raw.get("categories", [])
    )
    items = tuple(
        AssetItem(
            name=i["name"],
            url=i["url"],
            is_folder=bool(i.get("is_folder", False)),
            size=i.get("size"),
        )
        for i in raw.get("items", [])
    )
    return AssetListResult(
        assets_root=raw.get("assets_root"),
        category=raw.get("category"),
        subpath=raw.get("subpath", ""),
        base_url=raw.get("base_url"),
        target_url=raw.get("target_url"),
        categories=categories,
        items=items,
        count=int(raw.get("count", len(items))),
    )
