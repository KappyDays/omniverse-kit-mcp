"""Pydantic models for async Job REST endpoints (Phase B)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JobStatusResponseModel(BaseModel):
    ok: bool = True
    job_id: str
    status: str
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at_epoch_ms: int
    updated_at_epoch_ms: int
