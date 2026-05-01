"""Pydantic models for Selection / Viewport-camera endpoints (Phase B+)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StageSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_paths: list[str] = Field(
        default_factory=list,
        description="Prim paths to select (replaces the current selection).",
    )
    expand_in_stage: bool = True


class ViewportActiveCameraRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_path: str = Field(description="Path of the camera prim to activate.")
    viewport_name: str = Field(default="Viewport")
