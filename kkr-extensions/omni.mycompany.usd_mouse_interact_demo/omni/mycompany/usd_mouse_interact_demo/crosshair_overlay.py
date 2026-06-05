"""Transparent crosshair overlay drawn directly on the active viewport frame.

Unlike a separate ``ui.Window`` (which renders Kit-level chrome — padding +
border — even when ``WINDOW_FLAGS_NO_BACKGROUND`` is set), a ``viewport_window
.get_frame(<name>)`` overlay shares the viewport's own composition layer and
adds zero chrome. Same pattern as ``info_overlay.py``.

Position is updated each tick via the Placer's ``offset_x`` / ``offset_y`` so
the circle stays at the viewport's geometric center across docking, resize,
and multi-monitor moves. We track the circle widget directly so ``set_color``
can restyle it live without rebuilding the frame.
"""

from __future__ import annotations

import math
from typing import Optional

import carb

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.crosshair_overlay"

_CIRCLE_SIZE = 10
_CIRCLE_RADIUS = 10
_DEFAULT_COLOR = 0xCC0000FF  # ABGR — red translucent (A=CC,B=00,G=00,R=FF)

CROSSHAIR_FRAME_NAME = "omni.mycompany.usd_mouse_interact_demo.crosshair_frame"


class CrosshairOverlay:

    def __init__(self) -> None:
        self._viewport_window = None
        self._frame = None
        self._placer = None
        self._circle = None
        self._tracking_rect = None
        self._last_pointer_local: Optional[tuple[float, float]] = None
        self._color: int = _DEFAULT_COLOR
        self._visible = False

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def _ensure_built(self) -> bool:
        if self._frame is not None:
            return True
        try:
            import omni.ui as ui
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] omni.ui import failed: {exc!r}")
            return False

        try:
            from omni.kit.viewport.utility import get_active_viewport_window
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] viewport utility import failed: {exc!r}")
            return False

        self._viewport_window = get_active_viewport_window()
        if self._viewport_window is None:
            return False

        try:
            self._frame = self._viewport_window.get_frame(CROSSHAIR_FRAME_NAME)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] get_frame failed: {exc!r}")
            self._frame = None
            return False

        try:
            self._build_frame_widgets(track_pointer=False)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] frame build failed: {exc!r}")
            return False

        self._frame.visible = False
        return True

    def _build_frame_widgets(self, *, track_pointer: bool) -> None:
        import omni.ui as ui  # noqa: WPS433

        if self._frame is None:
            return
        try:
            self._frame.clear()
        except Exception:  # noqa: BLE001
            pass
        self._tracking_rect = None
        with self._frame:
            with ui.ZStack():
                if track_pointer:
                    kwargs = {
                        "width": ui.Fraction(1),
                        "height": ui.Fraction(1),
                        "style": {"background_color": 0x00000000},
                    }
                    try:
                        self._tracking_rect = ui.Rectangle(
                            opaque_for_mouse_events=True,
                            **kwargs,
                        )
                    except TypeError:
                        self._tracking_rect = ui.Rectangle(**kwargs)
                    self._wire_pointer_tracking(self._tracking_rect)
                self._placer = ui.Placer(
                    offset_x=ui.Pixel(0),
                    offset_y=ui.Pixel(0),
                )
                with self._placer:
                    self._circle = ui.Circle(
                        width=_CIRCLE_SIZE,
                        height=_CIRCLE_SIZE,
                        radius=_CIRCLE_RADIUS,
                        style={"background_color": self._color},
                    )

    def _wire_pointer_tracking(self, widget) -> None:
        for setter_name in ("set_mouse_moved_fn", "set_mouse_pressed_fn"):
            try:
                getattr(widget, setter_name)(self._on_pointer_event)
            except Exception:  # noqa: BLE001
                continue

    def _on_pointer_event(self, x: float, y: float, *args) -> None:
        del args
        point = self._screen_or_local_to_frame_point(x, y)
        if point is not None:
            self._last_pointer_local = point

    def _screen_or_local_to_frame_point(
        self,
        x: float,
        y: float,
    ) -> Optional[tuple[float, float]]:
        try:
            px = float(x)
            py = float(y)
        except Exception:  # noqa: BLE001
            return None
        if not math.isfinite(px) or not math.isfinite(py):
            return None
        try:
            w = float(self._viewport_window.width or 0)
            h = float(self._viewport_window.height or 0)
        except Exception:  # noqa: BLE001
            w = h = 0.0
        try:
            frame_x = float(self._frame.screen_position_x)
            frame_y = float(self._frame.screen_position_y)
        except Exception:  # noqa: BLE001
            frame_x = frame_y = 0.0

        local_x = px - frame_x
        local_y = py - frame_y
        if w > 0 and h > 0 and 0.0 <= local_x <= w and 0.0 <= local_y <= h:
            return local_x, local_y
        if w > 0 and h > 0 and 0.0 <= px <= w and 0.0 <= py <= h:
            return px, py
        return None

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def show(self) -> None:
        if not self._ensure_built():
            return
        try:
            self._build_frame_widgets(track_pointer=False)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] center crosshair rebuild failed: {exc!r}")
        self._frame.visible = True
        self._visible = True
        # Compute initial position so the circle isn't briefly stuck at (0,0).
        self.update_position()

    def show_at_pointer(self) -> None:
        """Show the crosshair without forcing it to the viewport center."""
        if not self._ensure_built():
            return
        try:
            self._build_frame_widgets(track_pointer=True)
            self._frame.visible = True
            self._visible = True
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] show_at_pointer failed: {exc!r}")

    def hide(self) -> None:
        if self._frame is not None:
            self._frame.visible = False
        self._visible = False
        self._last_pointer_local = None

    def set_color(self, rgba: int) -> None:
        """Update the circle color. Accepts an ABGR int (omni.ui convention).

        Persists the value so a later show()/build reuses it. Safe to call
        before the frame is built.
        """
        self._color = int(rgba)
        if self._circle is None:
            return
        try:
            self._circle.set_style({"background_color": self._color})
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] set_color failed: {exc!r}")

    def update_position(self) -> None:
        """Center the circle inside the viewport frame.

        Frame coordinates are local to the viewport (origin = viewport top-
        left), so screen-space conversion is unnecessary. Half-circle offset
        keeps the dot's geometric center exactly at the viewport center.
        """
        if not self._visible or self._placer is None or self._viewport_window is None:
            return
        try:
            import omni.ui as ui
        except Exception:  # noqa: BLE001
            return
        try:
            w = float(self._viewport_window.width or 0)
            h = float(self._viewport_window.height or 0)
        except Exception:  # noqa: BLE001
            return
        if w <= 0 or h <= 0:
            return
        try:
            self._placer.offset_x = ui.Pixel((w - _CIRCLE_SIZE) / 2.0)
            self._placer.offset_y = ui.Pixel((h - _CIRCLE_SIZE) / 2.0)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] position write failed: {exc!r}")

    def update_pointer_position(self, x: float, y: float) -> None:
        """Move the circle to viewport-local pointer coordinates."""
        if not self._visible or self._placer is None:
            return
        try:
            px = float(x)
            py = float(y)
        except Exception:  # noqa: BLE001
            return
        if not math.isfinite(px) or not math.isfinite(py):
            return
        try:
            import omni.ui as ui
        except Exception:  # noqa: BLE001
            return
        try:
            half_size = _CIRCLE_SIZE / 2.0
            self._placer.offset_x = ui.Pixel(px - half_size)
            self._placer.offset_y = ui.Pixel(py - half_size)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] pointer position write failed: {exc!r}")

    def get_tracked_pointer_position(self) -> Optional[tuple[float, float]]:
        return self._last_pointer_local

    def destroy(self) -> None:
        if self._frame is not None:
            try:
                self._frame.visible = False
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] hide on destroy failed: {exc!r}")
        # Frame ownership belongs to the viewport — we only release our refs.
        # The viewport disposes the frame on its own teardown.
        self._frame = None
        self._placer = None
        self._circle = None
        self._tracking_rect = None
        self._viewport_window = None
        self._last_pointer_local = None
        self._visible = False

    # ------------------------------------------------------------------
    # introspection (compat with old API — viewport center pixel coord
    # for any caller that still wants the screen-space center)
    # ------------------------------------------------------------------

    def _compute_viewport_center(self) -> Optional[tuple[int, int]]:
        try:
            from omni.kit.viewport.utility import get_active_viewport_window
        except Exception:  # noqa: BLE001
            return None
        vp_window = get_active_viewport_window()
        if vp_window is None:
            return None
        try:
            x = float(vp_window.position_x or 0)
            y = float(vp_window.position_y or 0)
            w = float(vp_window.width or 0)
            h = float(vp_window.height or 0)
        except Exception:  # noqa: BLE001
            return None
        if w <= 0 or h <= 0:
            return None
        return int(x + w * 0.5), int(y + h * 0.5)
