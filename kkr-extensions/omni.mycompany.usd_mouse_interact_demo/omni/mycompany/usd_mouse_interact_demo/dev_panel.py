"""Operator panel -- whitelist editor + tuning sliders.

Two sections:

* **Whitelist + Descriptions** -- Add/Remove/Clear/Save buttons, scrollable
  per-prim list with inline "Edit desc" modal. The only way an operator
  curates which prims highlight on hover (without hand-editing
  customLayerData["usdMouseInteractDemo"]).
* **Tuning** -- Speed (units/s) + Sensitivity (mouse-multiplier) IntDrag
  sliders. Updates the controller live so the operator can dial in feel.

Visible regardless of timeline state so the operator can prepare the
whitelist before pressing Play.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import replace

import carb
import omni.usd

from .config_model import (
    ButtonConfig,
    ButtonModeConfig,
    ButtonStyleConfig,
    PreviewGridConfig,
    UsdMouseInteractConfig,
    camera_set_size_for_key,
)
from .mode_state import RuntimeMode, parse_runtime_mode
from . import metadata_store

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.dev_panel"

_WINDOW_TITLE = "USD Mouse Interact Demo"
_MODE_CHOICES = (RuntimeMode.FPS, RuntimeMode.TOP_VIEW, RuntimeMode.BUTTON_MODE)
_MODE_LABELS = ("FPS", "Top View", "Buttons")
_BUTTON_KEYS = ("a", "b")
_BUTTON_ACTIONS = ("capture", "switch")
_BUTTON_ACTION_LABELS = ("Capture", "Switch")
_BUTTON_SHAPES = ("rect", "circle", "raised", "orb")
_BUTTON_SHAPE_LABELS = ("Rect", "Circle", "Raised", "Orb")
_LABEL_WIDTH = 58
_ROW_HEIGHT = 20
_FIELD_HEIGHT = 18


class DevPanel:

    def __init__(self, controller=None) -> None:
        self._controller = controller

        self._window = None

        # Run section widgets (set in _build_run_section)
        self._run_model = None
        self._run_status_label = None
        self._mode_model = None
        self._backend_status_label = None

        # Runtime config section models
        self._default_camera_model = None
        self._top_camera_model = None
        self._button_models = {}
        self._exploring_button_models = {}
        self._dream_ai_button_models = {}
        self._back_button_models = {}
        self._final_preview_back_button_models = {}
        self._camera_slot_models = {}
        self._button_style_models = {}
        self._preview_grid_models = {}
        self._preview_width_model = None
        self._preview_height_model = None
        self._capture_fallback_model = None
        self._tour_camera_hold_model = None
        self._tour_final_hold_model = None
        self._tour_matrix_hold_model = None
        self._new_button_name_model = None
        self._syncing_models = False
        self._rebuild_pending = False

        # Whitelist section widgets (set in _build_metadata_section)
        self._whitelist_status_label = None
        self._whitelist_scroll = None

        # Tuning section models (set in _build_sliders_section)
        self._speed_model = None
        self._sens_model = None

        # Crosshair section widget (set in _build_crosshair_section)
        self._color_widget = None

    def build(self) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed: {exc!r}")
            return

        if self._window is not None:
            return

        self._window = ui.Window(_WINDOW_TITLE, width=420, height=760)
        with self._window.frame:
            # Root ScrollingFrame so the panel never clips when the user
            # resizes the window smaller than the natural content height.
            # Without this, sub-sections (Tuning sliders especially) get
            # cut off and become unreachable.
            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                with ui.VStack(spacing=2, name="root_v"):
                    self._build_run_section()
                    self._build_config_section()
                    self._build_button_mode_section()
                    self._build_metadata_section()
                    self._build_sliders_section()
                    self._build_crosshair_section()
                    # Bottom spacer so the last slider has a visual margin
                    # when the user expands the window past the content size.
                    ui.Spacer(height=4)

        # Populate initial whitelist view
        try:
            allowed, descs = self._allowed_descs()
            self._refresh_whitelist_view(allowed, descs)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] initial whitelist view failed: {exc!r}")
        self._sync_config_models_from_controller()

    def destroy(self) -> None:
        try:
            if self._window is not None:
                self._window.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] destroy failed: {exc!r}")
        self._window = None
        self._run_model = None
        self._run_status_label = None
        self._mode_model = None
        self._backend_status_label = None
        self._default_camera_model = None
        self._top_camera_model = None
        self._button_models = {}
        self._exploring_button_models = {}
        self._dream_ai_button_models = {}
        self._back_button_models = {}
        self._final_preview_back_button_models = {}
        self._camera_slot_models = {}
        self._button_style_models = {}
        self._preview_grid_models = {}
        self._preview_width_model = None
        self._preview_height_model = None
        self._capture_fallback_model = None
        self._tour_camera_hold_model = None
        self._tour_final_hold_model = None
        self._tour_matrix_hold_model = None
        self._new_button_name_model = None

    # ------------------------------------------------------------------
    # Public API — controller pushes state changes here
    # ------------------------------------------------------------------

    def set_status(self, text: str) -> None:
        """Show a one-word state label next to the Run checkbox.

        Best-effort: silently no-ops when the panel hasn't been built yet
        or has been torn down (controller may push a status before / after
        the window's lifetime).
        """
        if self._run_status_label is None:
            return
        try:
            self._run_status_label.text = _paren_status(text)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] set_status failed: {exc!r}")

    def refresh_config_models(self) -> None:
        """Refresh config-editing widgets from ``controller.config``.

        Public hook for ModeCoordinator stage reloads. The private sync path
        sets _syncing_models, so value callbacks fired by model.set_value()
        do not push stale config back into the controller.
        """
        try:
            self._sync_config_models_from_controller()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] refresh_config_models failed: {exc!r}")

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _build_run_section(self) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed in _build_run_section: {exc!r}")
            return

        with ui.HStack(height=22, spacing=4):
            ui.Label("Run", width=28)
            self._run_model = ui.SimpleBoolModel(False)
            ui.CheckBox(self._run_model, height=20, width=20)
            self._run_model.add_value_changed_fn(self._on_run_toggled)
            # Status label — controller pushes "Active" / "Idle" via set_status.
            self._run_status_label = ui.Label("(Idle)", width=58, height=20)
            ui.Label("Mode", width=38)
            mode_index = self._mode_index_from_config()
            combo = ui.ComboBox(mode_index, *_MODE_LABELS, height=20)
            self._mode_model = combo.model.get_item_value_model()
            self._mode_model.add_value_changed_fn(self._on_mode_changed)
            self._backend_status_label = ui.Label("Backend: local", width=92, height=20)

    def _build_config_section(self) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed in _build_config_section: {exc!r}")
            return

        with ui.CollapsableFrame("Config", height=0):
            with ui.VStack(spacing=1):
                with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                    ui.Label("Top View", width=_LABEL_WIDTH)
                    field = ui.StringField(height=_FIELD_HEIGHT)
                    self._top_camera_model = field.model
                    self._top_camera_model.add_value_changed_fn(self._on_config_model_changed)
                    ui.Button(
                        "Selected",
                        width=62,
                        height=_FIELD_HEIGHT,
                        clicked_fn=self._on_selected_top_camera,
                    )
                with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                    ui.Label("Default Cam", width=_LABEL_WIDTH)
                    field = ui.StringField(height=_FIELD_HEIGHT)
                    self._default_camera_model = field.model
                    self._default_camera_model.add_value_changed_fn(self._on_config_model_changed)
                    ui.Button(
                        "Selected",
                        width=62,
                        height=_FIELD_HEIGHT,
                        clicked_fn=self._on_selected_default_camera,
                    )

    def _build_button_mode_section(self) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed in _build_button_mode_section: {exc!r}")
            return

        with ui.CollapsableFrame("Viewport Buttons", height=0):
            with ui.VStack(spacing=1):
                with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                    ui.Label("Preview", width=_LABEL_WIDTH)
                    self._preview_width_model = ui.SimpleIntModel(640)
                    ui.IntDrag(
                        self._preview_width_model,
                        min=64,
                        max=4096,
                        step=16,
                        height=_FIELD_HEIGHT,
                    )
                    self._preview_width_model.add_value_changed_fn(self._on_config_model_changed)
                    ui.Label("x", width=8)
                    self._preview_height_model = ui.SimpleIntModel(360)
                    ui.IntDrag(
                        self._preview_height_model,
                        min=64,
                        max=4096,
                        step=16,
                        height=_FIELD_HEIGHT,
                    )
                    self._preview_height_model.add_value_changed_fn(self._on_config_model_changed)
                self._capture_fallback_model = None
                self._build_tour_timing_row(ui)
                self._build_preview_grid_row(ui)
                self._build_viewport_style_rows(ui)
                self._build_exploring_button_config_rows(ui)
                self._build_dream_ai_button_config_rows(ui)

                with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                    ui.Label("Buttons", width=_LABEL_WIDTH)
                    ui.Label("Name", width=34)
                    name_field = ui.StringField(height=_FIELD_HEIGHT, width=ui.Fraction(1))
                    self._new_button_name_model = name_field.model
                    ui.Button(
                        "Add",
                        width=ui.Pixel(48),
                        height=_FIELD_HEIGHT,
                        clicked_fn=self._on_add_button,
                    )

                for button_key in self._button_keys_from_config():
                    self._build_button_config_rows(ui, button_key)
                self._build_final_preview_back_button_config_rows(ui)
                self._build_back_button_config_rows(ui)

    def _build_button_config_rows(self, ui, button_key: str) -> None:
        title = _button_title(button_key)
        self._button_models[button_key] = {}
        self._camera_slot_models[button_key] = []

        with ui.CollapsableFrame(f"Button {title}", height=0):
            with ui.VStack(spacing=1):
                if button_key not in _BUTTON_KEYS:
                    with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                        ui.Label("Manage", width=_LABEL_WIDTH)
                        ui.Button(
                            "Remove",
                            height=_FIELD_HEIGHT,
                            clicked_fn=lambda key=button_key: self._on_remove_button(key),
                        )
                self._build_button_label_row(ui, self._button_models[button_key])
                self._build_button_shape_row(ui, self._button_models[button_key])
                self._build_button_workflow_row(ui, self._button_models[button_key], button_key)
                self._build_geometry_row(ui, self._button_models[button_key])
                self._build_camera_slots_row(ui, title, button_key)

    def _build_back_button_config_rows(self, ui) -> None:
        self._back_button_models = {}
        with ui.CollapsableFrame("Back Button", height=0):
            with ui.VStack(spacing=1):
                self._build_button_label_row(ui, self._back_button_models)
                self._build_button_shape_row(ui, self._back_button_models)
                self._build_geometry_row(ui, self._back_button_models)

    def _build_final_preview_back_button_config_rows(self, ui) -> None:
        self._final_preview_back_button_models = {}
        with ui.CollapsableFrame("Final Preview Back Button", height=0):
            with ui.VStack(spacing=1):
                self._build_button_label_row(ui, self._final_preview_back_button_models)
                self._build_button_shape_row(ui, self._final_preview_back_button_models)
                self._build_geometry_row(ui, self._final_preview_back_button_models)

    def _build_exploring_button_config_rows(self, ui) -> None:
        self._exploring_button_models = {}
        with ui.CollapsableFrame("Start Button", height=0):
            with ui.VStack(spacing=1):
                self._build_button_label_row(ui, self._exploring_button_models)
                self._build_button_shape_row(ui, self._exploring_button_models)
                self._build_geometry_row(ui, self._exploring_button_models)

    def _build_dream_ai_button_config_rows(self, ui) -> None:
        self._dream_ai_button_models = {}
        with ui.CollapsableFrame("Dream-AI Space Button", height=0):
            with ui.VStack(spacing=1):
                self._build_button_label_row(ui, self._dream_ai_button_models)
                self._build_button_shape_row(ui, self._dream_ai_button_models)
                self._build_geometry_row(ui, self._dream_ai_button_models)

    def _build_label_row(self, ui, label: str):
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            ui.Label(label, width=_LABEL_WIDTH)
            return ui.StringField(height=_FIELD_HEIGHT)

    def _build_button_label_row(self, ui, models: dict) -> None:
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            ui.Label("Label", width=_LABEL_WIDTH)
            label_field = ui.StringField(height=_FIELD_HEIGHT, width=ui.Fraction(2))
            models["label"] = label_field.model
            label_field.model.add_value_changed_fn(self._on_config_model_changed)
            ui.Label("Color", width=34)
            color_widget = ui.ColorWidget(
                0.23,
                0.29,
                0.37,
                0.93,
                height=_FIELD_HEIGHT,
                width=ui.Fraction(1),
            )
            models["color_widget"] = color_widget
            color_widget.model.add_end_edit_fn(
                lambda model, item: self._on_config_model_changed(model, item)
            )
            ui.Label("Text", width=28)
            text_color_widget = ui.ColorWidget(
                1.0,
                1.0,
                1.0,
                1.0,
                height=_FIELD_HEIGHT,
                width=ui.Fraction(1),
            )
            models["text_color_widget"] = text_color_widget
            text_color_widget.model.add_end_edit_fn(
                lambda model, item: self._on_config_model_changed(model, item)
            )
            ui.Label("Font", width=28)
            font_model = ui.SimpleIntModel(0)
            models["font_size"] = font_model
            ui.IntDrag(
                font_model,
                min=0,
                max=96,
                step=1,
                height=_FIELD_HEIGHT,
                width=ui.Fraction(1),
            )
            font_model.add_value_changed_fn(self._on_config_model_changed)

    def _build_button_shape_row(self, ui, models: dict) -> None:
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            ui.Label("Shape", width=_LABEL_WIDTH)
            combo = ui.ComboBox(0, *_BUTTON_SHAPE_LABELS, height=_FIELD_HEIGHT, width=96)
            shape_model = combo.model.get_item_value_model()
            models["shape"] = shape_model
            shape_model.add_value_changed_fn(self._on_config_model_changed)
            ui.Spacer(width=ui.Fraction(1))

    def _build_geometry_row(self, ui, models: dict) -> None:
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            ui.Label("Rect %", width=_LABEL_WIDTH)
            for field_key, label, min_value in (
                ("x_pct", "X", 0),
                ("y_pct", "Y", 0),
                ("w_pct", "W", 1),
                ("h_pct", "H", 1),
            ):
                ui.Label(label, width=12)
                model = ui.SimpleIntModel(min_value)
                models[field_key] = model
                ui.IntDrag(
                    model,
                    min=min_value,
                    max=100,
                    step=1,
                    height=_FIELD_HEIGHT,
                    width=ui.Fraction(1),
                )
                model.add_value_changed_fn(self._on_config_model_changed)

    def _build_button_workflow_row(self, ui, models: dict, button_key: str) -> None:
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            ui.Label("Flow", width=_LABEL_WIDTH)
            ui.Label("Set", width=18)
            set_field = ui.StringField(height=_FIELD_HEIGHT, width=ui.Fraction(1))
            models["set_id"] = set_field.model
            set_field.model.add_value_changed_fn(self._on_config_model_changed)
            combo = ui.ComboBox(0, *_BUTTON_ACTION_LABELS, height=_FIELD_HEIGHT, width=78)
            action_model = combo.model.get_item_value_model()
            models["action"] = action_model
            action_model.add_value_changed_fn(self._on_config_model_changed)
            ui.Label("Cam", width=26)
            target_field = ui.StringField(height=_FIELD_HEIGHT, width=ui.Fraction(1))
            models["target_camera"] = target_field.model
            target_field.model.add_value_changed_fn(self._on_config_model_changed)
            ui.Button(
                "S",
                width=18,
                height=_FIELD_HEIGHT,
                clicked_fn=lambda key=button_key: self._on_selected_target_camera(key),
            )
            ui.Label("Next", width=28)
            next_field = ui.StringField(height=_FIELD_HEIGHT, width=ui.Fraction(1))
            models["next_set"] = next_field.model
            next_field.model.add_value_changed_fn(self._on_config_model_changed)

    def _build_camera_slots_row(self, ui, title: str, button_key: str) -> None:
        camera_count = camera_set_size_for_key(button_key)
        for row in range(2):
            with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                ui.Label("Cameras" if row == 0 else "", width=_LABEL_WIDTH)
                for offset in range(3):
                    index = row * 3 + offset
                    if index >= camera_count:
                        ui.Spacer(width=ui.Fraction(1))
                        continue
                    ui.Label(f"{title}{index + 1}", width=18)
                    field = ui.StringField(height=_FIELD_HEIGHT, width=ui.Fraction(1))
                    self._camera_slot_models[button_key].append(field.model)
                    field.model.add_value_changed_fn(self._on_config_model_changed)
                    ui.Button(
                        str(index + 1),
                        width=18,
                        height=_FIELD_HEIGHT,
                        clicked_fn=lambda k=button_key, i=index: (
                            self._on_selected_camera_slot(k, i)
                        ),
                    )

    def _build_tour_timing_row(self, ui) -> None:
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            ui.Label("Tour Sec", width=_LABEL_WIDTH)
            for attr_name, label, default in (
                ("_tour_camera_hold_model", "Each", 1.5),
                ("_tour_final_hold_model", "Final", 1.5),
                ("_tour_matrix_hold_model", "Grid", 6),
            ):
                ui.Label(label, width=34)
                model = ui.SimpleFloatModel(default)
                setattr(self, attr_name, model)
                ui.FloatDrag(
                    model,
                    min=0.1,
                    max=120,
                    step=0.1,
                    height=_FIELD_HEIGHT,
                    width=ui.Fraction(1),
                )
                model.add_value_changed_fn(self._on_config_model_changed)

    def _build_preview_grid_row(self, ui) -> None:
        self._preview_grid_models = {}
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            ui.Label("Grid %", width=_LABEL_WIDTH)
            for key, label in (("center_x_pct", "X"), ("center_y_pct", "Y")):
                ui.Label(label, width=12)
                model = ui.SimpleIntModel(50)
                self._preview_grid_models[key] = model
                ui.IntDrag(model, min=0, max=100, step=1, height=_FIELD_HEIGHT)
                model.add_value_changed_fn(self._on_config_model_changed)
            ui.Label("Scale", width=38)
            scale_model = ui.SimpleIntModel(100)
            self._preview_grid_models["scale_pct"] = scale_model
            ui.IntDrag(
                scale_model,
                min=50,
                max=200,
                step=1,
                height=_FIELD_HEIGHT,
            )
            scale_model.add_value_changed_fn(self._on_config_model_changed)

    def _build_viewport_style_rows(self, ui) -> None:
        self._button_style_models = {}
        with ui.CollapsableFrame("Viewport UI Style", height=0):
            with ui.VStack(spacing=1):
                self._build_style_color_triplet_row(
                    ui,
                    (
                        ("button_color", "Button"),
                        ("hover_color", "Hover"),
                        ("text_color", "Text"),
                    ),
                )
                self._build_style_color_triplet_row(
                    ui,
                    (
                        ("panel_color", "Panel"),
                        ("overlay_color", "Overlay"),
                        ("tile_border_color", "Border"),
                    ),
                )
                with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                    ui.Label("Shape", width=_LABEL_WIDTH)
                    ui.Label("Dim", width=26)
                    dim_model = ui.SimpleBoolModel(True)
                    self._button_style_models["dim_overlay"] = dim_model
                    ui.CheckBox(dim_model, height=_FIELD_HEIGHT, width=20)
                    dim_model.add_value_changed_fn(self._on_config_model_changed)
                    ui.Label("Radius", width=42)
                    radius_model = ui.SimpleIntModel(3)
                    self._button_style_models["border_radius"] = radius_model
                    ui.IntDrag(radius_model, min=0, max=24, step=1, height=_FIELD_HEIGHT)
                    radius_model.add_value_changed_fn(self._on_config_model_changed)
                    ui.Label("Font", width=28)
                    font_model = ui.SimpleIntModel(12)
                    self._button_style_models["font_size"] = font_model
                    ui.IntDrag(font_model, min=8, max=32, step=1, height=_FIELD_HEIGHT)
                    font_model.add_value_changed_fn(self._on_config_model_changed)
                with ui.HStack(height=_ROW_HEIGHT, spacing=3):
                    ui.Label("Preview", width=_LABEL_WIDTH)
                    ui.Label("Dim %", width=44)
                    preview_dim_model = ui.SimpleIntModel(80)
                    self._button_style_models["preview_dim_opacity"] = preview_dim_model
                    ui.IntDrag(
                        preview_dim_model,
                        min=0,
                        max=100,
                        step=1,
                        height=_FIELD_HEIGHT,
                    )
                    preview_dim_model.add_value_changed_fn(self._on_config_model_changed)

    def _build_style_color_triplet_row(self, ui, entries: tuple[tuple[str, str], ...]) -> None:
        with ui.HStack(height=_ROW_HEIGHT, spacing=3):
            for key, label in entries:
                ui.Label(label, width=44)
                color_widget = ui.ColorWidget(
                    0.23,
                    0.29,
                    0.37,
                    1.0,
                    height=_FIELD_HEIGHT,
                    width=ui.Fraction(1),
                )
                self._button_style_models[f"{key}_widget"] = color_widget
                color_widget.model.add_end_edit_fn(
                    lambda model, item: self._on_config_model_changed(model, item)
                )

    def _build_metadata_section(self) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed in _build_metadata_section: {exc!r}")
            return

        with ui.CollapsableFrame("Whitelist + Descriptions", height=0):
            with ui.VStack(spacing=2):
                with ui.HStack(height=20, spacing=2):
                    ui.Button("Add", clicked_fn=self._on_add_selected)
                    ui.Button("Remove", clicked_fn=self._on_remove_selected)
                    ui.Button("Clear", clicked_fn=self._on_clear_all)
                    ui.Button("Save", clicked_fn=self._on_save_to_stage)
                self._whitelist_status_label = ui.Label("(loading...)", height=14)
                # Inner scroll for the whitelist row list. Capped at 140 px
                # so the Tuning section below stays in view at the default
                # window height; the outer (root) ScrollingFrame handles
                # smaller-window cases.
                self._whitelist_scroll = ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    height=140,
                )

    def _build_sliders_section(self) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed in _build_sliders_section: {exc!r}")
            return

        if self._controller is None:
            return

        with ui.CollapsableFrame("Tuning", height=0):
            with ui.VStack(spacing=2):
                with ui.HStack(height=20, spacing=4):
                    ui.Label("Speed", width=80)
                    self._speed_model = ui.SimpleIntModel(self._controller.speed)
                    ui.IntDrag(self._speed_model, min=50, max=5000, step=10, height=20)
                    self._speed_model.add_value_changed_fn(self._on_speed_changed)
                with ui.HStack(height=20, spacing=4):
                    ui.Label("Sensitivity", width=80)
                    self._sens_model = ui.SimpleIntModel(self._controller.sensitivity)
                    ui.IntDrag(self._sens_model, min=1, max=100, step=1, height=20)
                    self._sens_model.add_value_changed_fn(self._on_sens_changed)

    def _build_crosshair_section(self) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed in _build_crosshair_section: {exc!r}")
            return

        if self._controller is None:
            return

        # ABGR int → RGBA floats for ColorWidget initial values.
        # omni.ui uses ABGR packing in the "background_color" style and the
        # ColorWidget child models read back r,g,b[,a] in that order.
        c = int(self._controller.crosshair_color)
        a = ((c >> 24) & 0xFF) / 255.0
        b = ((c >> 16) & 0xFF) / 255.0
        g = ((c >> 8) & 0xFF) / 255.0
        r = (c & 0xFF) / 255.0

        with ui.CollapsableFrame("Crosshair", height=0):
            with ui.VStack(spacing=2):
                with ui.HStack(height=20, spacing=4):
                    ui.Label("Color", width=80)
                    # 4-arg form gives RGBA. add_end_edit_fn fires once when
                    # the user releases the picker, so we don't spam the
                    # controller while dragging.
                    self._color_widget = ui.ColorWidget(r, g, b, a, height=20)
                    self._color_widget.model.add_end_edit_fn(
                        lambda model, item: self._on_color_changed()
                    )

    # ------------------------------------------------------------------
    # Runtime config model helpers
    # ------------------------------------------------------------------

    def _mode_index_from_config(self) -> int:
        cfg = self._current_config()
        mode = parse_runtime_mode(cfg.runtime.default_mode)
        return _MODE_CHOICES.index(mode)

    def _sync_config_models_from_controller(self) -> None:
        cfg = self._current_config()
        self._syncing_models = True
        try:
            self._set_model_value(
                self._mode_model,
                _MODE_CHOICES.index(parse_runtime_mode(cfg.runtime.default_mode)),
            )
            self._set_model_value(
                self._default_camera_model,
                cfg.runtime.default_camera_path,
            )
            self._set_model_value(self._top_camera_model, cfg.top_view.camera_path)
            self._set_model_value(
                self._preview_width_model,
                int(cfg.button_mode.preview_width),
            )
            self._set_model_value(
                self._preview_height_model,
                int(cfg.button_mode.preview_height),
            )
            self._set_model_value(
                self._capture_fallback_model,
                bool(cfg.button_mode.use_viewport_capture_fallback),
            )
            self._set_model_value(
                self._tour_camera_hold_model,
                float(cfg.button_mode.tour_camera_hold_seconds),
            )
            self._set_model_value(
                self._tour_final_hold_model,
                float(cfg.button_mode.tour_final_hold_seconds),
            )
            self._set_model_value(
                self._tour_matrix_hold_model,
                float(cfg.button_mode.tour_matrix_hold_seconds),
            )
            for button_key in self._button_keys_from_config(cfg):
                button = cfg.button_mode.buttons.get(button_key)
                if button is None:
                    button = _default_button_for_key(button_key)
                button_models = self._button_models.get(button_key, {})
                self._set_model_value(button_models.get("label"), button.label)
                self._set_model_value(button_models.get("x_pct"), round(button.x_pct * 100))
                self._set_model_value(button_models.get("y_pct"), round(button.y_pct * 100))
                self._set_model_value(button_models.get("w_pct"), round(button.w_pct * 100))
                self._set_model_value(button_models.get("h_pct"), round(button.h_pct * 100))
                self._sync_color_models(button_models, button.color, "color")
                self._sync_color_models(button_models, button.text_color, "text_color")
                self._set_model_value(button_models.get("font_size"), int(button.font_size))
                self._set_model_value(button_models.get("shape"), _shape_index(button.shape))
                self._set_model_value(button_models.get("set_id"), button.set_id)
                self._set_model_value(
                    button_models.get("action"),
                    _action_index(button.action),
                )
                self._set_model_value(button_models.get("target_camera"), button.target_camera)
                self._set_model_value(button_models.get("next_set"), button.next_set)

                camera_count = camera_set_size_for_key(button_key)
                paths = list(cfg.button_mode.camera_sets.get(button_key, []))[:camera_count]
                while len(paths) < camera_count:
                    paths.append("")
                for index, model in enumerate(self._camera_slot_models.get(button_key, [])):
                    self._set_model_value(model, paths[index])
            exploring_button = cfg.button_mode.exploring_button
            self._set_model_value(
                self._exploring_button_models.get("label"),
                exploring_button.label,
            )
            self._set_model_value(
                self._exploring_button_models.get("x_pct"),
                round(exploring_button.x_pct * 100),
            )
            self._set_model_value(
                self._exploring_button_models.get("y_pct"),
                round(exploring_button.y_pct * 100),
            )
            self._set_model_value(
                self._exploring_button_models.get("w_pct"),
                round(exploring_button.w_pct * 100),
            )
            self._set_model_value(
                self._exploring_button_models.get("h_pct"),
                round(exploring_button.h_pct * 100),
            )
            self._sync_color_models(
                self._exploring_button_models,
                exploring_button.color,
                "color",
            )
            self._sync_color_models(
                self._exploring_button_models,
                exploring_button.text_color,
                "text_color",
            )
            self._set_model_value(
                self._exploring_button_models.get("font_size"),
                int(exploring_button.font_size),
            )
            self._set_model_value(
                self._exploring_button_models.get("shape"),
                _shape_index(exploring_button.shape),
            )
            dream_ai_button = cfg.button_mode.dream_ai_button
            self._set_model_value(
                self._dream_ai_button_models.get("label"),
                dream_ai_button.label,
            )
            self._set_model_value(
                self._dream_ai_button_models.get("x_pct"),
                round(dream_ai_button.x_pct * 100),
            )
            self._set_model_value(
                self._dream_ai_button_models.get("y_pct"),
                round(dream_ai_button.y_pct * 100),
            )
            self._set_model_value(
                self._dream_ai_button_models.get("w_pct"),
                round(dream_ai_button.w_pct * 100),
            )
            self._set_model_value(
                self._dream_ai_button_models.get("h_pct"),
                round(dream_ai_button.h_pct * 100),
            )
            self._sync_color_models(
                self._dream_ai_button_models,
                dream_ai_button.color,
                "color",
            )
            self._sync_color_models(
                self._dream_ai_button_models,
                dream_ai_button.text_color,
                "text_color",
            )
            self._set_model_value(
                self._dream_ai_button_models.get("font_size"),
                int(dream_ai_button.font_size),
            )
            self._set_model_value(
                self._dream_ai_button_models.get("shape"),
                _shape_index(dream_ai_button.shape),
            )
            back_button = cfg.button_mode.back_button
            self._set_model_value(
                self._back_button_models.get("label"),
                back_button.label,
            )
            self._set_model_value(
                self._back_button_models.get("x_pct"),
                round(back_button.x_pct * 100),
            )
            self._set_model_value(
                self._back_button_models.get("y_pct"),
                round(back_button.y_pct * 100),
            )
            self._set_model_value(
                self._back_button_models.get("w_pct"),
                round(back_button.w_pct * 100),
            )
            self._set_model_value(
                self._back_button_models.get("h_pct"),
                round(back_button.h_pct * 100),
            )
            self._sync_color_models(self._back_button_models, back_button.color, "color")
            self._sync_color_models(
                self._back_button_models,
                back_button.text_color,
                "text_color",
            )
            self._set_model_value(
                self._back_button_models.get("font_size"),
                int(back_button.font_size),
            )
            self._set_model_value(
                self._back_button_models.get("shape"),
                _shape_index(back_button.shape),
            )
            final_preview_back_button = cfg.button_mode.final_preview_back_button
            self._set_model_value(
                self._final_preview_back_button_models.get("label"),
                final_preview_back_button.label,
            )
            self._set_model_value(
                self._final_preview_back_button_models.get("x_pct"),
                round(final_preview_back_button.x_pct * 100),
            )
            self._set_model_value(
                self._final_preview_back_button_models.get("y_pct"),
                round(final_preview_back_button.y_pct * 100),
            )
            self._set_model_value(
                self._final_preview_back_button_models.get("w_pct"),
                round(final_preview_back_button.w_pct * 100),
            )
            self._set_model_value(
                self._final_preview_back_button_models.get("h_pct"),
                round(final_preview_back_button.h_pct * 100),
            )
            self._sync_color_models(
                self._final_preview_back_button_models,
                final_preview_back_button.color,
                "color",
            )
            self._sync_color_models(
                self._final_preview_back_button_models,
                final_preview_back_button.text_color,
                "text_color",
            )
            self._set_model_value(
                self._final_preview_back_button_models.get("font_size"),
                int(final_preview_back_button.font_size),
            )
            self._set_model_value(
                self._final_preview_back_button_models.get("shape"),
                _shape_index(final_preview_back_button.shape),
            )
            style = cfg.button_mode.button_style
            for key in (
                "button_color",
                "hover_color",
                "text_color",
                "panel_color",
                "overlay_color",
                "tile_border_color",
            ):
                self._sync_color_models(
                    self._button_style_models,
                    int(getattr(style, key)),
                    key,
                )
            self._set_model_value(
                self._button_style_models.get("dim_overlay"),
                bool(style.dim_overlay),
            )
            self._set_model_value(
                self._button_style_models.get("preview_dim_opacity"),
                int(round(float(style.preview_dim_opacity) * 100)),
            )
            self._set_model_value(
                self._button_style_models.get("border_radius"),
                int(style.border_radius),
            )
            self._set_model_value(
                self._button_style_models.get("font_size"),
                int(style.font_size),
            )
            self._set_model_value(
                self._preview_grid_models.get("center_x_pct"),
                round(cfg.button_mode.preview_grid.center_x_pct * 100),
            )
            self._set_model_value(
                self._preview_grid_models.get("center_y_pct"),
                round(cfg.button_mode.preview_grid.center_y_pct * 100),
            )
            self._set_model_value(
                self._preview_grid_models.get("scale_pct"),
                round(cfg.button_mode.preview_overlay_scale * 100),
            )
        finally:
            self._syncing_models = False

    def _on_config_model_changed(self, *_args) -> None:
        if self._syncing_models:
            return
        self._push_config_from_models()

    def _on_selected_top_camera(self) -> None:
        path = self._selected_prim_path()
        if not path or self._top_camera_model is None:
            return
        was_syncing = self._syncing_models
        self._syncing_models = True
        try:
            self._set_model_value(self._top_camera_model, path)
        finally:
            self._syncing_models = was_syncing
        self._push_config_from_models()

    def _on_selected_default_camera(self) -> None:
        path = self._selected_prim_path()
        if not path or self._default_camera_model is None:
            return
        was_syncing = self._syncing_models
        self._syncing_models = True
        try:
            self._set_model_value(self._default_camera_model, path)
        finally:
            self._syncing_models = was_syncing
        self._push_config_from_models()

    def _on_selected_camera_slot(self, button_key: str, index: int) -> None:
        path = self._selected_prim_path()
        models = self._camera_slot_models.get(button_key, [])
        if not path or index < 0 or index >= len(models):
            return
        was_syncing = self._syncing_models
        self._syncing_models = True
        try:
            self._set_model_value(models[index], path)
        finally:
            self._syncing_models = was_syncing
        self._push_config_from_models()

    def _on_selected_target_camera(self, button_key: str) -> None:
        path = self._selected_prim_path()
        models = self._button_models.get(button_key, {})
        model = models.get("target_camera")
        if not path or model is None:
            return
        was_syncing = self._syncing_models
        self._syncing_models = True
        try:
            self._set_model_value(model, path)
        finally:
            self._syncing_models = was_syncing
        self._push_config_from_models()

    def _on_add_button(self) -> None:
        self._push_config_from_models()
        cfg = self._current_config()
        requested_name = self._model_string(self._new_button_name_model, "").strip()
        button_key = _button_key_for_new_name(requested_name, cfg.button_mode.buttons)
        button_label = requested_name or _default_button_label(button_key)
        buttons = dict(cfg.button_mode.buttons)
        camera_sets = {
            key: list(paths)
            for key, paths in cfg.button_mode.camera_sets.items()
        }
        buttons[button_key] = _default_button_for_key(button_key, label=button_label)
        camera_sets[button_key] = [""] * camera_set_size_for_key(button_key)
        self._set_model_value(self._new_button_name_model, "")
        self._apply_button_list_change(cfg, buttons, camera_sets)

    def _on_remove_button(self, button_key: str) -> None:
        if button_key in _BUTTON_KEYS:
            return
        self._push_config_from_models()
        cfg = self._current_config()
        buttons = dict(cfg.button_mode.buttons)
        camera_sets = {
            key: list(paths)
            for key, paths in cfg.button_mode.camera_sets.items()
        }
        buttons.pop(button_key, None)
        camera_sets.pop(button_key, None)
        self._apply_button_list_change(cfg, buttons, camera_sets)

    def _apply_button_list_change(
        self,
        cfg: UsdMouseInteractConfig,
        buttons: dict[str, ButtonConfig],
        camera_sets: dict[str, list[str]],
    ) -> None:
        apply_config = getattr(self._controller, "apply_config", None)
        if self._controller is None or not callable(apply_config):
            return
        next_config = replace(
            cfg,
            button_mode=replace(
                cfg.button_mode,
                buttons=buttons,
                camera_sets=camera_sets,
            ),
        )
        try:
            apply_config(next_config)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] button list apply failed: {exc!r}")
            return
        self._request_rebuild_window()

    def _request_rebuild_window(self) -> None:
        if self._rebuild_pending:
            return
        self._rebuild_pending = True
        expected_window = self._window
        try:
            asyncio.ensure_future(self._rebuild_window_on_next_update(expected_window))
        except Exception as exc:  # noqa: BLE001
            self._rebuild_pending = False
            carb.log_info(f"[{_SOURCE}] dev panel rebuild schedule failed: {exc!r}")

    async def _rebuild_window_on_next_update(self, expected_window) -> None:
        try:
            import omni.kit.app  # type: ignore[import-not-found] # noqa: WPS433

            await omni.kit.app.get_app().next_update_async()
            if self._window is not expected_window:
                return
            self._rebuild_window_now()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] dev panel deferred rebuild failed: {exc!r}")
        finally:
            self._rebuild_pending = False

    def _rebuild_window_now(self) -> None:
        try:
            self.destroy()
            self.build()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] dev panel rebuild failed: {exc!r}")

    def _on_mode_changed(self, model) -> None:
        if self._syncing_models:
            return
        mode = self._mode_from_model(model)
        if self._controller is not None:
            set_mode = getattr(self._controller, "set_mode", None)
            if callable(set_mode):
                try:
                    set_mode(mode)
                except Exception as exc:  # noqa: BLE001
                    carb.log_info(f"[{_SOURCE}] set_mode failed: {exc!r}")
        self._push_config_from_models(mode)

    def _push_config_from_models(self, mode: RuntimeMode | None = None) -> None:
        apply_config = getattr(self._controller, "apply_config", None)
        if self._controller is None or not callable(apply_config):
            return

        try:
            cfg = self._current_config()
            selected_mode = mode or self._mode_from_model(self._mode_model)
            runtime = replace(
                cfg.runtime,
                default_mode=selected_mode.value,
                default_camera_path=self._model_string(
                    self._default_camera_model,
                    cfg.runtime.default_camera_path,
                ),
            )
            top_view = replace(
                cfg.top_view,
                camera_path=self._model_string(self._top_camera_model, cfg.top_view.camera_path),
            )

            buttons = dict(cfg.button_mode.buttons)
            for button_key in self._button_keys_from_config(cfg):
                current = buttons.get(button_key, _default_button_for_key(button_key))
                models = self._button_models.get(button_key, {})
                buttons[button_key] = ButtonConfig(
                    label=self._model_string(models.get("label"), current.label),
                    x_pct=self._percent_model_float(models.get("x_pct"), current.x_pct, 0),
                    y_pct=self._percent_model_float(models.get("y_pct"), current.y_pct, 0),
                    w_pct=self._percent_model_float(models.get("w_pct"), current.w_pct, 1),
                    h_pct=self._percent_model_float(models.get("h_pct"), current.h_pct, 1),
                    color=self._color_from_models(models, "color", current.color),
                    text_color=self._color_from_models(
                        models,
                        "text_color",
                        current.text_color,
                    ),
                    font_size=self._clamped_model_int(
                        models.get("font_size"),
                        current.font_size,
                        0,
                        96,
                    ),
                    shape=_shape_from_model(models.get("shape"), current.shape),
                    set_id=self._model_string(models.get("set_id"), current.set_id) or "main",
                    action=_action_from_model(models.get("action"), current.action),
                    target_camera=self._model_string(
                        models.get("target_camera"),
                        current.target_camera,
                    ),
                    next_set=self._model_string(models.get("next_set"), current.next_set),
                )

            camera_sets = {
                key: list(paths)
                for key, paths in cfg.button_mode.camera_sets.items()
            }
            for button_key in self._button_keys_from_config(cfg):
                camera_count = camera_set_size_for_key(button_key)
                existing = list(
                    camera_sets.get(button_key, [""] * camera_count)
                )[:camera_count]
                while len(existing) < camera_count:
                    existing.append("")
                models = self._camera_slot_models.get(button_key, [])
                camera_sets[button_key] = [
                    self._model_string(models[index], existing[index])
                    if index < len(models)
                    else existing[index]
                    for index in range(camera_count)
                ]

            button_mode = ButtonModeConfig(
                buttons=buttons,
                camera_sets=camera_sets,
                exploring_button=ButtonConfig(
                    label=self._model_string(
                        self._exploring_button_models.get("label"),
                        cfg.button_mode.exploring_button.label,
                    ),
                    x_pct=self._percent_model_float(
                        self._exploring_button_models.get("x_pct"),
                        cfg.button_mode.exploring_button.x_pct,
                        0,
                    ),
                    y_pct=self._percent_model_float(
                        self._exploring_button_models.get("y_pct"),
                        cfg.button_mode.exploring_button.y_pct,
                        0,
                    ),
                    w_pct=self._percent_model_float(
                        self._exploring_button_models.get("w_pct"),
                        cfg.button_mode.exploring_button.w_pct,
                        1,
                    ),
                    h_pct=self._percent_model_float(
                        self._exploring_button_models.get("h_pct"),
                        cfg.button_mode.exploring_button.h_pct,
                        1,
                    ),
                    color=self._color_from_models(
                        self._exploring_button_models,
                        "color",
                        cfg.button_mode.exploring_button.color,
                    ),
                    text_color=self._color_from_models(
                        self._exploring_button_models,
                        "text_color",
                        cfg.button_mode.exploring_button.text_color,
                    ),
                    font_size=self._clamped_model_int(
                        self._exploring_button_models.get("font_size"),
                        cfg.button_mode.exploring_button.font_size,
                        0,
                        96,
                    ),
                    shape=_shape_from_model(
                        self._exploring_button_models.get("shape"),
                        cfg.button_mode.exploring_button.shape,
                    ),
                ),
                dream_ai_button=ButtonConfig(
                    label=self._model_string(
                        self._dream_ai_button_models.get("label"),
                        cfg.button_mode.dream_ai_button.label,
                    ),
                    x_pct=self._percent_model_float(
                        self._dream_ai_button_models.get("x_pct"),
                        cfg.button_mode.dream_ai_button.x_pct,
                        0,
                    ),
                    y_pct=self._percent_model_float(
                        self._dream_ai_button_models.get("y_pct"),
                        cfg.button_mode.dream_ai_button.y_pct,
                        0,
                    ),
                    w_pct=self._percent_model_float(
                        self._dream_ai_button_models.get("w_pct"),
                        cfg.button_mode.dream_ai_button.w_pct,
                        1,
                    ),
                    h_pct=self._percent_model_float(
                        self._dream_ai_button_models.get("h_pct"),
                        cfg.button_mode.dream_ai_button.h_pct,
                        1,
                    ),
                    color=self._color_from_models(
                        self._dream_ai_button_models,
                        "color",
                        cfg.button_mode.dream_ai_button.color,
                    ),
                    text_color=self._color_from_models(
                        self._dream_ai_button_models,
                        "text_color",
                        cfg.button_mode.dream_ai_button.text_color,
                    ),
                    font_size=self._clamped_model_int(
                        self._dream_ai_button_models.get("font_size"),
                        cfg.button_mode.dream_ai_button.font_size,
                        0,
                        96,
                    ),
                    shape=_shape_from_model(
                        self._dream_ai_button_models.get("shape"),
                        cfg.button_mode.dream_ai_button.shape,
                    ),
                ),
                back_button=ButtonConfig(
                    label=self._model_string(
                        self._back_button_models.get("label"),
                        cfg.button_mode.back_button.label,
                    ),
                    x_pct=self._percent_model_float(
                        self._back_button_models.get("x_pct"),
                        cfg.button_mode.back_button.x_pct,
                        0,
                    ),
                    y_pct=self._percent_model_float(
                        self._back_button_models.get("y_pct"),
                        cfg.button_mode.back_button.y_pct,
                        0,
                    ),
                    w_pct=self._percent_model_float(
                        self._back_button_models.get("w_pct"),
                        cfg.button_mode.back_button.w_pct,
                        1,
                    ),
                    h_pct=self._percent_model_float(
                        self._back_button_models.get("h_pct"),
                        cfg.button_mode.back_button.h_pct,
                        1,
                    ),
                    color=self._color_from_models(
                        self._back_button_models,
                        "color",
                        cfg.button_mode.back_button.color,
                    ),
                    text_color=self._color_from_models(
                        self._back_button_models,
                        "text_color",
                        cfg.button_mode.back_button.text_color,
                    ),
                    font_size=self._clamped_model_int(
                        self._back_button_models.get("font_size"),
                        cfg.button_mode.back_button.font_size,
                        0,
                        96,
                    ),
                    shape=_shape_from_model(
                        self._back_button_models.get("shape"),
                        cfg.button_mode.back_button.shape,
                    ),
                ),
                final_preview_back_button=ButtonConfig(
                    label=self._model_string(
                        self._final_preview_back_button_models.get("label"),
                        cfg.button_mode.final_preview_back_button.label,
                    ),
                    x_pct=self._percent_model_float(
                        self._final_preview_back_button_models.get("x_pct"),
                        cfg.button_mode.final_preview_back_button.x_pct,
                        0,
                    ),
                    y_pct=self._percent_model_float(
                        self._final_preview_back_button_models.get("y_pct"),
                        cfg.button_mode.final_preview_back_button.y_pct,
                        0,
                    ),
                    w_pct=self._percent_model_float(
                        self._final_preview_back_button_models.get("w_pct"),
                        cfg.button_mode.final_preview_back_button.w_pct,
                        1,
                    ),
                    h_pct=self._percent_model_float(
                        self._final_preview_back_button_models.get("h_pct"),
                        cfg.button_mode.final_preview_back_button.h_pct,
                        1,
                    ),
                    color=self._color_from_models(
                        self._final_preview_back_button_models,
                        "color",
                        cfg.button_mode.final_preview_back_button.color,
                    ),
                    text_color=self._color_from_models(
                        self._final_preview_back_button_models,
                        "text_color",
                        cfg.button_mode.final_preview_back_button.text_color,
                    ),
                    font_size=self._clamped_model_int(
                        self._final_preview_back_button_models.get("font_size"),
                        cfg.button_mode.final_preview_back_button.font_size,
                        0,
                        96,
                    ),
                    shape=_shape_from_model(
                        self._final_preview_back_button_models.get("shape"),
                        cfg.button_mode.final_preview_back_button.shape,
                    ),
                ),
                button_style=self._button_style_from_models(cfg.button_mode.button_style),
                preview_grid=PreviewGridConfig(
                    center_x_pct=self._percent_model_float(
                        self._preview_grid_models.get("center_x_pct"),
                        cfg.button_mode.preview_grid.center_x_pct,
                        0,
                    ),
                    center_y_pct=self._percent_model_float(
                        self._preview_grid_models.get("center_y_pct"),
                        cfg.button_mode.preview_grid.center_y_pct,
                        0,
                    ),
                ),
                preview_overlay_scale=float(
                    self._clamped_model_int(
                        self._preview_grid_models.get("scale_pct"),
                        int(round(cfg.button_mode.preview_overlay_scale * 100)),
                        50,
                        200,
                    )
                )
                / 100.0,
                preview_width=self._clamped_model_int(
                    self._preview_width_model,
                    cfg.button_mode.preview_width,
                    64,
                    4096,
                ),
                preview_height=self._clamped_model_int(
                    self._preview_height_model,
                    cfg.button_mode.preview_height,
                    64,
                    4096,
                ),
                use_viewport_capture_fallback=False,
                tour_camera_hold_seconds=float(
                    self._clamped_model_float(
                        self._tour_camera_hold_model,
                        cfg.button_mode.tour_camera_hold_seconds,
                        0.1,
                        120.0,
                    )
                ),
                tour_final_hold_seconds=float(
                    self._clamped_model_float(
                        self._tour_final_hold_model,
                        cfg.button_mode.tour_final_hold_seconds,
                        0.1,
                        120.0,
                    )
                ),
                tour_matrix_hold_seconds=float(
                    self._clamped_model_float(
                        self._tour_matrix_hold_model,
                        cfg.button_mode.tour_matrix_hold_seconds,
                        0.1,
                        120.0,
                    )
                ),
            )
            apply_config(
                UsdMouseInteractConfig(
                    runtime=runtime,
                    top_view=top_view,
                    button_mode=button_mode,
                )
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] config apply failed: {exc!r}")

    def _save_runtime_config(self) -> None:
        if self._controller is None:
            return
        save_config = getattr(self._controller, "save_config", None)
        if not callable(save_config):
            return
        try:
            save_config()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] save_config failed: {exc!r}")

    def _current_config(self) -> UsdMouseInteractConfig:
        cfg = getattr(self._controller, "config", None)
        if isinstance(cfg, UsdMouseInteractConfig):
            return cfg
        return UsdMouseInteractConfig.default()

    def _button_keys_from_config(
        self,
        cfg: UsdMouseInteractConfig | None = None,
    ) -> list[str]:
        config = cfg if cfg is not None else self._current_config()
        return _ordered_button_keys(config.button_mode.buttons)

    def _selected_prim_path(self) -> str:
        try:
            paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] selection read failed: {exc!r}")
            return ""
        if not paths:
            return ""
        return str(paths[0])

    def _mode_from_model(self, model) -> RuntimeMode:
        index = self._clamped_model_int(model, self._mode_index_from_config(), 0, len(_MODE_CHOICES) - 1)
        return _MODE_CHOICES[index]

    def _set_model_value(self, model, value) -> None:
        if model is None:
            return
        try:
            model.set_value(value)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] model set failed: {exc!r}")

    def _model_string(self, model, default: str) -> str:
        if model is None:
            return str(default)
        try:
            if hasattr(model, "as_string"):
                return str(model.as_string)
            if hasattr(model, "get_value_as_string"):
                return str(model.get_value_as_string())
        except Exception:
            return str(default)
        return str(default)

    def _model_bool(self, model, default: bool) -> bool:
        if model is None:
            return bool(default)
        try:
            if hasattr(model, "as_bool"):
                return bool(model.as_bool)
            if hasattr(model, "get_value_as_bool"):
                return bool(model.get_value_as_bool())
        except Exception:
            return bool(default)
        return bool(default)

    def _clamped_model_int(self, model, default: int, minimum: int, maximum: int) -> int:
        if model is None:
            value = int(default)
        else:
            try:
                if hasattr(model, "as_int"):
                    value = int(model.as_int)
                elif hasattr(model, "get_value_as_int"):
                    value = int(model.get_value_as_int())
                else:
                    value = int(default)
            except Exception:
                value = int(default)
        return max(minimum, min(maximum, value))

    def _clamped_model_float(
        self,
        model,
        default: float,
        minimum: float,
        maximum: float,
    ) -> float:
        if model is None:
            value = float(default)
        else:
            try:
                if hasattr(model, "as_float"):
                    value = float(model.as_float)
                elif hasattr(model, "get_value_as_float"):
                    value = float(model.get_value_as_float())
                elif hasattr(model, "as_int"):
                    value = float(model.as_int)
                else:
                    value = float(default)
            except Exception:
                value = float(default)
        return max(float(minimum), min(float(maximum), value))

    def _percent_model_float(self, model, default: float, minimum_int: int) -> float:
        default_int = int(round(default * 100))
        return self._clamped_model_int(model, default_int, minimum_int, 100) / 100.0

    def _sync_color_models(self, models: dict, color: int, key: str) -> None:
        widget = models.get("color_widget" if key == "color" else f"{key}_widget")
        _set_color_widget_value(widget, color)

    def _color_from_models(self, models: dict, key: str, default: int) -> int:
        widget = models.get("color_widget" if key == "color" else f"{key}_widget")
        return _color_from_widget(widget, default)

    def _button_style_from_models(self, default: ButtonStyleConfig) -> ButtonStyleConfig:
        models = self._button_style_models
        return ButtonStyleConfig(
            button_color=self._color_from_models(models, "button_color", default.button_color),
            hover_color=self._color_from_models(models, "hover_color", default.hover_color),
            text_color=self._color_from_models(models, "text_color", default.text_color),
            panel_color=self._color_from_models(models, "panel_color", default.panel_color),
            overlay_color=self._color_from_models(models, "overlay_color", default.overlay_color),
            dim_overlay=self._model_bool(models.get("dim_overlay"), default.dim_overlay),
            preview_dim_opacity=self._clamped_model_int(
                models.get("preview_dim_opacity"),
                int(round(float(default.preview_dim_opacity) * 100)),
                0,
                100,
            )
            / 100.0,
            tile_border_color=self._color_from_models(
                models,
                "tile_border_color",
                default.tile_border_color,
            ),
            border_radius=self._clamped_model_int(
                models.get("border_radius"),
                default.border_radius,
                0,
                24,
            ),
            font_size=self._clamped_model_int(models.get("font_size"), default.font_size, 8, 32),
        )

    # ------------------------------------------------------------------
    # Whitelist callbacks
    # ------------------------------------------------------------------

    def _allowed_descs(self) -> tuple[set[str], dict[str, str]]:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return set(), {}
        return metadata_store.load_from_stage(stage)

    def _persist(self, allowed: set[str], descs: dict[str, str]) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        metadata_store.save_to_stage(stage, allowed, descs)
        if self._controller is not None:
            try:
                self._controller.reload_metadata()
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] reload_metadata failed: {exc!r}")
        self._refresh_whitelist_view(allowed, descs)

    def _on_add_selected(self) -> None:
        try:
            sel = omni.usd.get_context().get_selection().get_selected_prim_paths()
            allowed, descs = self._allowed_descs()
            for p in sel:
                allowed.add(p)
            self._persist(allowed, descs)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] _on_add_selected failed: {exc!r}")

    def _on_remove_selected(self) -> None:
        try:
            sel = set(omni.usd.get_context().get_selection().get_selected_prim_paths())
            allowed, descs = self._allowed_descs()
            allowed -= sel
            descs = {k: v for k, v in descs.items() if k not in sel}
            self._persist(allowed, descs)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] _on_remove_selected failed: {exc!r}")

    def _on_clear_all(self) -> None:
        try:
            self._persist(set(), {})
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] _on_clear_all failed: {exc!r}")

    def _on_save_to_stage(self) -> None:
        self._push_config_from_models()
        self._save_runtime_config()
        try:
            allowed, descs = self._allowed_descs()
            self._persist(allowed, descs)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] _on_save_to_stage failed: {exc!r}")

    def _refresh_whitelist_view(self, allowed: set[str], descs: dict[str, str]) -> None:
        if self._whitelist_status_label is None or self._whitelist_scroll is None:
            return
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] omni.ui import failed in _refresh_whitelist_view: {exc!r}")
            return
        try:
            self._whitelist_status_label.text = f"{len(allowed)} prim(s) -- {len(descs)} described"
            # Clear before rebuild -- opening ScrollingFrame as context appends rather than replaces.
            try:
                self._whitelist_scroll.clear()
            except Exception:  # noqa: BLE001
                pass
            with self._whitelist_scroll:
                with ui.VStack(spacing=1):
                    if not allowed:
                        ui.Label("(empty -- select prims, then Add)", height=14)
                        return
                    for path in sorted(allowed):
                        desc = descs.get(path, "")
                        short_desc = (desc[:24] + "...") if len(desc) > 24 else desc or "(none)"
                        # Edit button is fixed width; the two Fraction labels
                        # share the remainder. Order matters in omni.ui --
                        # Fraction widgets are laid out first, fixed-width
                        # children are guaranteed their pixel allocation, so
                        # we keep Fraction(2)+Fraction(3) for path/desc.
                        with ui.HStack(height=18, spacing=2):
                            ui.Label(path, width=ui.Fraction(3), elided_text=True)
                            ui.Label(short_desc, width=ui.Fraction(2), elided_text=True)
                            ui.Button(
                                "Edit",
                                width=ui.Pixel(40),
                                height=ui.Pixel(16),
                                clicked_fn=lambda p=path: self._on_edit_desc(p),
                            )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] _refresh_whitelist_view failed: {exc!r}")

    def _on_edit_desc(self, path: str) -> None:
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed in _on_edit_desc: {exc!r}")
            return
        try:
            win = ui.Window(f"Edit description -- {path}", width=380, height=180)
            allowed, descs = self._allowed_descs()
            current = descs.get(path, "")

            with win.frame:
                with ui.VStack(spacing=2):
                    ui.Label(path, height=16)
                    field = ui.StringField(multiline=True, height=110)
                    field.model.set_value(current)
                    with ui.HStack(height=20, spacing=4):
                        ui.Button("OK", clicked_fn=lambda: self._save_desc(win, path, field))
                        ui.Button("Cancel", clicked_fn=win.destroy)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] _on_edit_desc failed: {exc!r}")

    def _save_desc(self, win, path: str, field) -> None:
        try:
            new_text = field.model.as_string
            allowed, descs = self._allowed_descs()
            if new_text:
                descs[path] = new_text
            else:
                descs.pop(path, None)
            self._persist(allowed, descs)
            win.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] _save_desc failed: {exc!r}")

    # ------------------------------------------------------------------
    # Run callback
    # ------------------------------------------------------------------

    def _on_run_toggled(self, model) -> None:
        if self._controller is None:
            return
        try:
            self._controller.set_armed(bool(model.as_bool))
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] _on_run_toggled failed: {exc!r}")

    # ------------------------------------------------------------------
    # Tuning callbacks
    # ------------------------------------------------------------------

    def _on_speed_changed(self, model) -> None:
        if self._controller is not None:
            try:
                self._controller.speed = int(model.as_int)
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] _on_speed_changed failed: {exc!r}")

    def _on_sens_changed(self, model) -> None:
        if self._controller is not None:
            try:
                self._controller.sensitivity = int(model.as_int)
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] _on_sens_changed failed: {exc!r}")

    # ------------------------------------------------------------------
    # Crosshair callback
    # ------------------------------------------------------------------

    def _on_color_changed(self) -> None:
        if self._controller is None or self._color_widget is None:
            return
        try:
            self._controller.set_crosshair_color(
                _color_from_widget(self._color_widget, self._controller.crosshair_color)
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] _on_color_changed failed: {exc!r}")


def _paren_status(text: str) -> str:
    value = str(text).strip()
    if not value:
        return "()"
    if value.startswith("(") and value.endswith(")"):
        return value
    return f"({value})"


def _ordered_button_keys(buttons: dict[str, object]) -> list[str]:
    preferred = [key for key in _BUTTON_KEYS if key in buttons]
    extra = sorted(key for key in buttons if key not in set(_BUTTON_KEYS))
    return preferred + extra


def _next_button_key(buttons: dict[str, object]) -> str:
    index = 1
    while True:
        key = f"button_{index}"
        if key not in buttons:
            return key
        index += 1


def _button_key_for_new_name(raw_name: str, buttons: dict[str, object]) -> str:
    text = str(raw_name).strip()
    if not text:
        return _next_button_key(buttons)

    slug = re.sub(r"[^0-9A-Za-z_]+", "_", text.strip().lower()).strip("_")
    if not slug:
        return _next_button_key(buttons)
    if slug in set(_BUTTON_KEYS):
        slug = f"button_{slug}"
    if slug not in buttons:
        return slug

    index = 2
    while True:
        key = f"{slug}_{index}"
        if key not in buttons:
            return key
        index += 1


def _default_button_label(button_key: str) -> str:
    if str(button_key).startswith("button_"):
        suffix = str(button_key).rsplit("_", 1)[-1]
        if suffix.isdigit():
            return suffix
    return _button_title(button_key)


def _button_title(button_key: str) -> str:
    if button_key in _BUTTON_KEYS:
        return button_key.upper()
    return button_key.replace("_", " ").title()


def _default_button_for_key(button_key: str, label: str | None = None) -> ButtonConfig:
    if button_key == "a":
        return UsdMouseInteractConfig.default().button_mode.buttons["a"]
    if button_key == "b":
        return UsdMouseInteractConfig.default().button_mode.buttons["b"]
    try:
        index = int(str(button_key).rsplit("_", 1)[-1])
    except Exception:
        index = 1
    x_pct = min(0.82, 0.08 + max(0, index - 1) * 0.12)
    y_pct = max(0.05, 0.74 - max(0, index - 1) * 0.06)
    return ButtonConfig(label or _default_button_label(button_key), x_pct, y_pct, 0.10, 0.045)


def _action_index(action: str) -> int:
    try:
        return _BUTTON_ACTIONS.index(str(action).strip().lower())
    except ValueError:
        return 0


def _action_from_model(model, default: str) -> str:
    index = 0
    if model is not None:
        try:
            if hasattr(model, "as_int"):
                index = int(model.as_int)
            elif hasattr(model, "get_value_as_int"):
                index = int(model.get_value_as_int())
        except Exception:
            index = 0
    if 0 <= index < len(_BUTTON_ACTIONS):
        return _BUTTON_ACTIONS[index]
    default_action = str(default).strip().lower()
    return default_action if default_action in _BUTTON_ACTIONS else "capture"


def _shape_index(shape: str) -> int:
    try:
        return _BUTTON_SHAPES.index(str(shape).strip().lower())
    except ValueError:
        return 0


def _shape_from_model(model, default: str) -> str:
    index = 0
    if model is not None:
        try:
            if hasattr(model, "as_int"):
                index = int(model.as_int)
            elif hasattr(model, "get_value_as_int"):
                index = int(model.get_value_as_int())
        except Exception:
            index = 0
    if 0 <= index < len(_BUTTON_SHAPES):
        return _BUTTON_SHAPES[index]
    default_shape = str(default).strip().lower()
    return default_shape if default_shape in _BUTTON_SHAPES else "rect"


def _set_color_widget_value(widget, color: int) -> None:
    if widget is None:
        return
    try:
        model = widget.model
        children = model.get_item_children(None)
        r, g, b, a = _rgba_floats_from_abgr(color)
        for child, value in zip(children, (r, g, b, a)):
            model.get_item_value_model(child).set_value(value)
    except Exception as exc:  # noqa: BLE001
        carb.log_info(f"[{_SOURCE}] color widget set failed: {exc!r}")


def _color_from_widget(widget, default: int) -> int:
    if widget is None:
        return int(default)
    try:
        model = widget.model
        children = model.get_item_children(None)
        floats: list[float] = []
        for child in children:
            value = float(model.get_item_value_model(child).as_float)
            floats.append(max(0.0, min(1.0, value)))
        while len(floats) < 4:
            floats.append(1.0)
        r, g, b, a = floats[:4]
        return _abgr_from_rgba_floats(r, g, b, a)
    except Exception:
        return int(default)


def _rgba_floats_from_abgr(color: int) -> tuple[float, float, float, float]:
    value = int(color)
    r = (value & 0xFF) / 255.0
    g = ((value >> 8) & 0xFF) / 255.0
    b = ((value >> 16) & 0xFF) / 255.0
    a = ((value >> 24) & 0xFF) / 255.0
    return r, g, b, a


def _abgr_from_rgba_floats(r: float, g: float, b: float, a: float) -> int:
    return (
        (int(round(a * 255)) & 0xFF) << 24
        | (int(round(b * 255)) & 0xFF) << 16
        | (int(round(g * 255)) & 0xFF) << 8
        | (int(round(r * 255)) & 0xFF)
    )
