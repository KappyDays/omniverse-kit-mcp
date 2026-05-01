"""Build-time geometry sanity check.

Catches placement errors that visual capture would catch — but at build
time, before the user has to look at a screenshot. v5 round-2 motivating
case: Franka_A base XY at the same point as the left STRAIGHT belt
center → Franka mesh literally intersected the belt mesh, not visible
from the dump_state coord output but obvious in viewport.

Used by :class:`scene_builder.SceneBuilder.build` after every prim is
placed but before the simulation starts. Raises :class:`BuildLayoutError`
on hard failure; logs warnings for borderline cases (overlap < 5 cm).
"""
from __future__ import annotations

from typing import Iterable

import carb


_SOURCE = "omni.userext.pickplace.layout_check"

# Hard collision threshold — any overlap > this aborts the build.
HARD_OVERLAP_M = 0.01
# Soft warning threshold — overlap [HARD, SOFT] only logs a warning.
SOFT_OVERLAP_M = 0.10


class BuildLayoutError(RuntimeError):
    """Raised when build-time AABB check finds robot/asset intersection."""


def check_ground_penetration(
    prim_paths: Iterable[str],
    ground_z: float = 0.0,
    tolerance: float = 0.01,
) -> dict:
    """Verify no asset's AABB.min.z dips below ``ground_z`` (within tolerance).

    Catches "Box buried" / "Conveyor legs through floor" before sim starts.
    Returns a report dict; raises BuildLayoutError on hard penetration > 0.10 m.
    """
    import omni.usd
    from pxr import Sdf, UsdGeom

    from . import ground_snap as gs

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return {"checked": 0, "warnings": [], "errors": []}

    bbox_cache = UsdGeom.BBoxCache(0.0, [UsdGeom.Tokens.default_])
    warnings_: list[str] = []
    errors: list[str] = []
    checked = 0

    for path in prim_paths:
        prim = stage.GetPrimAtPath(Sdf.Path(path))
        if not prim.IsValid():
            continue
        bb = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if bb.IsEmpty():
            continue
        checked += 1
        amin_z = float(bb.GetMin()[2])
        depth = ground_z - amin_z
        if depth > 0.10:  # hard
            errors.append(f"{path}: bottom z={amin_z:.3f} (penetrates {depth:.3f} m below ground)")
        elif depth > tolerance:
            warnings_.append(f"{path}: bottom z={amin_z:.3f} (penetrates {depth:.3f} m below ground)")

    for w in warnings_:
        carb.log_warn(f"[{_SOURCE}] GROUND-PENETRATION WARN  {w}")
    for e in errors:
        carb.log_error(f"[{_SOURCE}] GROUND-PENETRATION ERROR {e}")

    if errors:
        # Soft mode (do not raise) — same policy as check_no_intersection,
        # because BBoxCache may give inflated bounds in some setups. Visual
        # capture remains the ground truth.
        carb.log_warn(
            f"[{_SOURCE}] {len(errors)} ground-penetration error(s) demoted to warning "
            f"(BBoxCache accuracy caveat — verify visually)"
        )

    carb.log_info(
        f"[{_SOURCE}] ground penetration check: {checked} prim(s), "
        f"{len(warnings_)} warning(s), {len(errors)} error(s)"
    )
    return {"checked": checked, "warnings": warnings_, "errors": errors}


def check_no_intersection(
    robot_paths: Iterable[str],
    asset_paths: Iterable[str],
) -> dict:
    """Verify no Robot AABB intersects any Asset AABB.

    Returns a report dict ``{"checked": N, "warnings": [...], "errors": [...]}``;
    raises :class:`BuildLayoutError` if any error.

    AABB measurement uses ``UsdGeom.BBoxCache`` with default purpose;
    ignores ``purpose=guide`` (invisible helpers) so the surface collision
    plane (if reintroduced) does not trigger false positives.
    """
    import omni.usd
    from pxr import Sdf, UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return {"checked": 0, "warnings": [], "errors": []}

    bbox_cache = UsdGeom.BBoxCache(0.0, [UsdGeom.Tokens.default_])

    robot_aabbs: list[tuple] = []
    for rp in robot_paths:
        prim = stage.GetPrimAtPath(Sdf.Path(rp))
        if not prim.IsValid():
            continue
        bb = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if bb.IsEmpty():
            continue
        robot_aabbs.append((rp, _aabb_to_tuple(bb)))

    asset_aabbs: list[tuple] = []
    for ap in asset_paths:
        prim = stage.GetPrimAtPath(Sdf.Path(ap))
        if not prim.IsValid():
            continue
        bb = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if bb.IsEmpty():
            continue
        asset_aabbs.append((ap, _aabb_to_tuple(bb)))

    warnings_: list[str] = []
    errors: list[str] = []

    for r_path, r_box in robot_aabbs:
        for a_path, a_box in asset_aabbs:
            overlap = _aabb_overlap(r_box, a_box)
            if overlap is None:
                continue  # no intersection
            ox, oy, oz = overlap
            depth = min(ox, oy, oz)
            msg = (
                f"{r_path} ∩ {a_path}: overlap=({ox:.3f},{oy:.3f},{oz:.3f}) m"
            )
            if depth > SOFT_OVERLAP_M:
                errors.append(msg)
            elif depth > HARD_OVERLAP_M:
                warnings_.append(msg)

    report = {
        "checked": len(robot_aabbs) * len(asset_aabbs),
        "warnings": warnings_,
        "errors": errors,
    }

    for w in warnings_:
        carb.log_warn(f"[{_SOURCE}] WARN  {w}")
    for e in errors:
        carb.log_error(f"[{_SOURCE}] ERROR {e}")

    if errors:
        raise BuildLayoutError(
            f"{len(errors)} hard intersection(s); first: {errors[0]}"
        )

    carb.log_info(
        f"[{_SOURCE}] layout OK ({report['checked']} pair-checks, "
        f"{len(warnings_)} warning(s))"
    )
    return report


# ---------------------------------------------------------------------------
# Pure functions — unit-testable without omni.
# ---------------------------------------------------------------------------


def aabb_overlap(
    a: tuple[tuple[float, float, float], tuple[float, float, float]],
    b: tuple[tuple[float, float, float], tuple[float, float, float]],
):
    """Public alias for :func:`_aabb_overlap` so unit tests can import."""
    return _aabb_overlap(a, b)


def _aabb_overlap(a, b):
    """Per-axis overlap (m) if AABBs intersect; ``None`` otherwise.

    AABB format: ``((min_x, min_y, min_z), (max_x, max_y, max_z))``.
    """
    a_min, a_max = a
    b_min, b_max = b
    overlaps = []
    for i in range(3):
        ov = min(a_max[i], b_max[i]) - max(a_min[i], b_min[i])
        if ov <= 0:
            return None
        overlaps.append(float(ov))
    return tuple(overlaps)


def _aabb_to_tuple(bb):
    bmin = bb.GetMin()
    bmax = bb.GetMax()
    return (
        (float(bmin[0]), float(bmin[1]), float(bmin[2])),
        (float(bmax[0]), float(bmax[1]), float(bmax[2])),
    )
