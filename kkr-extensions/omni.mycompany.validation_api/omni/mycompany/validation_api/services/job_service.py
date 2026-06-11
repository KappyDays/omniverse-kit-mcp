"""Job service — tracks async background tasks with TTL cleanup (Phase B).

All tasks are launched via :func:`asyncio.create_task`. Job state is kept in
an in-memory dict keyed by ``job_id``. A background cleanup task purges
completed entries older than ``TTL_SECONDS``.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

TTL_SECONDS = 3600.0
CLEANUP_INTERVAL_SECONDS = 120.0


class JobService:
    """In-memory async job tracker.

    Each job entry: ``{status, progress, result, error, created_at_ms,
    updated_at_ms}`` with ``status`` ∈ {``pending``, ``running``, ``done``,
    ``error``, ``canceled``}.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._cleanup_task: asyncio.Task | None = None

    def start_job(
        self,
        coro_factory: Callable[[Callable[[float], None]], Awaitable[dict[str, Any]]],
    ) -> str:
        """Launch *coro_factory(update_progress)* as a background task and return its job_id.

        *coro_factory* receives a callable that updates progress (0.0–1.0)
        and must return a dict that becomes ``job.result`` on success. All
        exceptions inside the coroutine are captured into ``job.error`` —
        never silent.
        """
        job_id = uuid.uuid4().hex[:16]
        now = int(time.time() * 1000)
        self._jobs[job_id] = {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at_ms": now,
            "updated_at_ms": now,
        }

        def _update_progress(value: float) -> None:
            entry = self._jobs.get(job_id)
            if entry is None:
                return
            entry["progress"] = max(0.0, min(1.0, float(value)))
            entry["updated_at_ms"] = int(time.time() * 1000)

        async def _runner() -> None:
            entry = self._jobs.get(job_id)
            if entry is None:
                return
            entry["status"] = "running"
            entry["updated_at_ms"] = int(time.time() * 1000)
            try:
                result = await coro_factory(_update_progress)
                entry["status"] = "done"
                entry["progress"] = 1.0
                entry["result"] = result
            except asyncio.CancelledError:
                entry["status"] = "canceled"
                # Preserve any message cancel() already wrote (e.g. "Job canceled by user")
                entry["error"] = entry.get("error") or "Job canceled"
                raise
            except Exception as exc:
                entry["status"] = "error"
                entry["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
                logger.exception("Job %s failed", job_id)
            finally:
                entry["updated_at_ms"] = int(time.time() * 1000)

        task = asyncio.create_task(_runner(), name=f"job:{job_id}")
        self._tasks[job_id] = task
        self._ensure_cleanup_task()
        return job_id

    def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel a running job. No-op if the job already reached a terminal state."""
        entry = self._jobs.get(job_id)
        if entry is None:
            raise KeyError(f"Unknown job_id: {job_id}")
        task = self._tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()
            entry["status"] = "canceled"
            entry["error"] = entry.get("error") or "Job canceled by user"
            entry["updated_at_ms"] = int(time.time() * 1000)
        return {
            "job_id": job_id,
            "status": entry["status"],
            "progress": entry["progress"],
            "result": entry["result"],
            "error": entry["error"],
            "created_at_epoch_ms": entry["created_at_ms"],
            "updated_at_epoch_ms": entry["updated_at_ms"],
        }

    def get_status(self, job_id: str) -> dict[str, Any]:
        entry = self._jobs.get(job_id)
        if entry is None:
            raise KeyError(f"Unknown job_id: {job_id}")
        return {
            "job_id": job_id,
            "status": entry["status"],
            "progress": entry["progress"],
            "result": entry["result"],
            "error": entry["error"],
            "created_at_epoch_ms": entry["created_at_ms"],
            "updated_at_epoch_ms": entry["updated_at_ms"],
        }

    def active_job_ids(self) -> tuple[str, ...]:
        """Return non-terminal job IDs.

        Stage mutation while an async robot/character job is still ticking can
        race Kit/PhysX. Load services use this as a cheap preflight guard.
        """
        return tuple(
            job_id
            for job_id, entry in self._jobs.items()
            if entry.get("status") in {"pending", "running"}
        )

    def _ensure_cleanup_task(self) -> None:
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return
        self._cleanup_task = loop.create_task(self._cleanup_loop(), name="job_cleanup")

    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                self._sweep_expired()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("job cleanup loop error: %s", exc)

    def _sweep_expired(self) -> None:
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - int(TTL_SECONDS * 1000)
        expired = [
            jid for jid, entry in self._jobs.items()
            if entry["status"] in ("done", "error", "canceled")
            and entry["updated_at_ms"] < cutoff_ms
        ]
        for jid in expired:
            self._jobs.pop(jid, None)
            self._tasks.pop(jid, None)
        if expired:
            logger.debug("Swept %d expired jobs", len(expired))
