"""Pydantic models for asset helper endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExternalAssetConvertRequestModel(BaseModel):
    """Convert a downloaded external asset to USD without stage placement."""

    model_config = ConfigDict(extra="forbid")

    input_path: str = Field(description="Absolute local path to the downloaded source asset")
    output_path: str = Field(description="Absolute local path where the converted USD is written")
    output_format: str = Field(default="usd", description="Target format; v1 expects usd")
    timeout_s: float = Field(default=180.0, gt=0.0, le=1200.0)
