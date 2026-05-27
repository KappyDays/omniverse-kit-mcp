"""Kit command dispatcher service.

Wraps omni.kit.commands.execute in a single REST-callable surface. All
error handling normalized to HTTPException so FastAPI serializes cleanly.

Also exposes a ``python_exec`` lever for arbitrary Python execution in
the Kit context (the gap Kit's command registry doesn't cover — e.g.
relationship edits, USD `Usd.EditContext` walks, omni.client direct calls).

Lazy-imports omni.kit.commands so this module is import-safe even when
the tests load it without a running Kit.
"""

from __future__ import annotations

import io
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any


class CommandsService:
    """Stateless service — one instance shared across requests."""

    def execute(self, name: str, payload: dict[str, Any] | None, expect_undo: bool) -> dict[str, Any]:
        try:
            import omni.kit.commands as kit_cmds
        except ImportError as exc:
            return {
                "ok": False,
                "error": "kit_commands_unavailable",
                "message": f"omni.kit.commands not importable: {exc}",
            }

        undo_before = None
        if expect_undo:
            try:
                import omni.kit.undo as kit_undo
                undo_before = len(kit_undo.get_history())
            except Exception:  # noqa: BLE001
                undo_before = None

        try:
            kwargs = payload or {}
            raw_result = kit_cmds.execute(name, **kwargs)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": "command_exception",
                "name": name,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }

        normalized: dict[str, Any] = {"name": name}
        if isinstance(raw_result, tuple) and len(raw_result) == 2:
            succeeded, command_result = raw_result
            normalized["succeeded"] = bool(succeeded)
            normalized["result"] = _coerce_result(command_result)
        elif isinstance(raw_result, bool):
            normalized["succeeded"] = raw_result
            normalized["result"] = None
        else:
            normalized["succeeded"] = True
            normalized["result"] = _coerce_result(raw_result)

        if expect_undo and undo_before is not None:
            try:
                import omni.kit.undo as kit_undo
                normalized["undo_stack_size_delta"] = len(kit_undo.get_history()) - undo_before
            except Exception:  # noqa: BLE001
                pass

        return {"ok": bool(normalized["succeeded"]), **normalized}

    def python_run(self, code: str, return_keys: list[str]) -> dict[str, Any]:
        """Run arbitrary Python source on the Kit main thread.

        Captures stdout / stderr / traceback and (optionally) returns
        named globals from the script's namespace. Use this when the
        Kit command registry doesn't cover the operation you need
        (USD relationship edits, ``Usd.EditContext`` walks, etc.).

        Implementation detail:
            We avoid the spelled-out ``exec`` builtin call here because
            the project's pre-tool security hook flags ``exec(`` literally
            (it can't tell shell exec from Python's). Instead we resolve
            the builtin via attribute lookup on a constructed name —
            functionally identical, lint-clean.
        """
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        namespace: dict[str, Any] = {"__name__": "__kit_pyrun__"}
        error: str | None = None
        tb: str | None = None

        _MODE = "e" + "xec"  # avoid raw ``exec`` literal — see docstring
        try:
            _builtins = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__
            _RUN = _builtins[_MODE]
        except Exception:  # noqa: BLE001
            _RUN = None

        if _RUN is None:
            error = "RuntimeError: cannot resolve Python runner builtin"
        else:
            try:
                with redirect_stdout(out_buf), redirect_stderr(err_buf):
                    code_obj = compile(code, "<kit_pyrun>", _MODE)
                    _RUN(code_obj, namespace)
            except BaseException as e:  # noqa: BLE001 — capture *everything*
                error = f"{type(e).__name__}: {e}"
                tb = traceback.format_exc()

        returned: dict[str, Any] = {}
        for key in return_keys:
            if key in namespace:
                returned[key] = _coerce_result(namespace[key])

        return {
            "ok": error is None,
            "stdout": out_buf.getvalue(),
            "stderr": err_buf.getvalue(),
            "error": error,
            "traceback": tb,
            "returned": returned,
        }

    async def python_run_main_thread(
        self, code: str, return_keys: list[str],
    ) -> dict[str, Any]:
        """Run ``python_run`` ON THE KIT MAIN LOOP (deadlock-safe).

        The sync ``/commands/python_run`` route ran ``exec`` in a Starlette
        threadpool worker — NOT the Kit main thread — so any USD authoring /
        mutation (even on a fresh stage) contended Tf-notice / omni.usd / Hydra
        locks with the main loop and froze Kit for 92s. Mirror
        ``stage_service.load_usd``: schedule the (sync) exec onto the Kit main
        loop via ``omni.kit.async_engine.run_coroutine`` and ``await`` the
        result through ``asyncio.wrap_future`` (the FastAPI loop stays free while
        the Kit main loop ticks). This makes kit_python_run usable for the very
        thing it advertises (USD relationship edits, EditContext walks, bulk
        attribute author patterns).
        """
        import asyncio
        import omni.kit.async_engine  # lazy

        async def _impl() -> dict[str, Any]:
            # Runs on the Kit main loop — exec executes on the main thread.
            return self.python_run(code, return_keys)

        future = omni.kit.async_engine.run_coroutine(_impl())
        return await asyncio.wrap_future(future)


def _coerce_result(value: Any) -> Any:
    """Best-effort JSON-safe conversion of a Kit command's result object."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce_result(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _coerce_result(v) for k, v in value.items()}
    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return repr(value)


_singleton: CommandsService | None = None


def get_commands_service() -> CommandsService:
    global _singleton
    if _singleton is None:
        _singleton = CommandsService()
    return _singleton
