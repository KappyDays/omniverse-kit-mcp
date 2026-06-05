"""Viewport-owned overlay UI for USD Mouse Interact Demo button mode."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Sequence

from .button_layout import PercentRect, visible_pixel_rect
from .config_model import ButtonModeConfig, ButtonStyleConfig
from .preview_capture import CaptureResult, choose_display_kind

FRAME_NAME = "omni.mycompany.usd_mouse_interact_demo.button_mode_frame"

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.button_overlay"
def _log_warn(message: str) -> None:
    try:
        import carb  # noqa: WPS433

        carb.log_warn(message)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).warning(message)


class ButtonModeOverlayManager:
    """Draw the current button-mode UI inside the active viewport frame."""

    def __init__(self, frame_name: str = FRAME_NAME) -> None:
        self._frame_name = frame_name
        self._viewport_window = None
        self._frame = None

    def clear_current_state_ui(self) -> None:
        if self._frame is None:
            return
        try:
            self._frame.clear()
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] frame clear failed: {exc!r}")
        try:
            self._frame.visible = False
        except Exception:  # noqa: BLE001
            pass

    def shutdown(self) -> None:
        self.clear_current_state_ui()
        self._frame = None
        self._viewport_window = None

    def show_button_hud(
        self,
        config: ButtonModeConfig,
        on_button: Callable[[str], None],
        *,
        button_keys: Sequence[str] | None = None,
        show_back: bool = False,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        self.clear_current_state_ui()
        if not self._ensure_frame():
            return
        width, height = self._viewport_size()
        if width <= 0 or height <= 0:
            width, height = 1920, 1080

        ui = self._ui()
        if ui is None:
            return

        try:
            with self._frame:
                with self._root_stack(ui):
                    placed: list[tuple[int, int, int, int]] = []
                    for key in _ordered_button_keys(config.buttons, button_keys):
                        button = config.buttons.get(key)
                        if button is None:
                            continue
                        x, y, w, h = visible_pixel_rect(
                            PercentRect(
                                button.x_pct,
                                button.y_pct,
                                button.w_pct,
                                button.h_pct,
                            ),
                            width,
                            height,
                        )
                        x, y = _avoid_overlap(x, y, w, h, placed, int(width), int(height))
                        placed.append((x, y, w, h))
                        with ui.Placer(offset_x=ui.Pixel(x), offset_y=ui.Pixel(y)):
                            self._button(
                                str(button.label or key.upper()),
                                clicked_fn=lambda key=key: on_button(key),
                                width=w,
                                height=h,
                                config=config,
                                color=button.color,
                                text_color=button.text_color,
                                font_size=getattr(button, "font_size", 0),
                                shape=getattr(button, "shape", "rect"),
                                origin=(x, y),
                            )
                    if show_back and on_back is not None:
                        back_x, back_y, back_w, back_h = self._back_button_rect(config)
                        with ui.Placer(offset_x=ui.Pixel(back_x), offset_y=ui.Pixel(back_y)):
                            self._button(
                                str(config.back_button.label or "Back"),
                                clicked_fn=on_back,
                                width=back_w,
                                height=back_h,
                                config=config,
                                color=config.back_button.color,
                                text_color=config.back_button.text_color,
                                font_size=getattr(config.back_button, "font_size", 0),
                                shape=getattr(config.back_button, "shape", "rect"),
                                origin=(back_x, back_y),
                            )
            self._frame.visible = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] show_button_hud failed: {exc!r}")

    def show_loading(self, label: str, config: ButtonModeConfig | None = None) -> None:
        self.clear_current_state_ui()
        if not self._ensure_frame():
            return
        ui = self._ui()
        if ui is None:
            return

        try:
            width, height = self._viewport_size()
            if width <= 0 or height <= 0:
                width, height = 1280, 720
            box_w = 220
            box_h = 42
            box_x = max(0, int((width - box_w) / 2))
            box_y = max(0, int((height - box_h) / 2))
            with self._frame:
                with self._root_stack(ui):
                    if config is not None:
                        self._overlay_background(ui, config)
                    with ui.Placer(offset_x=ui.Pixel(box_x), offset_y=ui.Pixel(box_y)):
                        with ui.ZStack(width=box_w, height=box_h):
                            style = _style(config)
                            ui.Rectangle(style={"background_color": style.panel_color})
                            ui.Label(str(label), style={"color": style.text_color}, height=box_h)
            self._frame.visible = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] show_loading failed: {exc!r}")

    def show_exploring_button(
        self,
        config: ButtonModeConfig,
        on_click: Callable[[], None],
    ) -> None:
        self.clear_current_state_ui()
        if not self._ensure_frame():
            return
        ui = self._ui()
        if ui is None:
            return

        try:
            width, height = self._viewport_size()
            if width <= 0 or height <= 0:
                width, height = 1280, 720
            button_cfg = config.exploring_button
            button_x, button_y, button_w, button_h = visible_pixel_rect(
                PercentRect(
                    button_cfg.x_pct,
                    button_cfg.y_pct,
                    button_cfg.w_pct,
                    button_cfg.h_pct,
                ),
                width,
                height,
            )
            with self._frame:
                with self._root_stack(ui):
                    with ui.Placer(offset_x=ui.Pixel(button_x), offset_y=ui.Pixel(button_y)):
                        self._button(
                            str(button_cfg.label or "Exploring"),
                            clicked_fn=on_click,
                            width=button_w,
                            height=button_h,
                            config=config,
                            color=button_cfg.color,
                            text_color=button_cfg.text_color,
                            font_size=getattr(button_cfg, "font_size", 0),
                            shape=getattr(button_cfg, "shape", "rect"),
                            origin=(button_x, button_y),
                        )
            self._frame.visible = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] show_exploring_button failed: {exc!r}")

    def show_run_buttons(
        self,
        config: ButtonModeConfig,
        on_start: Callable[[], None],
    ) -> None:
        self.clear_current_state_ui()
        if not self._ensure_frame():
            return
        ui = self._ui()
        if ui is None:
            return

        try:
            width, height = self._viewport_size()
            if width <= 0 or height <= 0:
                width, height = 1280, 720
            with self._frame:
                with self._root_stack(ui):
                    for button_config, callback in (
                        (config.exploring_button, on_start),
                        (config.buttons.get("a"), _noop),
                        (config.buttons.get("b"), _noop),
                        (config.dream_ai_button, _noop),
                    ):
                        if button_config is None:
                            continue
                        x, y, w, h = visible_pixel_rect(
                            PercentRect(
                                button_config.x_pct,
                                button_config.y_pct,
                                button_config.w_pct,
                                button_config.h_pct,
                            ),
                            width,
                            height,
                        )
                        with ui.Placer(offset_x=ui.Pixel(x), offset_y=ui.Pixel(y)):
                            self._button(
                                str(button_config.label or ""),
                                clicked_fn=callback,
                                width=w,
                                height=h,
                                config=config,
                                color=button_config.color,
                                text_color=button_config.text_color,
                                font_size=getattr(button_config, "font_size", 0),
                                shape=getattr(button_config, "shape", "rect"),
                                origin=(x, y),
                            )
            self._frame.visible = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] show_run_buttons failed: {exc!r}")

    def show_capture_matrix(
        self,
        results: Sequence[CaptureResult],
        config: ButtonModeConfig,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        self.clear_current_state_ui()
        if not self._ensure_frame():
            return
        ui = self._ui()
        if ui is None:
            return

        count = 6 if len(results) >= 6 else 5
        viewport_width, viewport_height = self._viewport_size()
        if viewport_width <= 0 or viewport_height <= 0:
            viewport_width, viewport_height = 1280, 720
        layout = _matrix_layout(
            viewport_width,
            viewport_height,
            config,
            count=count,
        )
        try:
            with self._frame:
                with self._root_stack(ui):
                    self._preview_overlay_background(ui, config)
                    for index, result in enumerate(_pad_results(results, count=count)):
                        x, y, tile_w, tile_h = _matrix_tile_rect(layout, index, count=count)
                        with ui.Placer(offset_x=ui.Pixel(x), offset_y=ui.Pixel(y)):
                            self._preview_tile(
                                ui,
                                index,
                                result,
                                _noop,
                                tile_w,
                                tile_h,
                                config,
                            )
                    if on_back is not None:
                        back_button = config.final_preview_back_button
                        back_x, back_y, back_w, back_h = visible_pixel_rect(
                            PercentRect(
                                back_button.x_pct,
                                back_button.y_pct,
                                back_button.w_pct,
                                back_button.h_pct,
                            ),
                            viewport_width,
                            viewport_height,
                        )
                        with ui.Placer(offset_x=ui.Pixel(back_x), offset_y=ui.Pixel(back_y)):
                            self._button(
                                str(back_button.label or "Back"),
                                clicked_fn=on_back,
                                width=back_w,
                                height=back_h,
                                config=config,
                                color=back_button.color,
                                text_color=back_button.text_color,
                                font_size=getattr(back_button, "font_size", 0),
                                shape=getattr(back_button, "shape", "rect"),
                                origin=(back_x, back_y),
                            )
            self._frame.visible = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] show_capture_matrix failed: {exc!r}")

    def show_preview_chooser(
        self,
        results: Sequence[CaptureResult],
        on_select: Callable[[int], None],
        on_back: Callable[[], None],
        config: ButtonModeConfig,
    ) -> None:
        self.clear_current_state_ui()
        if not self._ensure_frame():
            return
        ui = self._ui()
        if ui is None:
            return

        layout = _preview_layout(*self._viewport_size(), config)
        back_x, back_y, back_w, back_h = self._back_button_rect(config)
        try:
            with self._frame:
                with self._root_stack(ui):
                    self._overlay_background(ui, config)
                    with ui.Placer(offset_x=ui.Pixel(back_x), offset_y=ui.Pixel(back_y)):
                        self._button(
                            str(config.back_button.label or "Back"),
                            clicked_fn=on_back,
                            width=back_w,
                            height=back_h,
                            config=config,
                            color=config.back_button.color,
                            text_color=config.back_button.text_color,
                            font_size=getattr(config.back_button, "font_size", 0),
                            shape=getattr(config.back_button, "shape", "rect"),
                            origin=(back_x, back_y),
                        )

                    for index, result in enumerate(_pad_results(results, count=4)):
                        col = index % 2
                        row = index // 2
                        x = layout.grid_x + col * (layout.tile_w + layout.gap)
                        y = layout.grid_y + row * (layout.tile_h + layout.gap)
                        with ui.Placer(offset_x=ui.Pixel(x), offset_y=ui.Pixel(y)):
                            self._preview_tile(
                                ui,
                                index,
                                result,
                                on_select,
                                layout.tile_w,
                                layout.tile_h,
                                config,
                            )
            self._frame.visible = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] show_preview_chooser failed: {exc!r}")

    def show_camera_detail_back(
        self,
        on_back: Callable[[], None],
        config: ButtonModeConfig,
    ) -> None:
        self.clear_current_state_ui()
        if not self._ensure_frame():
            return
        ui = self._ui()
        if ui is None:
            return

        try:
            with self._frame:
                with self._root_stack(ui):
                    self._overlay_background(ui, config)
                    back_x, back_y, back_w, back_h = self._back_button_rect(config)
                    with ui.Placer(offset_x=ui.Pixel(back_x), offset_y=ui.Pixel(back_y)):
                        self._button(
                            str(config.back_button.label or "Back"),
                            clicked_fn=on_back,
                            width=back_w,
                            height=back_h,
                            config=config,
                            color=config.back_button.color,
                            text_color=config.back_button.text_color,
                            font_size=getattr(config.back_button, "font_size", 0),
                            shape=getattr(config.back_button, "shape", "rect"),
                            origin=(back_x, back_y),
                        )
            self._frame.visible = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] show_camera_detail_back failed: {exc!r}")

    def current_viewport_size(self) -> tuple[float, float]:
        if not self._ensure_frame():
            return (0.0, 0.0)
        return self._viewport_size()

    def _ensure_frame(self) -> bool:
        if self._frame is not None:
            return True
        try:
            from omni.kit.viewport.utility import get_active_viewport_window  # noqa: WPS433
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] viewport utility import failed: {exc!r}")
            return False

        try:
            self._viewport_window = get_active_viewport_window()
            if self._viewport_window is None:
                _log_warn(f"[{_SOURCE}] no active viewport window")
                return False
            self._frame = self._viewport_window.get_frame(self._frame_name)
            return True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] get_frame failed: {exc!r}")
            self._frame = None
            return False

    def _viewport_size(self) -> tuple[float, float]:
        try:
            return (
                float(getattr(self._viewport_window, "width", 0) or 0),
                float(getattr(self._viewport_window, "height", 0) or 0),
            )
        except Exception:  # noqa: BLE001
            return (0.0, 0.0)

    def _button(
        self,
        label: str,
        clicked_fn,
        width: int,
        height: int,
        config: ButtonModeConfig | None = None,
        color: int | None = None,
        text_color: int | None = None,
        font_size: int | None = None,
        shape: str | None = None,
        origin: tuple[int, int] | None = None,
    ):
        ui = self._ui()
        if ui is None:
            return None
        style_config = _style(config)
        resolved_text_color = style_config.text_color if text_color is None else int(text_color)
        resolved_font_size = int(font_size or 0) or int(style_config.font_size)
        button_color = style_config.button_color if color is None else int(color)
        pixel_width = max(1, int(width))
        pixel_height = max(1, int(height))
        resolved_shape = str(shape or "rect").strip().lower()
        if resolved_shape == "circle":
            return self._rounded_button(
                ui,
                label,
                clicked_fn,
                pixel_width,
                pixel_height,
                button_color,
                int(style_config.hover_color),
                resolved_text_color,
                resolved_font_size,
                radius=max(1, int(min(pixel_width, pixel_height) / 2)),
                shadow_color=_with_alpha(_shade_color(button_color, 0.20), 0x55),
                shadow_offset_y=max(3, int(pixel_height * 0.05)),
            )
        if resolved_shape == "raised":
            return self._raised_button(
                ui,
                label,
                clicked_fn,
                pixel_width,
                pixel_height,
                button_color,
                int(style_config.hover_color),
                resolved_text_color,
                resolved_font_size,
                int(style_config.border_radius),
                origin,
            )
        if resolved_shape == "orb":
            return self._rounded_button(
                ui,
                label,
                clicked_fn,
                pixel_width,
                pixel_height,
                button_color,
                int(style_config.hover_color),
                resolved_text_color,
                resolved_font_size,
                radius=max(1, int(min(pixel_width, pixel_height) / 2)),
                border_width=max(2, int(min(pixel_width, pixel_height) * 0.055)),
                border_color=_with_alpha(_shade_color(button_color, 1.45), 0xFF),
                hover_border_color=_with_alpha(
                    _shade_color(int(style_config.hover_color), 1.55),
                    0xFF,
                ),
                shadow_color=_with_alpha(_shade_color(button_color, 0.20), 0x66),
                shadow_offset_y=max(4, int(pixel_height * 0.06)),
            )
        button_style = {
            "Button": {
                "background_color": button_color,
                "border_radius": int(style_config.border_radius),
                "padding": 0,
                "margin": 0,
            },
            "Button.Label": {
                "color": resolved_text_color,
                "font_size": resolved_font_size,
            },
            "Button:hovered": {
                "background_color": int(style_config.hover_color),
                "border_radius": int(style_config.border_radius),
                "padding": 0,
                "margin": 0,
            },
            "Button.Label:hovered": {
                "color": resolved_text_color,
                "font_size": resolved_font_size,
            },
            "Button:pressed": {
                "background_color": button_color,
                "border_radius": int(style_config.border_radius),
                "padding": 0,
                "margin": 0,
            },
            "Button.Label:pressed": {
                "color": resolved_text_color,
                "font_size": resolved_font_size,
            },
        }
        try:
            stack_kwargs = {
                "width": ui.Pixel(pixel_width),
                "height": ui.Pixel(pixel_height),
                "style": button_style,
                "content_clipping": True,
            }
            with ui.ZStack(**stack_kwargs):
                return self._ui_button(ui, label, clicked_fn, pixel_width, pixel_height)
        except TypeError:
            try:
                with ui.ZStack(
                    width=ui.Pixel(pixel_width),
                    height=ui.Pixel(pixel_height),
                    style=button_style,
                ):
                    return self._ui_button(ui, label, clicked_fn, pixel_width, pixel_height)
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"[{_SOURCE}] ui.Button fallback build failed: {exc!r}")
                return None
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] ui.Button build failed: {exc!r}")
            return None

    def _rounded_button(
        self,
        ui,
        label: str,
        clicked_fn,
        width: int,
        height: int,
        color: int,
        hover_color: int,
        text_color: int,
        font_size: int,
        *,
        radius: int,
        border_width: int = 0,
        border_color: int | None = None,
        hover_border_color: int | None = None,
        shadow_color: int | None = None,
        shadow_offset_y: int = 0,
    ):
        pixel_width = max(1, int(width))
        pixel_height = max(1, int(height))
        border_width = max(0, int(border_width))
        hover_font_size = int(font_size) + max(2, int(round(int(font_size) * 0.06)))
        transparent_button_style = {
            "Button": {
                "background_color": 0x00000000,
                "border_radius": max(1, int(radius)),
                "padding": 0,
                "margin": 0,
            },
            "Button.Label": {
                "color": int(text_color),
                "font_size": int(font_size),
            },
            "Button:hovered": {
                "background_color": 0x00000000,
                "border_radius": max(1, int(radius)),
                "padding": 0,
                "margin": 0,
            },
            "Button.Label:hovered": {
                "color": int(text_color),
                "font_size": hover_font_size,
            },
            "Button:pressed": {
                "background_color": 0x00000000,
                "border_radius": max(1, int(radius)),
                "padding": 0,
                "margin": 0,
            },
            "Button.Label:pressed": {
                "color": int(text_color),
                "font_size": int(font_size),
            },
        }
        try:
            with ui.ZStack(
                width=ui.Pixel(pixel_width),
                height=ui.Pixel(pixel_height),
                content_clipping=True,
            ):
                body = None
                ring = None
                if shadow_color is not None and int(shadow_offset_y) > 0:
                    with ui.Placer(offset_y=ui.Pixel(max(1, int(shadow_offset_y)))):
                        _circle_or_ellipse(
                            ui,
                            width=ui.Pixel(pixel_width),
                            height=ui.Pixel(pixel_height),
                            style={"background_color": int(shadow_color)},
                            radius=max(1, int(radius)),
                        )
                if border_width > 0 and border_color is not None:
                    ring = _circle_or_ellipse(
                        ui,
                        width=ui.Pixel(pixel_width),
                        height=ui.Pixel(pixel_height),
                        style={"background_color": int(border_color)},
                        radius=max(1, int(radius)),
                    )
                    inset = max(1, border_width)
                    body = None
                    with ui.Placer(offset_x=ui.Pixel(inset), offset_y=ui.Pixel(inset)):
                        body = _circle_or_ellipse(
                            ui,
                            width=ui.Pixel(max(1, pixel_width - inset * 2)),
                            height=ui.Pixel(max(1, pixel_height - inset * 2)),
                            style={"background_color": int(color)},
                            radius=max(1, int(radius) - inset),
                        )
                else:
                    body = _circle_or_ellipse(
                        ui,
                        width=ui.Pixel(pixel_width),
                        height=ui.Pixel(pixel_height),
                        style={"background_color": int(color)},
                        radius=max(1, int(radius)),
                    )
                button = ui.Button(
                    str(label),
                    clicked_fn=self._deferred_callback(clicked_fn),
                    width=ui.Pixel(pixel_width),
                    height=ui.Pixel(pixel_height),
                    tooltip=str(label),
                    style=transparent_button_style,
                )
                return button
        except TypeError:
            try:
                with ui.ZStack(
                    width=ui.Pixel(pixel_width),
                    height=ui.Pixel(pixel_height),
                ):
                    return self._ui_button(ui, label, clicked_fn, pixel_width, pixel_height)
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"[{_SOURCE}] rounded button fallback build failed: {exc!r}")
                return None
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] rounded button build failed: {exc!r}")
            return None

    def _shape_button(
        self,
        ui,
        label: str,
        clicked_fn,
        width: int,
        height: int,
        color: int,
        hover_color: int,
        text_color: int,
        font_size: int,
        origin: tuple[int, int] | None = None,
    ):
        pixel_width = max(1, int(width))
        pixel_height = max(1, int(height))
        try:
            with ui.ZStack(
                width=ui.Pixel(pixel_width),
                height=ui.Pixel(pixel_height),
                content_clipping=True,
            ):
                circle = ui.Circle(
                    width=ui.Pixel(pixel_width),
                    height=ui.Pixel(pixel_height),
                    radius=ui.Pixel(max(1, int(min(pixel_width, pixel_height) / 2))),
                    style={"background_color": int(color)},
                )
                label_kwargs = {
                    "width": ui.Pixel(pixel_width),
                    "height": ui.Pixel(pixel_height),
                    "style": {"color": int(text_color), "font_size": int(font_size)},
                }
                try:
                    ui.Label(str(label), alignment=ui.Alignment.CENTER, **label_kwargs)
                except TypeError:
                    ui.Label(str(label), **label_kwargs)
                return self._hit_rect(
                    ui,
                    clicked_fn,
                    pixel_width,
                    pixel_height,
                    hit_shape="ellipse",
                    origin=origin,
                    on_hover=lambda hovered: _set_widget_style(
                        circle,
                        {"background_color": int(hover_color) if hovered else int(color)},
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] shape button build failed: {exc!r}")
            return self._ui_button(ui, label, clicked_fn, pixel_width, pixel_height)

    def _raised_button(
        self,
        ui,
        label: str,
        clicked_fn,
        width: int,
        height: int,
        color: int,
        hover_color: int,
        text_color: int,
        font_size: int,
        border_radius: int,
        origin: tuple[int, int] | None = None,
    ):
        pixel_width = max(1, int(width))
        pixel_height = max(1, int(height))
        radius = max(2, int(border_radius) * 2)
        shadow_offset = max(2, min(10, int(pixel_height * 0.10)))
        body_height = max(1, pixel_height - shadow_offset)
        highlight_height = max(1, min(8, int(body_height * 0.18)))
        shadow_color = _with_alpha(_shade_color(color, 0.35), 0xAA)
        highlight_color = _with_alpha(_shade_color(color, 1.45), 0xCC)
        hover_shadow_color = _with_alpha(_shade_color(hover_color, 0.35), 0xAA)
        hover_highlight_color = _with_alpha(_shade_color(hover_color, 1.45), 0xCC)
        try:
            with ui.ZStack(
                width=ui.Pixel(pixel_width),
                height=ui.Pixel(pixel_height),
                content_clipping=True,
            ):
                with ui.Placer(offset_y=ui.Pixel(shadow_offset)):
                    shadow_rect = ui.Rectangle(
                        width=ui.Pixel(pixel_width),
                        height=ui.Pixel(body_height),
                        style={
                            "background_color": shadow_color,
                            "border_radius": radius,
                        },
                    )
                body_rect = ui.Rectangle(
                    width=ui.Pixel(pixel_width),
                    height=ui.Pixel(body_height),
                    style={
                        "background_color": int(color),
                        "border_radius": radius,
                    },
                )
                highlight_rect = ui.Rectangle(
                    width=ui.Pixel(pixel_width),
                    height=ui.Pixel(highlight_height),
                    style={
                        "background_color": highlight_color,
                        "border_radius": radius,
                    },
                )
                label_kwargs = {
                    "width": ui.Pixel(pixel_width),
                    "height": ui.Pixel(body_height),
                    "style": {"color": int(text_color), "font_size": int(font_size)},
                }
                try:
                    ui.Label(str(label), alignment=ui.Alignment.CENTER, **label_kwargs)
                except TypeError:
                    ui.Label(str(label), **label_kwargs)
                def set_hover(hovered: bool) -> None:
                    active_color = int(hover_color) if hovered else int(color)
                    active_shadow = hover_shadow_color if hovered else shadow_color
                    active_highlight = hover_highlight_color if hovered else highlight_color
                    _set_widget_style(
                        shadow_rect,
                        {"background_color": active_shadow, "border_radius": radius},
                    )
                    _set_widget_style(
                        body_rect,
                        {"background_color": active_color, "border_radius": radius},
                    )
                    _set_widget_style(
                        highlight_rect,
                        {"background_color": active_highlight, "border_radius": radius},
                    )

                return self._hit_rect(
                    ui,
                    clicked_fn,
                    pixel_width,
                    pixel_height,
                    origin=origin,
                    on_hover=set_hover,
                )
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] raised button build failed: {exc!r}")
            return self._ui_button(ui, label, clicked_fn, pixel_width, pixel_height)

    def _orb_button(
        self,
        ui,
        label: str,
        clicked_fn,
        width: int,
        height: int,
        color: int,
        hover_color: int,
        text_color: int,
        font_size: int,
        origin: tuple[int, int] | None = None,
    ):
        pixel_width = max(1, int(width))
        pixel_height = max(1, int(height))
        outer_w = pixel_width
        outer_h = pixel_height
        ring = max(3, int(min(outer_w, outer_h) * 0.055))
        inner_w = max(1, outer_w - ring * 2)
        inner_h = max(1, outer_h - ring * 2)
        inset = max(1, ring)
        shadow_y = max(3, int(min(outer_w, outer_h) * 0.08))
        ring_color = _with_alpha(_shade_color(color, 1.75), 0xF2)
        shadow_color = _with_alpha(_shade_color(color, 0.22), 0xAA)
        hover_ring_color = _with_alpha(_shade_color(hover_color, 1.75), 0xF2)
        hover_shadow_color = _with_alpha(_shade_color(hover_color, 0.22), 0xAA)
        try:
            with ui.ZStack(
                width=ui.Pixel(pixel_width),
                height=ui.Pixel(pixel_height),
                content_clipping=True,
            ):
                with ui.Placer(offset_y=ui.Pixel(shadow_y)):
                    shadow_circle = ui.Circle(
                        width=ui.Pixel(outer_w),
                        height=ui.Pixel(outer_h),
                        radius=ui.Pixel(max(1, int(min(outer_w, outer_h) / 2))),
                        style={"background_color": shadow_color},
                    )
                ring_circle = ui.Circle(
                    width=ui.Pixel(outer_w),
                    height=ui.Pixel(outer_h),
                    radius=ui.Pixel(max(1, int(min(outer_w, outer_h) / 2))),
                    style={"background_color": ring_color},
                )
                with ui.Placer(offset_x=ui.Pixel(inset), offset_y=ui.Pixel(inset)):
                    body_circle = ui.Circle(
                        width=ui.Pixel(inner_w),
                        height=ui.Pixel(inner_h),
                        radius=ui.Pixel(max(1, int(min(inner_w, inner_h) / 2))),
                        style={"background_color": int(color)},
                    )
                label_kwargs = {
                    "width": ui.Pixel(pixel_width),
                    "height": ui.Pixel(pixel_height),
                    "style": {
                        "color": int(text_color),
                        "font_size": int(font_size),
                    },
                }
                try:
                    ui.Label(str(label), alignment=ui.Alignment.CENTER, **label_kwargs)
                except TypeError:
                    ui.Label(str(label), **label_kwargs)
                def set_hover(hovered: bool) -> None:
                    _set_widget_style(
                        shadow_circle,
                        {"background_color": hover_shadow_color if hovered else shadow_color},
                    )
                    _set_widget_style(
                        ring_circle,
                        {"background_color": hover_ring_color if hovered else ring_color},
                    )
                    _set_widget_style(
                        body_circle,
                        {"background_color": int(hover_color) if hovered else int(color)},
                    )

                return self._hit_rect(
                    ui,
                    clicked_fn,
                    pixel_width,
                    pixel_height,
                    hit_shape="ellipse",
                    origin=origin,
                    on_hover=set_hover,
                )
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] orb button build failed: {exc!r}")
            return self._ui_button(ui, label, clicked_fn, pixel_width, pixel_height)

    def _ui_button(self, ui, label: str, clicked_fn, width: int, height: int):
        kwargs = {
            "clicked_fn": self._deferred_callback(clicked_fn),
            "width": ui.Pixel(max(1, int(width))),
            "height": ui.Pixel(max(1, int(height))),
            "tooltip": str(label),
            "opaque_for_mouse_events": True,
        }
        try:
            return ui.Button(str(label), **kwargs)
        except TypeError:
            kwargs.pop("opaque_for_mouse_events", None)
            return ui.Button(str(label), **kwargs)

    def _back_button_rect(self, config: ButtonModeConfig) -> tuple[int, int, int, int]:
        width, height = self._viewport_size()
        if width <= 0 or height <= 0:
            width, height = 1280, 720
        return visible_pixel_rect(
            PercentRect(
                config.back_button.x_pct,
                config.back_button.y_pct,
                config.back_button.w_pct,
                config.back_button.h_pct,
            ),
            width,
            height,
            min_width=56,
            min_height=22,
        )

    def _root_stack(self, ui):
        return ui.ZStack(width=ui.Fraction(1), height=ui.Fraction(1))

    def _overlay_background(self, ui, config: ButtonModeConfig, *, force: bool = False) -> None:
        if not force and not bool(getattr(config.button_style, "dim_overlay", True)):
            return
        try:
            ui.Rectangle(
                width=ui.Fraction(1),
                height=ui.Fraction(1),
                style={"background_color": config.button_style.overlay_color},
            )
        except Exception:  # noqa: BLE001
            pass

    def _preview_overlay_background(self, ui, config: ButtonModeConfig) -> None:
        try:
            opacity = float(getattr(config.button_style, "preview_dim_opacity", 0.65))
        except Exception:  # noqa: BLE001
            opacity = 0.65
        opacity = max(0.0, min(1.0, opacity))
        alpha = max(0, min(255, int(round(opacity * 255))))
        try:
            ui.Rectangle(
                width=ui.Fraction(1),
                height=ui.Fraction(1),
                style={"background_color": (alpha << 24)},
            )
        except Exception:  # noqa: BLE001
            pass

    def _preview_tile(
        self,
        ui,
        index: int,
        result: CaptureResult,
        on_select: Callable[[int], None],
        width: int,
        height: int,
        config: ButtonModeConfig,
    ) -> None:
        display_kind = choose_display_kind(result)
        rendered_image = False
        label = _preview_label(index, result)
        tooltip = result.image_path or result.error or result.camera_path

        try:
            with ui.ZStack(
                width=ui.Pixel(width),
                height=ui.Pixel(height),
                content_clipping=True,
            ):
                ui.Rectangle(
                    width=ui.Pixel(width),
                    height=ui.Pixel(height),
                    style={
                        "background_color": config.button_style.panel_color,
                        "border_color": config.button_style.tile_border_color,
                        "border_width": 1,
                    },
                )
                if display_kind == "image":
                    rendered_image = self._show_image(ui, result.image_path, width, height)
                if not rendered_image:
                    ui.Label(
                        label,
                        style={"color": config.button_style.text_color},
                        word_wrap=True,
                    )
                hit_rect = self._hit_rect(
                    ui,
                    clicked_fn=(
                        (lambda index=index: on_select(index))
                        if rendered_image and not result.error
                        else _noop
                    ),
                    width=width,
                    height=height,
                )
                try:
                    hit_rect.tooltip = tooltip
                except Exception:  # noqa: BLE001
                    pass
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] preview tile build failed: {exc!r}")

    def _hit_rect(
        self,
        ui,
        clicked_fn,
        width: int,
        height: int,
        *,
        on_hover=None,
        hit_shape: str = "rect",
        origin: tuple[int, int] | None = None,
    ):
        try:
            rect = ui.Rectangle(
                width=ui.Pixel(max(1, int(width))),
                height=ui.Pixel(max(1, int(height))),
                opaque_for_mouse_events=True,
                style={"background_color": 0x00000000},
            )
        except TypeError:
            rect = ui.Rectangle(
                width=ui.Pixel(max(1, int(width))),
                height=ui.Pixel(max(1, int(height))),
                style={"background_color": 0x00000000},
            )

        fired = {"value": False}
        hovered = {"value": False}
        hover_polling = {"value": False}
        normalized_hit_shape = str(hit_shape or "rect").strip().lower()

        def set_hover(value: bool) -> None:
            if on_hover is None or hovered["value"] == value:
                return
            hovered["value"] = value
            try:
                on_hover(value)
            except Exception:  # noqa: BLE001
                pass
            if value:
                start_hover_polling()

        def local_point_from_event(x, y) -> tuple[float, float] | None:
            try:
                px = float(x)
                py = float(y)
            except Exception:  # noqa: BLE001
                return None
            if 0.0 <= px <= float(width) and 0.0 <= py <= float(height):
                return px, py
            if origin is not None:
                ox, oy = float(origin[0]), float(origin[1])
                local_x = px - ox
                local_y = py - oy
                if 0.0 <= local_x <= float(width) and 0.0 <= local_y <= float(height):
                    return local_x, local_y
            widget_origin = _widget_screen_origin(rect)
            if widget_origin is None:
                return None
            ox, oy = widget_origin
            local_x = px - ox
            local_y = py - oy
            if 0.0 <= local_x <= float(width) and 0.0 <= local_y <= float(height):
                return local_x, local_y
            return None

        def point_inside_hit_shape(point: tuple[float, float] | None) -> bool:
            if point is None:
                return normalized_hit_shape == "rect"
            x, y = point
            if normalized_hit_shape != "ellipse":
                return 0.0 <= x <= float(width) and 0.0 <= y <= float(height)
            rx = max(0.5, float(width) / 2.0)
            ry = max(0.5, float(height) / 2.0)
            nx = (x - rx) / rx
            ny = (y - ry) / ry
            return (nx * nx + ny * ny) <= 1.0

        def event_inside_hit_shape(args) -> bool:
            if normalized_hit_shape == "rect":
                return True
            if len(args) < 2:
                return False
            return point_inside_hit_shape(local_point_from_event(args[0], args[1]))

        def cursor_inside_hit_shape() -> bool | None:
            if origin is None:
                return None
            cursor = _read_current_cursor_position()
            if cursor is None:
                return None
            local_x = float(cursor[0]) - float(origin[0])
            local_y = float(cursor[1]) - float(origin[1])
            if not (0.0 <= local_x <= float(width) and 0.0 <= local_y <= float(height)):
                return False
            return point_inside_hit_shape((local_x, local_y))

        async def poll_hover() -> None:
            try:
                while hovered["value"]:
                    await asyncio.sleep(0.05)
                    inside = cursor_inside_hit_shape()
                    if inside is False:
                        set_hover(False)
                        break
                    if inside is None:
                        break
            except Exception:  # noqa: BLE001
                pass
            finally:
                hover_polling["value"] = False

        def start_hover_polling() -> None:
            if hover_polling["value"]:
                return
            hover_polling["value"] = True
            try:
                asyncio.ensure_future(poll_hover())
            except Exception:  # noqa: BLE001
                hover_polling["value"] = False

        def on_mouse(button, *args) -> None:
            if not event_inside_hit_shape(args):
                set_hover(False)
                return
            try:
                button_index = int(button)
            except Exception:  # noqa: BLE001
                button_index = 0
            if button_index != 0 or fired["value"]:
                return
            fired["value"] = True

            def run_once() -> None:
                try:
                    clicked_fn()
                finally:
                    fired["value"] = False

            self._defer_callback(run_once)

        bound = False
        for setter_name in ("set_mouse_pressed_fn", "set_mouse_released_fn"):
            try:
                getattr(rect, setter_name)(
                    lambda x, y, button, modifier: on_mouse(button, x, y)
                )
                bound = True
            except Exception:  # noqa: BLE001
                continue
        if not bound:
            try:
                rect.set_mouse_clicked_fn(
                    lambda x, y, button, modifier: on_mouse(button, x, y)
                )
            except Exception:  # noqa: BLE001
                pass
        for setter_name, value in (
            ("set_mouse_entered_fn", True),
            ("set_mouse_hovered_fn", True),
            ("set_mouse_moved_fn", True),
            ("set_mouse_exited_fn", False),
            ("set_mouse_left_fn", False),
        ):
            try:
                getattr(rect, setter_name)(
                    lambda *args, value=value: (
                        set_hover(value) if value and event_inside_hit_shape(args) else set_hover(False)
                    )
                )
            except Exception:  # noqa: BLE001
                continue
        return rect

    def _show_image(self, ui, image_path: str, width: int, height: int) -> bool:
        for factory_name in ("Image", "ImageWithProvider"):
            factory = getattr(ui, factory_name, None)
            if not callable(factory):
                continue
            try:
                kwargs = {
                    "width": ui.Pixel(max(1, int(width))),
                    "height": ui.Pixel(max(1, int(height))),
                }
                try:
                    fill_policy = getattr(ui.FillPolicy, "PRESERVE_ASPECT_CROP", None)
                    if fill_policy is not None:
                        kwargs["fill_policy"] = fill_policy
                except Exception:  # noqa: BLE001
                    pass
                factory(image_path, **kwargs)
                return True
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"[{_SOURCE}] {factory_name} failed: {exc!r}")
        return False

    def _ui(self):
        try:
            import omni.ui as ui  # noqa: WPS433

            return ui
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] omni.ui import failed: {exc!r}")
            return None

    def _deferred_callback(self, callback):
        def wrapped() -> None:
            self._defer_callback(callback)

        return wrapped

    def _defer_callback(self, callback) -> None:
        try:
            asyncio.ensure_future(_run_after_next_update(callback))
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] callback defer failed: {exc!r}")


def _widget_screen_origin(widget) -> tuple[float, float] | None:
    try:
        x = float(widget.screen_position_x)
        y = float(widget.screen_position_y)
    except Exception:  # noqa: BLE001
        return None
    return x, y


def _read_current_cursor_position() -> tuple[float, float] | None:
    try:
        from .top_view_controller import _read_cursor_position_from_viewport  # noqa: WPS433

        return _read_cursor_position_from_viewport()
    except Exception:  # noqa: BLE001
        return None


def _pad_results(results: Sequence[CaptureResult], *, count: int) -> list[CaptureResult]:
    padded = list(results[:count])
    while len(padded) < count:
        padded.append(
            CaptureResult(
                camera_path="",
                image_path="",
                width=0,
                height=0,
                error="missing preview result",
            )
        )
    return padded


def _preview_label(index: int, result: CaptureResult) -> str:
    prefix = f"Camera {index + 1}"
    if result.error:
        return f"{prefix}\nUnavailable"
    if result.camera_path:
        return f"{prefix}\n{result.camera_path.rsplit('/', 1)[-1]}"
    return f"{prefix}\nNo camera"


def _noop() -> None:
    return None


async def _run_after_next_update(callback) -> None:
    try:
        import omni.kit.app  # type: ignore[import-not-found] # noqa: WPS433

        await omni.kit.app.get_app().next_update_async()
    except Exception as exc:  # noqa: BLE001
        _log_warn(f"[{_SOURCE}] next update wait failed: {exc!r}")
    try:
        callback()
    except Exception as exc:  # noqa: BLE001
        _log_warn(f"[{_SOURCE}] deferred callback failed: {exc!r}")


def _style(config: ButtonModeConfig | None) -> ButtonStyleConfig:
    if config is None:
        return ButtonStyleConfig()
    return config.button_style


def _ordered_button_keys(
    buttons: dict[str, object],
    selected: Sequence[str] | None = None,
) -> list[str]:
    source = set(selected) if selected is not None else set(buttons)
    preferred = [key for key in ("a", "b") if key in source and key in buttons]
    extra = sorted(key for key in source if key in buttons and key not in {"a", "b"})
    return preferred + extra


def _avoid_overlap(
    x: int,
    y: int,
    width: int,
    height: int,
    placed: list[tuple[int, int, int, int]],
    viewport_width: int,
    viewport_height: int,
) -> tuple[int, int]:
    for other_x, other_y, other_w, other_h in placed:
        if not _rects_overlap(x, y, width, height, other_x, other_y, other_w, other_h):
            continue
        candidate_y = other_y + other_h + 8
        if candidate_y + height <= viewport_height:
            return x, candidate_y
        candidate_y = max(0, other_y - height - 8)
        if candidate_y != y:
            return x, candidate_y
        candidate_x = other_x + other_w + 8
        if candidate_x + width <= viewport_width:
            return candidate_x, y
    return x, y


def _rects_overlap(
    ax: int,
    ay: int,
    aw: int,
    ah: int,
    bx: int,
    by: int,
    bw: int,
    bh: int,
) -> bool:
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


class _PreviewLayout:
    __slots__ = ("gap", "grid_x", "grid_y", "tile_h", "tile_w")

    def __init__(
        self,
        *,
        gap: int,
        grid_x: int,
        grid_y: int,
        tile_w: int,
        tile_h: int,
    ) -> None:
        self.gap = gap
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.tile_w = tile_w
        self.tile_h = tile_h


def _preview_layout(
    viewport_width: float,
    viewport_height: float,
    config: ButtonModeConfig,
) -> _PreviewLayout:
    width = int(viewport_width) if viewport_width and viewport_width > 0 else 1280
    height = int(viewport_height) if viewport_height and viewport_height > 0 else 720
    margin = 24
    gap = 12
    available_w = max(320, width - margin * 2)
    available_h = max(240, height - margin * 2 - 44)
    tile_w = min(360, max(150, int((available_w - gap) / 2)))
    tile_h = int(tile_w * 9 / 16)
    max_tile_h = max(100, int((available_h - gap) / 2))
    if tile_h > max_tile_h:
        tile_h = max_tile_h
        tile_w = int(tile_h * 16 / 9)
    grid_w = tile_w * 2 + gap
    grid_h = tile_h * 2 + gap
    center_x = int(width * config.preview_grid.center_x_pct)
    center_y = int(height * config.preview_grid.center_y_pct)
    grid_x = _clamp_int(center_x - int(grid_w / 2), margin, max(margin, width - margin - grid_w))
    grid_y = _clamp_int(center_y - int(grid_h / 2), 64, max(64, height - margin - grid_h))
    return _PreviewLayout(
        gap=gap,
        grid_x=grid_x,
        grid_y=grid_y,
        tile_w=tile_w,
        tile_h=tile_h,
    )


def _matrix_layout(
    viewport_width: float,
    viewport_height: float,
    config: ButtonModeConfig,
    *,
    count: int = 5,
) -> _PreviewLayout:
    width = int(viewport_width) if viewport_width and viewport_width > 0 else 1280
    height = int(viewport_height) if viewport_height and viewport_height > 0 else 720
    margin = 28
    gap = 12
    available_w = max(420, width - margin * 2)
    available_h = max(240, height - margin * 2)
    columns = 3 if count >= 6 else 4
    tile_w = int((available_w - gap * (columns - 1)) / columns)
    tile_h = int(tile_w * 9 / 16)
    max_tile_h = int((available_h - gap) / 2)
    if tile_h > max_tile_h:
        tile_h = max(80, max_tile_h)
        tile_w = int(tile_h * 16 / 9)
    tile_w = max(100, min(tile_w, 320))
    tile_h = max(72, min(tile_h, 236))
    scale = max(0.5, min(2.0, float(getattr(config, "preview_overlay_scale", 1.0))))
    tile_w = max(50, int(round(tile_w * scale)))
    tile_h = max(36, int(round(tile_h * scale)))
    gap = max(4, int(round(gap * scale)))
    grid_w = tile_w * columns + gap * (columns - 1)
    grid_h = tile_h * 2 + gap
    if grid_w > available_w or grid_h > available_h:
        width_fit = (
            (available_w - gap * (columns - 1)) / max(1, tile_w * columns)
        )
        height_fit = (available_h - gap) / max(1, tile_h * 2)
        fit = max(0.1, min(1.0, width_fit, height_fit))
        tile_w = max(50, int(round(tile_w * fit)))
        tile_h = max(36, int(round(tile_h * fit)))
        gap = max(4, int(round(gap * fit)))
        grid_w = tile_w * columns + gap * (columns - 1)
        grid_h = tile_h * 2 + gap
    center_x = int(width * config.preview_grid.center_x_pct)
    center_y = int(height * config.preview_grid.center_y_pct)
    return _PreviewLayout(
        gap=gap,
        grid_x=_clamp_int(
            center_x - int(grid_w / 2),
            margin,
            max(margin, width - margin - grid_w),
        ),
        grid_y=_clamp_int(
            center_y - int(grid_h / 2),
            margin,
            max(margin, height - margin - grid_h),
        ),
        tile_w=tile_w,
        tile_h=tile_h,
    )


def _matrix_tile_rect(
    layout: _PreviewLayout,
    index: int,
    *,
    count: int = 5,
) -> tuple[int, int, int, int]:
    if count >= 6:
        col = index % 3
        row = index // 3
        x = layout.grid_x + col * (layout.tile_w + layout.gap)
        y = layout.grid_y + row * (layout.tile_h + layout.gap)
        return x, y, layout.tile_w, layout.tile_h

    if index < 4:
        col = index % 2
        row = index // 2
        x = layout.grid_x + col * (layout.tile_w + layout.gap)
        y = layout.grid_y + row * (layout.tile_h + layout.gap)
        return x, y, layout.tile_w, layout.tile_h

    big_x = layout.grid_x + 2 * (layout.tile_w + layout.gap)
    big_y = layout.grid_y
    big_w = layout.tile_w * 2 + layout.gap
    big_h = layout.tile_h * 2 + layout.gap
    return big_x, big_y, big_w, big_h


def _shade_color(color: int, factor: float) -> int:
    alpha = int(color) & 0xFF000000
    red = int(color) & 0x000000FF
    green = (int(color) >> 8) & 0xFF
    blue = (int(color) >> 16) & 0xFF
    red = max(0, min(255, int(round(red * factor))))
    green = max(0, min(255, int(round(green * factor))))
    blue = max(0, min(255, int(round(blue * factor))))
    return alpha | (blue << 16) | (green << 8) | red


def _with_alpha(color: int, alpha: int) -> int:
    return (max(0, min(255, int(alpha))) << 24) | (int(color) & 0x00FFFFFF)


def _circle_or_ellipse(ui, *, width, height, style: dict, radius: int):
    try:
        return ui.Circle(width=width, height=height, style=style)
    except TypeError:
        return ui.Circle(
            width=width,
            height=height,
            radius=ui.Pixel(max(1, int(radius))),
            style=style,
        )


def _set_widget_style(widget, style: dict) -> None:
    try:
        set_style = getattr(widget, "set_style", None)
        if callable(set_style):
            set_style(style)
            return
    except Exception:  # noqa: BLE001
        pass
    try:
        widget.style = style
    except Exception:  # noqa: BLE001
        pass


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))
