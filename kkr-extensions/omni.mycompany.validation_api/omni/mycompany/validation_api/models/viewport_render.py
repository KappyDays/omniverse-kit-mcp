"""Pydantic models for Viewport render extension (Phase F)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ViewportSetRenderModeRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viewport_name: str = "Viewport"
    mode: Literal["RealTime", "PathTracing"]


class ViewportSetRenderQualityRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    samples: int = Field(default=1, ge=1, le=4096)
    denoiser: Literal["auto", "DLSS", "NRD", "off"] = "auto"


class ViewportToggleOverlayRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viewport_name: str = "Viewport"
    overlay: Literal["gridlines", "axis", "stats"]
    visible: bool = True


class ViewportSetFovRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viewport_name: str = "Viewport"
    fov_deg: float = Field(ge=1.0, le=179.0)


class ViewportSetCameraLookatRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eye: list[float] = Field(min_length=3, max_length=3)
    target: list[float] = Field(min_length=3, max_length=3)
    up: list[float] = Field(default=[0.0, 0.0, 1.0], min_length=3, max_length=3)
    viewport_name: str = "Viewport"
    camera_path: str | None = None


class ViewportFocusPrimRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    viewport_name: str = "Viewport"
    camera_path: str | None = None
    padding: float = Field(default=1.35, ge=1.0, le=10.0)
    select: bool = True
