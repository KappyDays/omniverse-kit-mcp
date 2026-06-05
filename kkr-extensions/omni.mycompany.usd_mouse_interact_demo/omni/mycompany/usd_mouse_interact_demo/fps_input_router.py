"""FPS input backend routing scaffolding.

This module is intentionally Kit-free so router behavior can be tested outside
USD Composer. Live camera movement still uses the existing local input path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .camera_math import MovementInput


@dataclass(frozen=True, slots=True)
class FpsInputSample:
    dx: float
    dy: float
    keys: MovementInput
    backend_name: str
    active: bool = True


class FpsInputBackend(Protocol):
    name: str

    def activate(self) -> None:
        ...

    def deactivate(self) -> None:
        ...

    def sample(
        self, center: tuple[float, float] | None, now_s: float
    ) -> FpsInputSample | None:
        ...


class FpsInputRouter:
    def __init__(self, backends: list[FpsInputBackend]) -> None:
        self._backends = list(backends)
        self._active_backend_name = "none"

    @property
    def active_backend_name(self) -> str:
        return self._active_backend_name

    def activate(self) -> None:
        for backend in self._backends:
            backend.activate()

    def deactivate(self) -> None:
        for backend in self._backends:
            backend.deactivate()
        self._active_backend_name = "none"

    def sample(
        self, center: tuple[float, float] | None, now_s: float
    ) -> FpsInputSample:
        for backend in self._backends:
            sample = backend.sample(center, now_s)
            if sample is not None and sample.active:
                self._active_backend_name = sample.backend_name
                return sample

        self._active_backend_name = "none"
        return FpsInputSample(
            dx=0.0,
            dy=0.0,
            keys=MovementInput(),
            backend_name="none",
            active=False,
        )
