"""CompassHUD — the floating radar widget.

Renders a top-down disc with concentric rings, prim dots, waypoint flags,
and a centred camera marker. The radar is heading-rotated: the camera's
forward direction always points to the top of the disc, so reading the
disc is "where I'm looking is up". World-fixed compass labels (N/E/S/W)
ride around the rim and rotate with the user's heading so they always
point to the corresponding world direction.

Drawing strategy: ``Frame.set_build_fn`` registers a closure that
constructs the entire radar tree using ``omni.ui`` shapes inside a
``ZStack`` with absolute ``Placer`` offsets. ``rebuild()`` re-invokes the
closure — called from the extension update tick at ~10 Hz so the
readout keeps up with viewport tumble without thrashing the UI thread.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

import carb
import omni.ui as ui

from .camera_helper import RadarProjection
from .stage_scanner import CameraPose, PrimMarker, StageScanner, color_for_type
from .waypoint_store import Waypoint, WaypointStore


HUD_TITLE = "Stage Compass"
DEFAULT_SIZE = 280
MIN_WORLD_RADIUS = 1.0
MAX_WORLD_RADIUS = 500.0


class CompassHUD:

    BG_COLOR = 0xE0181820
    BG_BORDER = 0xFF505068
    RING_COLOR = 0x40A0A0A0
    TICK_COLOR = 0xC0E0E0E0
    CAM_DOT_COLOR = 0xFF40FFC0
    CAM_HEADING_COLOR = 0xC040FFC0
    LABEL_COLOR = 0xFFE0E0E0
    SECTOR_COLOR = 0x3040FFC0

    def __init__(
        self,
        scanner: StageScanner,
        waypoints: WaypointStore,
        teleport_cb: Callable[[float, float], bool],
    ) -> None:
        self._scanner = scanner
        self._waypoints = waypoints
        self._teleport_cb = teleport_cb
        self._size = DEFAULT_SIZE
        self._world_radius = 30.0
        self._cam_pose: Optional[CameraPose] = None
        self._window: Optional[ui.Window] = None
        self._frame: Optional[ui.Frame] = None
        self._coord_label: Optional[ui.Label] = None
        self._scale_label: Optional[ui.Label] = None
        self._heading_label: Optional[ui.Label] = None
        self._save_waypoint_cb: Optional[Callable[[], None]] = None
        self._show_waypoint_dialog: Optional[Callable[[float, float, float], None]] = None
        self._allowed_types: Optional[set[str]] = None

    # ------------------------------------------------------------------
    # External hooks
    # ------------------------------------------------------------------
    def set_save_waypoint_callback(self, fn: Callable[[], None]) -> None:
        self._save_waypoint_cb = fn

    def set_world_radius(self, r: float) -> None:
        self._world_radius = max(MIN_WORLD_RADIUS, min(MAX_WORLD_RADIUS, r))
        if self._scale_label is not None:
            self._scale_label.text = f"Range: {self._world_radius:.0f} m  (wheel to zoom)"
        self._safe_rebuild()

    def world_radius(self) -> float:
        return self._world_radius

    def set_allowed_types(self, types: Optional[set[str]]) -> None:
        self._allowed_types = types
        self._safe_rebuild()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self) -> ui.Window:
        try:
            existing = ui.Workspace.get_window(HUD_TITLE)
            if existing is not None:
                existing.visible = False
                existing.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_compass] zombie sweep failed: {exc}")
        flags = (
            ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_COLLAPSE
        )
        self._window = ui.Window(
            HUD_TITLE,
            width=self._size + 24,
            height=self._size + 130,
            flags=flags,
            dockPreference=ui.DockPreference.RIGHT_TOP,
        )
        with self._window.frame:
            with ui.VStack(spacing=4, height=0):
                with ui.HStack(height=18, spacing=8):
                    self._coord_label = ui.Label(
                        "X --  Y --  Z --",
                        style={"color": self.LABEL_COLOR, "font_size": 12},
                    )
                with ui.HStack(height=18, spacing=8):
                    self._heading_label = ui.Label(
                        "Heading --°    Hover prim type below for legend.",
                        style={"color": self.LABEL_COLOR, "font_size": 11},
                    )
                self._frame = ui.Frame(
                    width=self._size,
                    height=self._size,
                    style={"background_color": 0xFF000000},
                )
                self._frame.set_build_fn(self._build_radar)
                # Mouse handlers — wrapped because the omni.ui mouse API
                # changed across Kit versions; falling back to no-handler
                # keeps the widget usable for read-only viewing.
                self._wire_mouse(self._frame)
                self._scale_label = ui.Label(
                    f"Range: {self._world_radius:.0f} m  (wheel to zoom)",
                    style={"color": self.LABEL_COLOR, "font_size": 11},
                    height=16,
                )
                with ui.HStack(height=24, spacing=4):
                    ui.Button(
                        "Zoom -",
                        width=58,
                        tooltip="Zoom out (wider radar coverage)",
                        clicked_fn=lambda: self.set_world_radius(self._world_radius * 1.5),
                    )
                    ui.Button(
                        "Zoom +",
                        width=58,
                        tooltip="Zoom in (closer detail)",
                        clicked_fn=lambda: self.set_world_radius(self._world_radius / 1.5),
                    )
                    ui.Button(
                        "Fit",
                        width=40,
                        tooltip="Frame the radar around the full stage extents.",
                        clicked_fn=self._on_fit_clicked,
                    )
                    ui.Button(
                        "Pin",
                        width=40,
                        tooltip="Save current camera spot as a persistent waypoint.",
                        clicked_fn=self._on_pin_clicked,
                    )
        return self._window

    def destroy(self) -> None:
        if self._window is not None:
            try:
                self._window.visible = False
                self._window.destroy()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[stage_compass] window destroy failed: {exc}")
            self._window = None
        self._frame = None
        self._coord_label = None
        self._scale_label = None
        self._heading_label = None

    # ------------------------------------------------------------------
    # Update tick
    # ------------------------------------------------------------------
    def update(self, cam_pose: Optional[CameraPose]) -> None:
        self._cam_pose = cam_pose
        if cam_pose is not None and self._coord_label is not None:
            self._coord_label.text = (
                f"X {cam_pose.floor_a:+8.2f}   "
                f"Y {cam_pose.floor_b:+8.2f}   "
                f"Z {cam_pose.height:+8.2f}"
            )
        if cam_pose is not None and self._heading_label is not None:
            heading_deg = math.degrees(cam_pose.heading_rad)
            cardinal = _heading_to_cardinal(heading_deg)
            self._heading_label.text = (
                f"Heading {heading_deg:+6.1f}°  ({cardinal})    "
                f"FOV {cam_pose.fov_deg:.0f}°"
            )
        self._safe_rebuild()

    def _safe_rebuild(self) -> None:
        if self._frame is None:
            return
        try:
            self._frame.rebuild()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_compass] rebuild failed: {exc}")

    # ------------------------------------------------------------------
    # Radar drawing
    # ------------------------------------------------------------------
    def _build_radar(self) -> None:
        cx = self._size / 2.0
        cy = self._size / 2.0
        proj = RadarProjection(self._size, self._world_radius)
        pose = self._cam_pose

        with ui.ZStack():
            # ----- background disc -----
            ui.Rectangle(
                style={
                    "background_color": self.BG_COLOR,
                    "border_radius": self._size / 2.0,
                    "border_width": 1.0,
                    "border_color": self.BG_BORDER,
                }
            )
            # ----- concentric range rings -----
            for frac in (0.25, 0.5, 0.75, 1.0):
                ring_size = self._size * frac
                with ui.Placer(
                    offset_x=cx - ring_size / 2.0,
                    offset_y=cy - ring_size / 2.0,
                ):
                    ui.Rectangle(
                        width=ring_size,
                        height=ring_size,
                        style={
                            "background_color": 0x00000000,
                            "border_radius": ring_size / 2.0,
                            "border_width": 1.0,
                            "border_color": self.RING_COLOR,
                        },
                    )
            # ----- prim dots -----
            if pose is not None:
                self._draw_prim_dots(proj, pose, cx, cy)
                self._draw_waypoints(proj, pose, cx, cy)
                self._draw_compass_labels(pose, cx, cy)
                self._draw_heading_indicator(cx, cy)
                self._draw_camera_marker(cx, cy)
            else:
                with ui.Placer(offset_x=cx - 60, offset_y=cy - 8):
                    ui.Label(
                        "(no active camera)",
                        style={"color": 0xC0808088, "font_size": 12},
                    )

    def _draw_camera_marker(self, cx: float, cy: float) -> None:
        # Triangle pointing up (heading is rotated so forward = up in HUD).
        try:
            with ui.Placer(offset_x=cx - 7, offset_y=cy - 9):
                ui.Triangle(
                    width=14,
                    height=18,
                    alignment=ui.Alignment.CENTER_TOP,
                    style={"background_color": self.CAM_DOT_COLOR},
                )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_compass] camera triangle: {exc}")
            with ui.Placer(offset_x=cx - 4, offset_y=cy - 4):
                ui.Rectangle(
                    width=8, height=8,
                    style={
                        "background_color": self.CAM_DOT_COLOR,
                        "border_radius": 4,
                    },
                )

    def _draw_heading_indicator(self, cx: float, cy: float) -> None:
        # Stylised "north arrow" that always points up in the rotated frame
        # — visual anchor for the user that the radar is camera-relative.
        bar_h = self._size * 0.08
        with ui.Placer(offset_x=cx - 1, offset_y=cy - bar_h):
            ui.Rectangle(
                width=2, height=bar_h,
                style={"background_color": self.CAM_HEADING_COLOR},
            )

    def _draw_prim_dots(
        self,
        proj: RadarProjection,
        pose: CameraPose,
        cx: float, cy: float,
    ) -> None:
        markers = self._scanner.get_markers()
        allow = self._allowed_types
        n_drawn = 0
        # ``BUDGET`` keeps the radar responsive on huge stages — anything
        # past the first 600 dots is statistically not adding info to the
        # human reader anyway. Enforced after sorting by distance so the
        # closest prims always win.
        BUDGET = 600
        if allow is not None:
            markers = [m for m in markers if m.type_name in allow]
        # Pre-filter by world distance so the projection step doesn't waste
        # work on prims behind the user (they'd land off-frame anyway).
        cull_radius = self._world_radius * 1.15
        candidates: list[tuple[float, PrimMarker]] = []
        for m in markers:
            da = m.floor_a - pose.floor_a
            db = m.floor_b - pose.floor_b
            d2 = da * da + db * db
            if d2 > cull_radius * cull_radius:
                continue
            candidates.append((d2, m))
        candidates.sort(key=lambda p: p[0])
        for _, m in candidates[:BUDGET]:
            px, py = proj.world_to_hud(
                m.floor_a, m.floor_b,
                pose.floor_a, pose.floor_b,
                pose.heading_rad,
            )
            # Cull dots that landed outside the radar disc — checked with a
            # circular bound, not the bounding box, so corners aren't lit.
            ddx = px - cx
            ddy = py - cy
            if ddx * ddx + ddy * ddy > (cx - 2) * (cx - 2):
                continue
            radius = m.size_px
            with ui.Placer(offset_x=px - radius / 2.0, offset_y=py - radius / 2.0):
                ui.Rectangle(
                    width=radius, height=radius,
                    style={
                        "background_color": m.color_argb,
                        "border_radius": radius / 2.0,
                    },
                )
            n_drawn += 1
        # cheap perf hint — only updated when the inner label exists
        if self._scale_label is not None and n_drawn:
            # Leave the existing range text intact when no diagnostics
            # are needed; only append count if the user pinned it.
            pass

    def _draw_waypoints(
        self,
        proj: RadarProjection,
        pose: CameraPose,
        cx: float, cy: float,
    ) -> None:
        for wp in self._waypoints.list():
            px, py = proj.world_to_hud(
                wp.floor_a, wp.floor_b,
                pose.floor_a, pose.floor_b,
                pose.heading_rad,
            )
            ddx = px - cx
            ddy = py - cy
            if ddx * ddx + ddy * ddy > (cx + 12) * (cx + 12):
                continue
            with ui.Placer(offset_x=px - 7, offset_y=py - 7):
                ui.Rectangle(
                    width=14, height=14,
                    style={
                        "background_color": wp.color_argb,
                        "border_width": 2,
                        "border_color": 0xFFFFFFFF,
                        "border_radius": 3,
                    },
                )
            # Short label below the flag
            if wp.name:
                short = wp.name if len(wp.name) <= 10 else wp.name[:9] + "…"
                with ui.Placer(offset_x=px - 24, offset_y=py + 8):
                    ui.Label(
                        short,
                        width=48,
                        style={"color": 0xFFFFFFFF, "font_size": 10},
                    )

    def _draw_compass_labels(
        self, pose: CameraPose, cx: float, cy: float,
    ) -> None:
        # World-fixed cardinal labels at the rim. We only project the
        # direction vector (no translation) so they stay at unit
        # distance, then push to the rim at ``rim_factor``.
        rim_factor = 0.92
        rim = (self._size / 2.0) * rim_factor
        proj = RadarProjection(self._size, 1.0)
        for label, (da, db) in (
            ("N", (0.0, 1.0)),
            ("E", (1.0, 0.0)),
            ("S", (0.0, -1.0)),
            ("W", (-1.0, 0.0)),
        ):
            px, py = proj.world_to_hud(
                pose.floor_a + da, pose.floor_b + db,
                pose.floor_a, pose.floor_b,
                pose.heading_rad,
            )
            # Re-scale so the unit vector hits the rim instead of the
            # outermost ring (which uses world_radius scaling).
            dx = px - cx
            dy = py - cy
            mag = math.sqrt(dx * dx + dy * dy) or 1.0
            tx = cx + dx / mag * rim - 6
            ty = cy + dy / mag * rim - 8
            with ui.Placer(offset_x=tx, offset_y=ty):
                ui.Label(
                    label,
                    width=14,
                    style={
                        "color": self.TICK_COLOR,
                        "font_size": 12,
                    },
                )

    # ------------------------------------------------------------------
    # Mouse handling
    # ------------------------------------------------------------------
    def _wire_mouse(self, frame: ui.Frame) -> None:
        # Mouse click → teleport the camera. Wheel → zoom radar. Some
        # Kit builds expose set_mouse_pressed_fn, others use
        # set_mouse_double_clicked_fn / set_mouse_released_fn — try a
        # couple so the HUD remains interactive on whichever platform.
        for setter in ("set_mouse_pressed_fn", "set_mouse_released_fn"):
            try:
                getattr(frame, setter)(self._on_mouse_pressed)
                break
            except Exception:
                continue
        for setter in ("set_mouse_wheel_fn",):
            try:
                getattr(frame, setter)(self._on_mouse_wheel)
                break
            except Exception:
                continue

    def _on_mouse_pressed(
        self, x: float, y: float, button: int, modifier: int,
    ) -> None:
        # Left-click teleports; other buttons reserved.
        if button != 0:
            return
        if self._frame is None or self._cam_pose is None:
            return
        try:
            screen_x = float(self._frame.screen_position_x)
            screen_y = float(self._frame.screen_position_y)
        except Exception:
            screen_x = screen_y = 0.0
        local_x = float(x) - screen_x
        local_y = float(y) - screen_y
        # Reject clicks outside the radar disc.
        cx = self._size / 2.0
        ddx = local_x - cx
        ddy = local_y - cx
        if ddx * ddx + ddy * ddy > cx * cx:
            return
        proj = RadarProjection(self._size, self._world_radius)
        wa, wb = proj.hud_to_world(
            local_x, local_y,
            self._cam_pose.floor_a, self._cam_pose.floor_b,
            self._cam_pose.heading_rad,
        )
        ok = self._teleport_cb(wa, wb)
        if not ok:
            carb.log_warn("[stage_compass] teleport failed (no active camera?)")

    def _on_mouse_wheel(
        self, x: float, y: float, dx: float, dy: float, modifier: int,
    ) -> None:
        # Wheel up zooms in (smaller world_radius).
        if dy == 0:
            return
        factor = 1.25 if dy > 0 else 1 / 1.25
        self.set_world_radius(self._world_radius / factor)

    def _on_fit_clicked(self) -> None:
        ext = self._scanner.world_extents
        min_a, min_b, max_a, max_b = ext
        if max_a > min_a and max_b > min_b:
            radius = max(max_a - min_a, max_b - min_b) / 2.0
            self.set_world_radius(max(MIN_WORLD_RADIUS, radius * 1.1))

    def _on_pin_clicked(self) -> None:
        if self._save_waypoint_cb is not None:
            self._save_waypoint_cb()


# ----------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------
def _heading_to_cardinal(deg: float) -> str:
    """Map a 0..360-ish heading to a compass tag."""
    d = ((deg % 360.0) + 360.0) % 360.0
    table = (
        (22.5,   "E"),
        (67.5,   "NE"),
        (112.5,  "N"),
        (157.5,  "NW"),
        (202.5,  "W"),
        (247.5,  "SW"),
        (292.5,  "S"),
        (337.5,  "SE"),
    )
    for thresh, tag in table:
        if d < thresh:
            return tag
    return "E"
