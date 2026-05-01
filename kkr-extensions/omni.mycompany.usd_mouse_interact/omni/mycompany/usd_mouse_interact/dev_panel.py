"""Operator panel -- whitelist editor + tuning sliders.

Two sections:

* **Whitelist + Descriptions** -- Add/Remove/Clear/Save buttons, scrollable
  per-prim list with inline "Edit desc" modal. The only way an operator
  curates which prims highlight on hover (without hand-editing
  customLayerData["usdMouseInteract"]).
* **Tuning** -- Speed (units/s) + Sensitivity (mouse-multiplier) IntDrag
  sliders. Updates the controller live so the operator can dial in feel.

Visible regardless of timeline state so the operator can prepare the
whitelist before pressing Play.
"""

from __future__ import annotations

import carb
import omni.usd

from . import metadata_store

_SOURCE = "omni.mycompany.usd_mouse_interact.dev_panel"

_WINDOW_TITLE = "USD Mouse Interact"


class DevPanel:

    def __init__(self, controller=None) -> None:
        self._controller = controller

        self._window = None

        # Run section widgets (set in _build_run_section)
        self._run_model = None
        self._run_status_label = None

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

        self._window = ui.Window(_WINDOW_TITLE, width=340, height=400)
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
                    ui.Label(
                        "Whitelist picker + tuning",
                        height=16,
                        name="header",
                    )
                    ui.Separator(height=1)
                    self._build_run_section()
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

    def destroy(self) -> None:
        try:
            if self._window is not None:
                self._window.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] destroy failed: {exc!r}")
        self._window = None
        self._run_model = None
        self._run_status_label = None

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
            self._run_status_label.text = text
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] set_status failed: {exc!r}")

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
            ui.Label("Run", width=80)
            self._run_model = ui.SimpleBoolModel(False)
            ui.CheckBox(self._run_model, height=20, width=20)
            self._run_model.add_value_changed_fn(self._on_run_toggled)
            # Status label — controller pushes "Active" / "Idle" via
            # set_status. Initial text matches the default armed=False
            # state set on InteractionController.
            self._run_status_label = ui.Label("Idle", height=20)

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
            model = self._color_widget.model
            children = model.get_item_children(None)
            floats: list[float] = []
            for child in children:
                v = float(model.get_item_value_model(child).as_float)
                floats.append(max(0.0, min(1.0, v)))
            # ColorWidget(r,g,b,a) yields 4 children in RGBA order.
            # Defensive: pad with opaque alpha if the build returned only RGB.
            while len(floats) < 4:
                floats.append(1.0)
            r, g, b, a = floats[:4]
            rgba = (
                (int(round(a * 255)) & 0xFF) << 24
                | (int(round(b * 255)) & 0xFF) << 16
                | (int(round(g * 255)) & 0xFF) << 8
                | (int(round(r * 255)) & 0xFF)
            )
            self._controller.set_crosshair_color(rgba)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] _on_color_changed failed: {exc!r}")
