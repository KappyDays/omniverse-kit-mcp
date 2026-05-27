"""Simulation service — timeline control (live Isaac Sim environment).

All omni.*/pxr.* imports are lazy (inside functions) per API rule #7.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SimulationService:
    """Controls Isaac Sim simulation timeline via omni.timeline."""

    async def play(self) -> dict[str, Any]:
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        return self._status_dict(timeline)

    async def pause(self) -> dict[str, Any]:
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        timeline.pause()
        return self._status_dict(timeline)

    async def stop(self) -> dict[str, Any]:
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        timeline.stop()
        return self._status_dict(timeline)

    async def get_status(self) -> dict[str, Any]:
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        return self._status_dict(timeline)

    async def step(self, request: dict[str, Any]) -> dict[str, Any]:
        """Advance the timeline by ``frames`` ticks (Phase G).

        Uses ``forward_one_frame()`` where Kit exposes it (per-frame advance
        without resuming play). Otherwise falls back to a short play burst
        gated by ``next_update_async()`` to preserve the previous play/stop
        state.
        """
        import omni.kit.app  # lazy
        import omni.timeline

        frames = int(request.get("frames", 1))
        if frames < 1:
            raise ValueError("frames must be >= 1")

        timeline = omni.timeline.get_timeline_interface()
        app = omni.kit.app.get_app()
        start_time = float(timeline.get_current_time())
        was_playing = bool(timeline.is_playing())

        has_forward = hasattr(timeline, "forward_one_frame")
        advance_mode = "forward_one_frame" if has_forward else "play_burst"

        if has_forward:
            for _ in range(frames):
                timeline.forward_one_frame()
                await app.next_update_async()
        else:
            if not was_playing:
                timeline.play()
            for _ in range(frames):
                await app.next_update_async()
            if not was_playing:
                timeline.pause()

        status = self._status_dict(timeline)
        status.update({
            "frames": frames,
            "start_time": start_time,
            "advance_mode": advance_mode,
            "was_playing": was_playing,
        })
        return status

    async def wait_until(self, request: dict[str, Any]) -> dict[str, Any]:
        """Tick the Kit loop until current_time >= until_time or wall timeout.

        Yields each tick via ``next_update_async`` so the event loop is never
        blocked (deadlock-safe). The timeline must be PLAYING for current_time
        to advance — otherwise this returns ``timed_out=True``.
        """
        import time as _time

        import omni.kit.app  # lazy
        import omni.timeline

        until_time = float(request["until_time"])
        timeout_s = float(request.get("timeout_s", 30.0))

        timeline = omni.timeline.get_timeline_interface()
        app = omni.kit.app.get_app()

        wall_start = _time.time()
        frames = 0
        reached = False
        while True:
            if float(timeline.get_current_time()) >= until_time:
                reached = True
                break
            if (_time.time() - wall_start) >= timeout_s:
                break
            await app.next_update_async()
            frames += 1

        status = self._status_dict(timeline)
        status.update({
            "until_time": until_time,
            "reached": reached,
            "timed_out": not reached,
            "elapsed_s": _time.time() - wall_start,
            "frames_waited": frames,
        })
        return status

    async def set_time(self, request: dict[str, Any]) -> dict[str, Any]:
        """Seek the timeline to ``time_seconds`` (Phase G)."""
        import omni.timeline  # lazy

        target = float(request["time_seconds"])
        if target < 0:
            raise ValueError("time_seconds must be >= 0")

        timeline = omni.timeline.get_timeline_interface()
        previous = float(timeline.get_current_time())
        timeline.set_current_time(target)

        status = self._status_dict(timeline)
        status.update({
            "requested_time": target,
            "previous_time": previous,
        })
        return status

    # ------------------------------------------------------------------

    @staticmethod
    def _status_dict(timeline: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "is_playing": timeline.is_playing(),
            "is_stopped": timeline.is_stopped(),
            "current_time": timeline.get_current_time(),
            "start_time": timeline.get_start_time(),
            "end_time": timeline.get_end_time(),
            "time_codes_per_second": timeline.get_time_codes_per_seconds(),
        }
