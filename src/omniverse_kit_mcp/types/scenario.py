"""Scenario engine types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from omniverse_kit_mcp.types.common import (
    ExecutionStatus,
    JsonValue,
    ModuleName,
    RetryPolicy,
)


class ScenarioState(str, Enum):
    START = "start"
    SCENARIO_LOADED = "scenario_loaded"
    SCHEMA_VALIDATED = "schema_validated"
    COMPILED = "compiled"
    ARRANGE_RUNNING = "arrange_running"
    ARRANGE_DONE = "arrange_done"
    ACT_RUNNING = "act_running"
    ACT_DONE = "act_done"
    ASSERT_RUNNING = "assert_running"
    ASSERT_DONE = "assert_done"
    CLEANUP_RUNNING = "cleanup_running"
    CLEANUP_DONE = "cleanup_done"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELED = "canceled"


@dataclass(slots=True, frozen=True)
class CompiledStep:
    id: str
    phase: Literal["arrange", "act", "assert", "cleanup"]
    module: ModuleName
    action: str
    args: dict[str, JsonValue]
    timeout_s: float | None = None
    retry_policy: RetryPolicy | None = None
    continue_on_failure: bool = False
    idempotent: bool = False


@dataclass(slots=True, frozen=True)
class StepResult:
    step_id: str
    phase: Literal["arrange", "act", "assert", "cleanup"]
    status: ExecutionStatus
    message: str | None = None
    duration_ms: int | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    data_summary: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ScenarioDefaults:
    step_timeout_s: float = 60.0
    scenario_timeout_s: float = 600.0
    fail_fast: bool = True


@dataclass(slots=True, frozen=True)
class CompiledScenario:
    scenario_id: str
    name: str
    tags: tuple[str, ...]
    defaults: ScenarioDefaults
    variables: dict[str, JsonValue]
    arrange_steps: tuple[CompiledStep, ...]
    act_steps: tuple[CompiledStep, ...]
    assert_steps: tuple[CompiledStep, ...]
    cleanup_steps: tuple[CompiledStep, ...]


@dataclass(slots=True, frozen=True)
class ScenarioRunSummary:
    scenario_id: str
    status: ExecutionStatus
    passed_steps: int
    failed_steps: int
    skipped_steps: int
    started_at_epoch_ms: int
    ended_at_epoch_ms: int
    step_results: tuple[StepResult, ...]
    artifact_paths: tuple[str, ...]
