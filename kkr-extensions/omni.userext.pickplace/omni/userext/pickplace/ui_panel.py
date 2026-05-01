"""omni.ui Window for the Pick-and-Place Workshop."""
from __future__ import annotations

import carb


_SOURCE = "omni.userext.pickplace"

WINDOW_NAME = "Pick & Place Workshop"


class WorkshopPanel:
    """omni.ui window with control buttons + status label."""

    def __init__(self, callbacks: dict):
        self._callbacks = callbacks
        self._window = None
        self._status_label = None
        self._metrics_label = None
        self._build()

    def _build(self) -> None:
        import omni.ui as ui

        # Always create a fresh Window. We do not reuse `ui.Workspace.get_window`
        # because in Kit 107 it returns a lightweight WindowHandle which does
        # NOT expose `.frame`. The omni.ui runtime tolerates duplicate-name
        # creation (the new instance replaces the old in the workspace).
        self._window = ui.Window(WINDOW_NAME, width=320, height=480)

        try:
            self._window.visible = True
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] could not set visible: {exc!r}")

        with self._window.frame:
            with ui.VStack(spacing=4):
                ui.Label("Pick & Place Workshop", height=24)
                ui.Spacer(height=4)

                with ui.VStack(spacing=4):
                    ui.Button(
                        "1. Build Scene",
                        height=32,
                        clicked_fn=lambda: self._safe_call("build_scene"),
                    )
                    ui.Button(
                        "2. Start Simulation",
                        height=32,
                        clicked_fn=lambda: self._safe_call("start"),
                    )
                    ui.Button(
                        "3. Pause",
                        height=32,
                        clicked_fn=lambda: self._safe_call("pause"),
                    )
                    ui.Button(
                        "4. Reset",
                        height=32,
                        clicked_fn=lambda: self._safe_call("reset"),
                    )
                    ui.Spacer(height=4)
                    ui.Button(
                        "Spawn Cube Now",
                        height=28,
                        clicked_fn=lambda: self._safe_call("spawn_cube"),
                    )
                    ui.Button(
                        "Dump State (JSON)",
                        height=28,
                        clicked_fn=lambda: self._safe_call("dump_state"),
                    )

                ui.Spacer(height=8)
                ui.Label("Metrics", height=20)
                self._metrics_label = ui.Label(
                    "Spawned: 0 | Box A: 0 | Box B: 0 | Rate: 0 %",
                    height=20,
                    word_wrap=True,
                )

                ui.Spacer(height=8)
                ui.Label("Status", height=20)
                self._status_label = ui.Label("idle", height=120, word_wrap=True)

    def _safe_call(self, key: str) -> None:
        cb = self._callbacks.get(key)
        if cb is None:
            carb.log_warn(f"[{_SOURCE}] no callback for '{key}'")
            return
        try:
            cb()
        except Exception as exc:
            carb.log_error(f"[{_SOURCE}] {key} callback raised: {exc!r}")

    def set_status(self, text: str) -> None:
        if self._status_label is not None:
            try:
                self._status_label.text = text
            except Exception:
                pass

    def update_metrics(
        self, spawned: int, in_a: int, in_b: int, rate: float
    ) -> None:
        """Refresh the metric label — Task 6 throughput / arrival counters."""
        if self._metrics_label is None:
            return
        try:
            self._metrics_label.text = (
                f"Spawned: {spawned} | Box A: {in_a} | Box B: {in_b} | "
                f"Rate: {rate:.0f} %"
            )
        except Exception:
            pass

    def destroy(self) -> None:
        if self._window is not None:
            try:
                self._window.visible = False
                self._window.destroy()
            except Exception:
                pass
            self._window = None
