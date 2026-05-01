"""Box arrival metric helpers — pure functions, omni-free.

Used by ``extension.py`` to compute "cubes inside box" counts and the
overall arrival rate displayed on the workshop UI panel. Decoupled from
omni / pxr so the geometry helpers can be unit-tested in pure Python
(``isaac-pick-place/tests/test_cube_metrics.py``).

KLT bin inner-volume estimate sourced from ``RECON.md`` §2 — outer
~0.4 m × 0.3 m × 0.15 m, walls ~0.03 m, so the inner footprint is
roughly 0.34 × 0.24 × 0.13 m. We expose half-extents (origin at the
KLT bin's xform translate) and add a small "top slack" that lets a
cube count as in-box while it is still falling into the bin from
above (the gripper releases at ~0.35 m above the bin floor, so the
cube spends a few physics ticks above ``+half_z`` before settling).

Task 7 will measure the actual KLT bbox in-sim and tighten these
constants if needed (RECON.md §3 todo).
"""
from __future__ import annotations

from typing import Tuple


# RECON.md §2.4 — small_KLT outer footprint × wall thickness assumption.
KLT_INNER_HALF: Tuple[float, float, float] = (0.17, 0.12, 0.07)
# Slack above the bin top so cubes still in mid-fall count as "in box".
KLT_TOP_SLACK: float = 0.05


def cube_in_box(
    cube_pos: Tuple[float, float, float],
    box_pos: Tuple[float, float, float],
    half_extent: Tuple[float, float, float] = KLT_INNER_HALF,
    top_slack: float = KLT_TOP_SLACK,
) -> bool:
    """Return True iff ``cube_pos`` is inside the KLT bin at ``box_pos``.

    Args:
        cube_pos:    cube center in world coords (x, y, z).
        box_pos:    KLT bin xform translate in world coords (x, y, z).
        half_extent: per-axis half-extent of the bin's inner volume.
        top_slack:   extra +z tolerance — counts cubes mid-fall as in-box.

    Returns:
        True if cube center sits within the inner bbox plus top slack.
    """
    dx = cube_pos[0] - box_pos[0]
    dy = cube_pos[1] - box_pos[1]
    dz = cube_pos[2] - box_pos[2]
    return (
        abs(dx) < half_extent[0]
        and abs(dy) < half_extent[1]
        and abs(dz) < half_extent[2] + top_slack
    )


def arrival_rate(spawned: int, in_a: int, in_b: int) -> float:
    """Percentage of spawned cubes that landed inside either KLT bin.

    Returns 0.0 when no cube has spawned yet (avoid /0 on UI startup).
    """
    if spawned <= 0:
        return 0.0
    return (in_a + in_b) / spawned * 100.0
