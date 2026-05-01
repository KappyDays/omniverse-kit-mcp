"""Keyframe trajectory tables for the humanoid pick-and-place demo.

The trajectory is expressed as a sequence of *role-keyed* keyframes —
``{"right_shoulder1": -1.4, ...}`` — and the controller resolves the role
to a DOF index at runtime against the live ``dof_names`` array. This
keeps the trajectory portable across humanoid assets whose joint
naming differs (Phase 2 candidates).

Angles are radians. Sign conventions follow USD/PhysX joint axis (which
in turn follows the humanoid's URDF/MJCF). Roles unknown to a given
asset are silently skipped, so a Phase 2 humanoid with no
``abdomen_z`` simply keeps that DOF at default while the rest of the
trajectory still plays.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CubeAttachment(Enum):
    """What the controller does with the cube during this keyframe.

    ``NONE``        — cube is not driven; physics governs.
    ``ATTACH``      — start parenting cube to the right hand link
                       (controller stamps cube position to follow link).
    ``DETACH``      — stop parenting; cube falls under gravity.
    """

    NONE = "none"
    ATTACH = "attach"
    DETACH = "detach"


@dataclass(frozen=True)
class Keyframe:
    """One step in the pick-and-place trajectory.

    Attributes:
        label: Short identifier — stamped to ``/World/PickStatus.stage``
            so an out-of-process verifier can correlate progress with
            the trajectory phase.
        targets: Role name → joint position (radians).
        hold_frames: Number of Kit update ticks to hold the targets
            before advancing. At 60 fps physics, 60 = 1 s hold.
        cube: Cube attachment behaviour for this frame.
    """

    label: str
    targets: dict[str, float]
    hold_frames: int = 60
    cube: CubeAttachment = CubeAttachment.NONE


# ---------------------------------------------------------------------------
# Default trajectory — single-arm right-side pick at +X (0.55) → place at -X.
#
# Joint convention — verified live against humanoid_28.usd 2026-05-01:
#   right_shoulder_y (alias right_shoulder1) — NEGATIVE rotates the arm
#       up & back (overhead); POSITIVE pitches the arm forward & down
#       toward the floor. PhysX clamps this DOF at roughly +1.05 so
#       trajectory targets above that limit are silently truncated.
#   right_shoulder_x (alias right_shoulder2) — abduction. POSITIVE
#       opens the arm outward (away from torso); NEGATIVE pulls the arm
#       across the midline (adduct). Range roughly [-1.0, +1.0].
#   right_shoulder_z (kept at 0) — twist around the upper-arm long axis.
#       Visible effect on pose is small; we leave it at home so the
#       cube parenting trick rides on a stable forearm orientation.
#   right_elbow (alias right_elbow) — flexion, NEGATIVE = bent, POSITIVE
#       blocks at ~0 (joint limit). Pose values stay in [-1.5, 0].
#   abdomen_z — torso yaw (positive = CCW from above; +0.4 turns torso
#       toward humanoid's left → swings the right arm across to -X).
#
# These values were tuned by stepping through robot_set_joint_positions
# tests (live MCP) and observing viewport poses; see
# `docs/phase-i-humanoid-pickplace-validation-report.md` for the
# capture trail.
# ---------------------------------------------------------------------------

_HOME_TARGETS = {
    "abdomen_x": 0.0, "abdomen_y": 0.0, "abdomen_z": 0.0,
    "right_shoulder1": 0.0, "right_shoulder2": 0.0, "right_elbow": 0.0,
    "left_shoulder1": 0.0, "left_shoulder2": 0.0, "left_elbow": 0.0,
}


DEFAULT_TRAJECTORY: tuple[Keyframe, ...] = (
    Keyframe(
        label="home",
        targets=dict(_HOME_TARGETS),
        hold_frames=30,
    ),
    Keyframe(
        label="reach_pick_above",
        # Pitch arm forward+down (positive shoulder_y), abduct out a bit,
        # bend elbow so the wrist clears the pick table top.
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  0.90,   # arm forward+down (clamped at ~1.05)
            "right_shoulder2":  0.30,   # gentle outward abduction
            "right_elbow":     -0.50,   # forearm bent toward the chest
            "abdomen_z":       -0.15,   # subtle torso lean toward pick side
        },
        hold_frames=60,
    ),
    Keyframe(
        label="at_cube",
        # Straighten the elbow so the lower-arm tip drops to the cube,
        # push shoulder_y to its joint limit so the arm reaches lowest.
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  1.05,   # at the joint upper limit (down)
            "right_shoulder2":  0.25,
            "right_elbow":     -0.20,   # nearly straight to maximize reach
            "abdomen_z":       -0.15,
        },
        hold_frames=60,
        cube=CubeAttachment.ATTACH,  # start carrying — kinematic ON
    ),
    Keyframe(
        label="lift",
        # Lift arm back up + tighten elbow so the cube clears the table.
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  0.40,   # arm half forward (between home and reach)
            "right_shoulder2":  0.30,
            "right_elbow":     -1.20,   # tight bend → cube up at chest
            "abdomen_z":       -0.05,
        },
        hold_frames=60,
    ),
    Keyframe(
        label="swing_to_place",
        # Twist torso CCW (abdomen_z positive) so the arm sweeps left
        # without much shoulder_x change. Adducting shoulder helps too.
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  0.40,
            "right_shoulder2": -0.40,   # arm adducts across body
            "right_elbow":     -1.20,
            "abdomen_z":        0.50,   # large CCW yaw — swings arm to -X
        },
        hold_frames=80,
    ),
    Keyframe(
        label="above_place",
        # Position over place table on humanoid's left (-X side).
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  0.85,
            "right_shoulder2": -0.50,
            "right_elbow":     -0.80,
            "abdomen_z":        0.50,
        },
        hold_frames=60,
    ),
    Keyframe(
        label="lower_place",
        # Lower hand toward the place table top.
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  1.05,
            "right_shoulder2": -0.45,
            "right_elbow":     -0.30,
            "abdomen_z":        0.50,
        },
        hold_frames=60,
    ),
    Keyframe(
        label="release",
        # Same pose, but detach so gravity drops the cube onto the table.
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  1.05,
            "right_shoulder2": -0.45,
            "right_elbow":     -0.30,
            "abdomen_z":        0.50,
        },
        hold_frames=30,
        cube=CubeAttachment.DETACH,
    ),
    Keyframe(
        label="retract",
        # Pull arm back without dragging across the place table.
        targets={
            **_HOME_TARGETS,
            "right_shoulder1":  0.40,
            "right_shoulder2": -0.20,
            "right_elbow":     -1.00,
            "abdomen_z":        0.20,
        },
        hold_frames=60,
    ),
    Keyframe(
        label="home_back",
        targets=dict(_HOME_TARGETS),
        hold_frames=60,
    ),
)


def total_frames(trajectory: tuple[Keyframe, ...] = DEFAULT_TRAJECTORY) -> int:
    """Sum of ``hold_frames`` across every keyframe — used by tests."""
    return sum(kf.hold_frames for kf in trajectory)
