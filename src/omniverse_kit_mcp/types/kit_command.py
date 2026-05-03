"""Typed request/response for kit_command_execute + kit_python_exec tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class KitCommandExecuteRequest:
    name: str
    payload: dict[str, Any] | None = None
    expect_undo: bool = False


@dataclass(slots=True, frozen=True)
class KitPythonExecRequest:
    code: str
    return_keys: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class KitPythonExecResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    traceback: str | None = None
    returned: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "KitPythonExecResult":
        return cls(
            ok=bool(raw.get("ok", False)),
            stdout=str(raw.get("stdout", "")),
            stderr=str(raw.get("stderr", "")),
            error=raw.get("error"),
            traceback=raw.get("traceback"),
            returned=dict(raw.get("returned") or {}),
        )


@dataclass(slots=True, frozen=True)
class KitCommandExecuteResult:
    name: str
    succeeded: bool
    result: Any = None
    error: str | None = None
    message: str | None = None
    traceback: str | None = None
    undo_stack_size_delta: int | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "KitCommandExecuteResult":
        return cls(
            name=raw.get("name", "unknown"),
            succeeded=bool(raw.get("succeeded", False)),
            result=raw.get("result"),
            error=raw.get("error"),
            message=raw.get("message"),
            traceback=raw.get("traceback"),
            undo_stack_size_delta=raw.get("undo_stack_size_delta"),
        )
