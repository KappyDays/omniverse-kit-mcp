"""Content browser types — omni.client list / stat / resolve (Phase H)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class ContentBrowseRequest:
    url: str
    recursive: bool = False
    max_depth: int = 2
    max_entries: int = 500


@dataclass(slots=True, frozen=True)
class ContentEntry:
    url: str
    name: str
    is_folder: bool
    size: int | None = None
    modified_time_ns: int | None = None
    flags: int = 0


@dataclass(slots=True, frozen=True)
class ContentBrowseResult:
    ok: bool
    url: str
    recursive: bool
    entries: tuple[ContentEntry, ...] = field(default_factory=tuple)
    entry_count: int = 0
    truncated: bool = False
    backend: str = ""


@dataclass(slots=True, frozen=True)
class ContentPreviewRequest:
    url: str


@dataclass(slots=True, frozen=True)
class ContentPreviewResult:
    ok: bool
    url: str
    info: dict[str, Any] = field(default_factory=dict)
    backend: str = ""


@dataclass(slots=True, frozen=True)
class ContentInspectRequest:
    url: str


@dataclass(slots=True, frozen=True)
class ContentInspectResult:
    """USD geometric info — what content_preview (file metadata only) lacks."""

    ok: bool
    url: str
    default_prim: str
    bbox_min: tuple[float, float, float] | None
    bbox_max: tuple[float, float, float] | None
    meters_per_unit: float
    up_axis: str
    prim_count: int
    backend: str = ""


@dataclass(slots=True, frozen=True)
class ContentResolveRequest:
    url: str


@dataclass(slots=True, frozen=True)
class ContentResolveResult:
    ok: bool
    url: str
    resolved: str
    backend: str = ""
