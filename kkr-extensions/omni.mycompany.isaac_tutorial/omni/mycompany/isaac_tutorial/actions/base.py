"""Shared UI-feedback decorator + BaseAction with prereq auto-chain."""
from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

import carb


async def run_with_ui_feedback(ui, coro: Awaitable, label: str = "", services=None):
    """Wrap a coroutine with UI busy/status/notification lifecycle.

    If `services` is provided and the result string contains `job=<id>`,
    ui.start_job_polling is automatically called to poll the async job.

    Expects ui to expose: set_busy(bool, label=str), status_label.text,
    post_notification(str).
    """
    ui.set_busy(True, label=label)
    try:
        result = await coro
        ui.status_label.text = f"[OK] {result}"
        # Detect async job id in result string and start polling
        if services is not None and isinstance(result, str):
            m = re.search(r"job=([^\s)]+)", result)
            if m and hasattr(ui, "start_job_polling"):
                ui.start_job_polling(
                    job_id=m.group(1),
                    services=services,
                    # JobService.cancel is SYNC — invoke directly.
                    cancel_cb=lambda jid: services.jobs.cancel(jid),
                )
        return result
    except Exception as exc:
        err = f"[FAIL] {type(exc).__name__}: {exc}"
        ui.status_label.text = err
        carb.log_error(f"[isaac_tutorial] {label}: {exc}")
        try:
            ui.post_notification(f"{label} failed: {exc}")
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        ui.set_busy(False)


class BaseAction(ABC):
    """Common base for all actions — holds ui/state/services + prereq auto-chain."""

    def __init__(self, ui, state, services) -> None:
        self.ui = ui
        self.state = state
        self.services = services

    @abstractmethod
    async def run(self):
        """Subclass implementation."""

    async def run_with_prereqs(
        self,
        prereqs: list[tuple[Callable[[], Awaitable], Callable[[], bool]]],
    ):
        """Each (exec_fn, done_check): runs exec_fn only when done_check() is False."""
        for exec_fn, done_check in prereqs:
            if not done_check():
                await exec_fn()
        await self.run()
