"""Extension module — trigger, reset, get_state + UI / log capture (Phase D)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.exceptions import ExtensionBusyError
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.extension import (
    ExtensionResetRequest,
    ExtensionState,
    ExtensionTriggerRequest,
)
from omniverse_kit_mcp.types.log import LogCaptureResult, LogEntry
from omniverse_kit_mcp.types.ui import (
    ExtensionActivateResult,
    ExtensionDeactivateResult,
    ExtensionInfoResult,
    ExtensionListAllResult,
    ExtensionReloadResult,
    ExtensionSummary,
    UiInvokeResult,
    UiTreeResult,
    WidgetInfo,
    WindowMeta,
)

logger = logging.getLogger(__name__)


class ExtensionModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def trigger(
        self, meta: OperationMeta, request: ExtensionTriggerRequest
    ) -> ModuleResult[ExtensionState]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_trigger({
                "operation": request.operation,
                "payload": request.payload,
                "wait_for_idle": request.wait_for_idle,
                "idle_timeout_s": request.idle_timeout_s,
            })

            if request.wait_for_idle:
                state = _parse_state(raw)
                if state.busy:
                    state = await self._poll_until_idle(
                        request.idle_timeout_s, request.poll_interval_s
                    )
            else:
                state = _parse_state(raw)

            return ok_result(state, started_ms=started)
        except ExtensionBusyError:
            return error_result(
                "Extension is busy", started_ms=started, error_code="EXTENSION_BUSY"
            )
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="EXTENSION_TRIGGER_ERROR")

    async def reset(
        self, meta: OperationMeta, request: ExtensionResetRequest
    ) -> ModuleResult[ExtensionState]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_reset({
                "reset_stage_changes": request.reset_stage_changes,
                "reset_internal_state": request.reset_internal_state,
                "clear_caches": request.clear_caches,
                "reload_config": request.reload_config,
            })
            return ok_result(_parse_state(raw), started_ms=started)
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="EXTENSION_RESET_ERROR")

    async def get_state(self, meta: OperationMeta) -> ModuleResult[ExtensionState]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_state()
            return ok_result(_parse_state(raw), started_ms=started)
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="EXTENSION_STATE_ERROR")

    async def _poll_until_idle(
        self, timeout_s: float, interval_s: float
    ) -> ExtensionState:
        from omniverse_kit_mcp.exceptions import ExtensionTriggerError
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            raw = await self._client.extension_state()
            state = _parse_state(raw)
            if not state.busy:
                return state
            await asyncio.sleep(interval_s)
        # Timeout: extension still busy
        raise ExtensionTriggerError(
            f"Extension still busy after {timeout_s}s idle timeout",
            error_code="EXTENSION_IDLE_TIMEOUT",
        )

    # ------------------------------------------------------------------
    # Phase D — UI automation + carb log capture
    # ------------------------------------------------------------------

    async def activate(
        self, meta: OperationMeta, ext_id: str, reload: bool = False,
    ) -> ModuleResult[ExtensionActivateResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_activate(ext_id, reload=reload)
            return ok_result(
                ExtensionActivateResult(
                    ext_id=str(raw.get("ext_id", ext_id)),
                    was_enabled=bool(raw.get("was_enabled", False)),
                    enabled=bool(raw.get("enabled", False)),
                    reloaded=bool(raw.get("reloaded", False)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="EXTENSION_ACTIVATE_ERROR",
            )

    async def reload_clean(
        self, meta: OperationMeta, ext_id: str,
    ) -> ModuleResult[ExtensionReloadResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_reload_clean(ext_id)
            return ok_result(
                ExtensionReloadResult(
                    ext_id=str(raw.get("ext_id", ext_id)),
                    was_enabled=bool(raw.get("was_enabled", False)),
                    enabled=bool(raw.get("enabled", False)),
                    reloaded=bool(raw.get("reloaded", False)),
                    modules_purged=int(raw.get("modules_purged", 0)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="EXTENSION_RELOAD_ERROR",
            )

    async def get_ui_tree(
        self, meta: OperationMeta,
        ext_id: str | None = None,
        window: str | None = None,
        widget_types: list[str] | None = None,
    ) -> ModuleResult[UiTreeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_ui_tree(
                ext_id=ext_id, window=window, widget_types=widget_types,
            )
            result = UiTreeResult(
                ext_id=raw.get("ext_id"),
                window=raw.get("window"),
                matched_windows=tuple(raw.get("matched_windows") or ()),
                windows=tuple(
                    WindowMeta(
                        title=str(w.get("title", "")),
                        visible=bool(w.get("visible", False)),
                        docked=bool(w.get("docked", False)),
                    )
                    for w in raw.get("windows") or []
                ),
                widgets=tuple(_parse_widget(w) for w in raw.get("widgets") or []),
                widget_count=int(raw.get("widget_count") or 0),
                walk_errors=tuple(raw.get("walk_errors") or ()),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="EXTENSION_UI_TREE_ERROR",
            )

    async def ui_invoke(
        self, meta: OperationMeta,
        widget_path: str, action: str, value: Any = None,
    ) -> ModuleResult[UiInvokeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_ui_invoke(
                widget_path, action, value=value,
            )
            post = raw.get("post_state") or {}
            result = UiInvokeResult(
                widget_path=str(raw.get("widget_path", widget_path)),
                action_performed=str(raw.get("action_performed", action)),
                value=raw.get("value"),
                post_state=_parse_widget(post),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="EXTENSION_UI_INVOKE_ERROR",
            )

    async def clear_logs(
        self, meta: OperationMeta,
    ) -> ModuleResult[dict[str, Any]]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_clear_logs()
            return ok_result(
                {"ok": True, "removed": int(raw.get("removed") or 0)},
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="EXTENSION_LOGS_CLEAR_ERROR",
            )

    async def deactivate(
        self, meta: OperationMeta, ext_id: str,
    ) -> ModuleResult[ExtensionDeactivateResult]:
        """Disable a Kit Extension by id (Phase H)."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_deactivate(ext_id)
            return ok_result(
                ExtensionDeactivateResult(
                    ok=bool(raw.get("ok", True)),
                    ext_id=str(raw.get("ext_id", ext_id)),
                    was_enabled=bool(raw.get("was_enabled", False)),
                    enabled=bool(raw.get("enabled", False)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="EXTENSION_DEACTIVATE_ERROR",
            )

    async def list_all(
        self, meta: OperationMeta, enabled_only: bool = False,
    ) -> ModuleResult[ExtensionListAllResult]:
        """Enumerate Kit extensions (Phase H)."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_list_all(enabled_only=enabled_only)
            extensions = tuple(
                ExtensionSummary(
                    id=str(e.get("id", "")),
                    full_id=str(e.get("full_id", e.get("id", ""))),
                    name=str(e.get("name", e.get("id", ""))),
                    version=e.get("version"),
                    enabled=bool(e.get("enabled", False)),
                    path=e.get("path"),
                    title=e.get("title"),
                )
                for e in raw.get("extensions") or []
            )
            return ok_result(
                ExtensionListAllResult(
                    ok=bool(raw.get("ok", True)),
                    enabled_only=bool(raw.get("enabled_only", enabled_only)),
                    count=int(raw.get("count", len(extensions))),
                    extensions=extensions,
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="EXTENSION_LIST_ALL_ERROR",
            )

    async def get_info(
        self, meta: OperationMeta, ext_id: str,
    ) -> ModuleResult[ExtensionInfoResult]:
        """Read ExtensionManager dict for ext_id (Phase H)."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_get_info(ext_id)
            return ok_result(
                ExtensionInfoResult(
                    ok=bool(raw.get("ok", True)),
                    ext_id=str(raw.get("ext_id", ext_id)),
                    info=dict(raw.get("info") or {}),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="EXTENSION_GET_INFO_ERROR",
            )

    async def capture_logs(
        self, meta: OperationMeta,
        ext_id: str | None = None,
        since_ms: int | None = None,
        level: str = "INFO",
        limit: int = 1000,
    ) -> ModuleResult[LogCaptureResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.extension_logs(
                ext_id=ext_id, since_ms=since_ms, level=level, limit=limit,
            )
            entries = tuple(
                LogEntry(
                    ts_ms=int(e.get("ts_ms") or 0),
                    level=str(e.get("level", "")),
                    level_int=int(e.get("level_int") or 0),
                    source=str(e.get("source", "")),
                    filename=str(e.get("filename", "")),
                    line=int(e.get("line") or 0),
                    msg=str(e.get("msg", "")),
                )
                for e in raw.get("entries") or []
            )
            result = LogCaptureResult(
                entries=entries,
                count=int(raw.get("count") or len(entries)),
                truncated=bool(raw.get("truncated", False)),
                level_filter=str(raw.get("level_filter", level)),
                since_ms=raw.get("since_ms"),
                source_filter=raw.get("source_filter"),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="EXTENSION_LOGS_ERROR",
            )


def _parse_widget(raw: dict[str, Any]) -> WidgetInfo:
    return WidgetInfo(
        path=str(raw.get("path", "")),
        label=str(raw.get("label", "")),
        type=str(raw.get("type", "")),
        enabled=bool(raw.get("enabled", False)),
        visible=bool(raw.get("visible", False)),
        value=raw.get("value"),
    )


def _parse_state(raw: dict) -> ExtensionState:
    return ExtensionState(
        enabled=raw.get("enabled", True),
        busy=raw.get("busy", False),
        last_operation=raw.get("last_operation"),
        last_error=raw.get("last_error"),
        reset_token=raw.get("reset_token"),
        state_version=raw.get("state_version", 0),
    )
