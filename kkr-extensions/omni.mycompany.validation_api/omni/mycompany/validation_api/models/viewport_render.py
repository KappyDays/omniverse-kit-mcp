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
