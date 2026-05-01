"""Pydantic models for Extension management extensions (Phase H).

Complements the Phase D `extension_activate` / UI / log endpoints with
deactivate + listing + info probing — the remaining surface needed to
mirror the Window → Extensions panel behaviour from MCP.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtensionDeactivateRequestModel(BaseModel):
    """Disable a Kit extension by id via ExtensionManager."""

    model_config = ConfigDict(extra="forbid")

    ext_id: str = Field(description="Extension id (bare name, e.g. omni.kit.menu.utils)")


class ExtensionListAllRequestModel(BaseModel):
    """Enumerate every extension Kit knows about."""

    model_config = ConfigDict(extra="forbid")

    enabled_only: bool = Field(
        default=False,
        description="Restrict to currently enabled extensions",
    )


class ExtensionGetInfoRequestModel(BaseModel):
    """Read the full ExtensionManager dict for a given ext id."""

    model_config = ConfigDict(extra="forbid")

    ext_id: str = Field(description="Extension id (bare name)")
