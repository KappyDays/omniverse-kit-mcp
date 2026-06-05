"""Mouse-capture session: hide cursor + warp cursor to viewport center each frame.

Strategy
--------
We avoid OS-level raw input. Instead, every frame:

1. read current cursor position (pixels, screen-space)
2. compute delta from the viewport-window center
3. warp cursor back to the viewport center

This produces an unbounded mouse delta even when cursor would otherwise hit the
screen edge. Cursor visibility is toggled best-effort via omni.appwindow; if the
underlying API isn't available the cursor stays visible at the center.

Warp path priority (v0.2.1):
  1. **Win32 user32.GetCursorPos / SetCursorPos** via ctypes — works on every
     Kit-on-Windows host (Isaac Sim AND USD Composer). Bypasses Kit's appwindow
     surface entirely so it doesn't matter whether `set_cursor_position` is
     bound or not.
  2. carb.windowing.acquire_windowing_interface() — Isaac Sim fallback.
  3. appwindow cursor methods — USD Composer-only fallback (rarely effective).
If all three fail, delta is reported as 0 (camera rotation disabled, everything
else still works — see ``_probe_warp_support``).
"""

from __future__ import annotations

import os
import sys
from typing import Optional, Tuple

import carb

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.mouse_capture"

# --- Win32 cursor helpers (ctypes) --------------------------------------
# Kit ships on Windows; the user32 path is the only one that consistently
# moves the OS cursor in USD Composer. We import lazily to keep the module
# importable on Linux / macOS unit-test runners.
_IS_WINDOWS = sys.platform == "win32"
_user32 = None
_POINT_TYPE = None
_OUR_PID: Optional[int] = None
if _IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes

        class _POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        _user32 = ctypes.windll.user32
        _user32.GetCursorPos.argtypes = [ctypes.POINTER(_POINT)]
        _user32.GetCursorPos.restype = wintypes.BOOL
        _user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        _user32.SetCursorPos.restype = wintypes.BOOL
        # GetForegroundWindow + GetWindowThreadProcessId for focus probing —
        # used to pause cursor warp when the user alt-tabs to another app so
        # that fly mode doesn't keep dragging the cursor back to viewport
        # center while the user is interacting with a different window.
        _user32.GetForegroundWindow.argtypes = []
        _user32.GetForegroundWindow.restype = wintypes.HWND
        _user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
        ]
        _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        _POINT_TYPE = _POINT
        _OUR_PID = os.getpid()
    except Exception:  # noqa: BLE001
        _user32 = None
        _POINT_TYPE = None
        _OUR_PID = None


def _is_kit_foreground() -> bool:
    """Return True iff the OS foreground window belongs to our Kit process.

    Used to gate cursor warp during fly mode — when the user alt-tabs away,
    we pause warp so the cursor can be used freely in the other application.

    Strategy: GetForegroundWindow → GetWindowThreadProcessId → compare PID
    against ours. Matching by PID (not HWND) is robust across Kit's many
    sub-windows (viewport, dev panel, modal dialogs etc) — any of them
    counts as "Kit focused".

    Fall back to True (= proceed with warp) on non-Windows hosts and on
    probe error so we don't accidentally disable fly mode on robust setups.
    """
    if not _IS_WINDOWS or _user32 is None or _OUR_PID is None:
        return True
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value) == _OUR_PID
    except Exception:  # noqa: BLE001
        return True


class MouseCaptureSession:

    def __init__(self) -> None:
        self._engaged = False
        self._app_window = None   # omni.appwindow.IAppWindow
        self._os_window = None    # carb.windowing window handle
        self._windowing = None    # carb.windowing interface (or None)
        self._cursor_was_visible = True
        self._first_frame_skipped = False
        # Warp-unsupported hosts (USD Composer Kit 110: appwindow exposes neither
        # set_cursor_position nor set_cursor_pos) leave the cursor where it sits.
        # Without a guard, each frame re-computes a large delta from the off-
        # center cursor → yaw integrates to thousands of radians within seconds.
        # _warp_works is probed once at engage-time; when False, deltas are
        # forced to zero (camera rotation effectively disabled — translation +
        # picker still work).
        self._warp_works = True

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def engage(self) -> bool:
        if self._engaged:
            return True
        try:
            import omni.appwindow

            self._app_window = omni.appwindow.get_default_app_window()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] get_default_app_window failed: {exc!r}")
            self._app_window = None

        # Acquire os_window handle for carb.windowing calls.
        self._os_window = None
        if self._app_window is not None:
            try:
                self._os_window = self._app_window.get_window()
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] get_window failed: {exc!r}")

        # Try carb.windowing — available in Isaac Sim, not in USD Composer.
        self._windowing = None
        try:
            import carb.windowing  # type: ignore

            self._windowing = carb.windowing.acquire_windowing_interface()
        except Exception:  # noqa: BLE001
            carb.log_info(
                f"[{_SOURCE}] carb.windowing unavailable — using appwindow cursor API"
            )

        # Best-effort cursor hide
        self._set_cursor_visible(False)
        self._engaged = True
        self._first_frame_skipped = False

        # Probe warp support: read pos → warp by +5px → read again. If the
        # second read isn't near the warp target, the host doesn't honor the
        # warp call and we must zero deltas to prevent yaw runaway.
        self._warp_works = self._probe_warp_support()
        if not self._warp_works:
            carb.log_warn(
                f"[{_SOURCE}] cursor warp unsupported on this host — "
                f"camera rotation disabled (translation + picker still work)"
            )

        carb.log_info(f"[{_SOURCE}] engaged (warp_works={self._warp_works})")
        return True

    def disengage(self) -> None:
        if not self._engaged:
            return
        self._set_cursor_visible(True)
        self._engaged = False
        self._app_window = None
        self._os_window = None
        self._windowing = None
        self._first_frame_skipped = False
        carb.log_info(f"[{_SOURCE}] disengaged")

    # activate / deactivate — plan-API aliases for engage / disengage.
    def activate(self) -> bool:
        return self.engage()

    def deactivate(self) -> None:
        self.disengage()

    @property
    def engaged(self) -> bool:
        return self._engaged

    # ------------------------------------------------------------------
    # per-frame
    # ------------------------------------------------------------------

    def viewport_window_center(self) -> Optional[Tuple[int, int]]:
        """Return (x, y) screen-pixel center of the active viewport window.

        Returns None if the viewport window can't be resolved.
        """
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

    def read_delta_and_warp(
        self,
        center_x: Optional[int] = None,
        center_y: Optional[int] = None,
    ) -> Tuple[float, float]:
        """Read cursor → return delta from center → warp to center.

        ``center_x`` / ``center_y`` are optional: when omitted the method falls
        back to ``viewport_window_center()``.  Pass explicit values when you
        already have the center (avoids a second viewport lookup).

        First call after engage() is treated as a calibration frame: warps without
        reporting a delta (otherwise the first frame would jump if the cursor
        wasn't at center already).

        On hosts where warp doesn't work (probe failed at engage time) returns
        (0, 0) every frame — see __init__ comment.
        """
        if not self._engaged:
            return 0.0, 0.0
        if not self._warp_works:
            return 0.0, 0.0
        # Pause warp when Kit is not the OS-level foreground process. The
        # engaged flag stays True so we resume seamlessly when focus comes
        # back. Also reset the calibration so the first frame after refocus
        # absorbs the cursor's drifted position instead of jumping the
        # camera. Without this, alt-tabbing dragged the cursor back to the
        # viewport center every frame (annoying when the user is interacting
        # with another application).
        if not _is_kit_foreground():
            self._first_frame_skipped = False
            return 0.0, 0.0

        if center_x is None or center_y is None:
            center = self.viewport_window_center()
            if center is None:
                return 0.0, 0.0
            center_x, center_y = center

        cur = self._get_cursor_pos()
        if cur is None:
            return 0.0, 0.0

        dx = float(cur[0] - center_x)
        dy = float(cur[1] - center_y)

        self._set_cursor_pos(center_x, center_y)

        if not self._first_frame_skipped:
            self._first_frame_skipped = True
            return 0.0, 0.0

        return dx, dy

    def _probe_warp_support(self) -> bool:
        """Verify the host actually moves the cursor when we ask. Returns False
        when set_cursor_pos is a no-op (USD Composer Kit 110)."""
        cur = self._get_cursor_pos()
        if cur is None:
            return False
        target_x = int(cur[0]) + 5
        target_y = int(cur[1]) + 5
        if not self._set_cursor_pos(target_x, target_y):
            return False
        after = self._get_cursor_pos()
        if after is None:
            return False
        # Allow ±2 px tolerance for OS-level snapping. We don't restore the
        # cursor — caller treats engage as the start of a new session.
        return abs(int(after[0]) - target_x) <= 2 and abs(int(after[1]) - target_y) <= 2

    # ------------------------------------------------------------------
    # OS / Kit cursor helpers — carb.windowing first, appwindow fallback
    # ------------------------------------------------------------------

    def _get_cursor_pos(self) -> Optional[Tuple[int, int]]:
        # Path 0 (preferred on Windows): user32.GetCursorPos via ctypes.
        if _user32 is not None and _POINT_TYPE is not None:
            try:
                pt = _POINT_TYPE()
                if _user32.GetCursorPos(ctypes.byref(pt)):
                    return (int(pt.x), int(pt.y))
            except Exception:  # noqa: BLE001
                pass

        # Path 1: carb.windowing (Isaac Sim)
        if self._windowing is not None and self._os_window is not None:
            for method in ("get_cursor_position", "get_cursor_pos"):
                fn = getattr(self._windowing, method, None)
                if fn is None:
                    continue
                try:
                    pos = fn(self._os_window)
                    if pos is not None:
                        return int(pos[0]), int(pos[1])
                except Exception:  # noqa: BLE001
                    continue

        # Path 2: appwindow direct cursor methods (USD Composer Kit 110)
        aw = self._app_window
        if aw is not None:
            for name in ("get_cursor_position", "get_cursor_pos"):
                fn = getattr(aw, name, None)
                if fn is None:
                    continue
                try:
                    pos = fn()
                    if pos is not None:
                        return int(pos[0]), int(pos[1])
                except Exception:  # noqa: BLE001
                    continue

        return None

    def _set_cursor_pos(self, x: int, y: int) -> bool:
        # Path 0 (preferred on Windows): user32.SetCursorPos via ctypes.
        if _user32 is not None:
            try:
                if _user32.SetCursorPos(int(x), int(y)):
                    return True
            except Exception:  # noqa: BLE001
                pass

        # Path 1: carb.windowing (Isaac Sim)
        if self._windowing is not None and self._os_window is not None:
            for method in ("set_cursor_position", "set_cursor_pos"):
                fn = getattr(self._windowing, method, None)
                if fn is None:
                    continue
                try:
                    fn(self._os_window, (int(x), int(y)))
                    return True
                except TypeError:
                    try:
                        fn(self._os_window, int(x), int(y))
                        return True
                    except Exception:  # noqa: BLE001
                        continue
                except Exception:  # noqa: BLE001
                    continue

        # Path 2: appwindow direct cursor methods (USD Composer Kit 110)
        aw = self._app_window
        if aw is not None:
            for name in ("set_cursor_position", "set_cursor_pos"):
                fn = getattr(aw, name, None)
                if fn is None:
                    continue
                try:
                    fn((int(x), int(y)))
                    return True
                except TypeError:
                    try:
                        fn(int(x), int(y))
                        return True
                    except Exception:  # noqa: BLE001
                        continue
                except Exception:  # noqa: BLE001
                    continue

        return False

    def _set_cursor_visible(self, visible: bool) -> None:
        # Path 1: carb.windowing CursorMode (Isaac Sim)
        if self._windowing is not None and self._os_window is not None:
            try:
                import carb.windowing  # type: ignore

                mode_attr = "NORMAL" if visible else "HIDDEN"
                mode = getattr(carb.windowing.CursorMode, mode_attr, None)
                if mode is not None:
                    self._windowing.set_cursor_mode(self._os_window, mode)
                    return
            except Exception:  # noqa: BLE001
                pass

        # Path 2: appwindow set_cursor_visible / set_cursor_mode
        aw = self._app_window
        if aw is None:
            return
        for name in ("set_cursor_visible", "set_cursor_mode"):
            fn = getattr(aw, name, None)
            if fn is None:
                continue
            try:
                if name == "set_cursor_visible":
                    fn(bool(visible))
                else:
                    fn("normal" if visible else "hidden")
                return
            except Exception:  # noqa: BLE001
                continue
