"""Percent-based layout helpers for viewport button rectangles."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class PercentRect:
    x_pct: float
    y_pct: float
    w_pct: float
    h_pct: float


def pixel_rect(
    rect: PercentRect, viewport_width: float, viewport_height: float
) -> tuple[int, int, int, int]:
    if viewport_width <= 0 or viewport_height <= 0:
        return (0, 0, 0, 0)

    x_pct = _clamp01(rect.x_pct)
    y_pct = _clamp01(rect.y_pct)
    w_pct = _clamp01(rect.w_pct)
    h_pct = _clamp01(rect.h_pct)

    x = int(x_pct * viewport_width)
    y = int(y_pct * viewport_height)
    width = _pixel_size(w_pct, viewport_width)
    height = _pixel_size(h_pct, viewport_height)

    width = min(width, max(0, int(viewport_width) - x))
    height = min(height, max(0, int(viewport_height) - y))
    return (x, y, width, height)


def visible_pixel_rect(
    rect: PercentRect,
    viewport_width: float,
    viewport_height: float,
    *,
    min_width: int = 48,
    min_height: int = 32,
) -> tuple[int, int, int, int]:
    """Return a clamped rect that remains visible inside the viewport."""
    x, y, width, height = pixel_rect(rect, viewport_width, viewport_height)
    if viewport_width <= 0 or viewport_height <= 0:
        return (0, 0, 0, 0)

    width = max(int(min_width), int(width))
    height = max(int(min_height), int(height))
    width = min(width, int(viewport_width))
    height = min(height, int(viewport_height))
    x = max(0, min(int(x), int(viewport_width) - width))
    y = max(0, min(int(y), int(viewport_height) - height))
    return (x, y, width, height)


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _pixel_size(percent: float, viewport_size: float) -> int:
    size = int(percent * viewport_size)
    if percent > 0.0 and size == 0:
        return 1
    return size
