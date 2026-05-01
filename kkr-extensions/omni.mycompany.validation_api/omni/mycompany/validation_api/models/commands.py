"""Pydantic models for /commands/* endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KitCommandExecuteRequestModel(BaseModel):
    """Arguments for omni.kit.commands.execute(name, **payload).

    Fields:
      name: Command registry name (e.g. "CreateConveyorBelt",
            "CreatePrimWithDefaultXform", "ChangeProperty").
      payload: kwargs dict passed through. Values are serialized as-is
               from JSON — the Kit command is responsible for type coercion.
               None if the command takes no arguments.
      expect_undo: If true, the response will include undo_stack_size so
                   callers can detect whether the command registered an
                   undo record (diagnostic).
    """

    name: str = Field(..., min_length=1)
    payload: dict[str, Any] | None = None
    expect_undo: bool = False


class KitPythonExecRequestModel(BaseModel):
    """Arguments for arbitrary Python execution inside the Kit context.

    Fills the gap that omni.kit.commands.execute leaves — Kit doesn't
    register a "ExecutePythonScript" command, so any operation that isn't
    in the command registry (e.g. relationship edits, `Usd.EditContext` +
    descendant walks, omni.client direct calls) used to require the user
    to paste code into the GUI Script Editor. This route runs the code
    on the same main thread the Script Editor would use.

    Fields:
      code: Python source. Top-level statements only — no `def main()`
            wrapping needed. Pre-imported via the ``__main__`` style
            globals dict, so `import omni.usd; from pxr import Usd, UsdShade`
            works without setup.
      return_keys: Optional list of namespace variable names whose final
                   values should be returned in the response (best-effort
                   JSON-serialised via str() fallback). Empty = stdout-only
                   communication.
    """

    code: str = Field(..., min_length=1)
    return_keys: list[str] = Field(default_factory=list)
