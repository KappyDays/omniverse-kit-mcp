"""Content module — omni.client list / stat / resolve wrapper (Phase H)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.content import (
    ContentBrowseRequest,
    ContentBrowseResult,
    ContentEntry,
    ContentPreviewRequest,
    ContentPreviewResult,
    ContentResolveRequest,
    ContentResolveResult,
)

logger = logging.getLogger(__name__)


class ContentModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def browse(
        self, meta: OperationMeta, request: ContentBrowseRequest,
    ) -> ModuleResult[ContentBrowseResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.content_browse({
                "url": request.url,
                "recursive": request.recursive,
                "max_depth": request.max_depth,
                "max_entries": request.max_entries,
            })
            entries = tuple(
                ContentEntry(
                    url=str(e.get("url", "")),
                    name=str(e.get("name", "")),
                    is_folder=bool(e.get("is_folder", False)),
                    size=e.get("size"),
                    modified_time_ns=e.get("modified_time_ns"),
                    flags=int(e.get("flags", 0) or 0),
                )
                for e in raw.get("entries") or []
            )
            result = ContentBrowseResult(
                ok=bool(raw.get("ok", True)),
                url=str(raw.get("url", request.url)),
                recursive=bool(raw.get("recursive", request.recursive)),
                entries=entries,
                entry_count=int(raw.get("entry_count", len(entries))),
                truncated=bool(raw.get("truncated", False)),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="CONTENT_BROWSE_ERROR",
            )

    async def preview(
        self, meta: OperationMeta, request: ContentPreviewRequest,
    ) -> ModuleResult[ContentPreviewResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.content_preview({"url": request.url})
            result = ContentPreviewResult(
                ok=bool(raw.get("ok", True)),
                url=str(raw.get("url", request.url)),
                info=dict(raw.get("info") or {}),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="CONTENT_PREVIEW_ERROR",
            )

    async def resolve(
        self, meta: OperationMeta, request: ContentResolveRequest,
    ) -> ModuleResult[ContentResolveResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.content_resolve({"url": request.url})
            result = ContentResolveResult(
                ok=bool(raw.get("ok", True)),
                url=str(raw.get("url", request.url)),
                resolved=str(raw.get("resolved", request.url)),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="CONTENT_RESOLVE_ERROR",
            )
