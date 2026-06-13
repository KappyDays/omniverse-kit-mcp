"""carb log capture — ring buffer + since_ms / level / source filtering.

carb.logging hook notes (testbed #3, #4):
- `carb.log_fn` attribute does not exist — use `carb.logging.acquire_logging().add_logger(hook)`.
- Hook signature is `(source, level, filename, line, msg)` — 5 args (the public
  docs show 6, which is wrong for current Kit 107.x).
- Levels are signed ints: VERBOSE=-2, INFO=-1, WARN=0, ERROR=1, FATAL=2.
- Handle returned by `add_logger` MUST be released with `remove_logger` on
  Extension shutdown — otherwise the callback dangles across Extension
  reloads and causes duplicate entries.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any


# carb.logging level ints. Sorted ascending → higher = more severe.
_LEVEL_INT_TO_NAME: dict[int, str] = {
    -2: "VERBOSE",
    -1: "INFO",
    0: "WARN",
    1: "ERROR",
    2: "FATAL",
}

_LEVEL_NAME_TO_INT: dict[str, int] = {
    "VERBOSE": -2,
    "INFO": -1,
    "WARN": 0,
    "ERROR": 1,
    "FATAL": 2,
    "ALL": -100,  # sentinel — includes everything
}


class LogCaptureService:
    """Ring-buffer carb log capture, filter by level / source / since_ms.

    Use `start()` in Extension on_startup and `stop()` in on_shutdown.
    Concurrent append from Kit thread + query from FastAPI worker — guard
    with a lock.
    """

    def __init__(self, maxlen: int = 10000) -> None:
        self._buf: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._handle: Any = None
        self._logging_iface: Any = None
        self._maxlen = maxlen

    # --- lifecycle ---

    def start(self) -> None:
        """Register the carb log hook. Idempotent — double-start is a no-op."""
        if self._handle is not None:
            return
        try:
            import carb
            import carb.logging as carb_logging

            self._logging_iface = carb_logging.acquire_logging()
            # add_logger signature: callback(source, level, filename, line, msg)
            self._handle = self._logging_iface.add_logger(self._on_log)
            carb.log_warn(f"[log_capture] started (maxlen={self._maxlen})")
        except Exception as exc:  # noqa: BLE001
            try:
                import carb
                carb.log_error(f"[log_capture] failed to start: {exc}")
            except Exception:  # noqa: BLE001
                pass
            self._handle = None
            self._logging_iface = None

    def stop(self) -> None:
        """Remove the carb log hook. Idempotent."""
        if self._handle is None:
            return
        try:
            if self._logging_iface is not None:
                self._logging_iface.remove_logger(self._handle)
        except Exception:  # noqa: BLE001
            pass
        self._handle = None
        self._logging_iface = None

    # --- hook ---

    def _on_log(
        self,
        source: str,
        level: int,
        filename: str,
        line_number: int,
        message: str,
    ) -> None:
        """Called from the carb logging thread — keep it cheap."""
        try:
            entry = {
                "ts_ms": int(time.time() * 1000),
                "level": _LEVEL_INT_TO_NAME.get(int(level), f"LEVEL_{int(level)}"),
                "level_int": int(level),
                "source": str(source or ""),
                "filename": str(filename or ""),
                "line": int(line_number or 0),
                "msg": str(message or ""),
            }
            with self._lock:
                self._buf.append(entry)
        except Exception:  # noqa: BLE001 — never raise from carb hook
            pass

    # --- query ---

    def query(
        self,
        since_ms: int | None = None,
        level: str = "ALL",
        source_filter: str | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Return filtered entries. Peek-style (no drain) so multiple callers
        see the same data. `since_ms` lets callers time-slice."""
        level_norm = (level or "ALL").upper()
        min_level = _LEVEL_NAME_TO_INT.get(level_norm, -100)
        out: list[dict[str, Any]] = []
        with self._lock:
            snapshot = list(self._buf)
        truncated = False
        for e in snapshot:
            if since_ms is not None and e["ts_ms"] < since_ms:
                continue
            if e["level_int"] < min_level:
                continue
            if source_filter and source_filter not in e["source"]:
                continue
            out.append(e)
            if len(out) >= limit:
                truncated = True
                break
        return {
            "ok": True,
            "entries": out,
            "count": len(out),
            "truncated": truncated,
            "level_filter": level_norm,
            "since_ms": since_ms,
            "source_filter": source_filter,
        }

    def clear(self) -> int:
        """Drop all buffered entries. Returns the count that was cleared."""
        with self._lock:
            n = len(self._buf)
            self._buf.clear()
        return n

    def size(self) -> int:
        with self._lock:
            return len(self._buf)

    def is_running(self) -> bool:
        return self._handle is not None
