"""UI automation typed payloads (Phase D)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class WidgetInfo:
    path: str
    label: str
    type: str
    enabled: bool
    visible: bool
    value: Any = None


@dataclass(slots=True, frozen=True)
class WindowMeta:
    title: str
    visible: bool
    docked: bool


@dataclass(slots=True, frozen=True)
class UiTreeResult:
    ext_id: str | None
    window: str | None
    matched_windows: tuple[str, ...]
    windows: tuple[WindowMeta, ...]
    widgets: tuple[WidgetInfo, ...]
    widget_count: int
    walk_errors: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class UiInvokeResult:
    widget_path: str
    action_performed: str
    value: Any
    post_state: WidgetInfo


@dataclass(slots=True, frozen=True)
class UiRunAndWaitResult:
    widget_path: str
    action_performed: str
    invoked: bool
    wait_prim_path: str
    wait_property_name: str
    wait_comparator: str
    wait_passed: bool
    timed_out: bool
    poll_count: int
    elapsed_s: float
    last_failures: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ExtensionActivateResult:
    ext_id: str
    was_enabled: bool
    enabled: bool
    reloaded: bool


@dataclass(slots=True, frozen=True)
class ExtensionReloadResult:
    ext_id: str
    was_enabled: bool
    enabled: bool
    reloaded: bool
    modules_purged: int


# --- Phase H — Extension management extensions -------------------------------


@dataclass(slots=True, frozen=True)
class ExtensionDeactivateResult:
    ok: bool
    ext_id: str
    was_enabled: bool
    enabled: bool


@dataclass(slots=True, frozen=True)
class ExtensionSummary:
    id: str
    full_id: str
    name: str
    version: str | None
    enabled: bool
    path: str | None = None
    title: str | None = None


@dataclass(slots=True, frozen=True)
class ExtensionListAllResult:
    ok: bool
    enabled_only: bool
    count: int
    extensions: tuple[ExtensionSummary, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ExtensionInfoResult:
    ok: bool
    ext_id: str
    info: dict[str, Any] = field(default_factory=dict)
