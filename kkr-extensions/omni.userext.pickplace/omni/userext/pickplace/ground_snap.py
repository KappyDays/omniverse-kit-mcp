"""Bottom-anchor placement: snap any USD asset's bottom to a ground plane.

USD prim 의 ``xformOp:translate`` 은 prim origin (= pivot) 위치만 지정.
Pivot 이 어디에 있는지는 asset 마다 다름:

  - Franka Panda  : panda_link0 base (asset bottom == pivot) → z=0 OK
  - KLT_Bin small : bin geometry center → z=0 면 절반 파묻힘
  - ConveyorBelt  : belt + handrail mesh AABB center → z=0 면 다리가 ground 뚫음

이 모듈은 BBoxCache 로 prim 의 현재 world AABB 를 측정하고, bottom 을
``ground_z`` 위에 정확히 안착시키는 z-offset 을 계산해 ``xformOp:translate``
에 set 한다. **모든 NVIDIA asset 일반화 가능** — 새 asset 추가 시 hand-tune
불필요.

Pure helpers (omni-free) 가 있어 단위 테스트 가능; omni-heavy 진입점은
:func:`place_on_ground` 한 개.

레퍼런스: NVIDIA UR10 palletizing (`isaacsim.examples.interactive.ur10_palletizing`)
조차 hand-tune된 z 값을 사용 — NVIDIA 자체에 표준 "snap to ground" helper
없음. 이 모듈이 그 gap 채움.
"""
from __future__ import annotations

from typing import NamedTuple, Optional

import carb


_SOURCE = "omni.userext.pickplace.ground_snap"


class SnapResult(NamedTuple):
    """Return value of :func:`place_on_ground` — diagnostic fields."""
    prim_path: str
    old_translate_z: float
    new_translate_z: float
    aabb_min_z_before: float
    aabb_min_z_after: float  # should equal ground_z
    pivot_offset_above_bottom: float  # pivot z - bottom z


# ---------------------------------------------------------------------------
# Pure functions (omni-free, unit-testable)
# ---------------------------------------------------------------------------


def compute_snap_translate_z(
    current_translate_z: float,
    current_aabb_min_z: float,
    ground_z: float = 0.0,
) -> float:
    """How to set xformOp:translate.z so that the asset's bottom = ground_z.

    Math:
        pivot_offset = current_translate_z - current_aabb_min_z
                       (= "pivot 이 bottom 위 얼마나 떠있는가")
        new_translate_z = ground_z + pivot_offset
                          (= ground_z 위에 같은 offset 만큼 띄움)

    Pure function — no omni dependency, fully unit-testable.
    """
    pivot_offset = current_translate_z - current_aabb_min_z
    return ground_z + pivot_offset


def detects_ground_penetration(
    aabb_min_z: float, ground_z: float = 0.0, tolerance: float = 0.01
) -> bool:
    """True if asset bottom is below ground by more than ``tolerance`` m."""
    return aabb_min_z < (ground_z - tolerance)


# ---------------------------------------------------------------------------
# Omni-heavy entry point
# ---------------------------------------------------------------------------


def place_on_ground(
    prim,
    ground_z: float = 0.0,
) -> Optional[SnapResult]:
    """Snap ``prim`` 의 bottom 을 ``ground_z`` 위에 안착.

    1. BBoxCache 로 prim world AABB 측정 (현재 transform 포함)
    2. 현재 translate.z + AABB.min.z 차이로 pivot offset 계산
    3. translate.z 를 ``ground_z + pivot_offset`` 로 set
    4. (검증) 다시 측정해 AABB.min.z ≈ ground_z 확인

    XY 는 보존. translate op 가 없으면 AddTranslateOp 로 추가.
    Returns SnapResult on success, None if AABB empty / prim invalid.
    """
    from pxr import Gf, UsdGeom

    if not prim.IsValid():
        carb.log_warn(f"[{_SOURCE}] place_on_ground: prim invalid")
        return None

    bbox_cache = UsdGeom.BBoxCache(0.0, [UsdGeom.Tokens.default_])
    bb = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
    if bb.IsEmpty():
        carb.log_warn(f"[{_SOURCE}] place_on_ground: empty AABB for {prim.GetPath()}")
        return None
    aabb_min_z_before = float(bb.GetMin()[2])

    xformable = UsdGeom.Xformable(prim)
    translate_op = None
    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            translate_op = op
            break
    if translate_op is None:
        translate_op = xformable.AddTranslateOp()
    current_t = translate_op.Get()
    if current_t is None:
        current_t = Gf.Vec3d(0.0, 0.0, 0.0)
    current_translate_z = float(current_t[2])

    new_z = compute_snap_translate_z(current_translate_z, aabb_min_z_before, ground_z)
    pivot_offset = current_translate_z - aabb_min_z_before
    translate_op.Set(Gf.Vec3d(float(current_t[0]), float(current_t[1]), new_z))

    # Verify (re-measure)
    bb_after = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
    aabb_min_z_after = float(bb_after.GetMin()[2]) if not bb_after.IsEmpty() else float("nan")

    result = SnapResult(
        prim_path=str(prim.GetPath()),
        old_translate_z=current_translate_z,
        new_translate_z=new_z,
        aabb_min_z_before=aabb_min_z_before,
        aabb_min_z_after=aabb_min_z_after,
        pivot_offset_above_bottom=pivot_offset,
    )
    carb.log_info(
        f"[{_SOURCE}] snapped {result.prim_path}: "
        f"translate.z {current_translate_z:.3f} → {new_z:.3f}, "
        f"bottom {aabb_min_z_before:.3f} → {aabb_min_z_after:.3f} (target {ground_z:.3f})"
    )
    return result
