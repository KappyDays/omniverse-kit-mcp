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

from typing import Optional

import carb

_SOURCE = "omni.mycompany.usd_mouse_interact.crosshair_overlay"

_CIRCLE_SIZE = 10
_CIRCLE_RADIUS = 10
_DEFAULT_COLOR = 0xCC0000FF  # ABGR — red translucent (A=CC,B=00,G=00,R=FF)

CROSSHAIR_FRAME_NAME = "omni.mycompany.usd_mouse_interact.crosshair_frame"


class CrosshairOverlay:

    def __init__(self) -> None:
        self._viewport_window = None
        self._frame = None
        self._placer = None
        self._circle = None
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
            with self._frame:
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
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] frame build failed: {exc!r}")
            return False

        self._frame.visible = False
        return True

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def show(self) -> None:
        if not self._ensure_built():
            return
        self._frame.visible = True
        self._visible = True
        # Compute initial position so the circle isn't briefly stuck at (0,0).
        self.update_position()

    def hide(self) -> None:
        if self._frame is not None:
            self._frame.visible = False
        self._visible = False

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
        self._viewport_window = None
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
