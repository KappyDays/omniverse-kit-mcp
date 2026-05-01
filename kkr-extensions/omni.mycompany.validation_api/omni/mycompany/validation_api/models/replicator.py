"""Pydantic models for Replicator REST endpoints (Phase H).

Covers the Synthetic Data Generation surface: writer creation, randomizer
registration, and orchestrator triggers. The Extension exposes an
``omni.replicator.core`` wrapper — scene state lives in the Kit process;
MCP callers only see handles (writer_id / randomizer_id) and summaries.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ReplicatorCreateWriterRequestModel(BaseModel):
    """Create a replicator writer (BasicWriter / KittiWriter / CocoWriter)."""

    model_config = ConfigDict(extra="forbid")

    writer_type: Literal["BasicWriter", "KittiWriter", "CocoWriter"] = Field(
        description="Writer class registered under rep.WriterRegistry",
    )
    output_dir: str = Field(description="Absolute directory path for writer output")
    rgb: bool = Field(default=True, description="Enable RGB capture channel")
    depth: bool = Field(
        default=False,
        description="Enable distance_to_camera depth channel",
    )
    semantic_segmentation: bool = Field(
        default=False,
        description="Enable semantic_segmentation channel",
    )


class ReplicatorRegisterRandomizerRequestModel(BaseModel):
    """Register a randomizer hook (position / rotation / lighting)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["position", "rotation", "lighting"] = Field(
        description="Randomizer kind",
    )
    target: str = Field(
        description=(
            "Prim path pattern (glob) — 'position' / 'rotation' target "
            "scene prims; 'lighting' targets UsdLux lights"
        ),
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Type-specific config — "
            "position: {volume: [min_xyz, max_xyz]}; "
            "rotation: {min_rot: [rx,ry,rz], max_rot: [rx,ry,rz]}; "
            "lighting: {min_int: float, max_int: float}"
        ),
    )


class ReplicatorTriggerOnceRequestModel(BaseModel):
    """Run the orchestrator for N frames (default 1)."""

    model_config = ConfigDict(extra="forbid")

    num_frames: int = Field(default=1, ge=1, le=10_000)


class ReplicatorTriggerOnTimeRequestModel(BaseModel):
    """Register an on-time trigger (Kit schedules orchestrator steps)."""

    model_config = ConfigDict(extra="forbid")

    interval_s: float = Field(gt=0.0, description="Seconds between orchestrator steps")
