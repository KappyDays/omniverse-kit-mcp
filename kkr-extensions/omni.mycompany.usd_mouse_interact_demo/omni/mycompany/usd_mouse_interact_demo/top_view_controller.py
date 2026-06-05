"""Top View mode controller for pointer hover interaction."""

from __future__ import annotations

import logging
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .config_model import TopViewConfig
from .viewport_camera import (
    ViewportCameraSwitcher,
    normalize_camera_path,
    validate_camera_path,
)

if TYPE_CHECKING:
    from .crosshair_overlay import CrosshairOverlay
    from .pick_highlighter import PickHighlighter

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.top_view_controller"
_POINTER_SENSITIVITY_BASE = 0.04


def _log_info(message: str) -> None:
    try:
        import carb  # noqa: WPS433

        carb.log_info(message)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).info(message)


def _log_warn(message: str) -> None:
    try:
        import carb  # noqa: WPS433

        carb.log_warn(message)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).warning(message)


class TopViewController:
    """Owns Top View activation, camera lock, pointer crosshair, and hover pick."""

    def __init__(
        self,
        highlighter: Optional["PickHighlighter"] = None,
        *,
        crosshair: Optional["CrosshairOverlay"] = None,
        camera_switcher: Optional[ViewportCameraSwitcher] = None,
        cursor_reader: Optional[Callable[[], Optional[tuple[float, float]]]] = None,
        input_sampler: Optional[Callable[[Optional[tuple[int, int]], float], tuple[float, float]]] = None,
    ) -> None:
        self._config = TopViewConfig()
        self._crosshair = crosshair if crosshair is not None else _make_crosshair_overlay()
        self._highlighter = highlighter if highlighter is not None else _make_pick_highlighter()
        self._camera_switcher = (
            camera_switcher if camera_switcher is not None else ViewportCameraSwitcher()
        )
        self._cursor_reader = cursor_reader
        self._input_sampler = input_sampler
        self._input_router = None
        self._mouse = None
        self._pointer_state = _VirtualPointerState()
        self._sensitivity = 25.0
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def configure(self, config: TopViewConfig) -> None:
        self._config = config

    def set_sensitivity(self, value: float) -> None:
        self._sensitivity = max(1.0, float(value))

    def activate(self) -> bool:
        if self._active:
            return True

        stage = _get_current_stage()
        if stage is None:
            _log_warn(f"[{_SOURCE}] no USD stage for Top View activation")
            return False

        validation_error = validate_camera_path(stage, self._config.camera_path)
        if validation_error is not None:
            _log_warn(f"[{_SOURCE}] {validation_error}")
            return False

        try:
            self._camera_switcher.save_current()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] save current camera failed: {exc!r}")

        if not self._camera_switcher.set_active_camera(self._config.camera_path, stage=stage):
            try:
                self._camera_switcher.restore_saved()
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{_SOURCE}] restore after activation failure failed: {exc!r}")
            return False

        try:
            self._crosshair.show_at_pointer()
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] pointer crosshair show failed: {exc!r}")
            try:
                self._camera_switcher.restore_saved()
            except Exception as restore_exc:  # noqa: BLE001
                _log_info(f"[{_SOURCE}] restore after crosshair failure failed: {restore_exc!r}")
            return False

        size = _read_viewport_size()
        if size is not None:
            self._pointer_state.reset_to_center(size[0], size[1])

        try:
            self._activate_input()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] top-view input activate failed: {exc!r}")

        self._active = True
        return True

    def deactivate(self) -> None:
        try:
            self._deactivate_input()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] top-view input deactivate failed: {exc!r}")
        try:
            self._crosshair.hide()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] crosshair hide failed: {exc!r}")
        try:
            cancel_pending = getattr(self._highlighter, "cancel_pending_queries", None)
            if callable(cancel_pending):
                cancel_pending()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] pending query cancel failed: {exc!r}")
        try:
            self._highlighter.clear()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] highlighter clear failed: {exc!r}")
        try:
            self._camera_switcher.restore_saved()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] restore camera failed: {exc!r}")
        self._active = False

    def update(self) -> None:
        if not self._active:
            return

        stage = _get_current_stage()
        if stage is None:
            return

        if self._config.lock_camera:
            self._restore_locked_camera(stage)

        size = _read_viewport_size()
        if size is not None:
            dx, dy = self._sample_input_delta()
            point = self._pointer_state.advance(
                size[0],
                size[1],
                dx,
                dy,
                self._sensitivity,
            )
        else:
            point = self._read_cursor_position()
        if point is None:
            return
        x, y = point

        try:
            self._crosshair.update_pointer_position(x, y)
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] pointer crosshair update failed: {exc!r}")
        try:
            direct_pick = getattr(
                self._highlighter,
                "update_from_camera_viewport_point",
                None,
            )
            if size is not None and callable(direct_pick):
                width, height = size
                direct_pick(self._config.camera_path, x, y, width, height)
            else:
                direct_pick = getattr(
                    self._highlighter,
                    "update_at_viewport_point",
                    None,
                )
                if callable(direct_pick):
                    direct_pick(x, y)
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] pointer highlighter update failed: {exc!r}")

    def _activate_input(self) -> None:
        if self._input_sampler is not None:
            return
        if self._input_router is None:
            self._input_router = _make_fps_input_router()
        if self._mouse is None:
            self._mouse = _make_mouse_capture_session()
        try:
            if self._input_router is not None:
                self._input_router.activate()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] fps input router activate failed: {exc!r}")
        try:
            if self._mouse is not None:
                self._mouse.activate()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] mouse capture activate failed: {exc!r}")

    def _deactivate_input(self) -> None:
        if self._input_sampler is not None:
            return
        try:
            if self._mouse is not None:
                self._mouse.deactivate()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] mouse capture deactivate failed: {exc!r}")
        try:
            if self._input_router is not None:
                self._input_router.deactivate()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] fps input router deactivate failed: {exc!r}")

    def _sample_input_delta(self) -> tuple[float, float]:
        import time

        center = self._read_viewport_center()
        now_s = time.monotonic()
        if self._input_sampler is not None:
            try:
                return self._input_sampler(center, now_s)
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{_SOURCE}] injected input sampler failed: {exc!r}")
                return 0.0, 0.0

        if self._input_router is not None:
            try:
                sample = self._input_router.sample(center, now_s)
                if sample is not None and sample.active:
                    return float(sample.dx), float(sample.dy)
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{_SOURCE}] fps input router sample failed: {exc!r}")

        if self._mouse is not None and center is not None:
            try:
                return self._mouse.read_delta_and_warp(*center)
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{_SOURCE}] mouse capture sample failed: {exc!r}")
        return 0.0, 0.0

    def _read_viewport_center(self) -> Optional[tuple[int, int]]:
        if self._mouse is not None:
            try:
                center = self._mouse.viewport_window_center()
                if center is not None:
                    return center
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{_SOURCE}] viewport center read failed: {exc!r}")
        size = _read_viewport_size()
        if size is None:
            return None
        return int(size[0] * 0.5), int(size[1] * 0.5)

    def _restore_locked_camera(self, stage) -> None:
        target_camera = normalize_camera_path(self._config.camera_path)
        if target_camera is None:
            return
        try:
            active_camera = normalize_camera_path(self._camera_switcher.get_active_camera())
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] active camera read failed: {exc!r}")
            active_camera = None
        if active_camera == target_camera:
            return
        try:
            self._camera_switcher.set_active_camera(target_camera, stage=stage)
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] locked camera restore failed: {exc!r}")

    def _read_cursor_position(self) -> Optional[tuple[float, float]]:
        if self._cursor_reader is not None:
            try:
                return _coerce_point(self._cursor_reader())
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{_SOURCE}] injected cursor reader failed: {exc!r}")
                return None
        return _read_cursor_position_from_viewport()

    def _read_tracked_crosshair_position(self) -> Optional[tuple[float, float]]:
        getter = getattr(self._crosshair, "get_tracked_pointer_position", None)
        if not callable(getter):
            return None
        try:
            return _coerce_point(getter())
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{_SOURCE}] tracked crosshair position failed: {exc!r}")
            return None


def _get_current_stage():
    try:
        import omni.usd as omni_usd  # noqa: WPS433

        return omni_usd.get_context().get_stage()
    except Exception as exc:  # noqa: BLE001
        _log_info(f"[{_SOURCE}] stage read failed: {exc!r}")
        return None


def _make_crosshair_overlay():
    from .crosshair_overlay import CrosshairOverlay  # noqa: WPS433

    return CrosshairOverlay()


def _make_pick_highlighter():
    from .pick_highlighter import PickHighlighter  # noqa: WPS433

    return PickHighlighter()


def _make_fps_input_router():
    try:
        from .fps_input_router import FpsInputRouter  # noqa: WPS433
        from .stream_input_backend import StreamMessageBackend  # noqa: WPS433

        return FpsInputRouter([StreamMessageBackend()])
    except Exception as exc:  # noqa: BLE001
        _log_info(f"[{_SOURCE}] fps input router unavailable: {exc!r}")
        return None


def _make_mouse_capture_session():
    try:
        from .mouse_capture import MouseCaptureSession  # noqa: WPS433

        return MouseCaptureSession()
    except Exception as exc:  # noqa: BLE001
        _log_info(f"[{_SOURCE}] mouse capture unavailable: {exc!r}")
        return None


@dataclass
class _VirtualPointerState:
    x: Optional[float] = None
    y: Optional[float] = None

    def reset_to_center(self, width: float, height: float) -> tuple[float, float]:
        self.x = max(0.0, float(width) * 0.5)
        self.y = max(0.0, float(height) * 0.5)
        return self.x, self.y

    def advance(
        self,
        width: float,
        height: float,
        dx_pixels: float,
        dy_pixels: float,
        sensitivity: float,
    ) -> tuple[float, float]:
        width = max(1.0, float(width))
        height = max(1.0, float(height))
        if self.x is None or self.y is None:
            self.reset_to_center(width, height)

        scale = max(1.0, float(sensitivity)) * _POINTER_SENSITIVITY_BASE
        self.x = _clamp_float(float(self.x) + float(dx_pixels) * scale, 0.0, width - 1.0)
        self.y = _clamp_float(float(self.y) + float(dy_pixels) * scale, 0.0, height - 1.0)
        return self.x, self.y


def _read_cursor_position_from_viewport() -> Optional[tuple[float, float]]:
    try:
        from omni.kit.viewport.utility import get_active_viewport_window  # noqa: WPS433
    except Exception:  # noqa: BLE001
        return None

    try:
        viewport_window = get_active_viewport_window()
    except Exception:  # noqa: BLE001
        return None
    if viewport_window is None:
        return None

    for attr_name in ("local_cursor_position", "viewport_cursor_position"):
        point = _read_point_attr(viewport_window, attr_name)
        if point is not None:
            return _to_viewport_local_point(viewport_window, point)

    for attr_name in ("cursor_position", "mouse_position"):
        point = _read_point_attr(viewport_window, attr_name)
        if point is not None:
            return _to_viewport_point_from_ambiguous_source(viewport_window, point)

    for method_name in ("get_local_cursor_position", "get_viewport_cursor_position"):
        point = _read_point_attr(viewport_window, method_name)
        if point is not None:
            return _to_viewport_local_point(viewport_window, point)

    for method_name in ("get_cursor_position", "get_mouse_position"):
        point = _read_point_attr(viewport_window, method_name)
        if point is not None:
            return _to_viewport_point_from_ambiguous_source(viewport_window, point)

    screen_point = _read_screen_cursor_position()
    if screen_point is None:
        return None
    return _screen_to_viewport_local_point(viewport_window, screen_point)


def _read_viewport_size() -> Optional[tuple[float, float]]:
    try:
        from omni.kit.viewport.utility import get_active_viewport_window  # noqa: WPS433
    except Exception:  # noqa: BLE001
        return None
    try:
        viewport_window = get_active_viewport_window()
    except Exception:  # noqa: BLE001
        return None
    if viewport_window is None:
        return None
    try:
        width = float(getattr(viewport_window, "width", 0.0) or 0.0)
        height = float(getattr(viewport_window, "height", 0.0) or 0.0)
    except Exception:  # noqa: BLE001
        return None
    if not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0:
        return None
    return width, height


def _read_point_attr(obj, attr_name: str) -> Optional[tuple[float, float]]:
    try:
        value = getattr(obj, attr_name, None)
        if callable(value):
            value = value()
    except Exception:  # noqa: BLE001
        return None
    return _coerce_point(value)


def _to_viewport_local_point(
    viewport_window,
    point: tuple[float, float],
) -> Optional[tuple[float, float]]:
    """Normalize either local or screen-space cursor coordinates.

    Kit viewport APIs differ across apps/builds: some expose local viewport
    cursor coordinates, some expose screen coordinates, and some expose no
    cursor point at all. The pick/query path needs viewport-local pixels.
    """
    local_point = _coerce_point(point)
    if local_point is None:
        return None
    x, y = local_point

    rect = _read_viewport_rect(viewport_window)
    if rect is None:
        return local_point

    left, top, width, height = rect
    if 0.0 <= x <= width and 0.0 <= y <= height:
        return x, y

    right = left + width
    bottom = top + height
    if left <= x <= right and top <= y <= bottom:
        return x - left, y - top

    return None


def _to_viewport_point_from_ambiguous_source(
    viewport_window,
    point: tuple[float, float],
) -> Optional[tuple[float, float]]:
    screen_point = _screen_to_viewport_local_point(viewport_window, point)
    if screen_point is not None:
        return screen_point
    return _to_viewport_local_point(viewport_window, point)


def _screen_to_viewport_local_point(
    viewport_window,
    point: tuple[float, float],
) -> Optional[tuple[float, float]]:
    screen_point = _coerce_point(point)
    if screen_point is None:
        return None
    rect = _read_viewport_rect(viewport_window)
    if rect is None:
        return None

    x, y = screen_point
    left, top, width, height = rect
    right = left + width
    bottom = top + height
    if left <= x <= right and top <= y <= bottom:
        return x - left, y - top
    return None


def _read_viewport_rect(viewport_window) -> Optional[tuple[float, float, float, float]]:
    try:
        left = float(getattr(viewport_window, "position_x", 0.0) or 0.0)
        top = float(getattr(viewport_window, "position_y", 0.0) or 0.0)
        width = float(getattr(viewport_window, "width", 0.0) or 0.0)
        height = float(getattr(viewport_window, "height", 0.0) or 0.0)
    except Exception:  # noqa: BLE001
        return None
    if (
        not math.isfinite(left)
        or not math.isfinite(top)
        or not math.isfinite(width)
        or not math.isfinite(height)
        or width <= 0.0
        or height <= 0.0
    ):
        return None
    return left, top, width, height


def _read_screen_cursor_position() -> Optional[tuple[float, float]]:
    """Best-effort screen-space cursor read for hosts without viewport cursor APIs."""
    win32_point = _read_win32_cursor_position()
    if win32_point is not None:
        return win32_point

    app_window = _get_default_app_window()
    windowing_point = _read_carb_windowing_cursor_position(app_window)
    if windowing_point is not None:
        return windowing_point

    return _read_appwindow_cursor_position(app_window)


def _read_win32_cursor_position() -> Optional[tuple[float, float]]:
    if sys.platform != "win32":
        return None
    try:
        import ctypes  # noqa: WPS433
        from ctypes import wintypes  # noqa: WPS433

        class _Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.windll.user32
        user32.GetCursorPos.argtypes = [ctypes.POINTER(_Point)]
        user32.GetCursorPos.restype = wintypes.BOOL
        point = _Point()
        if not user32.GetCursorPos(ctypes.byref(point)):
            return None
        return float(point.x), float(point.y)
    except Exception:  # noqa: BLE001
        return None


def _get_default_app_window():
    try:
        import omni.appwindow  # noqa: WPS433

        return omni.appwindow.get_default_app_window()
    except Exception:  # noqa: BLE001
        return None


def _read_carb_windowing_cursor_position(app_window) -> Optional[tuple[float, float]]:
    if app_window is None:
        return None
    try:
        import carb.windowing  # type: ignore[import-not-found] # noqa: WPS433

        os_window = app_window.get_window()
        windowing = carb.windowing.acquire_windowing_interface()
    except Exception:  # noqa: BLE001
        return None

    for method_name in ("get_cursor_position", "get_cursor_pos"):
        method = getattr(windowing, method_name, None)
        if not callable(method):
            continue
        try:
            point = method(os_window)
        except Exception:  # noqa: BLE001
            continue
        coerced = _coerce_point(point)
        if coerced is not None:
            return coerced
    return None


def _read_appwindow_cursor_position(app_window) -> Optional[tuple[float, float]]:
    if app_window is None:
        return None
    for method_name in ("get_cursor_position", "get_cursor_pos"):
        method = getattr(app_window, method_name, None)
        if not callable(method):
            continue
        try:
            point = method()
        except Exception:  # noqa: BLE001
            continue
        coerced = _coerce_point(point)
        if coerced is not None:
            return coerced
    return None


def _coerce_point(value) -> Optional[tuple[float, float]]:
    if value is None:
        return None
    try:
        x, y = value
    except Exception:  # noqa: BLE001
        try:
            x = value.x
            y = value.y
        except Exception:  # noqa: BLE001
            return None
    try:
        px = float(x)
        py = float(y)
    except Exception:  # noqa: BLE001
        return None
    if not math.isfinite(px) or not math.isfinite(py):
        return None
    return px, py


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
