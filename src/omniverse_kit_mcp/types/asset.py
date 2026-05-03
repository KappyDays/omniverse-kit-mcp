"""Types for Asset Browser catalog listing (Phase B+)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class AssetCategory:
    name: str
    url: str


@dataclass(slots=True, frozen=True)
class AssetItem:
    name: str
    url: str
    is_folder: bool
    size: int | None = None


@dataclass(slots=True, frozen=True)
class AssetListResult:
    assets_root: str | None
    category: str | None
    subpath: str
    base_url: str | None
    target_url: str | None
    categories: tuple[AssetCategory, ...] = field(default_factory=tuple)
    items: tuple[AssetItem, ...] = field(default_factory=tuple)
    count: int = 0
