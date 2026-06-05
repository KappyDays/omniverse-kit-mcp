"""Unit tests for camera_math — pure math, no Kit / USD."""

from __future__ import annotations

import math

import pytest

from omni.mycompany.usd_mouse_interact import camera_math
from omni.mycompany.usd_mouse_interact.camera_math import (
    MovementInput,
    PITCH_LIMIT,
    basis_from_yaw_pitch,
    clamp,
    translation_from_input,
    update_yaw_pitch,
    yaw_pitch_from_forward,
)


def _norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return n


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _approx_eq(a, b, eps=1e-6):
    return abs(a - b) < eps


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------


def test_clamp_in_range():
    assert clamp(0.5, 0.0, 1.0) == 0.5


def test_clamp_below_low():
    assert clamp(-1.0, 0.0, 1.0) == 0.0


def test_clamp_above_high():
    assert clamp(2.0, 0.0, 1.0) == 1.0


# ---------------------------------------------------------------------------
# update_yaw_pitch
# ---------------------------------------------------------------------------


def test_update_yaw_pitch_zero_delta():
    yaw, pitch = update_yaw_pitch(0.5, 0.2, 0, 0)
    assert yaw == 0.5
    assert pitch == 0.2


def test_update_yaw_pitch_pitch_clamped_top():
    # large positive dy → pitch decreases (we subtract). Try huge negative dy
    # so pitch grows positively past the limit.
    _, pitch = update_yaw_pitch(0.0, 0.0, 0, -10000, sensitivity=0.01)
    assert pitch <= PITCH_LIMIT + 1e-9
    assert pitch >= PITCH_LIMIT - 1e-3


def test_update_yaw_pitch_pitch_clamped_bottom():
    _, pitch = update_yaw_pitch(0.0, 0.0, 0, 10000, sensitivity=0.01)
    assert pitch >= -PITCH_LIMIT - 1e-9
    assert pitch <= -PITCH_LIMIT + 1e-3


def test_update_yaw_unbounded():
    yaw, _ = update_yaw_pitch(0.0, 0.0, 1000, 0, sensitivity=0.01)
    assert _approx_eq(yaw, -10.0)


# ---------------------------------------------------------------------------
# basis_from_yaw_pitch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("up_axis", ["Y", "Z"])
def test_basis_orthonormal(up_axis):
    forward, right, up = basis_from_yaw_pitch(0.7, 0.3, up_axis)
    assert _approx_eq(_norm(forward), 1.0)
    assert _approx_eq(_norm(right), 1.0)
    assert _approx_eq(_norm(up), 1.0)
    assert _approx_eq(_dot(forward, right), 0.0)
    assert _approx_eq(_dot(forward, up), 0.0)
    assert _approx_eq(_dot(right, up), 0.0)


def test_basis_y_up_default_forward():
    forward, _, _ = basis_from_yaw_pitch(0.0, 0.0, "Y")
    # at yaw=0, pitch=0 → forward is -Z
    assert _approx_eq(forward[0], 0.0)
    assert _approx_eq(forward[1], 0.0)
    assert _approx_eq(forward[2], -1.0)


def test_basis_z_up_default_forward():
    forward, _, _ = basis_from_yaw_pitch(0.0, 0.0, "Z")
    # at yaw=0, pitch=0 with Z-up → forward is -Y
    assert _approx_eq(forward[0], 0.0)
    assert _approx_eq(forward[1], -1.0)
    assert _approx_eq(forward[2], 0.0)


def test_basis_yaw_90_y_up():
    forward, _, _ = basis_from_yaw_pitch(math.pi / 2, 0.0, "Y")
    # yaw +90° (around +Y) → forward rotates from -Z toward... should be -X
    assert _approx_eq(forward[0], -1.0, eps=1e-5)
    assert _approx_eq(forward[1], 0.0, eps=1e-5)
    assert _approx_eq(forward[2], 0.0, eps=1e-5)


# ---------------------------------------------------------------------------
# translation_from_input
# ---------------------------------------------------------------------------


def test_translation_no_keys_zero():
    f, r, u = (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    delta = translation_from_input(f, r, u, MovementInput(), speed=1.0, dt=0.1)
    assert delta == (0.0, 0.0, 0.0)


def test_translation_forward():
    f, r, u = (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    delta = translation_from_input(f, r, u, MovementInput(forward=True), speed=10.0, dt=0.1)
    # 10 * 0.1 = 1.0 unit toward forward
    assert _approx_eq(delta[0], 0.0)
    assert _approx_eq(delta[1], 0.0)
    assert _approx_eq(delta[2], -1.0)


def test_translation_strafe_right():
    f, r, u = (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    delta = translation_from_input(f, r, u, MovementInput(right=True), speed=10.0, dt=0.1)
    assert _approx_eq(delta[0], 1.0)
    assert _approx_eq(delta[1], 0.0)
    assert _approx_eq(delta[2], 0.0)


def test_translation_diagonal_normalized():
    """W+D should not be faster than just W."""
    f, r, u = (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    delta_diag = translation_from_input(
        f, r, u, MovementInput(forward=True, right=True), speed=10.0, dt=0.1
    )
    delta_single = translation_from_input(
        f, r, u, MovementInput(forward=True), speed=10.0, dt=0.1
    )
    mag_diag = _norm(delta_diag)
    mag_single = _norm(delta_single)
    assert _approx_eq(mag_diag, mag_single, eps=1e-6)


def test_translation_opposite_keys_cancel():
    f, r, u = (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    delta = translation_from_input(
        f, r, u, MovementInput(forward=True, backward=True), speed=10.0, dt=0.1
    )
    assert delta == (0.0, 0.0, 0.0)


def test_translation_zero_dt():
    f, r, u = (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    delta = translation_from_input(f, r, u, MovementInput(forward=True), speed=10.0, dt=0.0)
    assert delta == (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# yaw_pitch_from_forward (round-trip with basis_from_yaw_pitch)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("up_axis", ["Y", "Z"])
@pytest.mark.parametrize(
    "yaw,pitch",
    [
        (0.0, 0.0),
        (0.5, 0.3),
        (-1.2, -0.4),
        (math.pi / 4, math.pi / 6),
    ],
)
def test_yaw_pitch_round_trip(up_axis, yaw, pitch):
    forward, _, _ = basis_from_yaw_pitch(yaw, pitch, up_axis)
    yaw2, pitch2 = yaw_pitch_from_forward(forward, up_axis)
    forward2, _, _ = basis_from_yaw_pitch(yaw2, pitch2, up_axis)
    # forward vectors should match — the angle representation may wrap but the
    # direction is what matters.
    assert _approx_eq(forward[0], forward2[0], eps=1e-5)
    assert _approx_eq(forward[1], forward2[1], eps=1e-5)
    assert _approx_eq(forward[2], forward2[2], eps=1e-5)
