"""Window service — full Isaac Sim application window capture (GUI + viewport + menus).

Uses Win32 GDI + PrintWindow(PW_RENDERFULLCONTENT) so DWM-composed / RTX-rendered
windows are captured correctly even if occluded.

Pure ctypes + PIL — no pywin32 / mss dependency.
All omni.*/pxr.* imports are lazy (inside methods) per API rule #7.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import hashlib
import logging
import os
import tempfile
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "validation_api_captures")

# ---------------------------------------------------------------------------
# Win32 bindings
# ---------------------------------------------------------------------------
_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Explicit signatures — Windows expects correct LONG_PTR widths on x64
_ENUM_WINDOWS_PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

_user32.EnumWindows.argtypes = [_ENUM_WINDOWS_PROC, wt.LPARAM]
_user32.EnumWindows.restype = ctypes.c_bool
_user32.IsWindowVisible.argtypes = [wt.HWND]
_user32.IsWindowVisible.restype = ctypes.c_bool
_user32.GetWindowTextLengthW.argtypes = [wt.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.restype = ctypes.c_int
_user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
_user32.GetWindowThreadProcessId.restype = wt.DWORD
_user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
_user32.GetWindowRect.restype = ctypes.c_bool
_user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
_user32.GetClientRect.restype = ctypes.c_bool
_user32.GetWindowDC.argtypes = [wt.HWND]
_user32.GetWindowDC.restype = wt.HDC
_user32.GetDC.argtypes = [wt.HWND]
_user32.GetDC.restype = wt.HDC
_user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
_user32.ReleaseDC.restype = ctypes.c_int
_user32.PrintWindow.argtypes = [wt.HWND, wt.HDC, ctypes.c_uint]
_user32.PrintWindow.restype = ctypes.c_bool
_user32.GetForegroundWindow.restype = wt.HWND
_user32.SetForegroundWindow.argtypes = [wt.HWND]
_user32.SetForegroundWindow.restype = ctypes.c_bool
_user32.BringWindowToTop.argtypes = [wt.HWND]
_user32.BringWindowToTop.restype = ctypes.c_bool
_user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
_user32.ShowWindow.restype = ctypes.c_bool
_user32.IsIconic.argtypes = [wt.HWND]
_user32.IsIconic.restype = ctypes.c_bool


# WINDOWPLACEMENT — needed to detect whether a minimized window should be
# restored to its prior MAXIMIZED state vs the smaller "normal" windowed size.
# SW_RESTORE alone always returns a maximized-then-minimized window to "normal",
# which surprised the user (their full-screen Kit shrank after auto-restore).
class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition", _POINT),
        ("ptMaxPosition", _POINT),
        ("rcNormalPosition", wt.RECT),
    ]


_user32.GetWindowPlacement.argtypes = [wt.HWND, ctypes.POINTER(_WINDOWPLACEMENT)]
_user32.GetWindowPlacement.restype = ctypes.c_bool

_WPF_RESTORETOMAXIMIZED = 0x0002
_SW_SHOWMAXIMIZED = 3

_gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
_gdi32.CreateCompatibleDC.restype = wt.HDC
_gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
_gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
_gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
_gdi32.SelectObject.restype = wt.HGDIOBJ
_gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
_gdi32.DeleteObject.restype = ctypes.c_bool
_gdi32.DeleteDC.argtypes = [wt.HDC]
_gdi32.DeleteDC.restype = ctypes.c_bool
_gdi32.BitBlt.argtypes = [
    wt.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wt.HDC, ctypes.c_int, ctypes.c_int, wt.DWORD,
]
_gdi32.BitBlt.restype = ctypes.c_bool
_gdi32.GetDIBits.argtypes = [
    wt.HDC, wt.HBITMAP, ctypes.c_uint, ctypes.c_uint,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
]
_gdi32.GetDIBits.restype = ctypes.c_int

_kernel32.GetCurrentProcessId.restype = wt.DWORD


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", _BITMAPINFOHEADER),
        ("bmiColors", wt.DWORD * 3),
    ]


_PW_RENDERFULLCONTENT = 0x00000002
_SRCCOPY = 0x00CC0020
_DIB_RGB_COLORS = 0
_SW_RESTORE = 9


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_window_title(hwnd: int) -> str:
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value or ""


def _get_window_class(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, buf, 256)
    return buf.value or ""


def _find_kit_main_window(match_substrings: tuple[str, ...] = ("Isaac Sim", "Omniverse", "Kit", "Composer", "USD")) -> dict | None:
    """Enumerate top-level visible windows owned by the current (kit.exe) process and
    return the largest match. Selection priority:
      1. Window with class_name == "GLFW30" (the GLFW window class used by every
         Kit-based app — Isaac Sim, USD Composer, kit-app-template builds, etc.).
         This is robust against any app title rename.
      2. Title substring match against `match_substrings` (legacy fallback for
         non-GLFW-class Kit shells).
    Within each priority bucket the largest (by area) candidate wins.
    """
    my_pid = _kernel32.GetCurrentProcessId()
    glfw_candidates: list[dict] = []
    title_candidates: list[dict] = []

    @_ENUM_WINDOWS_PROC
    def _enum_proc(hwnd: int, _lparam: int) -> bool:
        try:
            if not _user32.IsWindowVisible(hwnd):
                return True
            pid = wt.DWORD()
            _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != my_pid:
                return True
            title = _get_window_title(hwnd)
            class_name = _get_window_class(hwnd)
            rect = wt.RECT()
            if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            w, h = rect.right - rect.left, rect.bottom - rect.top
            if w < 200 or h < 200:  # skip tiny windows
                return True
            entry = {
                "hwnd": int(hwnd),
                "title": title,
                "class_name": class_name,
                "width": w,
                "height": h,
                "rect": (rect.left, rect.top, rect.right, rect.bottom),
            }
            if class_name == "GLFW30":
                glfw_candidates.append(entry)
            elif title and any(sub in title for sub in match_substrings):
                title_candidates.append(entry)
        except Exception:  # noqa: BLE001
            pass
        return True

    _user32.EnumWindows(_enum_proc, 0)
    pool = glfw_candidates or title_candidates
    if not pool:
        return None
    pool.sort(key=lambda c: -(c["width"] * c["height"]))
    return pool[0]


def _mean_abs_pixel_diff(path_a: str, path_b: str, size: int = 128) -> float:
    """Compute mean L1 pixel diff between two images (0-1 scale). Resize to
    `size x size` grayscale for speed — tolerates minor overlay drift (FPS
    counter, timeline cursor) while still detecting meaningful browser
    content changes."""
    from PIL import Image  # lazy
    import numpy as np  # Kit Python includes numpy
    a = np.asarray(Image.open(path_a).convert("L").resize((size, size)), dtype=np.int16)
    b = np.asarray(Image.open(path_b).convert("L").resize((size, size)), dtype=np.int16)
    return float(np.mean(np.abs(a - b)) / 255.0)


def _capture_hwnd_to_pil(hwnd: int, use_client_rect: bool = False) -> tuple[Any, dict]:
    """Capture window `hwnd` to a PIL Image. Returns (image, meta)."""
    from PIL import Image  # lazy — available in Isaac Sim's Python

    rect = wt.RECT()
    ok = (_user32.GetClientRect if use_client_rect else _user32.GetWindowRect)(hwnd, ctypes.byref(rect))
    if not ok:
        raise RuntimeError(f"GetWindowRect failed for hwnd={hwnd}")
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        raise RuntimeError(f"Invalid window dimensions: {w}x{h}")

    hwnd_dc = _user32.GetWindowDC(hwnd) if not use_client_rect else _user32.GetDC(hwnd)
    if not hwnd_dc:
        raise RuntimeError("GetWindowDC/GetDC returned NULL")

    mem_dc = _gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = _gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    old_obj = _gdi32.SelectObject(mem_dc, bitmap)

    printwindow_result = False
    bitblt_result = False
    try:
        flags = _PW_RENDERFULLCONTENT if not use_client_rect else (_PW_RENDERFULLCONTENT | 0x1)
        printwindow_result = bool(_user32.PrintWindow(hwnd, mem_dc, flags))
        if not printwindow_result:
            printwindow_result = bool(_user32.PrintWindow(hwnd, mem_dc, 0))
        if not printwindow_result:
            bitblt_result = bool(_gdi32.BitBlt(mem_dc, 0, 0, w, h, hwnd_dc, 0, 0, _SRCCOPY))

        info = _BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        info.bmiHeader.biWidth = w
        info.bmiHeader.biHeight = -h  # negative → top-down
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = 0  # BI_RGB

        buf_size = w * h * 4
        buf = (ctypes.c_ubyte * buf_size)()
        scanlines = _gdi32.GetDIBits(mem_dc, bitmap, 0, h, buf, ctypes.byref(info), _DIB_RGB_COLORS)
        if not scanlines:
            raise RuntimeError("GetDIBits returned 0 scanlines")

        img = Image.frombuffer("RGB", (w, h), bytes(buf), "raw", "BGRX", 0, 1)
        meta = {
            "width": w,
            "height": h,
            "hwnd": int(hwnd),
            "used_printwindow": printwindow_result,
            "used_bitblt_fallback": bitblt_result,
            "use_client_rect": use_client_rect,
        }
        return img, meta
    finally:
        _gdi32.SelectObject(mem_dc, old_obj)
        _gdi32.DeleteObject(bitmap)
        _gdi32.DeleteDC(mem_dc)
        _user32.ReleaseDC(hwnd, hwnd_dc)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class WindowService:
    """Full Isaac Sim application window capture (GUI panels + viewport + menus)."""

    async def list_ui_windows(self, name_filter: str | None = None) -> dict[str, Any]:
        """Enumerate all registered omni.ui.Window instances (Asset Browser,
        SimReady Explorer, Content, Isaac Examples, Hub, Robot Assembler, ...).

        `name_filter` is a case-insensitive substring applied to each window's
        title — useful for isolating "Browser"/"Explorer"-category windows.
        """
        import omni.ui as ui  # lazy

        # Workspace.get_windows() returns omni.ui.Window objects
        try:
            raw_windows = list(ui.Workspace.get_windows())
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"omni.ui.Workspace.get_windows() failed: {exc}") from exc

        items: list[dict[str, Any]] = []
        fl = name_filter.lower() if name_filter else None
        for w in raw_windows:
            try:
                title = getattr(w, "title", "") or ""
                if fl and fl not in title.lower():
                    continue
                visible = bool(getattr(w, "visible", False))
                try:
                    dock_id = int(w.dock_id) if getattr(w, "docked", False) else 0
                except Exception:  # noqa: BLE001
                    dock_id = 0
                try:
                    width = float(getattr(w, "width", 0) or 0)
                    height = float(getattr(w, "height", 0) or 0)
                except Exception:  # noqa: BLE001
                    width = height = 0.0
                items.append({
                    "title": title,
                    "visible": visible,
                    "docked": bool(getattr(w, "docked", False)),
                    "dock_id": dock_id,
                    "width": width,
                    "height": height,
                })
            except Exception:  # noqa: BLE001
                continue

        items.sort(key=lambda it: it["title"].lower())
        return {
            "ok": True,
            "count": len(items),
            "filter": name_filter,
            "windows": items,
        }

    async def list_menu_items(self, menu_path: str | None = None) -> dict[str, Any]:
        """Walk Kit's merged menu tree and return item metadata.

        If `menu_path` is provided (e.g. "Window/Browsers"), only items under that
        subtree are returned. `onclick_action` is emitted as a 2-list so the caller
        can pass it to `/window/menu_trigger`.
        """
        import omni.kit.menu.utils as menu_utils  # lazy

        tree: dict = {}
        diag: dict[str, Any] = {}
        try:
            tree = menu_utils.get_merged_menus() or {}
            diag["get_merged_menus_keys"] = list(tree.keys())
            # Raw content probe for Window_Browsers to understand shape
            sample_key = "Window_Browsers"
            sample = tree.get(sample_key)
            diag["sample_key"] = sample_key
            diag["sample_type"] = type(sample).__name__
            if sample is not None:
                if isinstance(sample, dict):
                    diag["sample_dict_keys"] = list(sample.keys())[:10]
                elif isinstance(sample, list):
                    diag["sample_list_len"] = len(sample)
                    if sample:
                        first = sample[0]
                        diag["sample_first_type"] = type(first).__name__
                        diag["sample_first_attrs"] = [a for a in dir(first) if not a.startswith("_")][:30]
                        diag["sample_first_name"] = str(getattr(first, "name", None))
                        diag["sample_first_action"] = str(getattr(first, "onclick_action", None))
                        diag["sample_first_sub"] = str(getattr(first, "sub_menu", None))[:200]
                        # repr as string
                        try:
                            diag["sample_first_repr"] = repr(first)[:300]
                        except Exception:
                            pass
        except Exception as exc:  # noqa: BLE001
            diag["get_merged_menus_error"] = str(exc)

        # Fall back to instance.get_menu_data()
        if not tree:
            try:
                inst = menu_utils.get_instance()
                diag["instance"] = type(inst).__name__ if inst else None
                if inst and hasattr(inst, "get_menu_data"):
                    data = inst.get_menu_data()
                    diag["menu_data_type"] = type(data).__name__
                    if isinstance(data, dict):
                        tree = data
            except Exception as exc:  # noqa: BLE001
                diag["instance_error"] = str(exc)

        def extract_name(item):
            n = getattr(item, "name", None)
            if n:
                return n
            if isinstance(item, dict):
                return item.get("name")
            return None

        def extract_sub(item):
            s = getattr(item, "sub_menu", None)
            if s:
                return s
            if isinstance(item, dict):
                return item.get("sub_menu")
            return None

        def extract_action(item):
            a = getattr(item, "onclick_action", None)
            if a:
                return a
            if isinstance(item, dict):
                return item.get("onclick_action")
            return None

        def flatten(node, parent_path):
            out = []
            items = node if isinstance(node, list) else [node]
            for it in items:
                name = extract_name(it)
                if not name:
                    continue
                full = f"{parent_path}/{name}" if parent_path else name
                sub = extract_sub(it)
                action = extract_action(it)
                out.append({
                    "path": full,
                    "name": name,
                    "has_submenu": bool(sub),
                    "enabled": bool(getattr(it, "enabled", True)),
                    "onclick_action": list(action) if isinstance(action, (list, tuple)) else None,
                })
                if sub:
                    out.extend(flatten(sub, full))
            return out

        # Kit's get_merged_menus() returns a flat dict. Each value is itself a dict:
        #   { "items": [MenuItemDescription...], "action_prefix": "...", ... }
        # Top-level keys use "_" as hierarchy separator: "Window_Browsers" → Window > Browsers.
        flat: list[dict[str, Any]] = []
        for top_key, submenu in tree.items():
            if not isinstance(submenu, dict):
                continue
            items_list = submenu.get("items") or []
            parent_path = top_key.replace("_", "/")
            for raw in flatten(items_list, parent_path):
                raw["action_prefix"] = submenu.get("action_prefix")
                # Compose a synthetic onclick_action when missing — most Kit entries
                # register actions under "{action_prefix}:{menu name}" but the tuple
                # is already on the MenuItemDescription; only fall back when None.
                if not raw.get("onclick_action") and submenu.get("action_prefix"):
                    raw["onclick_action"] = [submenu["action_prefix"], raw["name"]]
                flat.append(raw)

        if menu_path:
            pref = menu_path.strip("/")
            flat = [i for i in flat if i["path"] == pref or i["path"].startswith(pref + "/")]

        return {
            "ok": True, "count": len(flat), "menu_path": menu_path,
            "items": flat, "diag": diag,
        }

    async def trigger_menu(self, menu_path: str) -> dict[str, Any]:
        """Programmatically click a menu item (e.g. 'Window/Browsers/Asset Browser').

        Resolves the item's `onclick_action` tuple via the merged menu tree, then
        dispatches it through `omni.kit.actions.core.execute_action` — the same
        path a real click takes.
        """
        import omni.kit.actions.core as actions_core  # lazy
        import omni.kit.app  # lazy
        import omni.kit.menu.utils as menu_utils  # lazy

        tree = menu_utils.get_merged_menus() or {}

        def walk(node, parent_path):
            items = node if isinstance(node, list) else [node]
            for it in items:
                name = getattr(it, "name", None) or (it.get("name") if isinstance(it, dict) else None)
                if not name:
                    continue
                full = f"{parent_path}/{name}" if parent_path else name
                if full == menu_path:
                    return it
                sub = getattr(it, "sub_menu", None) or (it.get("sub_menu") if isinstance(it, dict) else None)
                if sub:
                    r = walk(sub, full)
                    if r is not None:
                        return r
            return None

        target = None
        action_prefix = None
        for top_key, submenu in tree.items():
            if not isinstance(submenu, dict):
                continue
            items_list = submenu.get("items") or []
            parent_path = top_key.replace("_", "/")
            found = walk(items_list, parent_path)
            if found:
                target = found
                action_prefix = submenu.get("action_prefix")
                break

        if target is None:
            raise RuntimeError(f"Menu item not found: {menu_path}")

        action = getattr(target, "onclick_action", None)
        if not action and isinstance(target, dict):
            action = target.get("onclick_action")
        if not action and action_prefix:
            # Fall back to action_prefix + item name convention
            name = getattr(target, "name", None) or (target.get("name") if isinstance(target, dict) else None)
            action = (action_prefix, name)
        if not action:
            raise RuntimeError(f"Menu item '{menu_path}' has no onclick_action (submenu?)")

        ext_id, action_id = action[0], action[1]

        # Snapshot stage prim set before trigger for diff
        import omni.usd  # lazy
        stage = omni.usd.get_context().get_stage()
        before_prims: set[str] = set()
        if stage is not None:
            before_prims = {p.GetPath().pathString for p in stage.Traverse()}

        actions_core.execute_action(ext_id, action_id)

        app = omni.kit.app.get_app()
        for _ in range(8):
            await app.next_update_async()

        # Stage diff — new prims created by this action (sensor creation 등)
        created_prims: list[str] = []
        if stage is not None:
            after_prims = {p.GetPath().pathString for p in stage.Traverse()}
            created_prims = sorted(after_prims - before_prims)

        return {
            "ok": True,
            "menu_path": menu_path,
            "action": [ext_id, action_id],
            "created_prims": created_prims,
        }

    async def show_ui_window(
        self,
        name: str,
        visible: bool = True,
        focus: bool = True,
        settle_frames: int = 5,
    ) -> dict[str, Any]:
        """Show / hide a registered UI Window by title (Window menu item label).

        When `focus=True` and the window is docked within a tab group, it is
        brought to the front of that group (equivalent to clicking its tab).

        If no exact title match exists, falls back to a case-insensitive
        substring search — resolves cases like menu item "Isaac Sim Assets"
        opening a window actually titled "Isaac Sim Assets [Beta]".
        """
        import omni.kit.app  # lazy
        import omni.ui as ui  # lazy

        # Toggle visibility via Workspace — matches Window-menu checkbox behaviour
        try:
            ui.Workspace.show_window(name, show=visible)
        except TypeError:
            # older signature: show_window(name)
            ui.Workspace.show_window(name)

        # Let the UI actually mount the window before we try to focus it
        app = omni.kit.app.get_app()
        for _ in range(max(1, settle_frames // 2)):
            await app.next_update_async()

        win = ui.Workspace.get_window(name)
        resolved_name = name
        resolved_via = "exact" if win is not None else None
        if win is None:
            # Substring fallback
            needle = name.lower()
            for w in ui.Workspace.get_windows() or []:
                title = getattr(w, "title", "") or ""
                if title and needle in title.lower():
                    win = w
                    resolved_name = title
                    resolved_via = "substring"
                    try:
                        ui.Workspace.show_window(title, show=visible)
                    except TypeError:
                        ui.Workspace.show_window(title)
                    break

        info: dict[str, Any] = {
            "ok": True,
            "name": name,
            "resolved_name": resolved_name,
            "resolved_via": resolved_via,
            "requested_visible": visible,
            "found": win is not None,
        }

        if win is not None:
            if focus and visible:
                try:
                    win.focus()
                    info["focused"] = True
                except Exception as exc:  # noqa: BLE001
                    info["focused"] = False
                    info["focus_error"] = str(exc)
            info["visible_after"] = bool(getattr(win, "visible", False))
            info["docked"] = bool(getattr(win, "docked", False))
            try:
                info["dock_id"] = int(win.dock_id) if info["docked"] else 0
            except Exception:  # noqa: BLE001
                info["dock_id"] = 0

        # Final settle so subsequent window/capture sees the new state
        for _ in range(settle_frames):
            await app.next_update_async()
        return info

    async def list_windows(self) -> dict[str, Any]:
        """Enumerate visible top-level windows owned by kit.exe. Useful for debugging."""
        my_pid = _kernel32.GetCurrentProcessId()
        found: list[dict] = []

        @_ENUM_WINDOWS_PROC
        def _enum(hwnd: int, _lparam: int) -> bool:
            try:
                if not _user32.IsWindowVisible(hwnd):
                    return True
                pid = wt.DWORD()
                _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != my_pid:
                    return True
                rect = wt.RECT()
                _user32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append({
                    "hwnd": int(hwnd),
                    "title": _get_window_title(hwnd),
                    "class_name": _get_window_class(hwnd),
                    "width": rect.right - rect.left,
                    "height": rect.bottom - rect.top,
                })
            except Exception:  # noqa: BLE001
                pass
            return True

        _user32.EnumWindows(_enum, 0)
        return {"ok": True, "pid": my_pid, "count": len(found), "windows": found}

    async def capture(self, request: dict[str, Any]) -> dict[str, Any]:
        """Capture the full Isaac Sim application window."""
        import asyncio
        import omni.kit.app  # lazy

        mode: str = request.get("mode", "kit")
        explicit_hwnd = request.get("hwnd")
        settle_frames: int = int(request.get("settle_frames", 5))
        output_format: str = request.get("output_format", "png")
        bring_to_front: bool = bool(request.get("bring_to_front", False))
        use_client_rect: bool = bool(request.get("use_client_rect", False))
        wait_stable: bool = bool(request.get("wait_stable", False))
        stable_interval_s: float = float(request.get("stable_interval_s", 2.0))
        stable_consecutive: int = int(request.get("stable_consecutive", 2))
        stable_max_wait_s: float = float(request.get("stable_max_wait_s", 45.0))
        stable_diff_threshold: float = float(request.get("stable_diff_threshold", 0.01))

        # Let GUI/renderer settle
        app = omni.kit.app.get_app()
        for _ in range(settle_frames):
            await app.next_update_async()

        # Resolve target HWND
        if explicit_hwnd is not None:
            hwnd = int(explicit_hwnd)
            title = _get_window_title(hwnd)
            class_name = _get_window_class(hwnd)
        elif mode == "foreground":
            hwnd = int(_user32.GetForegroundWindow())
            if not hwnd:
                raise RuntimeError("No foreground window")
            title = _get_window_title(hwnd)
            class_name = _get_window_class(hwnd)
        else:  # "kit" — auto-detect main Isaac Sim / Kit window
            found = _find_kit_main_window()
            if not found:
                raise RuntimeError(
                    "Kit main window not found. List via /window/list to inspect candidates."
                )
            hwnd = found["hwnd"]
            title = found["title"]
            class_name = found["class_name"]

        # PrintWindow(PW_RENDERFULLCONTENT) reads from the DWM-composited
        # surface, so a window that's merely *occluded* (covered by another
        # app, or on a background monitor) captures fine without stealing
        # focus from the user. We only need to disrupt the user's foreground
        # state when the window is actually minimized — GLFW stops presenting
        # to the GPU surface in iconic state, so PrintWindow returns a stale
        # / black frame.
        focus_action = "none"
        if bring_to_front and _user32.IsIconic(hwnd):
            # Read prior placement so we restore to maximized vs normal correctly.
            # SW_RESTORE always returns to "normal" size, which un-maximizes a
            # window that the user had full-screen — visible as the Kit window
            # shrinking unexpectedly. WPF_RESTORETOMAXIMIZED preserves intent.
            placement = _WINDOWPLACEMENT()
            placement.length = ctypes.sizeof(_WINDOWPLACEMENT)
            restore_cmd = _SW_RESTORE
            if _user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
                if placement.flags & _WPF_RESTORETOMAXIMIZED:
                    restore_cmd = _SW_SHOWMAXIMIZED
            _user32.ShowWindow(hwnd, restore_cmd)
            _user32.BringWindowToTop(hwnd)
            _user32.SetForegroundWindow(hwnd)
            focus_action = (
                "restored_to_maximized"
                if restore_cmd == _SW_SHOWMAXIMIZED
                else "restored_to_normal"
            )
            # short settle after focus change
            for _ in range(3):
                await app.next_update_async()

        os.makedirs(_OUTPUT_DIR, exist_ok=True)

        def _do_one_capture() -> tuple[str, str, dict]:
            img, meta = _capture_hwnd_to_pil(hwnd, use_client_rect=use_client_rect)
            artifact_id = uuid.uuid4().hex[:12]
            filename = f"window_capture_{artifact_id}.{output_format}"
            filepath = os.path.join(_OUTPUT_DIR, filename).replace("\\", "/")
            img.save(filepath, output_format.upper())
            sha = hashlib.sha256()
            with open(filepath, "rb") as fh:
                for chunk in iter(lambda: fh.read(64 * 1024), b""):
                    sha.update(chunk)
            return artifact_id, filepath, {**meta, "sha256": sha.hexdigest()}

        # Non-stable path: single capture (original behavior)
        if not wait_stable:
            artifact_id, filepath, meta = _do_one_capture()
            return {
                "ok": True, "artifact_id": artifact_id, "path": filepath,
                "width": meta["width"], "height": meta["height"],
                "hwnd": meta["hwnd"], "title": title, "class_name": class_name,
                "mode": mode, "used_printwindow": meta["used_printwindow"],
                "used_bitblt_fallback": meta["used_bitblt_fallback"],
                "sha256": meta["sha256"],
                "wait_stable": False,
                "focus_action": focus_action,
                "created_at_epoch_ms": int(time.time() * 1000),
            }

        # wait_stable path: poll until pixel diff stays below threshold N times or timeout
        start_monotonic = time.monotonic()
        polls = 0
        consecutive = 0
        prev_filepath: str | None = None
        last_diff = 1.0
        max_diff_seen = 0.0
        diff_history: list[float] = []
        last_artifact_id = ""
        last_filepath = ""
        last_meta: dict = {}
        stabilized = False

        while True:
            polls += 1
            last_artifact_id, last_filepath, last_meta = _do_one_capture()
            if prev_filepath is not None:
                last_diff = _mean_abs_pixel_diff(prev_filepath, last_filepath)
                diff_history.append(last_diff)
                max_diff_seen = max(max_diff_seen, last_diff)
                if last_diff <= stable_diff_threshold:
                    consecutive += 1
                else:
                    consecutive = 1
            else:
                consecutive = 1  # first capture starts the run
            prev_filepath = last_filepath

            if consecutive >= stable_consecutive:
                stabilized = True
                break
            if time.monotonic() - start_monotonic >= stable_max_wait_s:
                break
            await asyncio.sleep(stable_interval_s)

        return {
            "ok": True, "artifact_id": last_artifact_id, "path": last_filepath,
            "width": last_meta["width"], "height": last_meta["height"],
            "hwnd": last_meta["hwnd"], "title": title, "class_name": class_name,
            "mode": mode, "used_printwindow": last_meta["used_printwindow"],
            "used_bitblt_fallback": last_meta["used_bitblt_fallback"],
            "sha256": last_meta["sha256"],
            "wait_stable": True,
            "stabilized": stabilized,
            "polls": polls,
            "last_diff": round(last_diff, 5),
            "max_diff_seen": round(max_diff_seen, 5),
            "diff_threshold": stable_diff_threshold,
            "diff_history": [round(d, 5) for d in diff_history],
            "elapsed_s": round(time.monotonic() - start_monotonic, 2),
            "focus_action": focus_action,
            "created_at_epoch_ms": int(time.time() * 1000),
        }
