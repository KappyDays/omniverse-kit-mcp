"""Common types shared across modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class ModuleName(str, Enum):
    STAGE = "stage"
    VIEWPORT = "viewport"
    LAKEHOUSE = "lakehouse"
    EXTENSION = "extension"
    SIMULATION = "simulation"
    ROBOT = "robot"
    JOB = "job"
    ASSET = "asset"
    CHARACTER = "character"
    WINDOW = "window"
    NAVIGATION = "navigation"
    SENSOR = "sensor"
    PHYSICS = "physics"
    LIGHTING = "lighting"
    MATERIAL = "material"
    # Phase H — Replicator / OmniGraph / Content
    REPLICATOR = "replicator"
    OMNIGRAPH = "omnigraph"
    CONTENT = "content"


class StepPhase(str, Enum):
    ARRANGE = "arrange"
    ACT = "act"
    ASSERT = "assert"
    CLEANUP = "cleanup"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELED = "canceled"


@dataclass(slots=True, frozen=True)
class TimeoutPolicy:
    connect_s: float = 5.0
    read_s: float = 30.0
    write_s: float = 30.0
    pool_s: float = 5.0
    request_s: float = 30.0
    step_s: float = 60.0
    scenario_s: float = 600.0


@dataclass(slots=True, frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_s: float = 0.5
    max_backoff_s: float = 5.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.2
    retry_on_status_codes: tuple[int, ...] = (408, 429, 500, 502, 503, 504)


@dataclass(slots=True, frozen=True)
class OperationMeta:
    request_id: str
    scenario_id: str | None = None
    step_id: str | None = None
    module: ModuleName | None = None
    started_at_epoch_ms: int | None = None


@dataclass(slots=True, frozen=True)
class ModuleResult[T]:
    ok: bool
    status: ExecutionStatus
    data: T | None
    message: str | None = None
    error_code: str | None = None
    duration_ms: int | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
