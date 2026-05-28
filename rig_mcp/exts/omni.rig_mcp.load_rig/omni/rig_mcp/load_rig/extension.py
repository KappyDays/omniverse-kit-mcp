"""Mechanical Rig Under Load extension.

on_startup builds the rig + payload; "Lift Load" sets the joint drive targets
(physics follows them while playing); "Measure" reads contact force + joint effort
(LIVE-only). UI is ASCII. Contact/effort readout API is LIVE-confirm per
mcp-upgrade/make_progress/rig_make.md.
"""
from __future__ import annotations

import carb
import omni.ext
import omni.ui as ui
import omni.usd

from . import config, kinematics, measure, scene_builder


class LoadRigExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._built = False
        self._window = ui.Window("Mechanical Rig Under Load", width=380, height=240)
        with self._window.frame:
            with ui.VStack(spacing=6):
                self._status = ui.Label("Status: idle")
                ui.Button("Build Rig", clicked_fn=lambda *_a: self._on_build())
                ui.Button("Lift Load (play first)", clicked_fn=lambda *_a: self._on_lift())
                ui.Button("Measure", clicked_fn=lambda *_a: self._on_measure())
        carb.log_info("[rig] startup")

    def _on_build(self) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Status: no stage"
            return
        info = scene_builder.build(stage)
        self._built = True
        self._status.text = f"Status: built ({len(info['joints'])} joints, {len(info['payload'])} payload)"
        carb.log_info(f"[rig] built {info}")

    def _on_lift(self) -> None:
        if not self._built:
            self._status.text = "Status: build rig first"
            return
        from pxr import UsdPhysics

        stage = omni.usd.get_context().get_stage()
        lift_target, tilt_target = kinematics.final_targets()
        ld = UsdPhysics.DriveAPI.Get(stage.GetPrimAtPath(config.LIFT_JOINT), "linear")
        ld.GetTargetPositionAttr().Set(lift_target)
        td = UsdPhysics.DriveAPI.Get(stage.GetPrimAtPath(config.TILT_JOINT), "angular")
        td.GetTargetPositionAttr().Set(tilt_target)
        self._status.text = f"Status: drive targets set (lift={lift_target}m tilt={tilt_target}deg) - Play"
        carb.log_info(f"[rig] lift target {lift_target}, tilt {tilt_target}")

    def _on_measure(self) -> None:
        if not self._built:
            self._status.text = "Status: build rig first"
            return
        # Run the sampling loop as an asyncio task that awaits next_update_async.
        # Synchronously calling app.update() inside the UI callback re-enters the
        # Kit update loop and after ~30+ ticks corrupts Vulkan command buffers ->
        # GPU crash (live-observed 2026-05-28: VkResult NOT_READY after Measure).
        import asyncio
        self._status.text = "Status: measuring..."
        asyncio.ensure_future(self._measure_async())

    async def _measure_async(self) -> None:
        try:
            summary = await self._sample_lift_series()
            self._status.text = (
                f"Status: samples={summary['samples']} "
                f"max_force={summary['max_force']:.1f}N "
                f"max_vel={summary['max_effort']:.2f}m/s"
            )
            carb.log_info(f"[rig] measurement {summary}")
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[rig] measure failed: {exc}")
            self._status.text = f"Status: measure error: {exc}"

    async def _sample_lift_series(self) -> dict:
        """LIVE async sampling: (sim_time, drive_force_est_N, carriage_vel_z m/s).

        Awaits ``app.next_update_async`` between samples — the deadlock-safe async
        yield (synchronous ``app.update()`` from a UI callback corrupts Vulkan and
        crashes the GPU). Reads carriage world Z via BBoxCache; estimates the linear
        drive force from the position error (stiffness * (target - current));
        reports z-velocity as the kinematic effort proxy (the rig is rigid bodies +
        joints, not a SingleArticulation, so no joint-effort tensor)."""
        import omni.kit.app
        import omni.timeline
        import omni.usd
        from pxr import Usd, UsdGeom

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return measure.summarize([])
        tl = omni.timeline.get_timeline_interface()
        app = omni.kit.app.get_app()

        def carriage_z() -> float:
            bc = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
            )
            p = stage.GetPrimAtPath(config.CARRIAGE)
            if not p.IsValid():
                return 0.0
            r = bc.ComputeWorldBound(p).ComputeAlignedRange()
            return float((r.GetMin()[2] + r.GetMax()[2]) * 0.5)

        series: list[tuple[float, float, float]] = []
        prev_z = carriage_z()
        prev_t = float(tl.get_current_time())
        z_target = config.CARRIAGE_Z0 + config.LIFT_HEIGHT
        for _ in range(15):
            for _ in range(3):
                await app.next_update_async()
            t = float(tl.get_current_time())
            z = carriage_z()
            err = z_target - z
            force = float(config.LIFT_STIFFNESS * err)
            dt = max(1e-3, t - prev_t)
            vel = (z - prev_z) / dt
            series.append((t, force, float(vel)))
            prev_z, prev_t = z, t
        carb.log_info(f"[rig] sampled series: {series}")
        return measure.summarize(series)

    def on_shutdown(self) -> None:
        self._window = None
        carb.log_info("[rig] shutdown")
