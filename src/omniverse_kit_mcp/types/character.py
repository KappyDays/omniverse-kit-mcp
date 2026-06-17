"""Types for character control (Phase C)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CharacterLoadRequest:
    usd_url: str
    prim_path: str | None = None
    position: tuple[float, float, float] | None = None
    yaw: float = 0.0


@dataclass(slots=True, frozen=True)
class CharacterLoadResult:
    ok: bool
    prim_path: str
    skel_root_path: str
    sanitized_prim_path: str
    has_skeleton: bool
    anim_graph_bound: bool


@dataclass(slots=True, frozen=True)
class CharacterPlayAnimationRequest:
    prim_path: str
    animation_name: str  # Literal["Idle","Walk","Run","Sit"] semantically — enforced server-side
    speed: float = 1.0
    target_position: tuple[float, float, float] | None = None


@dataclass(slots=True, frozen=True)
class CharacterPlayAnimationResult:
    prim_path: str
    action: str
    speed: float
    bound_graph: str


@dataclass(slots=True, frozen=True)
class CharacterSetPositionRequest:
    prim_path: str
    position: tuple[float, float, float]
    orientation: tuple[float, float, float, float] | None = None  # [qw,qx,qy,qz]


@dataclass(slots=True, frozen=True)
class CharacterSetPositionResult:
    prim_path: str
    position: tuple[float, float, float]
    orientation: tuple[float, float, float, float]


@dataclass(slots=True, frozen=True)
class CharacterStopAnimationRequest:
    prim_path: str


@dataclass(slots=True, frozen=True)
class CharacterStopAnimationResult:
    prim_path: str
    action: str
    speed: float


@dataclass(slots=True, frozen=True)
class CharacterNavigateRequest:
    prim_path: str
    target: tuple[float, float, float]
    speed: float = 1.0


@dataclass(slots=True, frozen=True)
class CharacterNavigateResult:
    job_id: str
    prim_path: str
    target: tuple[float, float, float]


@dataclass(slots=True, frozen=True)
class CharacterState:
    prim_path: str
    position: tuple[float, float, float]
    rotation: tuple[float, float, float, float]  # [qw,qx,qy,qz]
    action: str
    is_navigating: bool


# --- Phase G ---


@dataclass(slots=True, frozen=True)
class CharacterPlayAnimationVariantRequest:
    prim_path: str
    variant: str
    speed: float = 1.0
    target_position: tuple[float, float, float] | None = None
    dispatch_mode: str = "auto"


@dataclass(slots=True, frozen=True)
class CharacterPlayAnimationVariantResult:
    prim_path: str
    variant: str
    base_action: str
    speed: float
    variables_set: tuple[str, ...]
    bound_graph: str
    dispatch_mode: str = "auto"
    behavior_task_id: int | None = None
    behavior_task_name: str | None = None
    behavior_task_status: str | None = None
    behavior_task_running: bool | None = None
    task_error: str | None = None
    skel_animation_path: str | None = None
    skel_annotation_path: str | None = None
    skel_animation_start: float | None = None
    skel_animation_end: float | None = None
    skel_seek_time_seconds: float | None = None


@dataclass(slots=True, frozen=True)
class CharacterLoadCrowdRequest:
    count: int
    layout: str = "grid"  # Literal["grid","line","random"]
    spacing: float = 2.0
    base_name: str = "Crowd"
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    usd_url: str | None = None


@dataclass(slots=True, frozen=True)
class CharacterLoadCrowdMember:
    index: int
    prim_path: str | None
    position: tuple[float, float, float]
    error: str | None = None


@dataclass(slots=True, frozen=True)
class CharacterLoadCrowdResult:
    count: int
    success_count: int
    layout: str
    spacing: float
    base_name: str
    center: tuple[float, float, float]
    usd_url: str
    loaded: tuple[CharacterLoadCrowdMember, ...]
