"""Pydantic models for Stage REST endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StageCaptureFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_prim_patterns: list[str] = Field(default=["*"])
    exclude_prim_patterns: list[str] = Field(default=[])
    include_properties: bool = True
    include_metadata: bool = True
    max_prim_count: int = Field(default=10000, ge=1)


class PrimExistenceAssertionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    should_exist: bool = True
    expected_type_name: str | None = None
    expected_active: bool | None = None


class PropertyAssertionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    property_name: str
    property_type: str = "attribute"
    comparator: str = "equals"
    expected_value: Any = None
    expected_type_name: str | None = None
    tolerance: float | None = None


class AssertionReportModel(BaseModel):
    passed: bool
    failures: list[dict[str, Any]] = []
    checked_count: int = 0


# --- Phase A: WRITE operation models ---


class StageLoadUsdRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usd_url: str = Field(description="USD asset URL (local path or omniverse://)")
    prim_path: str = Field(description="Stage path where the reference is created")
    position: list[float] | None = Field(
        default=None, description="[x, y, z] world position"
    )
    rotation: list[float] | None = Field(
        default=None, description="[rx, ry, rz] Euler degrees (XYZ order)"
    )


class StageSetPropertyRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    property_name: str
    value: Any = Field(description="New value (JSON-compatible)")
    type_hint: str | None = Field(
        default=None,
        description="USD type hint: Vec3d, Vec3f, Quatd, float, int, bool, string, asset",
    )


class StageSetSemanticLabelRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Prim to label (label inherits to its subtree).")
    label_class: str = Field(description="Semantic class, e.g. 'forklift'.")
    label_type: str = Field(default="class", description="Label taxonomy bucket (e.g. 'class').")


class StageCreatePrimRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    prim_type: str = Field(default="Xform", description="USD prim type (Xform, Cube, Sphere, ...)")
    position: list[float] | None = Field(
        default=None, description="[x, y, z] world position"
    )


class StageDeletePrimRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str


class StageComputeWorldBboxRequestModel(BaseModel):
    """World-space axis-aligned bbox + transform of a prim."""

    model_config = ConfigDict(extra="forbid")

    prim_path: str
    include_purposes: list[str] = Field(
        default_factory=lambda: ["default", "render"],
        description="UsdGeom purposes to include (default / proxy / render / guide).",
    )


class StagePlacementValidationRequestModel(BaseModel):
    """Broad-phase placement validation using world-space aligned bboxes."""

    model_config = ConfigDict(extra="forbid")

    subject_prim_paths: list[str] = Field(min_length=1)
    container_prim_path: str | None = None
    support_prim_path: str | None = None
    obstacle_prim_paths: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=lambda: ["containment"])
    include_purposes: list[str] = Field(
        default_factory=lambda: ["default", "render"],
        description="UsdGeom purposes to include (default / proxy / render / guide).",
    )
    containment_axes: list[str] = Field(default_factory=lambda: ["x", "y"])
    margin_m: float = Field(default=0.0, ge=0.0)
    min_clearance_m: float = Field(default=0.0, ge=0.0)
    floor_tolerance_m: float = Field(default=0.01, ge=0.0)
    floor_axis: str = "z"
