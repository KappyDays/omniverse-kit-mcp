"""Pure streaming input packet parsing and aggregation.

This module intentionally stays free of Kit imports so browser-stream input
logic can be unit-tested in plain pytest.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .camera_math import MovementInput as MovementKeys

MAX_DELTA = 2000.0


@dataclass(frozen=True, slots=True)
class StreamInputPacket:
    seq: int
    dx: float
    dy: float
    keys: MovementKeys
    focused: bool
    pointer_locked: bool
    timestamp: float


@dataclass(frozen=True, slots=True)
class StreamInputSample:
    dx: float
    dy: float
    keys: MovementKeys
    active: bool


def _parse_int(value: Any) -> int:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(parsed):
        return 0
    return int(parsed)


def _parse_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(parsed):
        return 0.0
    return parsed


def _finite_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _parse_delta(value: Any) -> float:
    parsed = _parse_float(value)
    return max(-MAX_DELTA, min(MAX_DELTA, parsed))


def _parse_keys(value: Any) -> MovementKeys:
    keys = value if isinstance(value, dict) else {}
    return MovementKeys(
        forward=bool(keys.get("w", False)),
        backward=bool(keys.get("s", False)),
        left=bool(keys.get("a", False)),
        right=bool(keys.get("d", False)),
        up=bool(keys.get("e", False)),
        down=bool(keys.get("q", False)),
    )


def parse_stream_payload(payload: dict[str, Any]) -> StreamInputPacket:
    pointer_locked = payload.get("pointerLocked", payload.get("pointer_locked", True))
    return StreamInputPacket(
        seq=_parse_int(payload.get("seq", 0)),
        dx=_parse_delta(payload.get("dx", 0.0)),
        dy=_parse_delta(payload.get("dy", 0.0)),
        keys=_parse_keys(payload.get("keys", {})),
        focused=bool(payload.get("focused", True)),
        pointer_locked=bool(pointer_locked),
        timestamp=_parse_float(payload.get("timestamp", 0.0)),
    )


class StreamInputAggregator:
    def __init__(self, timeout_s: float = 0.25) -> None:
        parsed_timeout = _finite_float_or_none(timeout_s)
        self._timeout_s = parsed_timeout if parsed_timeout is not None and parsed_timeout > 0 else 0.25
        self._dx = 0.0
        self._dy = 0.0
        self._keys = MovementKeys()
        self._last_time: float | None = None
        self._active = False

    def push(self, packet: StreamInputPacket, now_s: float) -> None:
        parsed_now = _finite_float_or_none(now_s)
        if parsed_now is None:
            self.release()
            return

        self._last_time = parsed_now
        if not packet.focused or not packet.pointer_locked:
            self.release()
            self._last_time = parsed_now
            return

        self._dx += packet.dx
        self._dy += packet.dy
        self._keys = packet.keys
        self._active = True

    def consume(self, now_s: float) -> StreamInputSample:
        parsed_now = _finite_float_or_none(now_s)
        if (
            parsed_now is None
            or self._last_time is None
            or parsed_now - self._last_time > self._timeout_s
        ):
            self.release()
            return StreamInputSample(dx=0.0, dy=0.0, keys=self._keys, active=False)

        sample = StreamInputSample(
            dx=self._dx,
            dy=self._dy,
            keys=self._keys,
            active=self._active,
        )
        self._dx = 0.0
        self._dy = 0.0
        return sample

    def release(self) -> None:
        self._dx = 0.0
        self._dy = 0.0
        self._keys = MovementKeys()
        self._active = False
