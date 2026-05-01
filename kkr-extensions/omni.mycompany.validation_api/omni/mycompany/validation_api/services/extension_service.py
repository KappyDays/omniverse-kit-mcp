"""Extension service — controls the custom extension lifecycle (skeleton)."""

from __future__ import annotations

from typing import Any


class ExtensionService:
    """Manages the Custom Extension state and sync operations."""

    def __init__(self) -> None:
        self._busy = False
        self._last_operation: str | None = None
        self._last_error: str | None = None
        self._state_version = 0

    def get_state(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "busy": self._busy,
            "last_operation": self._last_operation,
            "last_error": self._last_error,
            "reset_token": None,
            "state_version": self._state_version,
        }

    def trigger(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        # TODO: Dispatch to actual sync logic
        self._last_operation = operation
        self._state_version += 1
        return self.get_state()

    def reset(self, request: dict[str, Any]) -> dict[str, Any]:
        self._busy = False
        self._last_operation = None
        self._last_error = None
        if request.get("reset_internal_state", True):
            self._state_version = 0
        return self.get_state()

    async def activate(self, ext_id: str, reload: bool = False) -> dict[str, Any]:
        """Enable an arbitrary Kit Extension by id via the ExtensionManager.

        `reload=True` disables the extension first (even if already enabled)
        and re-enables it — equivalent to toggling the checkbox in the Kit
        Extension Manager, which re-imports the Python package.

        Validity is inferred from `is_extension_enabled(...)` and the
        success/failure of `set_extension_enabled_immediate(...)`. We avoid
        `get_extension_dict(ext_id)` since that API requires the
        fully-qualified `{name}-{version}` identifier in Kit 107.x and
        returns None for bare ids even when the extension is registered.
        """
        import omni.kit.app  # lazy

        try:
            manager = omni.kit.app.get_app().get_extension_manager()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"ExtensionManager unavailable: {exc}") from exc

        if not ext_id:
            raise ValueError("ext_id is required")

        was_enabled = bool(manager.is_extension_enabled(ext_id))
        reloaded = False

        if reload and was_enabled:
            manager.set_extension_enabled_immediate(ext_id, False)
            if not manager.set_extension_enabled_immediate(ext_id, True):
                raise ValueError(
                    f"extension '{ext_id}' failed to re-enable during reload — "
                    "check --ext-folder and the extension.toml manifest"
                )
            reloaded = True
        elif not was_enabled:
            if not manager.set_extension_enabled_immediate(ext_id, True):
                raise ValueError(
                    f"extension '{ext_id}' is not registered with Kit — "
                    "check --ext-folder and package spelling"
                )
        # else: already enabled and reload=False → no-op

        return {
            "ok": True,
            "ext_id": ext_id,
            "was_enabled": was_enabled,
            "enabled": bool(manager.is_extension_enabled(ext_id)),
            "reloaded": reloaded,
        }

    # ------------------------------------------------------------------
    # Phase H — extension management (deactivate / list_all / get_info)
    # ------------------------------------------------------------------

    async def deactivate(self, ext_id: str) -> dict[str, Any]:
        """Disable a Kit Extension by id via ExtensionManager.

        Idempotent — disabling an already-disabled extension returns
        ``was_enabled=False`` and the operation succeeds. Python module
        imports survive the deactivate (Kit does not forcibly unload) —
        callers that need a clean re-import should pair with
        ``activate(ext_id, reload=True)``.
        """
        import omni.kit.app  # lazy

        try:
            manager = omni.kit.app.get_app().get_extension_manager()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"ExtensionManager unavailable: {exc}") from exc

        if not ext_id:
            raise ValueError("ext_id is required")

        was_enabled = bool(manager.is_extension_enabled(ext_id))
        if was_enabled:
            if not manager.set_extension_enabled_immediate(ext_id, False):
                raise ValueError(
                    f"extension '{ext_id}' failed to disable — "
                    "may be locked by dependent extensions"
                )
        return {
            "ok": True,
            "ext_id": ext_id,
            "was_enabled": was_enabled,
            "enabled": bool(manager.is_extension_enabled(ext_id)),
        }

    async def list_all(self, enabled_only: bool = False) -> dict[str, Any]:
        """Enumerate every extension Kit knows about.

        Response ``extensions[*]`` carries the bare ``id`` / ``name`` /
        ``version`` / ``enabled`` / ``path`` — just enough to drive
        ``get_info`` for deep drill-down.
        """
        import omni.kit.app  # lazy

        try:
            manager = omni.kit.app.get_app().get_extension_manager()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"ExtensionManager unavailable: {exc}") from exc

        extensions: list[dict[str, Any]] = []
        try:
            raw_list = manager.get_extensions()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"get_extensions failed: {exc}") from exc

        for ext in raw_list or []:
            # Kit wraps results as dict-like — handle both dict and obj forms.
            entry = _extract_ext_summary(ext, manager)
            if enabled_only and not entry.get("enabled"):
                continue
            extensions.append(entry)

        return {
            "ok": True,
            "enabled_only": enabled_only,
            "count": len(extensions),
            "extensions": extensions,
        }

    async def get_info(self, ext_id: str) -> dict[str, Any]:
        """Return the full ExtensionManager dict for *ext_id*.

        Kit 107.x returns ``None`` from ``get_extension_dict(bare_id)`` —
        this method iterates ``get_extensions()`` and matches on ``name``
        to find the exact dict. Falls back to the raw dict call when the
        iteration path doesn't produce a match.
        """
        import omni.kit.app  # lazy

        try:
            manager = omni.kit.app.get_app().get_extension_manager()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"ExtensionManager unavailable: {exc}") from exc
        if not ext_id:
            raise ValueError("ext_id is required")

        # Prefer iteration (works with bare id); fall back to bare dict call.
        info: dict[str, Any] | None = None
        try:
            for ext in manager.get_extensions() or []:
                entry = _extract_ext_summary(ext, manager)
                if entry.get("id") == ext_id or entry.get("name") == ext_id:
                    info = entry
                    # Enrich with dependencies if available
                    try:
                        full_id = entry.get("full_id") or entry.get("id")
                        raw_dict = manager.get_extension_dict(full_id)
                        if raw_dict is not None:
                            info["dependencies"] = list(
                                (raw_dict.get("dependencies") or {}).keys()
                            )
                            info["title"] = raw_dict.get("title") or info.get("title")
                    except Exception:  # noqa: BLE001
                        pass
                    break
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"get_extensions iteration failed: {exc}") from exc

        if info is None:
            # Last-ditch fallback — Kit may still accept bare id in some builds.
            try:
                raw = manager.get_extension_dict(ext_id)
            except Exception:  # noqa: BLE001
                raw = None
            if raw is None:
                raise KeyError(f"extension '{ext_id}' not found in ExtensionManager")
            info = {
                "id": ext_id,
                "name": ext_id,
                "enabled": bool(manager.is_extension_enabled(ext_id)),
                "raw": dict(raw),
            }

        return {
            "ok": True,
            "ext_id": ext_id,
            "info": info,
        }


def _extract_ext_summary(ext: Any, manager: Any) -> dict[str, Any]:
    """Normalize an ExtensionManager entry to a JSON-friendly dict."""
    if isinstance(ext, dict):
        getter = ext.get
    else:
        def getter(key: str, default: Any = None) -> Any:
            return getattr(ext, key, default)

    full_id = getter("id") or getter("ext_id") or ""
    name = getter("name")
    if not name and isinstance(full_id, str):
        name = full_id.split("-")[0]
    version = getter("version")
    if not version and isinstance(full_id, str) and "-" in full_id:
        version = full_id.split("-", 1)[1]
    enabled_flag = getter("enabled")
    if enabled_flag is None and name:
        try:
            enabled_flag = bool(manager.is_extension_enabled(name))
        except Exception:  # noqa: BLE001
            enabled_flag = None

    return {
        "id": name or full_id,
        "full_id": full_id,
        "name": name or full_id,
        "version": version,
        "enabled": bool(enabled_flag) if enabled_flag is not None else False,
        "path": getter("path"),
        "title": getter("title"),
    }
