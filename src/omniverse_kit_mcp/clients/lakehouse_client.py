"""Lakehouse REST client — query only."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from omniverse_kit_mcp.config import LakehouseConfig
from omniverse_kit_mcp.exceptions import (
    LakehouseQueryError,
    LakehouseResponseDecodeError,
    TransportError,
)

logger = logging.getLogger(__name__)


class LakehouseClient:
    """Async HTTP client for the Lakehouse REST API (read-only)."""

    def __init__(self, config: LakehouseConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(
                connect=config.connect_timeout,
                read=config.timeout,
                write=config.timeout,
                pool=5.0,
            ),
            headers={"User-Agent": "IsaacSimMCP-Lakehouse/0.1"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def query(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a query against the Lakehouse REST API."""
        last_exc: Exception | None = None
        for attempt in range(1, self._config.max_retries + 1):
            try:
                resp = await self._client.post("/query", json=params)
                if resp.status_code in (408, 429, 500, 502, 503, 504) and attempt < self._config.max_retries:
                    last_exc = LakehouseQueryError(
                        f"HTTP {resp.status_code}", error_code=f"HTTP_{resp.status_code}"
                    )
                    await self._backoff(attempt)
                    continue
                resp.raise_for_status()
                try:
                    return resp.json()  # type: ignore[no-any-return]
                except Exception as exc:
                    raise LakehouseResponseDecodeError(str(exc)) from exc
            except httpx.TimeoutException as exc:
                last_exc = LakehouseQueryError(f"Timeout: {exc}")
                if attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_exc from exc
            except httpx.HTTPStatusError as exc:
                raise LakehouseQueryError(
                    str(exc), error_code=f"HTTP_{exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                last_exc = TransportError(str(exc))
                if attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_exc from exc
        raise last_exc or TransportError("Lakehouse request failed after retries")

    async def _backoff(self, attempt: int) -> None:
        base = 0.5 * (2 ** (attempt - 1))
        jitter = random.uniform(0, base * 0.2)  # noqa: S311
        delay = min(base + jitter, 5.0)
        logger.debug("Lakehouse retry attempt %d, backing off %.2fs", attempt, delay)
        await asyncio.sleep(delay)
