"""CatalogModule — local queries over docs/references/extensions.json.

No REST / Isaac Sim dependency. Lazy-loads + in-memory caches the catalog.
Used by the `extension_search` MCP tool to surface ext candidates for
natural-language tasks.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta


class CatalogModule:
    def __init__(self, catalog_path: Path) -> None:
        self._catalog_path = catalog_path
        self._entries: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if self._entries is None:
            data = json.loads(self._catalog_path.read_text(encoding="utf-8"))
            self._entries = data.get("extensions") or []
        return self._entries

    async def search(
        self,
        meta: OperationMeta,
        keyword: str,
        app: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> ModuleResult[list[dict[str, Any]]]:
        started = int(time.time() * 1000)
        try:
            entries = self._load()
            k = (keyword or "").lower()
            cat = (category or "").lower()
            results: list[dict[str, Any]] = []
            for e in entries:
                if app and app not in (e.get("apps") or {}):
                    continue
                if cat and (e.get("category") or "").lower() != cat:
                    continue
                if k:
                    haystack_parts = [
                        e.get("name") or "",
                        e.get("title") or "",
                        e.get("summary") or "",
                        e.get("mcp_research_hint") or "",
                        e.get("raw_description") or "",
                        " ".join(e.get("keywords") or []),
                    ]
                    haystack = " ".join(haystack_parts).lower()
                    if k not in haystack:
                        continue
                results.append(
                    {
                        "name": e.get("name"),
                        "title": e.get("title"),
                        "summary": e.get("summary"),
                        "category": e.get("category"),
                        "apps": sorted((e.get("apps") or {}).keys()),
                        "key_symbols": e.get("key_symbols") or [],
                        "mcp_research_hint": e.get("mcp_research_hint"),
                    }
                )
                if len(results) >= limit:
                    break
            return ok_result(results, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="EXTENSION_SEARCH_ERROR",
            )
