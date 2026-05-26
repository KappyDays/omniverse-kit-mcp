"""Pydantic models for Extension REST endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtensionTriggerRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: str
    payload: dict[str, Any] = Field(default_factory=dict)
    wait_for_idle: bool = True
    idle_timeout_s: float = Field(default=30.0, gt=0)


class ExtensionResetRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reset_stage_changes: bool = False
    reset_internal_state: bool = True
    clear_caches: bool = True
    reload_config: bool = False


class ExtensionStateModel(BaseModel):
    enabled: bool
    busy: bool
    last_operation: str | None = None
    last_error: str | None = None
    reset_token: str | None = None
    state_version: int = 0


class ExtensionActivateRequestModel(BaseModel):
    """Enable a Kit Extension by id (optionally reload if already enabled)."""

    model_config = ConfigDict(extra="forbid")

    ext_id: str = Field(
        description="Kit extension id, e.g. 'omni.mycompany.ui_demo'",
    )
    reload: bool = Field(
        default=False,
        description="If already enabled, disable then re-enable to reload.",
    )


class ExtensionReloadCleanRequestModel(BaseModel):
    """Disable, purge sys.modules for the ext tree, then re-enable (clean reload)."""

    model_config = ConfigDict(extra="forbid")

    ext_id: str = Field(
        description="Kit extension id == its [[python.module]] name, e.g. 'omni.mycompany.ui_demo'",
    )
