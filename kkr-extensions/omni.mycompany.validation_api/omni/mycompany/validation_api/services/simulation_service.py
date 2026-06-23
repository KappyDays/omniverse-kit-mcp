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
        settle = await self._wait_for_timeline_state(
            timeline,
            is_playing=True,
            is_stopped=False,
        )
        status = self._status_dict(timeline)
        status.update(settle)
        return status

    async def pause(self) -> dict[str, Any]:
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        timeline.pause()
        settle = await self._wait_for_timeline_state(
            timeline,
            is_playing=False,
            is_stopped=False,
        )
        status = self._status_dict(timeline)
        status.update(settle)
        return status

    async def stop(self) -> dict[str, Any]:
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        timeline.stop()
        settle = await self._wait_for_timeline_state(
            timeline,
            is_playing=False,
            is_stopped=True,
        )
        status = self._status_dict(timeline)
        status.update(settle)
        return status

    async def get_status(self) -> dict[str, Any]:
        import omni.timeline  # lazy

        timeline = omni.timeline.get_timeline_interface()
        return self._status_dict(timeline)

    async def step(self, request: dict[str, Any]) -> dict[str, Any]:
        """Advance the timeline by ``frames`` ticks (Phase G).

        Isaac Sim 6.0 can crash when ``forward_one_frame()`` drives active
        Replicator/HydraTexture render products. Use a short play burst gated
        by ``next_update_async()`` instead; this follows the normal timeline
        tick path and preserves the previous play/stop state.
        """
        import time as _time

        import omni.kit.app  # lazy
        import omni.timeline

        frames = int(request.get("frames", 1))
        if frames < 1:
            raise ValueError("frames must be >= 1")

        timeline = omni.timeline.get_timeline_interface()
        app = omni.kit.app.get_app()
        start_time = float(timeline.get_current_time())
        was_playing = bool(timeline.is_playing())
        fps = float(timeline.get_time_codes_per_seconds() or 60.0)
        target_time = start_time + (frames / fps)
        deadline = _time.monotonic() + min(max((frames / fps) + 5.0, 5.0), 600.0)

        advance_mode = "play_burst"
        if not was_playing:
            timeline.play()
        ticks = 0
        timed_out = False
        while float(timeline.get_current_time()) < target_time:
            if _time.monotonic() >= deadline:
                timed_out = True
                break
            await app.next_update_async()
            ticks += 1
        if not was_playing:
            timeline.pause()

        if timed_out:
            timeline.set_current_time(target_time)
            await app.next_update_async()
            advance_mode = "set_time_fallback"

        status = self._status_dict(timeline)
        status.update({
            "frames": frames,
            "start_time": start_time,
            "advance_mode": advance_mode,
            "was_playing": was_playing,
            "ticks_waited": ticks,
            "target_time": target_time,
            "timed_out": timed_out,
        })
        return status

    async def step_observe(self, request: dict[str, Any]) -> dict[str, Any]:
        """Advance frames and gather synchronized runtime observations.

        This avoids the usual "step, then several unrelated polls" skew when
        debugging a live controller. It keeps capture/GPU out of the loop.
        """
        status = await self.step({"frames": int(request.get("frames", 1))})
        status.update({
            "prim_states": [
                _observe_prim_state(str(path))
                for path in request.get("observe_prims") or []
            ],
            "joint_states": [
                _observe_joint_state(str(path))
                for path in request.get("observe_joints") or []
            ],
            "ee_states": [
                _observe_ee_state(item)
                for item in request.get("observe_ee") or []
            ],
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
        import omni.kit.app  # lazy
        import omni.timeline  # lazy

        target = float(request["time_seconds"])
        if target < 0:
            raise ValueError("time_seconds must be >= 0")

        timeline = omni.timeline.get_timeline_interface()
        previous = float(timeline.get_current_time())
        timeline.set_current_time(target)
        await omni.kit.app.get_app().next_update_async()

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

    @staticmethod
    async def _wait_for_timeline_state(
        timeline: Any,
        *,
        is_playing: bool,
        is_stopped: bool,
        max_updates: int = 5,
    ) -> dict[str, Any]:
        import omni.kit.app  # lazy

        app = omni.kit.app.get_app()
        for updates in range(1, max_updates + 1):
            await app.next_update_async()
            if (
                bool(timeline.is_playing()) is is_playing
                and bool(timeline.is_stopped()) is is_stopped
            ):
                return {
                    "timeline_settled": True,
                    "timeline_settle_updates": updates,
                }
        return {
            "timeline_settled": False,
            "timeline_settle_updates": max_updates,
        }


def _observe_prim_state(prim_path: str) -> dict[str, Any]:
    import omni.usd
    from pxr import Usd, UsdGeom

    try:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim not found at {prim_path}")
        matrix = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default(),
        )
        translate = matrix.ExtractTranslation()
        rotation = matrix.ExtractRotation()
        quat = rotation.GetQuat()
        imag = quat.GetImaginary()
        return {
            "prim_path": prim_path,
            "position": [float(translate[0]), float(translate[1]), float(translate[2])],
            "orientation": [
                float(quat.GetReal()),
                float(imag[0]),
                float(imag[1]),
                float(imag[2]),
            ],
            "linear_velocity": None,
            "angular_velocity": None,
            "has_rigid_body": _has_rigid_body_api(prim),
            "source": "usd_world_transform",
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "prim_path": prim_path,
            "position": None,
            "orientation": None,
            "linear_velocity": None,
            "angular_velocity": None,
            "has_rigid_body": False,
            "source": "error",
            "error": str(exc),
        }


def _observe_joint_state(prim_path: str) -> dict[str, Any]:
    try:
        from isaacsim.core.prims import SingleArticulation

        art = SingleArticulation(prim_path)
        try:
            art.initialize()
        except Exception:
            pass
        positions = art.get_joint_positions()
        if positions is None:
            raise ValueError("get_joint_positions returned None")
        values = positions.tolist() if hasattr(positions, "tolist") else list(positions)
        return {
            "prim_path": prim_path,
            "positions": [float(v) for v in values],
            "dof_names": [str(v) for v in (art.dof_names or [])],
            "source": "SingleArticulation",
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "prim_path": prim_path,
            "positions": [],
            "dof_names": [],
            "source": "error",
            "error": str(exc),
        }


def _observe_ee_state(spec: dict[str, Any]) -> dict[str, Any]:
    prim_path = str(spec.get("prim_path", ""))
    end_effector_frame = spec.get("end_effector_frame")
    try:
        from .robot_service import _compute_ee_pose

        return _compute_ee_pose(
            prim_path,
            str(end_effector_frame) if end_effector_frame is not None else None,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "prim_path": prim_path,
            "end_effector_frame": str(end_effector_frame or ""),
            "position": None,
            "orientation": None,
            "source": "error",
            "error": str(exc),
        }


def _has_rigid_body_api(prim: Any) -> bool:
    try:
        return any(
            "RigidBody" in schema
            for schema in prim.GetAppliedSchemas()
        )
    except Exception:
        return False
