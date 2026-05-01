"""Pydantic models for Material REST endpoints (Phase F)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MaterialAssignMdlRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    mdl_url: str = Field(
        description="MDL module URL (e.g. OmniPBR.mdl or absolute path).",
    )
    material_name: str = Field(description="MDL material identifier within the module.")
