"""Isaac Sim Tutorial Extension — all panels hooked up (Task 15)."""
from __future__ import annotations

import carb
import omni.ext
import omni.usd

from .actions.state import TutorialState, recover_state_from_stage
from .bindings.services import get_services
from .ui.env_setup_panel import EnvSetupPanel
from .ui.main_window import MainWindow
from .ui.steps_panel import StepsPanel


_SOURCE = "omni.mycompany.isaac_tutorial"


class IsaacTutorialExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._ext_id = ext_id
        self._window = MainWindow()

        ctx = omni.usd.get_context()
        stage = ctx.get_stage() if ctx is not None else None
        self._state = recover_state_from_stage(stage) if stage is not None else TutorialState()

        self._env_panel = EnvSetupPanel(
            frame=self._window.env_setup_frame,
            ui_main=self._window,
            state=self._state,
        )
        self._steps_panel = StepsPanel(
            frame=self._window.steps_frame,
            ui_main=self._window,
            state=self._state,
            services_getter=get_services,
        )

        # Task 19 — reset all callback
        async def _reset_wrapped():
            from .actions import env_actions
            from .actions.base import run_with_ui_feedback
            services = get_services()
            await run_with_ui_feedback(
                self._window,
                env_actions.reset_all(services, self._state),
                label="Reset all",
            )
            # Refresh panel labels after reset
            if hasattr(self, "_steps_panel"):
                self._steps_panel._refresh_labels()

        self._window.set_reset_callback(_reset_wrapped)

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        try:
            if getattr(self, "_window", None) is not None:
                self._window.destroy()
                self._window = None
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] destroy failed: {exc}")
