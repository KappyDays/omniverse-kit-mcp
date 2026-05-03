"""Types for simulation timeline control."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SimulationStatus:
    """Snapshot of the Isaac Sim timeline state."""

    is_playing: bool
    is_stopped: bool
    current_time: float
    start_time: float
    end_time: float
    time_codes_per_second: float


@dataclass(slots=True, frozen=True)
class StageWriteResult:
    """Result of a stage write operation (load_usd, create_prim, set_property, delete_prim)."""

    ok: bool
    prim_path: str
    detail: str | None = None


# --- Phase G ---


@dataclass(slots=True, frozen=True)
class SimulationStepRequest:
    frames: int = 1


@dataclass(slots=True, frozen=True)
class SimulationStepResult:
    status: SimulationStatus
    frames: int
    start_time: float
    advance_mode: str
    was_playing: bool


@dataclass(slots=True, frozen=True)
class SimulationSetTimeRequest:
    time_seconds: float


@dataclass(slots=True, frozen=True)
class SimulationSetTimeResult:
    status: SimulationStatus
    requested_time: float
    previous_time: float
