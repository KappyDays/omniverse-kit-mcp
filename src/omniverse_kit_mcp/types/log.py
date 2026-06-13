"""carb log capture typed payloads (Phase D)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class LogEntry:
    ts_ms: int
    level: str
    level_int: int
    source: str
    filename: str
    line: int
    msg: str


@dataclass(slots=True, frozen=True)
class LogCaptureResult:
    entries: tuple[LogEntry, ...]
    count: int
    truncated: bool
    level_filter: str
    since_ms: int | None
    source_filter: str | None
    capture_running: bool = False
