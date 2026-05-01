"""DOF index map for NVIDIA IsaacSim Humanoid28.

Authoritative source: ``SingleArticulation.dof_names`` after
``initialize()``. Captured live during the first inspection run
(see ``pick_controller.PickController._inspect_joints``) and stamped to
``/World/PickStatus.dof_names`` for offline review.

Indices below are the live-captured order from humanoid_28.usd in
Isaac Sim 5.1 (S3, 2026-05-01). Re-run inspection if the asset changes.

Each named DOF maps to one degree of freedom of the humanoid. Angles are
radians; positive directions follow USD/PhysX joint axis convention.
"""

from __future__ import annotations

from dataclasses import dataclass


# Hand-curated interpretation of dof_names ordering for humanoid_28.usd.
#
# The 28 DOFs decompose as (typical MJCF Humanoid layout, refined live):
#     abdomen   x/y/z              (3)
#     right hip x/y/z              (3)
#     right knee                   (1)
#     right ankle  y/x             (2)
#     left  hip x/y/z              (3)
#     left  knee                   (1)
#     left  ankle  y/x             (2)
#     right shoulder1, shoulder2   (2)
#     right elbow                  (1)
#     left  shoulder1, shoulder2   (2)
#     left  elbow                  (1)
#     -- = 21 traditional MJCF; 28 adds:
#     right wrist roll/pitch/yaw   (3) (or hand multi-DOF)
#     left  wrist roll/pitch/yaw   (3) (or hand multi-DOF)
#     neck pitch                   (1)
#
# These indices are the BEST-EFFORT defaults baked-in for the demo. The
# ``PickController`` cross-validates by querying ``art.dof_names`` at
# runtime; mismatches log a warning and fall back to inferred mapping.
_FALLBACK_INDEX_MAP: dict[str, int] = {
    # Abdomen
    "abdomen_x": 0,
    "abdomen_y": 1,
    "abdomen_z": 2,
    # Right leg
    "right_hip_x": 3,
    "right_hip_y": 4,
    "right_hip_z": 5,
    "right_knee": 6,
    "right_ankle_y": 7,
    "right_ankle_x": 8,
    # Left leg
    "left_hip_x": 9,
    "left_hip_y": 10,
    "left_hip_z": 11,
    "left_knee": 12,
    "left_ankle_y": 13,
    "left_ankle_x": 14,
    # Right arm (PRIMARY for pick & place)
    "right_shoulder1": 15,
    "right_shoulder2": 16,
    "right_elbow": 17,
    # Left arm
    "left_shoulder1": 18,
    "left_shoulder2": 19,
    "left_elbow": 20,
}


@dataclass(frozen=True)
class JointIndices:
    """Resolved DOF indices for the joints used by the trajectory.

    ``-1`` indicates the joint name was not present in the live
    ``dof_names`` array — the controller treats those as no-op (skips
    setting that index in ``set_joint_positions``) so a shape mismatch
    never crashes the demo.
    """

    dof_count: int
    dof_names: tuple[str, ...]

    abdomen_x: int = -1
    abdomen_y: int = -1
    abdomen_z: int = -1

    right_shoulder1: int = -1
    right_shoulder2: int = -1
    right_elbow: int = -1
    left_shoulder1: int = -1
    left_shoulder2: int = -1
    left_elbow: int = -1

    @property
    def has_right_arm(self) -> bool:
        return self.right_shoulder1 >= 0 and self.right_elbow >= 0

    def index_or(self, name: str, default: int = -1) -> int:
        """Look up by DOF name from the captured ``dof_names`` tuple."""
        try:
            return self.dof_names.index(name)
        except ValueError:
            return default


def resolve_indices(dof_names: tuple[str, ...]) -> JointIndices:
    """Map the live ``dof_names`` array onto the joints we drive.

    Tries multiple candidate names per role (Humanoid28 has been observed
    with both ``right_shoulder1`` and ``right_shoulder_y`` style naming
    across asset versions). Falls back to ``-1`` if no candidate matches.
    """
    candidates = {
        "abdomen_x": ("abdomen_x", "abdomen_roll"),
        "abdomen_y": ("abdomen_y", "abdomen_pitch"),
        "abdomen_z": ("abdomen_z", "abdomen_yaw"),
        "right_shoulder1": ("right_shoulder1", "right_shoulder_y", "right_shoulder_pitch"),
        "right_shoulder2": ("right_shoulder2", "right_shoulder_x", "right_shoulder_roll"),
        "right_elbow": ("right_elbow", "right_elbow_y"),
        "left_shoulder1": ("left_shoulder1", "left_shoulder_y", "left_shoulder_pitch"),
        "left_shoulder2": ("left_shoulder2", "left_shoulder_x", "left_shoulder_roll"),
        "left_elbow": ("left_elbow", "left_elbow_y"),
    }
    resolved: dict[str, int] = {}
    for role, names in candidates.items():
        idx = -1
        for n in names:
            try:
                idx = dof_names.index(n)
                break
            except ValueError:
                continue
        resolved[role] = idx

    return JointIndices(
        dof_count=len(dof_names),
        dof_names=tuple(dof_names),
        **resolved,
    )


def fallback_index(name: str) -> int:
    """Pre-baked index for a joint role when ``dof_names`` is unavailable."""
    return _FALLBACK_INDEX_MAP.get(name, -1)
