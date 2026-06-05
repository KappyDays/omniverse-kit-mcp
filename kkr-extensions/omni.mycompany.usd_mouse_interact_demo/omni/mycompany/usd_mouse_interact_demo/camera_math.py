"""Pure camera math — yaw/pitch update, basis vectors, WASD translation.

Kept free of Kit / USD imports so it can be unit-tested with plain pytest.
Vectors are plain 3-tuples of floats. Right-handed coords; up-axis is "Y" or "Z".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

Vec3 = Tuple[float, float, float]

PITCH_LIMIT = math.pi / 2 - 0.01  # avoid gimbal flip at exactly ±90°


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def update_yaw_pitch(
    yaw: float,
    pitch: float,
    dx_pixels: float,
    dy_pixels: float,
    sensitivity: float = 0.0025,
) -> Tuple[float, float]:
    """Apply mouse delta to yaw/pitch.

    Convention: dx > 0 (mouse right) -> camera turns right in Kit viewport FPS
    interaction. Pitch keeps the existing screen-space convention: dy < 0 looks up.
    """
    new_yaw = yaw + dx_pixels * sensitivity
    new_pitch = clamp(pitch - dy_pixels * sensitivity, -PITCH_LIMIT, PITCH_LIMIT)
    return new_yaw, new_pitch


def _normalize(v: Vec3) -> Vec3:
    x, y, z = v
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-12:
        return (0.0, 0.0, 0.0)
    return (x / n, y / n, z / n)


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def basis_from_yaw_pitch(
    yaw: float, pitch: float, up_axis: str = "Y"
) -> Tuple[Vec3, Vec3, Vec3]:
    """Return (forward, right, up) orthonormal basis.

    up_axis="Y": world up is +Y. yaw rotates around +Y, pitch around right axis.
        At yaw=0, pitch=0 forward = -Z (Kit / USD default look direction).
    up_axis="Z": world up is +Z. yaw rotates around +Z, pitch around right axis.
        At yaw=0, pitch=0 forward = -Y.
    """
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    if up_axis.upper() == "Z":
        # Z-up: forward at yaw=0,pitch=0 is -Y
        forward = (-sy * cp, -cy * cp, sp)
        world_up: Vec3 = (0.0, 0.0, 1.0)
    else:
        # Y-up: forward at yaw=0,pitch=0 is -Z
        forward = (-sy * cp, sp, -cy * cp)
        world_up = (0.0, 1.0, 0.0)

    forward = _normalize(forward)
    right = _normalize(_cross(forward, world_up))
    if right == (0.0, 0.0, 0.0):
        # Looking straight up/down — pick an arbitrary right
        right = (1.0, 0.0, 0.0) if up_axis.upper() != "X" else (0.0, 1.0, 0.0)
    up = _normalize(_cross(right, forward))
    return forward, right, up


@dataclass(frozen=True)
class MovementInput:
    forward: bool = False
    backward: bool = False
    left: bool = False
    right: bool = False
    up: bool = False
    down: bool = False


def translation_from_input(
    forward: Vec3,
    right: Vec3,
    up: Vec3,
    keys: MovementInput,
    speed: float,
    dt: float,
) -> Vec3:
    """Compute world-space translation delta for this frame.

    speed in stage units / second. dt in seconds.
    """
    fx = (1.0 if keys.forward else 0.0) - (1.0 if keys.backward else 0.0)
    rx = (1.0 if keys.right else 0.0) - (1.0 if keys.left else 0.0)
    ux = (1.0 if keys.up else 0.0) - (1.0 if keys.down else 0.0)

    dx = forward[0] * fx + right[0] * rx + up[0] * ux
    dy = forward[1] * fx + right[1] * rx + up[1] * ux
    dz = forward[2] * fx + right[2] * rx + up[2] * ux

    # Normalize diagonal so combined keys aren't faster than single key
    mag = math.sqrt(dx * dx + dy * dy + dz * dz)
    if mag > 1e-9:
        inv = 1.0 / mag
        dx *= inv
        dy *= inv
        dz *= inv

    scale = speed * dt
    return (dx * scale, dy * scale, dz * scale)


def yaw_pitch_from_forward(forward: Vec3, up_axis: str = "Y") -> Tuple[float, float]:
    """Inverse of basis_from_yaw_pitch (forward only) — used to seed initial
    yaw/pitch from the active camera's current orientation.
    """
    fx, fy, fz = _normalize(forward)
    if up_axis.upper() == "Z":
        pitch = math.asin(clamp(fz, -1.0, 1.0))
        # forward.x = -sin(yaw)*cos(pitch); forward.y = -cos(yaw)*cos(pitch)
        cp = math.cos(pitch)
        if abs(cp) < 1e-6:
            return 0.0, pitch
        yaw = math.atan2(-fx, -fy)
    else:
        pitch = math.asin(clamp(fy, -1.0, 1.0))
        cp = math.cos(pitch)
        if abs(cp) < 1e-6:
            return 0.0, pitch
        yaw = math.atan2(-fx, -fz)
    return yaw, pitch
