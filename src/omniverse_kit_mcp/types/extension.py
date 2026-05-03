"""Extension control types."""

from __future__ import annotations

from dataclasses import dataclass, field

from omniverse_kit_mcp.types.common import JsonValue


@dataclass(slots=True, frozen=True)
class ExtensionTriggerRequest:
    operation: str  # free-form string for extensibility
    payload: dict[str, JsonValue] = field(default_factory=dict)
    wait_for_idle: bool = True
    idle_timeout_s: float = 30.0
    poll_interval_s: float = 0.5


@dataclass(slots=True, frozen=True)
class ExtensionResetRequest:
    reset_stage_changes: bool = False
    reset_internal_state: bool = True
    clear_caches: bool = True
    reload_config: bool = False


@dataclass(slots=True, frozen=True)
class ExtensionState:
    enabled: bool
    busy: bool
    last_operation: str | None
    last_error: str | None
    reset_token: str | None
    state_version: int
