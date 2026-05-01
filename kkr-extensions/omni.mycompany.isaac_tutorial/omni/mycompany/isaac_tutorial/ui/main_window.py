"""Main UI Window — status label + progress bar + 2 CollapsableFrame holders.

Built with omni.ui. Panels (env_setup_panel, steps_panel) later populate
the two CollapsableFrame attributes via `with window.env_setup_frame:` /
`with window.steps_frame:`.
"""
from __future__ import annotations

import omni.ui as ui


_WINDOW_TITLE = "Isaac Sim Tutorial"


class MainWindow:

    def __init__(self) -> None:
        self._window = ui.Window(_WINDOW_TITLE, width=560, height=640)
        self.status_label: ui.Label | None = None
        self.progress_frame: ui.Frame | None = None
        self.progress_bar: ui.ProgressBar | None = None
        self.progress_label: ui.Label | None = None
        self.cancel_button: ui.Button | None = None
        self.env_setup_frame: ui.CollapsableFrame | None = None
        self.steps_frame: ui.CollapsableFrame | None = None
        self.reset_all_button: ui.Button | None = None
        # job polling (Task 18)
        self._current_job_id: str | None = None
        self._cancel_cb = None
        self._polling_task = None
        self._build()

    def _build(self) -> None:
        with self._window.frame:
            with ui.VStack(spacing=6, name="root_vstack"):
                self.reset_all_button = ui.Button(
                    "Reset all (stage_new)",
                    height=28,
                    name="reset_all_button",
                    style={"background_color": 0xFF3333AA},
                )
                self.status_label = ui.Label(
                    "Status: (idle)",
                    height=22,
                    name="status_label",
                )
                ui.Separator(height=2)

                self.env_setup_frame = ui.CollapsableFrame(
                    "Environment Setup", name="env_setup_frame", collapsed=False,
                )
                self.steps_frame = ui.CollapsableFrame(
                    "Tutorial Steps", name="steps_frame", collapsed=False,
                )

                ui.Separator(height=2)
                self.progress_frame = ui.Frame(name="progress_frame", visible=False)
                with self.progress_frame:
                    with ui.HStack(spacing=6, height=28):
                        self.progress_label = ui.Label(
                            "Progress:", width=80, name="progress_label",
                        )
                        self.progress_bar = ui.ProgressBar(name="progress_bar")
                        self.cancel_button = ui.Button(
                            "Cancel", width=80, height=24, name="cancel_button",
                        )

    def set_busy(self, busy: bool, label: str = "") -> None:
        """run_with_ui_feedback interface: toggle progress frame visibility."""
        if self.progress_frame is not None:
            self.progress_frame.visible = busy
        if busy and self.progress_label is not None:
            self.progress_label.text = f"Progress: {label}"

    def start_job_polling(self, job_id: str, services, cancel_cb) -> None:
        """Called by run_with_ui_feedback when it detects `job=<id>` in result."""
        import asyncio
        self._current_job_id = job_id
        self._cancel_cb = cancel_cb
        if self.cancel_button is not None:
            self.cancel_button.set_clicked_fn(self._on_cancel)
        if self.progress_frame is not None:
            self.progress_frame.visible = True
        self._polling_task = asyncio.ensure_future(self._poll_loop(services))

    async def _poll_loop(self, services) -> None:
        import asyncio
        try:
            while True:
                await asyncio.sleep(0.5)
                # JobService.get_status is SYNC and returns a dict.
                status = services.jobs.get_status(self._current_job_id)
                progress = float(status.get("progress", 0.0))
                if self.progress_bar is not None:
                    self.progress_bar.model.set_value(progress)
                state = status.get("status", "unknown")
                if self.progress_label is not None:
                    self.progress_label.text = f"{state} ({progress:.0%})"
                if state in ("done", "error", "canceled"):
                    break
        finally:
            if self.progress_frame is not None:
                self.progress_frame.visible = False

    def _on_cancel(self) -> None:
        if getattr(self, "_cancel_cb", None) is not None and getattr(self, "_current_job_id", None):
            self._cancel_cb(self._current_job_id)

    def post_notification(self, msg: str) -> None:
        """Called by run_with_ui_feedback on error."""
        try:
            import omni.kit.notification_manager as nm
            nm.post_notification(
                msg, status=nm.NotificationStatus.WARNING, duration=8,
            )
        except Exception:  # noqa: BLE001
            pass

    def set_reset_callback(self, cb) -> None:
        """Wire top-level Reset All button to a callable `cb()` that performs reset.

        Implements 2-click confirm: first click posts a notification, second
        click within 3 seconds executes `cb`. Prevents accidental reset.
        """
        import time
        self._reset_cb = cb
        self._last_reset_click = 0.0

        def _on_click():
            import asyncio
            now = time.time()
            if now - self._last_reset_click < 3.0:
                asyncio.ensure_future(self._reset_cb())
                self._last_reset_click = 0.0
            else:
                self._last_reset_click = now
                self.post_notification(
                    "Click Reset again within 3 seconds to confirm."
                )

        if self.reset_all_button is not None:
            self.reset_all_button.set_clicked_fn(_on_click)

    def destroy(self) -> None:
        if getattr(self, "_window", None) is not None:
            self._window.destroy()
            self._window = None
