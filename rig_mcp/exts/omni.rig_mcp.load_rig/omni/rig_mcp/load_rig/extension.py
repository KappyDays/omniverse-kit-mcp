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
        try:
            summary = self._read_measurements()
            self._status.text = (
                f"Status: max_force={summary['max_force']:.1f}N samples={summary['samples']}"
            )
            carb.log_info(f"[rig] measurement {summary}")
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[rig] measure failed: {exc}")
            self._status.text = "Status: measure error (see console)"

    def _read_measurements(self) -> dict:
        """LIVE path: sample contact force + joint effort. The exact contact-sensor /
        articulation-effort read APIs are LIVE-confirm (rig_make.md) — wire on first
        live run; this returns the reduced summary of the collected series."""
        series: list[tuple[float, float, float]] = []
        # LIVE: append (sim_time, contact_force_N, joint_effort) samples here via the
        # Isaac contact sensor + articulation effort readout once confirmed in session.
        return measure.summarize(series)

    def on_shutdown(self) -> None:
        self._window = None
        carb.log_info("[rig] shutdown")
