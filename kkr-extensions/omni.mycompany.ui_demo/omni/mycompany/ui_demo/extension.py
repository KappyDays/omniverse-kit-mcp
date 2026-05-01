"""Phase D — tiny omni.ui.Window with a button, string field, and label.

Live-test target for extension_get_ui_tree / extension_ui_invoke /
extension_capture_logs. Emits carb.log_info on every interaction so the
ring-buffer capture has something concrete to match on.
"""

from __future__ import annotations

import carb
import omni.ext
import omni.ui as ui


_WINDOW_TITLE = "UI Demo"
_SOURCE = "omni.mycompany.ui_demo"


class UiDemoExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:  # noqa: D401
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._click_count = 0
        self._last_typed = ""
        self._build_window()

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        try:
            if getattr(self, "_window", None) is not None:
                self._window.destroy()
                self._window = None
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] destroy failed: {exc}")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        self._window = ui.Window(_WINDOW_TITLE, width=420, height=320)
        with self._window.frame:
            with ui.VStack(spacing=8, name="root_vstack"):
                ui.Label(
                    "Phase D UI Demo — click the button or type text.",
                    height=22,
                    name="header_label",
                )
                ui.Separator(height=2)
                self._counter_label = ui.Label(
                    "Clicked 0 times", height=28, name="counter_label",
                )
                ui.Button(
                    "Trigger",
                    clicked_fn=self._on_trigger,
                    height=32,
                    name="trigger_button",
                )
                ui.Label("Type something:", height=20, name="type_prompt")
                self._string_field = ui.StringField(height=26, name="input_field")
                self._echo_label = ui.Label(
                    "Echo: (empty)", height=24, name="echo_label",
                )
                ui.Button(
                    "Read field",
                    clicked_fn=self._on_read,
                    height=28,
                    name="read_button",
                )

    def _on_trigger(self) -> None:
        self._click_count += 1
        self._counter_label.text = f"Clicked {self._click_count} times"
        carb.log_info(f"[{_SOURCE}] trigger clicked ({self._click_count})")

    def _on_read(self) -> None:
        try:
            txt = self._string_field.model.get_value_as_string()
        except Exception as exc:  # noqa: BLE001
            txt = f"<read-error: {exc}>"
        self._last_typed = txt
        self._echo_label.text = f"Echo: {txt!r}"
        carb.log_info(f"[{_SOURCE}] read field value={txt!r}")
