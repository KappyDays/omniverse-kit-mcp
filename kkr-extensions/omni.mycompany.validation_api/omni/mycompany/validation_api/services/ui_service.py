"""UI introspection + invocation via omni.kit.ui_test (Phase D).

omni.kit.ui_test (Kit 1.3.7) public API:

- `find(path) -> WidgetRef` / `find_all(path) -> [WidgetRef]` — both **sync**
- `WidgetRef.click()` / `.double_click()` / `.input(text, end_key=ENTER)` — async
- Path syntax uses the `omni.ui_query` XPath-like grammar. The root segment
  before `//` is a window title; a path without `//` resolves directly to a
  window. Inside a window the query needs **widget types**:

    Cool Window//Frame/**/Button[*]     ← all descendant Buttons
    Cool Window//Frame/HStack[0]        ← first HStack child of Frame

  Plain `**/*` does NOT match — `*` is an index wildcard for `[*]`, not a
  type placeholder. To walk "everything" we iterate the well-known widget
  types below.

GUI-mode only (omni.ui no-ops under --no-window).

UI_TEST FLOAT-DIV-BY-ZERO WORKAROUND (2026-04-23 root-cause analysis)
=====================================================================
**Root cause**: ``omni.kit.ui_test.input.emulate_mouse`` (line ~49)
divides ``pos.x / window_width`` where ``window_width =
ui.Workspace.get_main_window_width()``. **Right after a panel is created
or its containing window is freshly enabled**, the omni.ui Workspace has
not yet computed dimensions for the new dock layout — both width and
height read as ``0`` for one or more frames. ``emulate_mouse`` then
raises ``ZeroDivisionError: float division by zero`` even though the
OS-level kit.exe window is fully sized (verified via ``window_list``:
3864×2100 on this 4K HiDPI rig).

Reproduction: ``extension_activate("...navmesh_playground", reload=True)``
→ immediate ``ext_ui_invoke`` on a panel button → 500. Repro window
closes after the panel layout settles (~10 frames or one
``window_ui_show``).

**Two-layer fix**:

1. ``_install_ui_test_dimensions_patch()`` wraps ``emulate_mouse`` so
   that when either dimension is ``<= 0`` we substitute the OS
   app-window dimensions (``omni.appwindow.get_window_width/height``).
   The absolute ``pos.to_tuple()`` arg that carb.input actually consumes
   is unaffected; only the legacy normalised-coordinate channel falls
   back. Idempotent — applied once at module import.

2. ``ui_invoke()`` auto-calls ``window_ui_show(window_title,
   focus=True, settle_frames=10)`` before delegating to ``ui_test``.
   This forces the workspace to lay out the target panel and resolves
   the race deterministically — even on the very first click after
   panel creation.

Either layer alone closes the bug; running both makes ``ext_ui_invoke``
robust to any future layout-init timing changes.

OS CURSOR INVISIBILITY (2026-04-23 user request)
================================================
The same ``safe_emulate_mouse`` patch deliberately omits the
``windowing.set_cursor_position(...)`` call from the upstream
``emulate_mouse``. Without that omission the operator's physical mouse
cursor jumps every time MCP automation clicks an Extension button,
which makes it impractical to do other desktop work while Claude Code
is driving Isaac Sim. The Kit input event (``buffer_mouse_event``) is
sufficient to deliver the click to the targeted widget — the cursor
move was only visual feedback.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _install_ui_test_dimensions_patch() -> None:
    """Replace ``omni.kit.ui_test.input.emulate_mouse`` with a 0-safe wrapper.

    Idempotent — safe to re-import. Failure is non-fatal so tests that do
    not exercise mouse input still load.
    """
    try:
        import omni.kit.ui_test.input as _ui_test_input
    except Exception as exc:  # noqa: BLE001 — extension may be unavailable
        logger.debug("ui_test patch skipped (import failed): %s", exc)
        return
    if getattr(_ui_test_input, "_validation_api_dim_patch_applied", False):
        return

    import carb
    import carb.input
    import carb.windowing
    import omni.appwindow
    import omni.ui as ui
    from carb.input import MouseEventType
    from omni.kit.ui_test.common import human_delay  # noqa: F401  re-export OK
    from omni.kit.ui_test.input import _get_input_provider, _get_windowing  # noqa: F401

    async def safe_emulate_mouse(event_type, pos=None, modifiers=None):
        from omni.kit.ui_test.vec2 import Vec2  # lazy
        if pos is None:
            pos = Vec2()

        app_window = omni.appwindow.get_default_app_window()
        mouse = app_window.get_mouse()

        ws_w = float(ui.Workspace.get_main_window_width() or 0.0)
        ws_h = float(ui.Workspace.get_main_window_height() or 0.0)
        if ws_w <= 0.0 or ws_h <= 0.0:
            # Fall back to OS app-window dimensions. These are always
            # populated for a visible kit.exe.
            try:
                os_w = float(app_window.get_window_width())
                os_h = float(app_window.get_window_height())
            except Exception:  # noqa: BLE001
                os_w, os_h = 1920.0, 1080.0
            ws_w = ws_w if ws_w > 0.0 else os_w
            ws_h = ws_h if ws_h > 0.0 else os_h
            logger.warning(
                "ui_test fallback dimensions: workspace=(%s,%s) → using (%s,%s) "
                "(see ui_service.py UI_TEST FLOAT-DIV-BY-ZERO WORKAROUND).",
                ui.Workspace.get_main_window_width(),
                ui.Workspace.get_main_window_height(),
                ws_w, ws_h,
            )

        scaled = pos * ui.Workspace.get_dpi_scale()
        if modifiers is None:
            modifiers = carb.input.acquire_input_interface().get_modifier_flags(
                device_types=[carb.input.DeviceType.KEYBOARD],
            )

        _get_input_provider().buffer_mouse_event(
            mouse, event_type,
            (scaled.x / ws_w, scaled.y / ws_h),
            modifiers,
            scaled.to_tuple(),
        )
        # NOTE: omni.kit.ui_test.input.emulate_mouse normally also calls
        # ``windowing.set_cursor_position(...)`` on every MOVE event so the
        # OS cursor visibly tracks the synthesised motion. We deliberately
        # skip that here so Claude Code can drive Extension UI clicks via
        # MCP without yanking the user's actual mouse pointer away from
        # whatever they are doing on the rest of the desktop. The Kit
        # input event above (``buffer_mouse_event``) is what actually
        # delivers the click to the widget — the cursor move was only a
        # visual aid. (User request 2026-04-23 — keep automation invisible
        # to the operator.)

    _ui_test_input.emulate_mouse = safe_emulate_mouse
    _ui_test_input._validation_api_dim_patch_applied = True
    logger.warning(
        "[validation_api] omni.kit.ui_test.input.emulate_mouse patched "
        "(zero-dimension fallback active).",
    )


_install_ui_test_dimensions_patch()


# Widget classes we enumerate when the caller does not specify a type.
# Ordering is descending by "ui noise" — interactive widgets first so callers
# making label/value assertions hit the important rows without wading through
# the layout/container entries.
_WIDGET_TYPES: tuple[str, ...] = (
    # Interactive
    "Button",
    "ToolButton",
    "RadioButton",
    "CheckBox",
    "ComboBox",
    "StringField",
    "FloatField",
    "FloatSlider",
    "FloatDrag",
    "IntField",
    "IntSlider",
    "IntDrag",
    "MultiFloatField",
    "MultiIntField",
    "ColorWidget",
    # Display
    "Label",
    "Image",
    "ImageWithProvider",
    "Plot",
    # Composite / list
    "TreeView",
    "ScrollingFrame",
    "CollapsableFrame",
    "Menu",
    "MenuItem",
    # Containers / layout (walked so tests can assert structure)
    "Frame",
    "HStack",
    "VStack",
    "ZStack",
    "Placer",
    "Spacer",
    "Separator",
    "Line",
    "Rectangle",
)


def _describe_widget(widget: Any, path: str, window_title: str) -> dict[str, Any]:
    cls_name = type(widget).__name__ if widget is not None else "Unknown"

    label = ""
    for attr in ("text", "title", "name"):
        try:
            val = getattr(widget, attr, None)
            if val is None:
                continue
            if hasattr(val, "as_string"):
                label = str(val.as_string)
            elif hasattr(val, "get_value_as_string"):
                label = str(val.get_value_as_string())
            else:
                label = str(val)
            if label:
                break
        except Exception:  # noqa: BLE001
            continue

    value: Any = None
    try:
        model = getattr(widget, "model", None)
        if model is not None:
            if hasattr(model, "get_value_as_string"):
                value = model.get_value_as_string()
            elif hasattr(model, "as_string"):
                value = model.as_string
            elif hasattr(model, "get_value_as_int"):
                value = int(model.get_value_as_int())
            elif hasattr(model, "get_value_as_float"):
                value = float(model.get_value_as_float())
            elif hasattr(model, "get_value_as_bool"):
                value = bool(model.get_value_as_bool())
    except Exception:  # noqa: BLE001
        value = None

    final_path = path or ""
    if final_path and "//" not in final_path:
        final_path = f"{window_title}//{final_path}"

    return {
        "path": final_path,
        "label": str(label)[:200],
        "type": cls_name,
        "enabled": bool(getattr(widget, "enabled", True)) if widget is not None else False,
        "visible": bool(getattr(widget, "visible", True)) if widget is not None else False,
        "value": value,
    }


class UiService:
    """Widget introspection + invocation for live Isaac Sim windows."""

    async def _auto_show_window(self, name: str, settle_frames: int = 10) -> None:
        """Bring an omni.ui.Window to front + tick the layout.

        Used by ui_invoke to defeat the "fresh panel ⇒ Workspace
        dimensions = 0 ⇒ float division by zero" race documented in the
        module docstring. Best-effort: any failure is swallowed so the
        click can still proceed (the safe_emulate_mouse patch handles
        the residual case).
        """
        try:
            import omni.ui as ui
        except Exception:  # noqa: BLE001
            return
        windows = list(ui.Workspace.get_windows() or [])
        target = next(
            (w for w in windows if getattr(w, "title", "") == name),
            None,
        )
        if target is None:
            for w in windows:
                if name.lower() in str(getattr(w, "title", "")).lower():
                    target = w
                    break
        if target is None:
            return
        try:
            target.visible = True
        except Exception:  # noqa: BLE001
            pass
        try:
            target.focus()
        except Exception:  # noqa: BLE001
            pass
        try:
            import omni.kit.app
            app = omni.kit.app.get_app()
            for _ in range(max(1, int(settle_frames))):
                await app.next_update_async()
        except Exception:  # noqa: BLE001
            pass

    async def get_ui_tree(
        self,
        ext_id: str | None = None,
        window: str | None = None,
        widget_types: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Walk widgets inside `window`. `widget_types` overrides the default
        enumeration list when provided — useful for custom widget classes
        (e.g. KKR-specific composites) that are not in `_WIDGET_TYPES`."""
        import omni.ui as ui  # lazy

        try:
            raw_windows = list(ui.Workspace.get_windows())
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"omni.ui.Workspace.get_windows() failed: {exc}") from exc

        windows_meta: list[dict[str, Any]] = []
        matched_titles: list[str] = []
        needle = window.lower() if window else None
        for w in raw_windows:
            title = getattr(w, "title", "") or ""
            if not title:
                continue
            visible = bool(getattr(w, "visible", False))
            windows_meta.append({
                "title": title,
                "visible": visible,
                "docked": bool(getattr(w, "docked", False)),
            })
            if needle is None:
                continue
            if needle == title.lower() or needle in title.lower():
                matched_titles.append(title)

        widgets: list[dict[str, Any]] = []
        walk_errors: list[dict[str, Any]] = []
        types_to_walk = tuple(widget_types) if widget_types else _WIDGET_TYPES
        for title in matched_titles:
            try:
                widgets.extend(self._walk_widgets(title, types_to_walk))
            except Exception as exc:  # noqa: BLE001
                walk_errors.append({"window": title, "error": str(exc)})

        # Deduplicate by path — different queries can return the same widget.
        seen_paths: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for w in widgets:
            p = w.get("path") or ""
            key = (p, w.get("type"), w.get("label"))
            if key in seen_paths:
                continue
            seen_paths.add(key)
            deduped.append(w)

        return {
            "ok": True,
            "ext_id": ext_id,
            "window": window,
            "matched_windows": matched_titles,
            "windows": windows_meta,
            "widgets": deduped,
            "widget_count": len(deduped),
            "walk_errors": walk_errors,
        }

    def _walk_widgets(
        self, window_title: str, widget_types: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        """Iterate given widget types under a window via omni.kit.ui_test."""
        import omni.kit.ui_test as ui_test  # lazy

        out: list[dict[str, Any]] = []
        for wt in widget_types:
            query = f"{window_title}//Frame/**/{wt}[*]"
            try:
                refs = ui_test.find_all(query)
            except Exception:  # noqa: BLE001
                refs = None
            for ref in refs or []:
                try:
                    path = getattr(ref, "path", "") or query
                    # Prefer the resolved realpath when available
                    realpath = getattr(ref, "realpath", "") or ""
                    if realpath:
                        if "//" not in realpath:
                            realpath = f"{window_title}//{realpath}"
                        path = realpath
                    widget = getattr(ref, "widget", None)
                    if widget is None:
                        continue
                    out.append(_describe_widget(widget, path, window_title))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("describe widget failed (%s): %s", wt, exc)
                    continue
        return out

    async def ui_invoke(
        self,
        widget_path: str,
        action: str,
        value: Any = None,
    ) -> dict[str, Any]:
        import omni.kit.ui_test as ui_test  # lazy

        if not widget_path or "//" not in widget_path:
            raise ValueError(
                f"invalid widget_path: {widget_path!r} — expected 'Window Title//...'"
            )

        # Auto-settle layer for the layout-init race documented in the
        # module docstring. Without this, the very first ext_ui_invoke
        # after extension_activate() raises "float division by zero"
        # because ui.Workspace.get_main_window_width() returns 0 until
        # the workspace finishes laying the panel out for one or two
        # frames. window_ui_show forces focus + a settle window which
        # populates the dimensions before ui_test issues the click.
        window_title = widget_path.split("//", 1)[0]
        if window_title:
            try:
                await self._auto_show_window(window_title, settle_frames=10)
            except Exception as exc:  # noqa: BLE001 — soft-fail; click may still succeed
                logger.info("auto-show %s soft-fail: %s", window_title, exc)

        # find() is sync (not a coroutine). It returns None on mismatch/ambiguity.
        element = ui_test.find(widget_path)
        if element is None:
            raise ValueError(f"widget not found at path: {widget_path}")

        act = (action or "click").lower()
        if act == "click":
            await element.click()
        elif act == "double_click":
            await element.double_click()
        elif act == "type":
            if value is None:
                raise ValueError("action='type' requires a string value")
            await element.input(str(value), clear_before_input=True)
        elif act == "select":
            if value is None:
                raise ValueError("action='select' requires an integer value (index)")
            widget = getattr(element, "widget", None)
            if widget is None or not hasattr(widget, "model"):
                raise ValueError(f"widget at {widget_path} has no selectable model")
            model = widget.model
            if hasattr(model, "get_item_value_model"):
                inner = model.get_item_value_model()
                if inner is None:
                    raise ValueError("select: get_item_value_model() returned None")
                inner.set_value(int(value))
            else:
                model.set_value(int(value))
        elif act in ("check", "uncheck"):
            widget = getattr(element, "widget", None)
            if widget is None or not hasattr(widget, "model"):
                raise ValueError(f"widget at {widget_path} has no toggleable model")
            widget.model.set_value(act == "check")
        else:
            raise ValueError(f"unsupported action: {action}")

        try:
            import omni.kit.app  # lazy
            app = omni.kit.app.get_app()
            for _ in range(4):
                await app.next_update_async()
        except Exception:  # noqa: BLE001
            pass

        widget = getattr(element, "widget", None)
        post = _describe_widget(widget, widget_path, widget_path.split("//", 1)[0])
        return {
            "ok": True,
            "widget_path": widget_path,
            "action_performed": act,
            "value": value,
            "post_state": post,
        }
