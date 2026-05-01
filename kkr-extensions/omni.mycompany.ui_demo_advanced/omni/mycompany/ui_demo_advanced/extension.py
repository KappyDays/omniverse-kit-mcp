"""Phase E advanced UI demo — exercises CollapsableFrame / ComboBox /
FloatSlider / TreeView / CheckBox / ScrollingFrame / nested VStack, i.e.
the widget classes a realistic production Extension actually uses.

Phase D's `omni.mycompany.ui_demo` uses only Button + StringField + Label,
which by itself cannot prove the _WIDGET_TYPES enumeration extension. This
window is a smaller-scale stand-in for a real workbench Extension
(KKR-A-style).
"""

from __future__ import annotations

import carb
import omni.ext
import omni.ui as ui


_WINDOW_TITLE = "UI Demo Advanced"
_SOURCE = "omni.mycompany.ui_demo_advanced"


class _SimpleStringItem(ui.AbstractItem):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.model = ui.SimpleStringModel(text)


class _SimpleListModel(ui.AbstractItemModel):
    """Minimal single-column TreeView model — a list of string items."""

    def __init__(self, items: list[str]) -> None:
        super().__init__()
        self._items = [_SimpleStringItem(x) for x in items]

    def get_item_children(self, item):  # noqa: D401 — Omni signature
        if item is None:
            return self._items
        return []

    def get_item_value_model_count(self, item):
        return 1

    def get_item_value_model(self, item, column_id):
        return item.model if item is not None else None


class _SimpleListDelegate(ui.AbstractItemDelegate):
    def build_widget(self, model, item, column_id, level, expanded):
        ui.Label(item.model.as_string, name="tree_row_label")

    def build_branch(self, model, item, column_id, level, expanded):
        ui.Spacer(width=5)

    def build_header(self, column_id):
        ui.Label("Entries", name="tree_header")


class UiDemoAdvancedExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:  # noqa: D401
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._mode_index = 0
        self._gain_value = 0.5
        self._enabled = True
        self._items = ["alpha", "beta", "gamma"]
        self._status = "ready"
        self._tree_model = _SimpleListModel(self._items)
        self._tree_delegate = _SimpleListDelegate()
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
        self._window = ui.Window(_WINDOW_TITLE, width=520, height=540)
        with self._window.frame:
            with ui.VStack(spacing=6, name="root_vstack"):
                ui.Label(
                    "Phase E advanced demo — CollapsableFrame + ComboBox + Slider + TreeView.",
                    height=22, name="header_label",
                )
                ui.Separator(height=2)

                # --- Settings (CollapsableFrame + ComboBox + FloatSlider + CheckBox) ---
                with ui.CollapsableFrame("Settings", name="settings_frame"):
                    with ui.VStack(spacing=4):
                        with ui.HStack(height=28, name="mode_row"):
                            ui.Label("Mode:", width=80, name="mode_label")
                            self._mode_combo = ui.ComboBox(
                                self._mode_index, "Simple", "Advanced", "Expert",
                                name="mode_combo",
                            )
                            self._mode_combo.model.get_item_value_model().add_value_changed_fn(
                                self._on_mode_changed,
                            )

                        with ui.HStack(height=28, name="gain_row"):
                            ui.Label("Gain:", width=80, name="gain_label")
                            self._gain_slider = ui.FloatSlider(
                                min=0.0, max=1.0, name="gain_slider",
                            )
                            self._gain_slider.model.set_value(self._gain_value)
                            self._gain_slider.model.add_value_changed_fn(self._on_gain_changed)

                        with ui.HStack(height=28, name="enabled_row"):
                            ui.Label("Enabled:", width=80, name="enabled_label")
                            self._enabled_check = ui.CheckBox(name="enabled_check")
                            self._enabled_check.model.set_value(self._enabled)
                            self._enabled_check.model.add_value_changed_fn(self._on_enabled_changed)

                # --- Entries (ScrollingFrame + TreeView) ---
                with ui.CollapsableFrame("Entries", name="entries_frame"):
                    with ui.ScrollingFrame(height=140, name="entries_scroll"):
                        self._tree = ui.TreeView(
                            self._tree_model,
                            delegate=self._tree_delegate,
                            root_visible=False,
                            name="entries_tree",
                        )

                # --- Actions (Buttons) ---
                with ui.CollapsableFrame("Actions", name="actions_frame"):
                    with ui.HStack(spacing=6, height=32, name="actions_row"):
                        ui.Button("Apply", clicked_fn=self._on_apply, name="apply_button")
                        ui.Button("Reset", clicked_fn=self._on_reset, name="reset_button")

                # --- Status ---
                ui.Separator(height=2)
                self._status_label = ui.Label(
                    f"Status: {self._status}", height=22, name="status_label",
                )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_mode_changed(self, model) -> None:
        try:
            self._mode_index = int(model.get_value_as_int())
            carb.log_info(f"[{_SOURCE}] mode changed index={self._mode_index}")
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] mode change error: {exc}")

    def _on_gain_changed(self, model) -> None:
        try:
            self._gain_value = float(model.get_value_as_float())
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] gain change error: {exc}")

    def _on_enabled_changed(self, model) -> None:
        try:
            self._enabled = bool(model.get_value_as_bool())
            carb.log_info(f"[{_SOURCE}] enabled={self._enabled}")
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] enabled change error: {exc}")

    def _on_apply(self) -> None:
        self._status = f"applied mode={self._mode_index} gain={self._gain_value:.2f} enabled={self._enabled}"
        self._status_label.text = f"Status: {self._status}"
        carb.log_info(f"[{_SOURCE}] apply — {self._status}")

    def _on_reset(self) -> None:
        self._mode_index = 0
        self._gain_value = 0.5
        self._enabled = True
        self._mode_combo.model.get_item_value_model().set_value(0)
        self._gain_slider.model.set_value(self._gain_value)
        self._enabled_check.model.set_value(True)
        self._status = "reset"
        self._status_label.text = f"Status: {self._status}"
        carb.log_info(f"[{_SOURCE}] reset")
