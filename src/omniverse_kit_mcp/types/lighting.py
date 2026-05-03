"""Lighting types — UsdLux Dome/Distant/Disk/Rect/Sphere + exposure (Phase F)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LightingCreateDomeRequest:
    prim_path: str
    intensity: float = 1000.0
    texture: str | None = None


@dataclass(slots=True, frozen=True)
class LightingCreateDistantRequest:
    prim_path: str
    intensity: float = 1000.0
    angle_deg: float = 0.53


@dataclass(slots=True, frozen=True)
class LightingCreateDiskRequest:
    prim_path: str
    intensity: float = 1000.0
    radius: float = 1.0


@dataclass(slots=True, frozen=True)
class LightingCreateRectRequest:
    prim_path: str
    intensity: float = 1000.0
    width: float = 1.0
    height: float = 1.0


@dataclass(slots=True, frozen=True)
class LightingCreateSphereRequest:
    prim_path: str
    intensity: float = 1000.0
    radius: float = 1.0


@dataclass(slots=True, frozen=True)
class LightingCreateResult:
    ok: bool
    prim_path: str
    light_type: str
    intensity: float
    extra: dict[str, float | str | None]


@dataclass(slots=True, frozen=True)
class LightingSetExposureRequest:
    exposure: float


@dataclass(slots=True, frozen=True)
class LightingSetExposureResult:
    ok: bool
    exposure: float
    setting_path: str
