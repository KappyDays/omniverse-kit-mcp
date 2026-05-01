"""Pydantic models for Navigation REST endpoints beyond bake/query (Phase E + J)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NavigationSetVisualizationRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["walkable", "obstacles", "off"] = Field(
        description=(
            "'walkable' highlights the baked NavMesh walkable surface, "
            "'obstacles' shows only the Exclude regions, 'off' hides all overlays."
        ),
    )


class SampleWalkablePointsRequestModel(BaseModel):
    """Sample N random walkable points on the baked NavMesh.

    Algorithm prefers area-weighted barycentric over the triangle list
    (spec §8.1). When the triangle API is unavailable on this Kit build,
    falls back to bbox-rejection: random points within the NavMesh volume
    bbox, accepted only if ``query_shortest_path`` reaches them from a
    seed origin.
    """

    model_config = ConfigDict(extra="forbid")

    count: int = Field(..., ge=1, le=1000)
    bounds_min: list[float] | None = Field(
        default=None,
        description="Optional [x,y,z] AABB minimum (componentwise) — both bounds must be set or both null.",
    )
    bounds_max: list[float] | None = None
    seed: int | None = None


class SampleWalkablePointsResponseModel(BaseModel):
    ok: bool = True
    points: list[list[float]] = Field(description="World-space [x,y,z] points on walkable surface")
    triangle_count: int = Field(description="Triangles considered (0 if bbox-fallback path)")
    total_area_m2: float = Field(description="Sum of triangle areas (0 in fallback path)")
    seed: int | None = None
    method: Literal["area_weighted", "bbox_reachability"] = Field(
        description="area_weighted = spec §8.1 path; bbox_reachability = fallback when triangle API absent"
    )
