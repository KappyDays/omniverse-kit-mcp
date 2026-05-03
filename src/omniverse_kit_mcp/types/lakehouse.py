"""Lakehouse types — query only (no inject/cleanup per interview spec)."""

from __future__ import annotations

from dataclasses import dataclass, field

from omniverse_kit_mcp.types.common import JsonValue


@dataclass(slots=True, frozen=True)
class LakehouseDatasetRef:
    namespace: str
    dataset: str
    table: str | None = None
    version: str | None = None


@dataclass(slots=True, frozen=True)
class LakehouseQueryRequest:
    sql: str | None = None
    target: LakehouseDatasetRef | None = None
    filters: dict[str, JsonValue] = field(default_factory=dict)
    limit: int = 1_000


@dataclass(slots=True, frozen=True)
class LakehouseRow:
    values: dict[str, JsonValue]


@dataclass(slots=True, frozen=True)
class LakehouseQueryResult:
    row_count: int
    rows: tuple[LakehouseRow, ...]
    schema: dict[str, str]
