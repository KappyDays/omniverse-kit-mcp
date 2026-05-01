"""Conveyor Pick Extension — entry point + UI window."""

from __future__ import annotations

import asyncio
import carb
import omni.ext
import omni.kit.app
import omni.ui as ui

from .scene_builder import build_scene
from .cube_spawner import CubeSpawner, CUBES_PARENT
from .pick_controller import PickController


# Top-level prims this extension authors. Cleared on shutdown so a
# previous "Start Cycle" run does not leave the stage littered with
# hundreds of orphan cubes that PhysX keeps simulating in the background
# (visible to the user as a halo of small dots in the viewport, and a
# significant FPS drop on cold reload).
_SPAWNED_PARENTS = (
    CUBES_PARENT,        # /World/Cubes — every red cube the spawner ever made
    "/World/Conveyors",  # belt props authored by build_scene()
    "/World/Franka",     # franka payload reference
    "/World/Basket",     # basket prop
)


class ConveyorPickExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        carb.log_info(f"[conveyor_pick] startup ext_id={ext_id}")
        self._ext_id = ext_id
        self._window: ui.Window | None = None
        self._spawner: CubeSpawner | None = None
        self._spawner_task = None
        self._pick_ctrl: PickController | None = None
        self._pick_task = None
        self._update_sub = None
        # Clean any cubes left over from a previous session so a fresh
        # session does not start with hundreds of orphan rigid bodies
        # already accumulated. Idempotent — silent on missing prims.
        self._cleanup_spawned_prims()
        self._build_window()

    def on_shutdown(self) -> None:
        carb.log_info("[conveyor_pick] shutdown")
        self._stop_cycle()
        self._cleanup_spawned_prims()
        if self._window is not None:
            self._window.visible = False
            self._window.destroy()
            self._window = None

    def _build_window(self) -> None:
        existing = ui.Workspace.get_window("Conveyor Pick")
        if existing is not None:
            existing.visible = False
            existing.destroy()
        self._window = ui.Window("Conveyor Pick", width=320, height=200)
        with self._window.frame:
            with ui.VStack(spacing=4):
                ui.Button("Build Scene", clicked_fn=self._on_build)
                ui.Button("Start Cycle", clicked_fn=self._on_start)
                ui.Button("Stop Cycle", clicked_fn=self._stop_cycle)
                self._status_label = ui.Label("Status: idle")
                self._pick_count_label = ui.Label("Picks: 0")

    def _on_build(self) -> None:
        try:
            summary = build_scene()
            carb.log_info(f"[conveyor_pick] build_scene summary: {summary}")
            self._status_label.text = "Status: scene built"
        except Exception as exc:
            carb.log_error(f"[conveyor_pick] build_scene error: {exc}")
            self._status_label.text = f"Status: build failed ({exc})"

    def _on_start(self) -> None:
        if self._spawner_task is not None:
            return
        self._spawner = CubeSpawner()
        self._pick_ctrl = PickController()
        self._spawner_task = asyncio.ensure_future(self._spawner.run())
        self._pick_task = asyncio.ensure_future(self._pick_ctrl.run())
        self._status_label.text = "Status: cycle running"
        try:
            app = omni.kit.app.get_app()
            self._update_sub = app.get_update_event_stream().create_subscription_to_pop(
                self._update_status, name="conveyor_pick_status"
            )
        except Exception as exc:
            carb.log_warn(f"[conveyor_pick] status sub error: {exc}")

    def _stop_cycle(self) -> None:
        if self._spawner is not None:
            self._spawner.stop()
        if self._pick_ctrl is not None:
            self._pick_ctrl.stop()
        for task in (self._spawner_task, self._pick_task):
            if task is not None and not task.done():
                try:
                    task.cancel()
                except Exception:
                    pass
        self._spawner_task = None
        self._pick_task = None
        self._spawner = None
        self._pick_ctrl = None
        self._update_sub = None
        if hasattr(self, "_status_label") and self._status_label is not None:
            self._status_label.text = "Status: stopped"

    def _update_status(self, _event) -> None:
        if self._pick_ctrl is not None and hasattr(self, "_pick_count_label"):
            self._pick_count_label.text = f"Picks: {self._pick_ctrl.picks_done()}"

    def _cleanup_spawned_prims(self) -> None:
        """Delete every prim this extension authors. Tolerates missing
        prims (extension may shutdown before scene was ever built)."""
        try:
            import omni.kit.commands
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return
            paths = [
                p for p in _SPAWNED_PARENTS
                if stage.GetPrimAtPath(p).IsValid()
            ]
            if not paths:
                return
            try:
                omni.kit.commands.execute("DeletePrims", paths=paths)
            except Exception:
                # Fallback when DeletePrims is unavailable — drop them
                # one at a time via the Sdf layer. Keeps shutdown silent.
                from pxr import Sdf
                with Sdf.ChangeBlock():
                    layer = stage.GetEditTarget().GetLayer()
                    for p in paths:
                        layer.GetPrimAtPath(p).RemoveFromParent()
            carb.log_info(
                f"[conveyor_pick] cleanup deleted {len(paths)} spawned root(s): {paths}"
            )
        except Exception as exc:
            carb.log_warn(f"[conveyor_pick] cleanup error (non-fatal): {exc}")
