"""Pydantic models for Simulation REST endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SimulationStatusModel(BaseModel):
    ok: bool = True
    is_playing: bool
    is_stopped: bool
    current_time: float
    start_time: float
    end_time: float
    time_codes_per_second: float


class SimulationStepRequestModel(BaseModel):
    """Advance the timeline by *frames* ticks (Phase G).

    Uses ``omni.timeline.forward_one_frame()`` when available, else falls
    back to short play → ``next_update_async`` bursts → pause. Scenario
    authors use this to replace the usual ``simulation_play → sleep``
    pattern with a deterministic frame count.
    """

    model_config = ConfigDict(extra="forbid")

    frames: int = Field(default=1, ge=1, le=10000)


class SimulationSetTimeRequestModel(BaseModel):
    """Seek the timeline to *time_seconds* (Phase G).

    Thin wrapper around ``omni.timeline.set_current_time()``. Honours the
    current play/stop state — seeking during play continues playing from
    the new position; seeking while stopped leaves the timeline stopped.
    """

    model_config = ConfigDict(extra="forbid")

    time_seconds: float = Field(ge=0.0)
