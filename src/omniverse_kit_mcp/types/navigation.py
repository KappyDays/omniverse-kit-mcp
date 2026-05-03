"""NavMesh / navigation typed payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True, frozen=True)
class NavMeshBakeResult:
    ok: bool
    agent_max_radius: float | None
    area_count: int | None
    mesh_signature: str | None
    volume_prim_path: str | None
    volume_created: bool
    volume_scale: float
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class NavPathResult:
    ok: bool
    points: tuple[tuple[float, float, float], ...]
    length: float
    straight: bool
    auto_baked: bool
    agent_radius: float
    agent_height: float


@dataclass(slots=True, frozen=True)
class NavExcludeVolumeResult:
    ok: bool
    volume_prim_path: str
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    padding: float
    source_prim_path: str | None


@dataclass(slots=True, frozen=True)
class NavPathQueryRequest:
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    agent_radius: float = 0.25
    agent_height: float = 1.8
    straighten: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": list(self.start),
            "end": list(self.end),
            "agent_radius": self.agent_radius,
            "agent_height": self.agent_height,
            "straighten": self.straighten,
        }


@dataclass(slots=True, frozen=True)
class NavigationSetVisualizationRequest:
    mode: Literal["walkable", "obstacles", "off"]


@dataclass(slots=True, frozen=True)
class NavigationSetVisualizationResult:
    ok: bool
    mode: str
    backend: str
    setting_path: str | None


@dataclass(slots=True, frozen=True)
class SampleWalkablePointsRequest:
    count: int
    bounds_min: tuple[float, float, float] | None = None
    bounds_max: tuple[float, float, float] | None = None
    seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"count": self.count}
        if self.bounds_min is not None:
            d["bounds_min"] = list(self.bounds_min)
        if self.bounds_max is not None:
            d["bounds_max"] = list(self.bounds_max)
        if self.seed is not None:
            d["seed"] = self.seed
        return d


@dataclass(slots=True, frozen=True)
class SampleWalkablePointsResult:
    ok: bool
    points: tuple[tuple[float, float, float], ...]
    triangle_count: int
    total_area_m2: float
    seed: int | None
    method: str  # "area_weighted" | "bbox_reachability"
