"""Unit tests for the pure-Python helpers shipped with
``omni.mycompany.humanoid_pick_place``.

The Kit extension's ``__init__.py`` eagerly imports ``extension`` (a
``omni.ext.IExt`` subclass) which in turn imports ``omni.kit.*`` —
unavailable under pytest. To test the pure data modules in isolation
we load them by file path with ``importlib.util.spec_from_file_location``,
bypassing the package's ``__init__.py`` entirely.

These tests guard the trajectory invariants (every step has a label,
hold_frames > 0, role names match the resolver candidates) and the
registry shape (Humanoid28 is the Phase 1 default, URLs use the
allow-listed S3 prefix from ``docs/invariants/usd-load.md``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PKG_ROOT = (
    _REPO_ROOT
    / "isaac_extension"
    / "omni.mycompany.humanoid_pick_place"
    / "omni"
    / "mycompany"
    / "humanoid_pick_place"
)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not build spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    # Python 3.14 ``@dataclass`` looks up the module in ``sys.modules``
    # while building each class's __module__ — register before exec.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


humanoids = _load_module("humanoids", _PKG_ROOT / "humanoids.py")
joint_layout = _load_module("joint_layout", _PKG_ROOT / "joint_layout.py")
trajectory = _load_module("trajectory", _PKG_ROOT / "trajectory.py")


# ---------------------------------------------------------------------------
# humanoids.py
# ---------------------------------------------------------------------------

ALLOWED_S3_PREFIXES = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/",
    "https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/",
)


class TestHumanoidRegistry:
    def test_phase1_default_is_humanoid28(self):
        assert humanoids.default_humanoid().key == "humanoid28"
        assert humanoids.default_humanoid() is humanoids.HUMANOID28

    def test_phase1_humanoid28_first(self):
        # Humanoid28 is the demo's default; UI ComboBox seeds index 0
        # to it, so the spec must remain at position 0 of the active list.
        assert humanoids.PHASE1_HUMANOIDS[0].key == "humanoid28"

    def test_phase1_includes_unitree_h1(self):
        # 2026-05-01 Phase 2 wave 1: H1 promoted to the active roster
        # after live joint-roster capture confirmed compatibility with
        # the role-keyed trajectory resolver.
        keys = [h.key for h in humanoids.PHASE1_HUMANOIDS]
        assert "unitree_h1" in keys

    def test_all_humanoid_urls_use_allowed_s3_prefix(self):
        # Defends docs/invariants/usd-load.md condition #1 — file:// or
        # arbitrary domains are forbidden.
        for h in humanoids.ALL_HUMANOIDS:
            assert any(
                h.usd_url.startswith(p) for p in ALLOWED_S3_PREFIXES
            ), f"{h.key} has disallowed URL: {h.usd_url}"

    def test_get_by_key_round_trip(self):
        for h in humanoids.ALL_HUMANOIDS:
            assert humanoids.get_by_key(h.key) is h

    def test_get_by_key_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown humanoid"):
            humanoids.get_by_key("definitely_not_a_humanoid")

    def test_humanoid_specs_have_anchor_link(self):
        # The Build Scene step relies on a non-empty anchor_link_hint to
        # author the FixedJoint that prevents the humanoid from toppling.
        for h in humanoids.ALL_HUMANOIDS:
            assert h.anchor_link_hint, f"{h.key} missing anchor_link_hint"

    def test_phase2_candidates_are_real_robots(self):
        # Sanity: remaining Phase 2 candidates point to real Isaac Sim
        # robot assets — not placeholders. Unitree H1 was promoted to
        # PHASE1_HUMANOIDS in 2026-05-01 Phase 2 wave 1.
        keys = {h.key for h in humanoids.PHASE2_CANDIDATES}
        assert "gr1t2" in keys


# ---------------------------------------------------------------------------
# joint_layout.py
# ---------------------------------------------------------------------------

class TestJointLayout:
    def test_resolve_indices_humanoid28_canonical(self):
        # Canonical MJCF Humanoid28 dof_names ordering — the resolver
        # must find right_shoulder1/2 + right_elbow + abdomen_z.
        names = (
            "abdomen_x", "abdomen_y", "abdomen_z",
            "right_hip_x", "right_hip_y", "right_hip_z", "right_knee",
            "right_ankle_y", "right_ankle_x",
            "left_hip_x", "left_hip_y", "left_hip_z", "left_knee",
            "left_ankle_y", "left_ankle_x",
            "right_shoulder1", "right_shoulder2", "right_elbow",
            "left_shoulder1", "left_shoulder2", "left_elbow",
        )
        idx = joint_layout.resolve_indices(names)
        assert idx.dof_count == 21
        assert idx.right_shoulder1 == 15
        assert idx.right_shoulder2 == 16
        assert idx.right_elbow == 17
        assert idx.left_shoulder1 == 18
        assert idx.left_elbow == 20
        assert idx.abdomen_z == 2
        assert idx.has_right_arm

    def test_resolve_indices_unknown_names_return_minus_one(self):
        idx = joint_layout.resolve_indices(("foo", "bar"))
        assert idx.right_shoulder1 == -1
        assert idx.right_elbow == -1
        assert not idx.has_right_arm

    def test_resolve_indices_alternative_naming(self):
        # Some humanoids name shoulder DOFs with axis suffix (e.g.
        # right_shoulder_y). The resolver must accept both spellings.
        names = (
            "abdomen_yaw",
            "right_shoulder_y", "right_shoulder_x", "right_elbow_y",
            "left_shoulder_y",  "left_shoulder_x",  "left_elbow_y",
        )
        idx = joint_layout.resolve_indices(names)
        assert idx.right_shoulder1 == 1
        assert idx.right_shoulder2 == 2
        assert idx.right_elbow == 3
        assert idx.abdomen_z == 0
        assert idx.has_right_arm

    def test_index_or_lookup(self):
        names = ("a", "b", "c")
        idx = joint_layout.resolve_indices(names)
        assert idx.index_or("b") == 1
        assert idx.index_or("missing") == -1
        assert idx.index_or("missing", default=99) == 99

    def test_fallback_index_known_role(self):
        # Roles in the fallback map should return their hard-coded index.
        assert joint_layout.fallback_index("right_shoulder1") == 15
        assert joint_layout.fallback_index("right_elbow") == 17

    def test_fallback_index_unknown_role(self):
        assert joint_layout.fallback_index("right_pinkie") == -1


# ---------------------------------------------------------------------------
# trajectory.py
# ---------------------------------------------------------------------------

class TestTrajectory:
    def test_default_trajectory_is_non_empty(self):
        assert len(trajectory.DEFAULT_TRAJECTORY) >= 5

    def test_default_trajectory_starts_and_ends_at_home(self):
        kfs = trajectory.DEFAULT_TRAJECTORY
        assert kfs[0].label == "home"
        assert kfs[-1].label == "home_back"

    def test_every_keyframe_has_positive_hold(self):
        for kf in trajectory.DEFAULT_TRAJECTORY:
            assert kf.hold_frames > 0, f"{kf.label} has hold_frames=0"

    def test_keyframe_labels_unique(self):
        labels = [kf.label for kf in trajectory.DEFAULT_TRAJECTORY]
        assert len(labels) == len(set(labels)), (
            f"Duplicate keyframe label(s): {labels}"
        )

    def test_attach_then_detach_exactly_once(self):
        attaches = [kf for kf in trajectory.DEFAULT_TRAJECTORY
                    if kf.cube == trajectory.CubeAttachment.ATTACH]
        detaches = [kf for kf in trajectory.DEFAULT_TRAJECTORY
                    if kf.cube == trajectory.CubeAttachment.DETACH]
        assert len(attaches) == 1, "exactly one ATTACH keyframe expected"
        assert len(detaches) == 1, "exactly one DETACH keyframe expected"
        # ATTACH must precede DETACH.
        attach_idx = trajectory.DEFAULT_TRAJECTORY.index(attaches[0])
        detach_idx = trajectory.DEFAULT_TRAJECTORY.index(detaches[0])
        assert attach_idx < detach_idx

    def test_total_frames_matches_sum_of_holds(self):
        manual = sum(kf.hold_frames for kf in trajectory.DEFAULT_TRAJECTORY)
        assert trajectory.total_frames() == manual

    def test_targets_use_role_names_known_to_resolver(self):
        # Every role mentioned in any keyframe must have a candidate
        # entry in joint_layout.resolve_indices — otherwise the role is
        # silently a no-op and the demo will look wrong.
        sample_dof = (
            "abdomen_x", "abdomen_y", "abdomen_z",
            "right_shoulder1", "right_shoulder2", "right_elbow",
            "left_shoulder1", "left_shoulder2", "left_elbow",
        )
        idx = joint_layout.resolve_indices(sample_dof)
        for kf in trajectory.DEFAULT_TRAJECTORY:
            for role in kf.targets.keys():
                resolved = idx.index_or(role)
                if resolved < 0:
                    resolved = getattr(idx, role, -1)
                assert resolved >= 0, (
                    f"Keyframe '{kf.label}' references role '{role}' "
                    f"that the joint_layout resolver does not recognise."
                )

    def test_keyframe_angles_within_safe_range(self):
        # Catch typos like 30.0 instead of 0.30 — radians for human
        # joints should not exceed ~3.14.
        for kf in trajectory.DEFAULT_TRAJECTORY:
            for role, value in kf.targets.items():
                assert -3.5 <= value <= 3.5, (
                    f"{kf.label}.{role}={value} exceeds plausible range"
                )
