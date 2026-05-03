"""Shared context between scenario steps (snapshots, artifacts)."""

from __future__ import annotations

from typing import Any


class ScenarioContext:
    """Mutable context shared across scenario steps for artifact/data passing."""

    def __init__(self) -> None:
        self._artifacts: dict[str, str] = {}
        self._step_data: dict[str, Any] = {}

    def store_artifact(self, step_id: str, key: str, path: str) -> None:
        self._artifacts[f"{step_id}.{key}"] = path

    def get_artifact(self, step_id: str, key: str) -> str | None:
        return self._artifacts.get(f"{step_id}.{key}")

    def store_step_data(self, step_id: str, data: Any) -> None:
        self._step_data[step_id] = data

    def get_step_data(self, step_id: str) -> Any | None:
        return self._step_data.get(step_id)

    @property
    def all_artifact_paths(self) -> tuple[str, ...]:
        return tuple(self._artifacts.values())
