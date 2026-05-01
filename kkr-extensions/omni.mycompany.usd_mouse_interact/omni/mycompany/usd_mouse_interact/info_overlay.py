# info_overlay.py -- viewport top-left info frame.

from __future__ import annotations

import carb
import omni.ui as ui
import omni.kit.viewport.utility as vp_utils

INFO_FRAME_NAME = "omni.mycompany.usd_mouse_interact.info_frame"

_BG_COLOR = 0xCC202020       # dark, semi-transparent
_TITLE_COLOR = 0xFFFFFFFF
_DESC_COLOR = 0xFFCCCCCC


class InfoOverlay:
    """Small viewport-top-left panel: bold title + 2-line description.

    Only widgets are rebuilt once. show(title, desc) only updates label text
    when path actually changes (cache via _last_title/_last_desc) so the cost
    per frame is near-zero when hovering the same prim.
    """

    def __init__(self) -> None:
        self._frame: ui.Frame | None = None
        self._viewport_window = None
        self._title_label: ui.Label | None = None
        self._desc_label: ui.Label | None = None
        self._last_title: str | None = None
        self._last_desc: str | None = None
        self._warned_no_viewport = False

    # --- lifecycle ---

    def _ensure_built(self) -> bool:
        if self._frame is not None:
            return True
        self._viewport_window = vp_utils.get_active_viewport_window()
        if self._viewport_window is None:
            if not self._warned_no_viewport:
                carb.log_warn(f"[{INFO_FRAME_NAME}] no active viewport window — overlay not built")
                self._warned_no_viewport = True
            return False
        self._frame = self._viewport_window.get_frame(INFO_FRAME_NAME)
        with self._frame:
            with ui.Placer(offset_x=ui.Pixel(12), offset_y=ui.Pixel(45)):
                with ui.ZStack(width=320, height=80):
                    ui.Rectangle(
                        style={"background_color": _BG_COLOR, "border_radius": 6}
                    )
                    with ui.VStack(spacing=4, style={"margin": 8}):
                        self._title_label = ui.Label(
                            "",
                            style={"color": _TITLE_COLOR, "font_size": 16},
                            height=20,
                        )
                        self._desc_label = ui.Label(
                            "",
                            style={"color": _DESC_COLOR, "font_size": 12},
                            word_wrap=True,
                        )
        self._frame.visible = False
        return True

    # --- API ---

    def show(self, title: str, desc: str) -> None:
        if not self._ensure_built():
            return
        if title != self._last_title:
            self._title_label.text = title
            self._last_title = title
        if desc != self._last_desc:
            self._desc_label.text = desc
            self._last_desc = desc
        self._frame.visible = True

    def hide(self) -> None:
        if self._frame is not None:
            self._frame.visible = False

    def destroy(self) -> None:
        if self._frame is not None:
            self._frame.visible = False
            self._frame = None
            self._title_label = None
            self._desc_label = None
            self._viewport_window = None
            self._last_title = None
            self._last_desc = None
