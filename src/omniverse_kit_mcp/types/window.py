"""Kit GUI window domain typed payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class WindowInfo:
    """OS-level window (Win32 EnumWindows row)."""
    hwnd: int
    title: str
    class_name: str
    width: int
    height: int


@dataclass(slots=True, frozen=True)
class UiWindowInfo:
    """omni.ui.Window row."""
    title: str
    visible: bool
    docked: bool
    dock_id: int = 0
    width: float = 0.0
    height: float = 0.0


@dataclass(slots=True, frozen=True)
class MenuItemInfo:
    path: str
    name: str
    has_submenu: bool
    enabled: bool
    onclick_action: tuple[str, str] | None = None
    action_prefix: str | None = None


@dataclass(slots=True, frozen=True)
class WindowCaptureResult:
    artifact_id: str
    path: str
    width: int
    height: int
    hwnd: int
    title: str
    class_name: str
    mode: str
    used_printwindow: bool
    used_bitblt_fallback: bool
    sha256: str
    wait_stable: bool
    stabilized: bool | None = None
    polls: int | None = None
    last_diff: float | None = None
    max_diff_seen: float | None = None
    diff_threshold: float | None = None
    diff_history: tuple[float, ...] = field(default_factory=tuple)
    elapsed_s: float | None = None
    focus_action: str = "none"  # "none" | "restored_to_maximized" | "restored_to_normal"
    created_at_epoch_ms: int | None = None


@dataclass(slots=True, frozen=True)
class WindowListResult:
    pid: int
    count: int
    windows: tuple[WindowInfo, ...]


@dataclass(slots=True, frozen=True)
class UiWindowListResult:
    count: int
    filter: str | None
    windows: tuple[UiWindowInfo, ...]


@dataclass(slots=True, frozen=True)
class UiWindowShowResult:
    name: str
    resolved_name: str
    resolved_via: str | None
    requested_visible: bool
    found: bool
    focused: bool | None = None
    visible_after: bool | None = None
    docked: bool | None = None
    dock_id: int | None = None
    focus_error: str | None = None


@dataclass(slots=True, frozen=True)
class MenuListResult:
    menu_path: str | None
    count: int
    items: tuple[MenuItemInfo, ...]


@dataclass(slots=True, frozen=True)
class MenuTriggerResult:
    menu_path: str
    action: tuple[str, str]
    created_prims: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class WindowCaptureRequest:
    """Caller-facing options for `window_capture`."""
    mode: str = "kit"  # "kit" | "foreground" | explicit hwnd
    hwnd: int | None = None
    settle_frames: int = 5
    output_format: str = "png"
    bring_to_front: bool = False
    use_client_rect: bool = False
    wait_stable: bool = False
    stable_interval_s: float = 2.0
    stable_consecutive: int = 2
    stable_max_wait_s: float = 45.0
    stable_diff_threshold: float = 0.01

    def to_dict(self) -> dict[str, Any]:
        out = {
            "mode": self.mode,
            "settle_frames": self.settle_frames,
            "output_format": self.output_format,
            "bring_to_front": self.bring_to_front,
            "use_client_rect": self.use_client_rect,
            "wait_stable": self.wait_stable,
            "stable_interval_s": self.stable_interval_s,
            "stable_consecutive": self.stable_consecutive,
            "stable_max_wait_s": self.stable_max_wait_s,
            "stable_diff_threshold": self.stable_diff_threshold,
        }
        if self.hwnd is not None:
            out["hwnd"] = self.hwnd
        return out
