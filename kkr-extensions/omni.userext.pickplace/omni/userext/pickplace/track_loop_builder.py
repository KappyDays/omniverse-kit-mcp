"""ㅁ-shape closed conveyor loop via NVIDIA ConveyorBuilder API (v5).

Replaces the v4 4-segment ``SEGMENTS`` / ``_load_conveyor_segment`` approach
with an anchor-chained 8-segment loop (4 STRAIGHT + 4 FULL_LARGE corner)
built through the official ``isaacsim.asset.gen.conveyor.ui.impl.conveyor_builder``
programmatic API. Anchor matrices auto-align segments — no manual coord math.

Why this design:
  - NVIDIA-native asset re-use (no custom mesh / no scale hack).
  - LARGE curvature (``direction.z = -16.67``) = max corner radius =
    minimal cube centrifugal slip.
  - 4 STRAIGHT runs give robots a stable straight-line pickup window
    (curve segments are unstable for predictive grasp).
  - ConveyorBuilder auto-applies SurfaceVelocityAPI via CreateConveyorBelt;
    we only need to post-process kinematic flag + surface collision plane
    (same v4 fixes for roller-mesh gap problem).

Segment chain (clockwise loop from origin):
  ┌─────────────────────────────────────────────────────────────┐
  │ idx │ asset                  │ type     │ note              │
  ├─────────────────────────────────────────────────────────────┤
  │  0  │ ConveyorBelt_A04       │ DUAL STR │ first (anchor "") │
  │  1  │ ConveyorBelt_A16       │ DUAL FULL LARGE corner       │
  │  2  │ ConveyorBelt_A04       │ DUAL STR                     │
  │  3  │ ConveyorBelt_A16       │ DUAL FULL LARGE corner       │
  │  4  │ ConveyorBelt_A04       │ DUAL STR                     │
  │  5  │ ConveyorBelt_A16       │ DUAL FULL LARGE corner       │
  │  6  │ ConveyorBelt_A04       │ DUAL STR                     │
  │  7  │ ConveyorBelt_A16       │ DUAL FULL LARGE corner       │
  └─────────────────────────────────────────────────────────────┘
4 × 90° corner = 360° → closes back to seg 0 entry geometrically.
ConveyorBuilder does not validate closure; we measure after build.

Asset paths: ConveyorSelector pulls from ``ConveyorBuilderPreferences.assets_location``
which we set via ``track_types.json`` config (S3 URL prefix). The local
``track_types.json`` was path-fixed in this session (carb persistent settings).
"""
from __future__ import annotations

import json
import os
from typing import NamedTuple, Optional

import carb


_SOURCE = "omni.userext.pickplace.track_loop_builder"


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

LOOP_ROOT = "/World/ConveyorLoop"

# Slow belt — predictive grasp needs cube to dwell in pickup region (v4 §7).
BELT_SPEED = 0.04  # m/s (signed; negative reverses tangent)

# Anchor chain — alternating STRAIGHT BELT + CURVE BELT (style: BELT only).
#
# v5 round-2 (사용자 시각 검증 후 fix):
#   - 이전: A04 (DUAL STRAIGHT) + A13 (DUAL FULL MEDIUM)
#     DUAL = roller layer + belt layer (2층). 사용자가 "2층으로 보임" 지적.
#   - 변경: A06 (BELT STRAIGHT) + A15 (BELT FULL MEDIUM)
#     BELT only = 평탄 단일 layer. small cube (5cm) 가 매끄럽게 이송됨.
#
# track_types.json 분류 (v5 정찰 결과):
#   - style "BELT" : smooth flat surface, ramp 없는 한 cube/package 모두 ok
#   - style "ROLLER" : powered roller, ≥15cm package 전용 (gap 5cm 통과)
#   - style "DUAL"  : roller + belt 2층 동시, 산업 외관용 (실제 cube 이송엔 부적합)
#
# Index 0 is the entry segment (no parent_anchor); 1-7 chain via "/Anchorpoint".
TRACK_CHAIN: tuple[str, ...] = (
    "ConveyorBelt_A06.usd",  # 0  BELT STRAIGHT
    "ConveyorBelt_A15.usd",  # 1  BELT CURVE 90° MEDIUM
    "ConveyorBelt_A06.usd",  # 2  BELT STRAIGHT
    "ConveyorBelt_A15.usd",  # 3  BELT CURVE 90° MEDIUM
    "ConveyorBelt_A06.usd",  # 4  BELT STRAIGHT
    "ConveyorBelt_A15.usd",  # 5  BELT CURVE 90° MEDIUM
    "ConveyorBelt_A06.usd",  # 6  BELT STRAIGHT
    "ConveyorBelt_A15.usd",  # 7  BELT CURVE 90° MEDIUM — closes back to seg 0
)

# Indices of STRAIGHT vs CURVE segments — used by spawner / reach_assignment
# to choose pickup zones (only on straights for predictive grasp stability).
STRAIGHT_INDICES: tuple[int, ...] = (0, 2, 4, 6)
CURVE_INDICES: tuple[int, ...] = (1, 3, 5, 7)


class TrackLoopResult(NamedTuple):
    """Build result for downstream coord decisions (Franka / Box / spawn)."""

    paths: list[str]                              # 8 segment xform paths
    straight_centers: list[tuple[float, float, float]]  # 4 STRAIGHT world centers (x,y,z_top)
    curve_centers: list[tuple[float, float, float]]     # 4 CURVE world centers
    aabb_min: tuple[float, float, float]          # loop overall world AABB
    aabb_max: tuple[float, float, float]
    inner_aabb_min: tuple[float, float, float]    # interior bounding (Franka placement region)
    inner_aabb_max: tuple[float, float, float]


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def build_track_loop(belt_speed: float = BELT_SPEED) -> TrackLoopResult:
    """Build the 8-segment closed conveyor loop.

    Returns world-frame measurements (centers, AABB) so the caller can place
    Franka / Box / cube spawn at coords derived from actual NVIDIA asset
    geometry — no hardcoded magic numbers.
    """
    import omni.kit.app
    import omni.usd
    from pxr import Sdf, UsdGeom

    stage = omni.usd.get_context().get_stage()

    # Ensure /World/ConveyorLoop exists.
    if not stage.GetPrimAtPath(Sdf.Path(LOOP_ROOT)).IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path(LOOP_ROOT))

    selector = _load_track_selector()
    builder = _new_conveyor_builder(stage, selector)

    # Build chain — first segment at LOOP_ROOT (no parent), rest chain via
    # /Anchorpoint of the previous segment.
    paths: list[str] = []
    prev_path = LOOP_ROOT
    prev_anchor = ""
    for idx, asset_name in enumerate(TRACK_CHAIN):
        track = selector.tracks[asset_name]
        seg_path = builder.add_track(
            track,
            track_anchor="" if idx == 0 else "",  # entry anchor on the new track
            x_direction=1,
            y_direction=1,
            parent=prev_path,
            parent_anchor="" if idx == 0 else "/Anchorpoint",
        )
        paths.append(seg_path)
        prev_path = seg_path
        # Allow USD references / kit commands to settle each iteration —
        # ConveyorBuilder.add_track invokes CreateConveyorBelt internally
        # which may schedule async USD load.
        await omni.kit.app.get_app().next_update_async()

    # Lower LOOP_ROOT so the belt running surface lands at the industrial
    # standard waist height (0.40 m, visual-validation R4). Previously
    # (round-4) we used _snap_loop_to_ground which put the lowest leg
    # on ground → belt top ≈ 0.85 m (native handrail leg length), but a
    # ground-mount Franka Panda (reach 0.855 m sphere from base z=0)
    # can't intersect cubes at z=0.85 m when REACH_OFFSET ≈ 0.72 m
    # (3D distance ≈ 1.10 m, far outside the reach sphere).
    #
    # Trade-off: visually the conveyor legs penetrate the ground (R6
    # ground penetration warning is expected, demoted to soft). The
    # alternative — adding Franka stands — multiplies layout complexity.
    # User decision (2026-04-30 round-5): "robot 이 닿을 수 있는 위치로
    # 옮길 것" — function over visual realism.
    _lower_loop_to_target_belt_z(stage, paths, target_belt_top_z=0.40)

    # Apply velocity + kinematic to every segment.
    # v5 round-2: surface collision plane removed — BELT-style segments
    # (A06/A15) have a flat continuous mesh, no roller gaps. The previous
    # extra plane was for ROLLER/DUAL gap workaround, but it sat above the
    # belt at handrail height (visual "2층" artifact reported by user).
    for seg_path in paths:
        _apply_velocity_to_segment(stage, seg_path, belt_speed)
        _make_segment_kinematic(stage, seg_path)

    # Measure world-frame geometry for caller.
    result = _measure_loop_geometry(stage, paths)
    carb.log_info(
        f"[{_SOURCE}] track loop built: 8 segments, "
        f"AABB={result.aabb_min} → {result.aabb_max}, "
        f"inner={result.inner_aabb_min} → {result.inner_aabb_max}"
    )
    return result


# ---------------------------------------------------------------------------
# ConveyorBuilder bootstrap
# ---------------------------------------------------------------------------


def _load_track_selector():
    """Load ``track_types.json`` and instantiate ``ConveyorSelector``.

    The catalog ships inside the conveyor.ui ext data folder. We resolve the
    path via the ext manager so a Kit re-install (or our recent stale-path
    fix in user.config.json) does not bind us to a hardcoded location.
    """
    from isaacsim.asset.gen.conveyor.ui.impl.conveyor_builder import ConveyorSelector

    config_path = _resolve_track_types_json()
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    selector = ConveyorSelector(config)
    return selector


def _resolve_track_types_json() -> str:
    """Find ``track_types.json`` under the conveyor.ui ext data dir."""
    import omni.kit.app

    ext_manager = omni.kit.app.get_app().get_extension_manager()
    ext_id = ext_manager.get_enabled_extension_id("isaacsim.asset.gen.conveyor.ui")
    if not ext_id:
        # Fallback: use carb persistent setting (set by preferences.py)
        carb_settings = carb.settings.get_settings()
        cfg = carb_settings.get(
            "/persistent/exts/isaacsim.asset.gen.conveyor.ui.settings/config_location"
        )
        if cfg and os.path.isfile(cfg):
            return cfg
        raise RuntimeError(
            "isaacsim.asset.gen.conveyor.ui not enabled and no carb config_location"
        )
    ext_path = ext_manager.get_extension_path(ext_id)
    candidate = os.path.join(ext_path, "data", "track_types.json")
    if not os.path.isfile(candidate):
        raise RuntimeError(f"track_types.json not found at {candidate}")
    return candidate


def _new_conveyor_builder(stage, selector):
    from isaacsim.asset.gen.conveyor.ui.impl.conveyor_builder import ConveyorBuilder

    return ConveyorBuilder(stage, conveyor_selector=selector)


# ---------------------------------------------------------------------------
# Per-segment post-processing (kinematic + surface plane + velocity)
# ---------------------------------------------------------------------------


def _apply_velocity_to_segment(stage, seg_path: str, velocity: float) -> None:
    """Set the inputs:velocity on every ConveyorNode under the segment.

    ConveyorBuilder.add_track creates one or more ConveyorNode (one per
    conveyor_node entry — DUAL has Rollers + Belt → 2 nodes). We set
    velocity on each so both sub-meshes animate.
    """
    from pxr import Sdf

    seg_prim = stage.GetPrimAtPath(Sdf.Path(seg_path))
    if not seg_prim.IsValid():
        carb.log_warn(f"[{_SOURCE}] velocity skip: {seg_path} not valid")
        return

    n_set = 0
    for child in _walk_descendants(seg_prim):
        # ConveyorNode is the OmniGraph node prim (typeName "OmniGraphNode"
        # with inputs:velocity attr). Match by attribute presence.
        attr = child.GetAttribute("inputs:velocity")
        if attr.IsValid():
            attr.Set(float(velocity))
            n_set += 1
    if n_set == 0:
        carb.log_warn(f"[{_SOURCE}] no ConveyorNode under {seg_path}")


def _make_segment_kinematic(stage, seg_path: str) -> None:
    """Mark the segment's RigidBodyAPI kinematic.

    Needed so cube impacts don't tilt the loop (v4 Task 9 finding). The
    RigidBodyAPI is auto-applied by CreateConveyorBelt.
    """
    from pxr import Sdf, UsdPhysics

    seg_prim = stage.GetPrimAtPath(Sdf.Path(seg_path))
    if not seg_prim.IsValid():
        return

    # CreateConveyorBelt applies RigidBody to each ConveyorNode-bearing prim
    # (typically segment-local mesh prims, not the segment xform). Walk and
    # apply kinematic to every RigidBodyAPI we find.
    n_kin = 0
    for prim in _walk_descendants(seg_prim, include_self=True):
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            rb = UsdPhysics.RigidBodyAPI(prim)
            rb.CreateKinematicEnabledAttr().Set(True)
            n_kin += 1
    if n_kin == 0:
        # Fallback — apply RigidBodyAPI + kinematic to segment xform itself.
        rb = UsdPhysics.RigidBodyAPI.Apply(seg_prim)
        rb.CreateKinematicEnabledAttr().Set(True)


def _add_surface_collision_plane(stage, seg_path: str) -> None:
    """Add invisible thin collision plane on top of the belt.

    DEAD CODE in v5 round-2 (BELT chain has flat mesh, no roller gaps).
    Kept for future ROLLER/DUAL usage — call site removed in build_track_loop.
    """
    from pxr import Gf, Sdf, UsdGeom, UsdPhysics

    seg_prim = stage.GetPrimAtPath(Sdf.Path(seg_path))
    if not seg_prim.IsValid():
        return

    # Compute local AABB of the segment (using BBoxCache in default purpose).
    bbox_cache = UsdGeom.BBoxCache(0.0, [UsdGeom.Tokens.default_])
    bbox = bbox_cache.ComputeWorldBound(seg_prim).ComputeAlignedRange()
    if bbox.IsEmpty():
        carb.log_warn(f"[{_SOURCE}] cannot compute AABB for {seg_path}")
        return

    # World AABB → derive local extents (segment may be rotated).
    # For the surface plane we use a single thin Cube sized to the local
    # bbox of the visible mesh in segment-local space.
    bbox_local = bbox_cache.ComputeLocalBound(seg_prim).ComputeAlignedRange()
    if bbox_local.IsEmpty():
        bbox_local = bbox  # fallback

    lmin = bbox_local.GetMin()
    lmax = bbox_local.GetMax()
    sx = float(lmax[0] - lmin[0])
    sy = float(lmax[1] - lmin[1])
    # Belt running surface ≈ lower 30% of segment height (handrail occupies
    # the upper ~70%). Same heuristic as _measure_belt_top_z for spawn z.
    z_low = float(lmin[2])
    z_high = float(lmax[2])
    belt_top_local = z_low + (z_high - z_low) * 0.30

    surf_path = f"{seg_path}/SurfaceCollisionPlane"
    if stage.GetPrimAtPath(Sdf.Path(surf_path)).IsValid():
        return  # already added

    surf = UsdGeom.Cube.Define(stage, Sdf.Path(surf_path))
    surf.CreateSizeAttr(1.0)
    xform = UsdGeom.Xformable(surf)
    xform.ClearXformOpOrder()
    cx = 0.5 * float(lmin[0] + lmax[0])
    cy = 0.5 * float(lmin[1] + lmax[1])
    xform.AddTranslateOp().Set(Gf.Vec3d(cx, cy, belt_top_local + 0.005))
    # Slightly wider than belt visible width so cubes can't slip off the
    # corner curve outer edge.
    xform.AddScaleOp().Set(Gf.Vec3f(sx * 0.95, sy * 0.95, 0.01))
    surf.GetPurposeAttr().Set(UsdGeom.Tokens.guide)  # invisible
    UsdPhysics.CollisionAPI.Apply(surf.GetPrim())
    rb = UsdPhysics.RigidBodyAPI.Apply(surf.GetPrim())
    rb.CreateKinematicEnabledAttr().Set(True)


# ---------------------------------------------------------------------------
# Geometry measurement
# ---------------------------------------------------------------------------


def _measure_loop_geometry(stage, paths: list[str]) -> TrackLoopResult:
    """Compute world AABB of the full loop + per-segment centers.

    Per-segment z is the **belt mesh** top (not the handrail), measured
    from the segment's "Belt" / "Rollers" sub-prim — so cube spawn lands
    on the actual roller surface, not 1.5m above on the rail top.
    Inner AABB heuristic: shrink overall AABB by the average segment
    radial extent (rough estimate of belt width).
    """
    from pxr import Sdf, UsdGeom

    bbox_cache = UsdGeom.BBoxCache(0.0, [UsdGeom.Tokens.default_])

    seg_centers: list[tuple[float, float, float]] = []
    seg_aabbs: list[tuple] = []  # (min, max) per segment

    overall_min = [float("inf")] * 3
    overall_max = [float("-inf")] * 3

    for seg_path in paths:
        prim = stage.GetPrimAtPath(Sdf.Path(seg_path))
        if not prim.IsValid():
            continue
        bbox = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if bbox.IsEmpty():
            continue
        bmin = bbox.GetMin()
        bmax = bbox.GetMax()
        seg_aabbs.append(((float(bmin[0]), float(bmin[1]), float(bmin[2])),
                          (float(bmax[0]), float(bmax[1]), float(bmax[2]))))
        belt_top_z = _measure_belt_top_z(stage, prim, bbox_cache)
        seg_centers.append((
            0.5 * float(bmin[0] + bmax[0]),
            0.5 * float(bmin[1] + bmax[1]),
            belt_top_z,
        ))
        for i in range(3):
            overall_min[i] = min(overall_min[i], float(bmin[i]))
            overall_max[i] = max(overall_max[i], float(bmax[i]))

    straight_centers = [seg_centers[i] for i in STRAIGHT_INDICES if i < len(seg_centers)]
    curve_centers = [seg_centers[i] for i in CURVE_INDICES if i < len(seg_centers)]

    # Inner AABB — shrink overall AABB by belt width estimate (max of XY
    # extents of any single segment's local bbox, halved).
    inset = _estimate_belt_width(seg_aabbs) * 1.1  # +10% margin
    inner_min = (overall_min[0] + inset, overall_min[1] + inset, overall_min[2])
    inner_max = (overall_max[0] - inset, overall_max[1] - inset, overall_max[2])

    return TrackLoopResult(
        paths=paths,
        straight_centers=straight_centers,
        curve_centers=curve_centers,
        aabb_min=tuple(overall_min),
        aabb_max=tuple(overall_max),
        inner_aabb_min=inner_min,
        inner_aabb_max=inner_max,
    )


def _lower_loop_to_target_belt_z(stage, paths: list[str],
                                  target_belt_top_z: float) -> None:
    """Translate LOOP_ROOT so the belt surface sits at ``target_belt_top_z``.

    Reads the first segment's ``/Belt`` sub-prim translate.z (NVIDIA puts
    the cube-rest surface there), computes the offset needed to land it
    at ``target_belt_top_z``, and applies that offset as a translate on
    the LOOP_ROOT Xform. All segments inherit the offset.

    v5 round-5: this is the canonical placement (replaces _snap_loop_to_ground).
    Belt top at industrial-standard 0.40 m so a ground-mount Franka Panda
    (reach 0.855 m sphere from z=0) can intersect cubes resting on the belt
    when REACH_OFFSET ≈ 0.72 m. Side-effect: native conveyor legs end up
    below ground (visible R6 warning, demoted to soft).
    """
    from pxr import Gf, Sdf, UsdGeom

    if not paths:
        return
    belt_prim = stage.GetPrimAtPath(Sdf.Path(paths[0] + "/Belt"))
    if not belt_prim.IsValid():
        carb.log_warn(f"[{_SOURCE}] no /Belt sub-prim under {paths[0]}; skip lower")
        return
    attr = belt_prim.GetAttribute("xformOp:translate")
    if not attr.IsValid() or attr.Get() is None:
        return
    current_belt_z = float(attr.Get()[2])
    z_offset = target_belt_top_z - current_belt_z

    loop_prim = stage.GetPrimAtPath(Sdf.Path(LOOP_ROOT))
    if not loop_prim.IsValid():
        return
    xform = UsdGeom.Xformable(loop_prim)
    # Reuse existing translate op if any (avoid duplicate xformOp:translate).
    translate_op = None
    for op in xform.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            translate_op = op
            break
    if translate_op is None:
        translate_op = xform.AddTranslateOp()
    translate_op.Set(Gf.Vec3d(0.0, 0.0, z_offset))
    carb.log_info(
        f"[{_SOURCE}] lowered LOOP_ROOT by {z_offset:.3f} m "
        f"(belt was at {current_belt_z:.3f} m → target {target_belt_top_z:.3f} m)"
    )


def _measure_belt_top_z(stage, seg_prim, bbox_cache) -> float:
    """Belt running surface WORLD z (where cubes rest), from the Belt sub-prim.

    BELT-style segments (A06 / A15 / etc.) put the conveyable surface in a
    dedicated ``Belt`` Xform child. We use ``ComputeLocalToWorldTransform``
    to capture the LOOP_ROOT lowering applied by ``_lower_loop_to_target_belt_z``
    (and any anchor-chain offsets).

    Falls back to segment AABB lower-30% heuristic only if the Belt
    sub-prim is missing (ROLLER-only segments).
    """
    from pxr import Sdf, UsdGeom

    belt_prim = stage.GetPrimAtPath(Sdf.Path(str(seg_prim.GetPath()) + "/Belt"))
    if belt_prim.IsValid():
        belt_xform = UsdGeom.Xformable(belt_prim)
        m = belt_xform.ComputeLocalToWorldTransform(0.0)
        return float(m.ExtractTranslation()[2])

    # Fallback: AABB-based heuristic (DUAL/ROLLER segments without /Belt).
    bb = bbox_cache.ComputeWorldBound(seg_prim).ComputeAlignedRange()
    if bb.IsEmpty():
        return 0.5
    z_min = float(bb.GetMin()[2])
    z_max = float(bb.GetMax()[2])
    return z_min + (z_max - z_min) * 0.30


def _estimate_belt_width(seg_aabbs: list[tuple]) -> float:
    """Belt width ≈ shorter horizontal extent of a STRAIGHT segment AABB."""
    if not seg_aabbs:
        return 0.5  # conservative default (50 cm)
    widths = []
    for bmin, bmax in seg_aabbs:
        ex = bmax[0] - bmin[0]
        ey = bmax[1] - bmin[1]
        widths.append(min(ex, ey))
    return float(sum(widths) / len(widths))


def _walk_descendants(prim, include_self: bool = False):
    """Yield every prim under (and optionally including) ``prim``."""
    if include_self:
        yield prim
    for child in prim.GetChildren():
        yield child
        yield from _walk_descendants(child)


# ---------------------------------------------------------------------------
# Module-level state for cleanup
# ---------------------------------------------------------------------------


_LAST_RESULT: Optional[TrackLoopResult] = None


def get_last_result() -> Optional[TrackLoopResult]:
    return _LAST_RESULT


def remember(result: TrackLoopResult) -> None:
    global _LAST_RESULT
    _LAST_RESULT = result


def forget() -> None:
    global _LAST_RESULT
    _LAST_RESULT = None
