"""Material types — MDL enumeration / assignment / binding readback (Phase F)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MaterialListMdlRequest:
    library: str = "default"


@dataclass(slots=True, frozen=True)
class MaterialMdlEntry:
    name: str
    url: str
    library: str


@dataclass(slots=True, frozen=True)
class MaterialListMdlResult:
    ok: bool
    library: str
    count: int
    entries: tuple[MaterialMdlEntry, ...]


@dataclass(slots=True, frozen=True)
class MaterialAssignMdlRequest:
    prim_path: str
    mdl_url: str
    material_name: str


@dataclass(slots=True, frozen=True)
class MaterialAssignMdlResult:
    ok: bool
    prim_path: str
    material_prim_path: str
    mdl_url: str
    material_name: str


@dataclass(slots=True, frozen=True)
class MaterialGetBoundRequest:
    prim_path: str


@dataclass(slots=True, frozen=True)
class MaterialGetBoundResult:
    ok: bool
    prim_path: str
    material_path: str | None
    binding_strength: str | None
