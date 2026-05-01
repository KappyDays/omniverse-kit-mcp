"""Pydantic models for Lighting REST endpoints (Phase F)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LightingCreateDomeRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    intensity: float = Field(default=1000.0, ge=0.0)
    texture: str | None = None


class LightingCreateDistantRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    intensity: float = Field(default=1000.0, ge=0.0)
    angle_deg: float = Field(default=0.53, ge=0.0, le=180.0)


class LightingCreateDiskRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    intensity: float = Field(default=1000.0, ge=0.0)
    radius: float = Field(default=1.0, gt=0.0)


class LightingCreateRectRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    intensity: float = Field(default=1000.0, ge=0.0)
    width: float = Field(default=1.0, gt=0.0)
    height: float = Field(default=1.0, gt=0.0)


class LightingCreateSphereRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    intensity: float = Field(default=1000.0, ge=0.0)
    radius: float = Field(default=1.0, gt=0.0)


class LightingSetExposureRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exposure: float
