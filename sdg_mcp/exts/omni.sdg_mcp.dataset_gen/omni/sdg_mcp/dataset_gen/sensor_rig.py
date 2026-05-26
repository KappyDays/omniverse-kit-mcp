"""Pure camera-rig math (NO omni / pxr): look-at transform + ring placement.

Returns a row-major 4x4 in USD convention (row vectors; camera looks down local -Z),
so scene_builder can build a Gf.Matrix4d directly from the flat 16-tuple.
"""
from __future__ import annotations

import math


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if n == 0.0:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def compute_lookat_matrix(eye, target, up=(0.0, 0.0, 1.0)) -> tuple[float, ...]:
    """Camera local-to-world as a flat row-major 16-tuple.

    USD camera looks down local -Z, so local +Z points back toward the eye.
    Rows: [xaxis 0][yaxis 0][zaxis 0][eye 1].
    """
    zaxis = _normalize((eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]))
    xaxis = _normalize(_cross(up, zaxis))
    yaxis = _cross(zaxis, xaxis)
    return (
        xaxis[0], xaxis[1], xaxis[2], 0.0,
        yaxis[0], yaxis[1], yaxis[2], 0.0,
        zaxis[0], zaxis[1], zaxis[2], 0.0,
        eye[0], eye[1], eye[2], 1.0,
    )


def ring_camera_eyes(count, radius, height, center=(0.0, 0.0, 0.0)) -> list[tuple[float, float, float]]:
    """Evenly spaced eye positions on a horizontal ring at `height`."""
    eyes = []
    for i in range(count):
        ang = 2.0 * math.pi * i / count
        eyes.append(
            (center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang), center[2] + height)
        )
    return eyes
