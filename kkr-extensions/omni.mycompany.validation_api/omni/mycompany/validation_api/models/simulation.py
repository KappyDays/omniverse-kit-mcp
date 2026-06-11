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

    Uses short play → ``next_update_async`` bursts → pause. Scenario authors
    use this to replace the usual ``simulation_play → sleep`` pattern with a
    deterministic frame count. Isaac Sim 6.0 avoids ``forward_one_frame`` here
    because it can crash with active Replicator/HydraTexture render products.
    If the play burst cannot advance time, the service falls back to
    ``set_current_time`` and reports ``advance_mode='set_time_fallback'``.
    """

    model_config = ConfigDict(extra="forbid")

    frames: int = Field(default=1, ge=1, le=10000)


class SimulationEESpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    end_effector_frame: str | None = None


class SimulationStepObserveRequestModel(BaseModel):
    """Advance frames and return synchronized prim/joint/EE observations."""

    model_config = ConfigDict(extra="forbid")

    frames: int = Field(default=1, ge=1, le=10000)
    observe_prims: list[str] = Field(default_factory=list)
    observe_joints: list[str] = Field(default_factory=list)
    observe_ee: list[SimulationEESpecModel] = Field(default_factory=list)


class SimulationSetTimeRequestModel(BaseModel):
    """Seek the timeline to *time_seconds* (Phase G).

    Thin wrapper around ``omni.timeline.set_current_time()``. Honours the
    current play/stop state — seeking during play continues playing from
    the new position; seeking while stopped leaves the timeline stopped.
    """

    model_config = ConfigDict(extra="forbid")

    time_seconds: float = Field(ge=0.0)


class SimulationWaitUntilRequestModel(BaseModel):
    """Tick until timeline current_time >= until_time (or wall timeout)."""

    model_config = ConfigDict(extra="forbid")

    until_time: float = Field(ge=0.0, description="Target sim time (seconds) to reach.")
    timeout_s: float = Field(default=30.0, gt=0.0, le=600.0)
