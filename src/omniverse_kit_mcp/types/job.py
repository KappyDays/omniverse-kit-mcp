"""Types for async Job polling (Phase B)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class JobStatus:
    job_id: str
    status: str
    progress: float
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at_epoch_ms: int = 0
    updated_at_epoch_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)
