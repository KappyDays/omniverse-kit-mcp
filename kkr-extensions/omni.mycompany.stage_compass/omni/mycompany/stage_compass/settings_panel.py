"""Stage Compass settings window.

Lives separate from the HUD so the HUD stays compact. Houses prim-type
filter checkboxes, the waypoint list (rename/delete/jump), a colour
legend, and quick stage stats. Exposes ``mark_dirty`` so external code
(e.g. stage event subscriptions) can request a re-render.
"""
from __future__ import annotations

from typing import Callable, Optional

import carb
import omni.kit.app
import omni.kit.async_engine
import omni.ui as ui

from .stage_scanner import StageScanner, color_for_type
from .waypoint_store import Waypoint, WaypointStore


PANEL_TITLE = "Stage Compass — Settings"

# Types we expose as filter chips. Order is intentional for the legend.
LEGEND_TYPES: tuple[tuple[str, str], ...] = (
    ("Mesh",          "Geometry"),
    ("Cube",          "Primitive"),
    ("PointInstancer","Instancer"),
    ("Camera",        "Camera"),
    ("DistantLight",  "Distant Light"),
    ("DomeLight",     "Dome Light"),
    ("RectLight",     "Rect Light"),
    ("SphereLight",   "Sphere Light"),
    ("DiskLight",     "Disk Light"),
    ("Xform",         "Xform"),
    ("SkelRoot",      "Skel Root"),
    ("NavMeshVolume", "NavMesh Volume"),
)


class CompassSettingsPanel:

    def __init__(
        self,
        scanner: StageScanner,
        waypoints: WaypointStore,
        teleport_cb: Callable[[float, float], bool],
        on_filter_changed: Callable[[Optional[set[str]]], None],
        on_pin_current: Callable[[Optional[str]], bool],
        on_rescan: Callable[[], None],
    ) -> None:
        self._scanner = scanner
        self._waypoints = waypoints
        self._teleport_cb = teleport_cb
        self._on_filter_changed = on_filter_changed
        self._on_pin_current = on_pin_current
        self._on_rescan = on_rescan
        self._window: Optional[ui.Window] = None
        self._waypoints_container: Optional[ui.VStack] = None
        self._stats_label: Optional[ui.Label] = None
        self._filter_checks: dict[str, ui.CheckBox] = {}
        self._waypoint_name_field: Optional[ui.StringField] = None
        self._refresh_pending = False

    # ------------------------------------------------------------------
    def build(self) -> ui.Window:
        try:
            existing = ui.Workspace.get_window(PANEL_TITLE)
            if existing is not None:
                existing.visible = False
                existing.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_compass] panel sweep: {exc}")
        self._window = ui.Window(PANEL_TITLE, width=360, height=520)
        with self._window.frame:
            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                with ui.VStack(spacing=4, height=0):
                    self._build_filter_section()
                    self._build_waypoint_section()
                    self._build_stats_section()
                    self._build_actions_section()
        self._refresh_waypoint_rows()
        self._refresh_stats()
        return self._window

    def destroy(self) -> None:
        if self._window is not None:
            try:
                self._window.visible = False
                self._window.destroy()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[stage_compass] panel destroy: {exc}")
            self._window = None

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------
    def _build_filter_section(self) -> None:
        with ui.CollapsableFrame("Prim Filter", collapsed=False, name="frame_filter"):
            with ui.VStack(spacing=2, height=0):
                ui.Label(
                    "Toggle which prim types show up on the radar.",
                    style={"font_size": 11, "color": 0xC0A0A0A0},
                )
                with ui.HStack(height=20, spacing=4):
                    ui.Button("Show All", width=70, clicked_fn=self._show_all_filters)
                    ui.Button("Hide All", width=70, clicked_fn=self._hide_all_filters)
                    ui.Button("Geometry Only", width=110, clicked_fn=self._geometry_only)
                # Two-column legend.
                rows = (len(LEGEND_TYPES) + 1) // 2
                for r in range(rows):
                    with ui.HStack(height=22, spacing=8):
                        for c in range(2):
                            idx = r + c * rows
                            if idx >= len(LEGEND_TYPES):
                                ui.Spacer(width=170)
                                continue
                            type_name, pretty = LEGEND_TYPES[idx]
                            with ui.HStack(width=170, height=22, spacing=6):
                                # Coloured swatch
                                ui.Rectangle(
                                    width=12, height=12,
                                    style={
                                        "background_color": color_for_type(type_name),
                                        "border_radius": 6,
                                    },
                                )
                                cb = ui.CheckBox(width=18)
                                cb.model.set_value(True)
                                cb.model.add_value_changed_fn(
                                    lambda _m, _t=type_name: self._notify_filter_change()
                                )
                                self._filter_checks[type_name] = cb
                                ui.Label(
                                    pretty,
                                    style={"font_size": 11, "color": 0xFFE0E0E0},
                                )

    def _show_all_filters(self) -> None:
        for cb in self._filter_checks.values():
            cb.model.set_value(True)
        self._notify_filter_change()

    def _hide_all_filters(self) -> None:
        for cb in self._filter_checks.values():
            cb.model.set_value(False)
        self._notify_filter_change()

    def _geometry_only(self) -> None:
        geometry = {"Mesh", "Cube", "Sphere", "Cylinder", "Cone", "Plane",
                    "PointInstancer", "BasisCurves"}
        for t, cb in self._filter_checks.items():
            cb.model.set_value(t in geometry)
        self._notify_filter_change()

    def _notify_filter_change(self) -> None:
        active: set[str] = {
            t for t, cb in self._filter_checks.items()
            if bool(cb.model.get_value_as_bool())
        }
        # If the user unchecked everything, treat as "show all" so the
        # radar isn't useless.
        self._on_filter_changed(active if active else None)

    # ------------------------------------------------------------------
    # Waypoints
    # ------------------------------------------------------------------
    def _build_waypoint_section(self) -> None:
        with ui.CollapsableFrame("Waypoints", collapsed=False, name="frame_waypoints"):
            with ui.VStack(spacing=4, height=0):
                with ui.HStack(height=24, spacing=4):
                    ui.Label("Name:", width=40)
                    self._waypoint_name_field = ui.StringField()
                    self._waypoint_name_field.model.set_value("Spot")
                    ui.Button(
                        "Pin Camera Here",
                        width=130,
                        tooltip="Save the active camera's floor location.",
                        clicked_fn=self._on_pin_clicked,
                    )
                with ui.HStack(height=24, spacing=4):
                    ui.Button(
                        "Clear All",
                        width=80,
                        tooltip="Remove every waypoint from this stage.",
                        clicked_fn=self._on_clear_all,
                    )
                    ui.Spacer(width=4)
                    ui.Button(
                        "Refresh List",
                        width=110,
                        tooltip="Reload waypoint rows from stage customData.",
                        clicked_fn=self._refresh_waypoint_rows,
                    )
                self._waypoints_container = ui.VStack(spacing=2, height=0)
                with self._waypoints_container:
                    ui.Label("(no waypoints)")

    def _on_pin_clicked(self) -> None:
        name = "Spot"
        if self._waypoint_name_field is not None:
            try:
                name = (
                    self._waypoint_name_field.model.get_value_as_string()
                    or "Spot"
                )
            except Exception:
                pass
        ok = self._on_pin_current(name)
        if ok:
            self._refresh_waypoint_rows()

    def _on_clear_all(self) -> None:
        self._waypoints.clear()
        self._refresh_waypoint_rows()

    def _refresh_waypoint_rows(self) -> None:
        # Defer container clear out of any active draw event.
        if self._refresh_pending:
            return
        self._refresh_pending = True

        async def _deferred():
            app = omni.kit.app.get_app()
            await app.next_update_async()
            self._refresh_pending = False
            self._do_refresh_waypoint_rows()

        omni.kit.async_engine.run_coroutine(_deferred())

    def _do_refresh_waypoint_rows(self) -> None:
        if self._waypoints_container is None:
            return
        self._waypoints_container.clear()
        with self._waypoints_container:
            wps = self._waypoints.list()
            if not wps:
                ui.Label(
                    "(no waypoints — click Pin Camera Here)",
                    style={"color": 0x80A0A0A0},
                )
                return
            for wp in wps:
                self._build_waypoint_row(wp)

    def _build_waypoint_row(self, wp: Waypoint) -> None:
        with ui.HStack(height=24, spacing=4):
            ui.Rectangle(
                width=12, height=12,
                style={
                    "background_color": wp.color_argb,
                    "border_radius": 3,
                    "border_width": 1,
                    "border_color": 0xFFFFFFFF,
                },
            )
            ui.Label(
                f"{wp.name}",
                width=110,
                style={"color": 0xFFE0E0E0},
            )
            ui.Label(
                f"{wp.floor_a:+6.1f}, {wp.floor_b:+6.1f}",
                width=110,
                style={"color": 0x80A0A0A0, "font_size": 10},
            )
            ui.Button(
                "Go",
                width=32,
                tooltip="Teleport the camera to this waypoint.",
                clicked_fn=lambda wp=wp: self._teleport_cb(wp.floor_a, wp.floor_b),
            )
            ui.Button(
                "X",
                width=24,
                tooltip="Delete this waypoint.",
                clicked_fn=lambda wp=wp: self._delete_waypoint(wp.name),
            )

    def _delete_waypoint(self, name: str) -> None:
        self._waypoints.remove(name)
        self._refresh_waypoint_rows()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def _build_stats_section(self) -> None:
        with ui.CollapsableFrame("Stage Stats", collapsed=False, name="frame_stats"):
            with ui.VStack(spacing=2, height=0):
                self._stats_label = ui.Label(
                    "(loading…)",
                    style={"color": 0xFFD0D0E0, "font_size": 11},
                )

    def _refresh_stats(self) -> None:
        if self._stats_label is None:
            return
        markers = self._scanner.get_markers()
        type_counts: dict[str, int] = {}
        for m in markers:
            type_counts[m.type_name] = type_counts.get(m.type_name, 0) + 1
        if not type_counts:
            self._stats_label.text = "Empty stage."
            return
        # Show top N types by count.
        items = sorted(type_counts.items(), key=lambda kv: -kv[1])[:10]
        ext = self._scanner.world_extents
        size_a = max(0.0, ext[2] - ext[0])
        size_b = max(0.0, ext[3] - ext[1])
        lines = [
            f"Total tracked prims: {len(markers)}",
            f"Stage extent: {size_a:.1f} × {size_b:.1f} m  (up-axis: {self._scanner.up_axis})",
            "",
        ]
        for tp, count in items:
            lines.append(f"  • {tp:<20s} {count}")
        self._stats_label.text = "\n".join(lines)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _build_actions_section(self) -> None:
        with ui.CollapsableFrame("Actions", collapsed=True, name="frame_actions"):
            with ui.VStack(spacing=4, height=0):
                ui.Button(
                    "Rescan Stage",
                    tooltip="Force a fresh prim scan (e.g. after editing).",
                    clicked_fn=self._on_rescan_clicked,
                    height=26,
                )
                ui.Button(
                    "Refresh Stats",
                    clicked_fn=self._refresh_stats,
                    height=26,
                )

    def _on_rescan_clicked(self) -> None:
        self._on_rescan()
        self._refresh_stats()

    # ------------------------------------------------------------------
    # External hooks
    # ------------------------------------------------------------------
    def mark_stage_changed(self) -> None:
        self._refresh_waypoint_rows()
        self._refresh_stats()
