"""Pydantic models for Content Browser REST endpoints (Phase H).

Wraps ``omni.client`` (``list`` / ``stat`` / ``normalize_url``) so MCP
callers can inspect Nucleus / S3 / local / omniverse:// URLs without
opening the Kit GUI. Operates identically whether the Kit Extension
``omni.kit.window.content_browser`` is enabled or not — ``omni.client``
is always available in Kit.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ContentBrowseRequestModel(BaseModel):
    """List immediate children of a URL (optionally recursive)."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(
        description=(
            "URL to enumerate — supports omniverse://, https://, s3://, "
            "file:///, or plain absolute local paths"
        ),
    )
    recursive: bool = Field(
        default=False,
        description="Walk subfolders; depth bounded by max_depth",
    )
    max_depth: int = Field(
        default=2, ge=1, le=6,
        description="Recursion depth cap (only used when recursive=True)",
    )
    max_entries: int = Field(
        default=500, ge=1, le=5000,
        description="Hard cap on returned entries",
    )


class ContentPreviewRequestModel(BaseModel):
    """Stat a single URL — returns size, mtime, entry flags, type."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="URL to stat")


class ContentInspectRequestModel(BaseModel):
    """Open a USD asset off-thread and return its geometric info."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="USD URL to open + inspect (bbox / default prim / units)")


class ContentResolveRequestModel(BaseModel):
    """Normalize a URL (collapse relative components, resolve prefix)."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="URL to normalize")
