"""Types for simulation timeline control."""

from __future__ import annotations

from dataclasses import dataclass, field


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
class SimulationEESpec:
    prim_path: str
    end_effector_frame: str | None = None


@dataclass(slots=True, frozen=True)
class ObservedPrimState:
    prim_path: str
    position: tuple[float, float, float] | None
    orientation: tuple[float, float, float, float] | None
    linear_velocity: tuple[float, float, float] | None = None
    angular_velocity: tuple[float, float, float] | None = None
    has_rigid_body: bool = False
    source: str = ""
    error: str | None = None


@dataclass(slots=True, frozen=True)
class ObservedJointState:
    prim_path: str
    positions: tuple[float, ...]
    dof_names: tuple[str, ...] = field(default_factory=tuple)
    source: str = ""
    error: str | None = None


@dataclass(slots=True, frozen=True)
class ObservedEETarget:
    prim_path: str
    end_effector_frame: str
    position: tuple[float, float, float] | None
    orientation: tuple[float, float, float, float] | None
    source: str = ""
    error: str | None = None


@dataclass(slots=True, frozen=True)
class SimulationStepObserveRequest:
    frames: int = 1
    observe_prims: tuple[str, ...] = field(default_factory=tuple)
    observe_joints: tuple[str, ...] = field(default_factory=tuple)
    observe_ee: tuple[SimulationEESpec, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class SimulationStepObserveResult:
    status: SimulationStatus
    frames: int
    start_time: float
    advance_mode: str
    was_playing: bool
    prim_states: tuple[ObservedPrimState, ...] = field(default_factory=tuple)
    joint_states: tuple[ObservedJointState, ...] = field(default_factory=tuple)
    ee_states: tuple[ObservedEETarget, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class SimulationSetTimeRequest:
    time_seconds: float


@dataclass(slots=True, frozen=True)
class SimulationSetTimeResult:
    status: SimulationStatus
    requested_time: float
    previous_time: float


@dataclass(slots=True, frozen=True)
class SimulationWaitUntilRequest:
    """Tick the timeline until current_time >= until_time (or wall timeout)."""

    until_time: float
    timeout_s: float = 30.0


@dataclass(slots=True, frozen=True)
class SimulationWaitUntilResult:
    status: SimulationStatus
    until_time: float
    reached: bool
    timed_out: bool
    elapsed_s: float
    frames_waited: int
