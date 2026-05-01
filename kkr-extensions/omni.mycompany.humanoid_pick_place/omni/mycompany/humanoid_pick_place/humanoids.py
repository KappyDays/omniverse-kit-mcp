"""Humanoid catalog — USD URL + per-asset metadata.

Design intent:
    Phase 1 ships with NVIDIA IsaacSim/Humanoid28 (the literal "NVIDIA built-in
    humanoid"). Phase 2 adds production humanoids (Unitree H1, Fourier GR-1T2)
    by appending a single entry below + tuning the keyframe table in
    ``trajectory.py``. Trajectories themselves are role-driven (right shoulder,
    right elbow, ...) and resolved against the live ``dof_names`` array, so the
    same trajectory file works across humanoids whose joint naming differs.

Each entry is immutable and self-contained — no inheritance — to keep the
registry trivially serializable / testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Asset URLs (Isaac Sim 5.1 S3 — verified 2026-05-01)
# ---------------------------------------------------------------------------

ISAAC_S3_ROOT = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac"
)


@dataclass(frozen=True)
class HumanoidSpec:
    """Static metadata for a humanoid asset.

    Attributes:
        key: Short identifier used by UI / scenario YAML (e.g. ``"humanoid28"``).
        title: Human-readable label for the UI dropdown.
        usd_url: S3 URL of the humanoid root USD.
        standing_height_m: Approximate hip height when standing — used as
            the spawn ``z`` so the feet land near floor level on the ground
            plane. Off by a few cm is fine; PhysX settles within 1-2 sim
            seconds anyway.
        right_hand_link_hint: Substring appearing in the right-hand link's
            prim name. Used by ``scene_builder.find_right_hand_link`` to
            locate the wrist/hand link for the cube-grasp parenting trick.
            ``None`` means the asset has no dedicated hand link → the
            controller falls back to following the right elbow link.
        anchor_link_hint: Substring of the link to pin to ``/World`` via a
            FixedJoint so the humanoid does not topple while the demo runs.
            Pelvis / torso / base — depends on the asset's link names.
        notes: Free-form notes that show up in the panel's tooltip and the
            scenario YAML's documentation.
    """

    key: str
    title: str
    usd_url: str
    standing_height_m: float
    right_hand_link_hint: str | None
    anchor_link_hint: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Registry — Phase 1 ships only Humanoid28; Phase 2 appends.
# ---------------------------------------------------------------------------

HUMANOID28 = HumanoidSpec(
    key="humanoid28",
    title="NVIDIA Humanoid28 (28-DOF)",
    usd_url=f"{ISAAC_S3_ROOT}/Robots/IsaacSim/Humanoid28/humanoid_28.usd",
    # Torso pinned at 0.70 m places the feet on the Grid floor
    # (default_environment.usd at z=0). Both 1.34 (original) and 1.05
    # (first fix) left the humanoid hovering ~30-50 cm above the floor.
    # Live measurement against the grid surface 2026-05-01 shows the
    # MJCF Humanoid28 torso link sits ~0.70 m above the feet, so
    # pinning the torso joint at 0.70 m world Z puts the soles at z ≈ 0.
    # anchor_link_hint stays "torso" because pinning the pelvis (which
    # is the MJCF articulation root) trips
    # ``SingleArticulation.initialize() →
    # 'NoneType' has no attribute 'link_names'``.
    standing_height_m=0.70,
    # MJCF Humanoid28 has no dedicated hand mesh; the right_lower_arm link
    # is the closest end-effector. The cube parenting trick clamps onto
    # whichever link's name contains this hint.
    right_hand_link_hint="right_lower_arm",
    anchor_link_hint="torso",
    notes="NVIDIA IsaacSim educational humanoid — 28 DOF, MJCF-style. "
          "No discrete hand mesh; the cube is parented to the right "
          "lower-arm link during transport.",
)

UNITREE_H1 = HumanoidSpec(
    key="unitree_h1",
    title="Unitree H1 (Phase 2 candidate)",
    usd_url=f"{ISAAC_S3_ROOT}/Robots/Unitree/H1/h1.usd",
    standing_height_m=1.05,
    right_hand_link_hint="right_elbow_link",
    anchor_link_hint="pelvis",
    notes="Unitree H1 production humanoid — paddle end-effector. "
          "Phase 2: validate joint roster and re-tune keyframes.",
)

GR1T2 = HumanoidSpec(
    key="gr1t2",
    title="Fourier GR-1T2 with 6-DOF hands (Phase 2 candidate)",
    usd_url=(
        f"{ISAAC_S3_ROOT}/Robots/FourierIntelligence/GR-1/"
        "GR1T2_fourier_hand_6dof/GR1T2_fourier_hand_6dof.usd"
    ),
    standing_height_m=1.0,
    right_hand_link_hint="right_hand",
    anchor_link_hint="pelvis",
    notes="Fourier GR-1 with 6-DOF dexterous hands. Phase 2 stretch goal: "
          "use individual finger DOFs for actual grasp closure.",
)


# Phase 1 = Humanoid28 (NVIDIA in-house educational rig). Phase 2
# extends the active list with production humanoids; both spec entries
# point at real Isaac Sim 5.1 S3 assets and were live-validated via
# `asset_list` 2026-05-01. GR-1T2 stays in PHASE2_CANDIDATES until its
# 6-DOF dexterous hands are wired into the cube grasp logic.
PHASE1_HUMANOIDS: tuple[HumanoidSpec, ...] = (HUMANOID28, UNITREE_H1)
PHASE2_CANDIDATES: tuple[HumanoidSpec, ...] = (GR1T2,)
ALL_HUMANOIDS: tuple[HumanoidSpec, ...] = PHASE1_HUMANOIDS + PHASE2_CANDIDATES


def get_by_key(key: str) -> HumanoidSpec:
    """Return the spec whose ``key`` matches; raises ``KeyError`` otherwise."""
    for spec in ALL_HUMANOIDS:
        if spec.key == key:
            return spec
    raise KeyError(
        f"Unknown humanoid key {key!r}. Known: "
        f"{[h.key for h in ALL_HUMANOIDS]}"
    )


def default_humanoid() -> HumanoidSpec:
    """The default humanoid the demo loads on first Build Scene."""
    return PHASE1_HUMANOIDS[0]
