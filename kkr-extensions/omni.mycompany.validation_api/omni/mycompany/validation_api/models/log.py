"""Pydantic models for carb log capture (Phase D)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LogLevelName = Literal["VERBOSE", "INFO", "WARN", "ERROR", "FATAL", "ALL"]


class LogEntryModel(BaseModel):
    ts_ms: int
    level: str
    level_int: int
    source: str
    filename: str
    line: int
    msg: str


class LogCaptureResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    entries: list[LogEntryModel] = Field(default_factory=list)
    count: int
    truncated: bool = False
    level_filter: str
    since_ms: int | None = None
    source_filter: str | None = None
    capture_running: bool = False
    capture_stop_requested: bool = False
    capture_stop_completed: bool | None = None
    capture_stop_timed_out: bool = False
    capture_stop_timeout_s: float | None = None
