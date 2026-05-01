"""Humanoid Pick & Place — Kit Extension entry + UI.

Independent extension (no validation_api dependency, per 2026-04-22
policy). Workflow:

    1. Build Scene  — assemble ground / tables / cube / humanoid +
                      FixedJoint anchor + camera + status xform.
    2. Inspect      — dump live DOF names to Console + /World/PickStatus
                      (one-shot diagnostic; Run Pick & Place does this
                      implicitly so this button is for manual tuning).
    3. Run Pick & Place — async keyframe trajectory, single cycle.
    4. Reset Cube  — move cube back to A.
    5. Stop        — cancel any running trajectory.
"""

from __future__ import annotations

import asyncio

import carb
import omni.ext
import omni.kit.app
import omni.kit.async_engine
import omni.timeline
import omni.ui as ui
import omni.usd

from .humanoids import HumanoidSpec, PHASE1_HUMANOIDS, default_humanoid
from .pick_controller import PickController
from .scene_builder import (
    PICK_CUBE_PATH,
    build_scene,
    reset_pick_cube,
    stamp_status,
)


_SOURCE = "omni.mycompany.humanoid_pick_place"
_WINDOW_TITLE = "Humanoid Pick & Place"


class HumanoidPickPlaceExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_info(f"[{_SOURCE}] startup ext_id={ext_id}")
        self._ext_id = ext_id
        # Defensive sentinel — see usd-load-deadlock-recipe (T0.2).
        self._log_capture = None
        self._pick_task: asyncio.Future | None = None
        self._pick_ctrl: PickController | None = None
        # Phase 1 ships only Humanoid28 — the registry is exposed via the
        # combo box ready for Phase 2 entries.
        self._humanoids: tuple[HumanoidSpec, ...] = PHASE1_HUMANOIDS
        self._selected_humanoid: HumanoidSpec = default_humanoid()
        self._build_window()

    def on_shutdown(self) -> None:
        carb.log_info(f"[{_SOURCE}] shutdown")
        self._cancel_pick_task()
        if self._window is not None:
            try:
                self._window.visible = False
                self._window.destroy()
            except Exception as exc:
                carb.log_warn(f"[{_SOURCE}] window destroy: {exc}")
            self._window = None

    # ----- UI -----

    def _build_window(self) -> None:
        # Sweep zombie window from a previous fswatcher reload.
        try:
            existing = ui.Workspace.get_window(_WINDOW_TITLE)
            if existing is not None:
                existing.visible = False
                existing.destroy()
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] zombie sweep: {exc}")

        self._window = ui.Window(_WINDOW_TITLE, width=360, height=300)
        with self._window.frame:
            with ui.VStack(spacing=4, height=0):
                with ui.CollapsableFrame("Humanoid", collapsed=False,
                                         name="frame_humanoid"):
                    with ui.VStack(spacing=4, height=0):
                        labels = [h.title for h in self._humanoids]
                        self._humanoid_combo = ui.ComboBox(
                            0, *labels, name="humanoid_combo",
                            tooltip="Phase 1: NVIDIA Humanoid28. Phase 2 "
                                    "candidates appended once their joint "
                                    "rosters are validated.",
                        )
                        self._humanoid_combo.model.add_item_changed_fn(
                            self._on_humanoid_changed,
                        )

                with ui.CollapsableFrame("Build", collapsed=False, name="frame_build"):
                    with ui.VStack(spacing=4, height=0):
                        ui.Button(
                            "Build Scene", name="build_scene",
                            tooltip="Assemble ground + tables + cube + humanoid "
                                    "+ fixed-joint anchor.",
                            clicked_fn=self._on_build_scene, height=28,
                        )
                        ui.Button(
                            "Inspect Joints", name="inspect_joints",
                            tooltip="Initialise SingleArticulation and dump "
                                    "dof_names to Console / PickStatus.",
                            clicked_fn=self._on_inspect_joints, height=28,
                        )

                with ui.CollapsableFrame("Run", collapsed=False, name="frame_run"):
                    with ui.VStack(spacing=4, height=0):
                        ui.Button(
                            "Run Pick & Place", name="run_pick_place",
                            tooltip="Start one keyframe pick-and-place cycle.",
                            clicked_fn=self._on_run_pick_place, height=28,
                        )
                        ui.Button(
                            "Stop", name="stop_pick_place",
                            tooltip="Cancel a running cycle (cube reverts to "
                                    "dynamic; arm holds last pose).",
                            clicked_fn=self._on_stop, height=28,
                        )
                        ui.Button(
                            "Reset Cube", name="reset_cube",
                            tooltip="Move the pick cube back to its initial "
                                    "position on the pick table.",
                            clicked_fn=self._on_reset_cube, height=28,
                        )

                with ui.CollapsableFrame("Status", collapsed=False, name="frame_status"):
                    with ui.VStack(spacing=2, height=0):
                        self._status_label = ui.Label("Status: idle",
                                                      name="status_label")
                        self._cycle_label = ui.Label("Cycles: 0",
                                                     name="cycle_label")
                        self._humanoid_label = ui.Label(
                            f"Selected: {self._selected_humanoid.title}",
                            name="humanoid_label",
                        )

    # ----- Button handlers -----

    def _read_selected_humanoid(self) -> HumanoidSpec:
        """Resolve the currently-selected humanoid from the ComboBox model.

        Reading the model on demand (rather than caching the value via
        ``add_item_changed_fn``) sidesteps a ui_test quirk: invoking
        ``extension_ui_invoke action="select" value=N`` updates the
        widget value but does NOT fire item_changed_fn callbacks, so a
        cached attribute would still point at the old humanoid.
        """
        try:
            idx = self._humanoid_combo.model.get_item_value_model().as_int
            if 0 <= idx < len(self._humanoids):
                return self._humanoids[idx]
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] read combo: {exc}")
        return self._selected_humanoid

    def _on_humanoid_changed(self, _model, _item) -> None:
        # Best-effort live label update. The Build Scene button reads
        # the model state directly on click, so this callback is purely
        # cosmetic.
        spec = self._read_selected_humanoid()
        self._selected_humanoid = spec
        if hasattr(self, "_humanoid_label") and self._humanoid_label is not None:
            self._humanoid_label.text = f"Selected: {spec.title}"

    def _on_build_scene(self) -> None:
        try:
            spec = self._read_selected_humanoid()
            # Sync the cache so the run/inspect buttons see the same spec.
            self._selected_humanoid = spec
            if hasattr(self, "_humanoid_label") and self._humanoid_label is not None:
                self._humanoid_label.text = f"Selected: {spec.title}"
            self._set_status(f"Build: starting ({spec.key})...")
            summary = build_scene(spec)
            stamp_status(stage="scene_built", humanoid=spec.key)
            anchor = summary.get("anchor_link", "?")
            self._set_status(f"Build: ok (humanoid={spec.key}, anchor={anchor})")
        except Exception as exc:
            carb.log_error(f"[{_SOURCE}] build failed: {exc}")
            self._set_status(f"Build failed: {exc}")

    def _on_inspect_joints(self) -> None:
        """One-shot articulation init → dof_names dump."""
        omni.kit.async_engine.run_coroutine(self._inspect_joints_async())

    async def _inspect_joints_async(self) -> None:
        try:
            self._set_status("Inspect: ensuring sim play...")
            self._ensure_play()
            # Warm-up tick.
            for _ in range(60):
                await omni.kit.app.get_app().next_update_async()
            try:
                from isaacsim.core.prims import SingleArticulation
            except ImportError:
                from omni.isaac.core.prims import SingleArticulation
            from .scene_builder import HUMANOID_PRIM_PATH
            art = SingleArticulation(prim_path=HUMANOID_PRIM_PATH, name="inspect")
            art.initialize()
            names = art.dof_names or []
            stamp_status(
                stage="inspect_complete",
                dof_count=int(len(names)),
                dof_names=",".join(names),
            )
            carb.log_warn(f"[{_SOURCE}] dof_names ({len(names)}): {names}")
            self._set_status(f"Inspect: dof_count={len(names)} (Console)")
        except Exception as exc:
            carb.log_error(f"[{_SOURCE}] inspect failed: {exc}")
            self._set_status(f"Inspect failed: {exc}")

    def _on_run_pick_place(self) -> None:
        if self._pick_task is not None and not self._pick_task.done():
            self._set_status("Run: already running; press Stop first.")
            return
        spec = self._read_selected_humanoid()
        self._selected_humanoid = spec
        self._set_status(f"Run: starting ({spec.key})...")
        self._ensure_play()
        self._pick_ctrl = PickController(humanoid=spec)
        self._pick_task = omni.kit.async_engine.run_coroutine(
            self._run_pick_place_async()
        )

    async def _run_pick_place_async(self) -> None:
        try:
            result = await self._pick_ctrl.run_once()
            if result.get("ok"):
                self._set_status(
                    f"Run: cycle complete (cycles={result.get('cycles', 1)})"
                )
            else:
                self._set_status(
                    f"Run: ended ({result.get('reason', 'unknown')})"
                )
            self._cycle_label.text = (
                f"Cycles: {self._pick_ctrl.cycles_done() if self._pick_ctrl else 0}"
            )
        except Exception as exc:
            carb.log_error(f"[{_SOURCE}] run failed: {exc}")
            self._set_status(f"Run failed: {exc}")
        finally:
            self._pick_task = None

    def _on_stop(self) -> None:
        if self._pick_ctrl is not None:
            self._pick_ctrl.stop()
        self._cancel_pick_task()
        self._set_status("Stopped")

    def _on_reset_cube(self) -> None:
        try:
            stage = omni.usd.get_context().get_stage()
            reset_pick_cube(stage)
            self._set_status("Cube reset to pick table")
        except Exception as exc:
            self._set_status(f"Reset failed: {exc}")

    # ----- Helpers -----

    def _ensure_play(self) -> None:
        tl = omni.timeline.get_timeline_interface()
        if not tl.is_playing():
            tl.play()

    def _cancel_pick_task(self) -> None:
        if self._pick_task is not None and not self._pick_task.done():
            try:
                self._pick_task.cancel()
            except Exception:
                pass
        self._pick_task = None
        self._pick_ctrl = None

    def _set_status(self, text: str) -> None:
        if hasattr(self, "_status_label") and self._status_label is not None:
            self._status_label.text = f"Status: {text}"
        carb.log_info(f"[{_SOURCE}] {text}")
