"""Pydantic models for REST request/response (common)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class RestErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = False
    error_code: str
    message: str
    request_id: str
    retryable: bool = False
    details: dict[str, Any] = {}
