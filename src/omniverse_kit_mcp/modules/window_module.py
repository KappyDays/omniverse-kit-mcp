"""Kit GUI window / menu / ui_window MCP module."""

from __future__ import annotations

import logging
import time
from typing import Any

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.window import (
    MenuItemInfo,
    MenuListResult,
    MenuTriggerResult,
    UiWindowInfo,
    UiWindowListResult,
    UiWindowShowResult,
    WindowCaptureRequest,
    WindowCaptureResult,
    WindowInfo,
    WindowListResult,
)

logger = logging.getLogger(__name__)


class WindowModule:
    """Kit GUI window control — counterpart to widget-level `omni.kit.ui_test`."""

    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def capture(
        self, meta: OperationMeta, request: WindowCaptureRequest,
    ) -> ModuleResult[WindowCaptureResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.window_capture(request.to_dict())
            result = WindowCaptureResult(
                artifact_id=str(raw.get("artifact_id", "")),
                path=str(raw.get("path", "")),
                width=int(raw.get("width", 0)),
                height=int(raw.get("height", 0)),
                hwnd=int(raw.get("hwnd", 0)),
                title=str(raw.get("title", "")),
                class_name=str(raw.get("class_name", "")),
                mode=str(raw.get("mode", request.mode)),
                used_printwindow=bool(raw.get("used_printwindow", False)),
                used_bitblt_fallback=bool(raw.get("used_bitblt_fallback", False)),
                sha256=str(raw.get("sha256", "")),
                wait_stable=bool(raw.get("wait_stable", False)),
                stabilized=raw.get("stabilized"),
                polls=raw.get("polls"),
                last_diff=raw.get("last_diff"),
                max_diff_seen=raw.get("max_diff_seen"),
                diff_threshold=raw.get("diff_threshold"),
                diff_history=tuple(raw.get("diff_history") or ()),
                elapsed_s=raw.get("elapsed_s"),
                focus_action=str(raw.get("focus_action", "none")),
                created_at_epoch_ms=raw.get("created_at_epoch_ms"),
            )
            artifacts = {"image": result.path} if result.path else {}
            return ok_result(result, started_ms=started, artifacts=artifacts)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="WINDOW_CAPTURE_ERROR",
            )

    async def list_windows(self, meta: OperationMeta) -> ModuleResult[WindowListResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.window_list()
            result = WindowListResult(
                pid=int(raw.get("pid") or 0),
                count=int(raw.get("count") or 0),
                windows=tuple(
                    WindowInfo(
                        hwnd=int(w.get("hwnd") or 0),
                        title=str(w.get("title", "")),
                        class_name=str(w.get("class_name", "")),
                        width=int(w.get("width") or 0),
                        height=int(w.get("height") or 0),
                    )
                    for w in raw.get("windows") or []
                ),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="WINDOW_LIST_ERROR",
            )

    async def list_ui_windows(
        self, meta: OperationMeta, name_filter: str | None = None,
    ) -> ModuleResult[UiWindowListResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.window_ui_list(name_filter)
            result = UiWindowListResult(
                count=int(raw.get("count") or 0),
                filter=raw.get("filter"),
                windows=tuple(
                    UiWindowInfo(
                        title=str(w.get("title", "")),
                        visible=bool(w.get("visible", False)),
                        docked=bool(w.get("docked", False)),
                        dock_id=int(w.get("dock_id") or 0),
                        width=float(w.get("width") or 0.0),
                        height=float(w.get("height") or 0.0),
                    )
                    for w in raw.get("windows") or []
                ),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="WINDOW_UI_LIST_ERROR",
            )

    async def show_ui_window(
        self, meta: OperationMeta,
        name: str, visible: bool = True, focus: bool = True, settle_frames: int = 5,
    ) -> ModuleResult[UiWindowShowResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.window_ui_show(
                name=name, visible=visible, focus=focus, settle_frames=settle_frames,
            )
            result = UiWindowShowResult(
                name=str(raw.get("name", name)),
                resolved_name=str(raw.get("resolved_name", name)),
                resolved_via=raw.get("resolved_via"),
                requested_visible=bool(raw.get("requested_visible", visible)),
                found=bool(raw.get("found", False)),
                focused=raw.get("focused"),
                visible_after=raw.get("visible_after"),
                docked=raw.get("docked"),
                dock_id=raw.get("dock_id"),
                focus_error=raw.get("focus_error"),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="WINDOW_UI_SHOW_ERROR",
            )

    async def list_menu_items(
        self, meta: OperationMeta, menu_path: str | None = None,
    ) -> ModuleResult[MenuListResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.window_menu_list(menu_path)
            items = tuple(_parse_menu_item(it) for it in raw.get("items") or [])
            result = MenuListResult(
                menu_path=raw.get("menu_path"),
                count=int(raw.get("count") or len(items)),
                items=items,
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="WINDOW_MENU_LIST_ERROR",
            )

    async def trigger_menu(
        self, meta: OperationMeta, menu_path: str,
    ) -> ModuleResult[MenuTriggerResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.window_menu_trigger(menu_path)
            action = raw.get("action") or ("", "")
            if isinstance(action, list):
                action_tuple = (str(action[0]) if len(action) > 0 else "",
                                str(action[1]) if len(action) > 1 else "")
            else:
                action_tuple = (str(action), "")
            result = MenuTriggerResult(
                menu_path=str(raw.get("menu_path", menu_path)),
                action=action_tuple,
                created_prims=tuple(raw.get("created_prims") or ()),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="WINDOW_MENU_TRIGGER_ERROR",
            )


def _parse_menu_item(raw: dict[str, Any]) -> MenuItemInfo:
    action = raw.get("onclick_action")
    action_tuple: tuple[str, str] | None = None
    if isinstance(action, list) and len(action) >= 2:
        action_tuple = (str(action[0]), str(action[1]))
    return MenuItemInfo(
        path=str(raw.get("path", "")),
        name=str(raw.get("name", "")),
        has_submenu=bool(raw.get("has_submenu", False)),
        enabled=bool(raw.get("enabled", True)),
        onclick_action=action_tuple,
        action_prefix=raw.get("action_prefix"),
    )
