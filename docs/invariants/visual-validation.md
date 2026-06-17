<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: viewport_capture / scene build / NVIDIA asset required before starting work -->
# Visual Validation — Invariants

`viewport_capture` To determine layout normality with only one PNG, follow the 5 steps:
Follow the rules. In case of violation, immediate action is taken from user visual verification (e.g. “2nd floor” in v5 round-1)
belt", "Passing Franka belt", "Conveyor attached to the ground").

## Verification timing — batch verification + inline stats (2026-05-26)

(Execution workflow of root CLAUDE.md Validation Rule R3 = "Read visual verification obligation after capture".)

- **Inline (implementing)**: `pixel_mean`/`pixel_variance` in `viewport_capture(return_stats=true)`
  Use automatic judgment only — `pixel_mean` If the channel average is below a threshold (e.g. < 8.0) or variance ≈ 0
  black/suspicious of non-renewal. **Only this time** Actual confirmation with `Read`. Do not read for every change.
- **Batch (after function completion)**: After all function implementation is completed, at the end at time `viewport_capture` → `Read`
  Perform verification in batches.
- If cold RTX first frame is black, then `viewport_capture(warmup_frames=N)` (e.g. 8) or
  Force continuous render with `simulation_play`.
- **Live Camera Framing**: `viewport_set_camera_lookat(eye, target, up)` — with Perspective
  Move the active camera to deadlock-safe (USD xformOp author, REST path). No build_scene rebuild required.

## Acceptance capture after live MCP stage work

Any MCP task that changes the user-visible Stage state must finish with visual
acceptance, not only prim/API assertions:

1. Frame the requested result with `viewport_frame_prims` or camera look-at.
2. Capture with `viewport_capture(return_stats=true, warmup_frames>0)`.
3. Reject blank/flat frames using pixel stats before claiming completion.
4. Read the PNG and verify the user-requested state is actually visible.
5. If occluded, too small, off-camera, or visually wrong, adjust the Stage/camera
   and repeat capture before final reporting.

Prim existence, bbox, and successful MCP return values are auxiliary evidence.
They do not replace the final visual acceptance image.

## R1 — Ground = Grid (using NVIDIA Flat Grid)

Plain solid-color ground (gray add_ground_plane) **Prohibited**. user
Belt / cube / robot location cannot be measured at a glance (both belt and ground are gray).

✅ **Use**: NVIDIA Flat Grid environment
```python
GRID_USD_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Environments/Grid/default_environment.usd"
)
ground_prim = stage.DefinePrim(GROUND_PATH, "Xform")
ground_prim.GetReferences().AddReference(GRID_USD_URL)
USDPhysics.CollisionAPI.Apply(ground_prim)  # cube collision
```

Source: `isaacsim.gui.menu.create_menu` Create → Environments → Flat Grid.

## R2 — Single-segment sample build required before using new NVIDIA assets

When using a new asset (e.g. ConveyorBelt_A06, Franka, KLT) for the first time:
1. **Only 1** build (before chain, before multiple robots)
2. `viewport_capture` Chapter 2: top-down + 45° tilt
3. `Read` tool visual confirmation items:
   - Smooth / rough / transparent (style meets intent?)
   - **Single layer or multi-layer** (2 layers for NVIDIA industrial appearance assets such as DUAL/ROLLER)
   - Mesh local origin location (bias including handrail?)
   - Belt surface z (based on cube spawn coordinates)

If you proceed with 8-chain without this step, you will see something like “2nd floor belt” in user visual verification.
Immediately. v5 round-1 (A04 DUAL chain) case.

## R3 — Robot reach vs asset geometry pre-calculation

Before deciding on the new robot ↔ new asset combination layout, calculate on paper:

| variable | Measure (Franka Panda + ConveyorBelt_A06) |
|------|------|
| Robot reach radius | URDF / spec (0.855 m sphere from base) |
| Robot base footprint radius | panda_link0 AABB (≈ 0.115 m radius) |
| Robot arm-raised half-width | default-pose AABB (≈ 0.55 m, used for layout_check soft warn) |
| Asset target surface z | Belt sub-prim world z |
| Asset half-width (belt + handrail) | segment AABB (0.55 m for A06) |

3D reach check (ground-mount robot, base z=0):

```
horizontal_max = √(reach² − (cube_z − base_z)²)
              = √(0.855² − 0.40² − 0.025²) ≈ 0.741 m  (cube on belt at z=0.40m)
```

Mesh-clearance check (so that the base does not hit the belt edge):

```
REACH_OFFSET_min = belt_half + base_radius + clearance
                 = 0.55 + 0.115 + 0.055 ≈ 0.72 m
```

Both budgets are satisfied simultaneously: REACH_OFFSET ≈ 0.72 m, belt_top_z ≈ 0.40 m. either side
If insufficient, add robot stand or belt z lower (ConveyorLoop translate.z).
v5 round-4 (belt_top_z=0.85 m + REACH_OFFSET=0.85 m) violates both sides → rate=0%.

## R4 — Ground / belt height = industry standard

Belt top z = 0.40 to 0.70 m (industry standard "waist height"). Below 0.05m
At "ground ground" time, cannot be reached without robot stand. Over 1.0m
Ground-mount Franka EE saturate available.

NVIDIA ConveyorBelt asset native handrail + leg → when applying only ground_snap
belt top z ≈ 0.85 m (leg length) → ground-mount Franka does not reach (round-4 rate=0%).
v5 round-5 decision: `track_loop_builder._lower_loop_to_target_belt_z(target=0.40)`
Add LOOP_ROOT by lowering it. Accept the loss of vision when your legs go below the ground.
(`check_ground_penetration` warning expected). Adding a robot stand increases layout complexity.
On hold as it increases.

## R6 — Ground anchor: Measure bottom with BBoxCache, prohibit z=0 hardcode

USD prim's `xformOp:translate` specifies only the prim **pivot** position. Pivot
The location of the asset varies depending on the USD:

| Asset | Pivot |
|-------|-------|
| Franka Panda (URDF conversion) | base bottom (mount) → z=0 OK |
| KLT_Bin small | bin geometry **center** → z=0 side half buried |
| ConveyorBelt | belt + handrail mesh AABB **center** → If z=0, the leg breaks through the ground |

→ **Do not set all assets to z=0.** Standard pattern:

```python
from omni.userext.pickplace import ground_snap

# after loading the asset USD
ground_snap.place_on_ground(prim, ground_z=0.0)
# internally: BBoxCache measures → computes pivot offset → sets translate.z automatically
# bottom = guarantees ground_z
```

**Mandatory verification after build** (build_layout_check automatically):
```python
layout_check.check_ground_penetration(
    prim_paths=[...all asset paths...],
    ground_z=0.0,
)  # bottom < -0.01 → warning, < -0.10 → error
```## R5 — Visual verification is ground truth, dump_state is auxiliaryThe coordinate value of `stage_capture_snapshot` does not detect collision/intersection.
(BBoxCache does not reflect anchor-chain transform). Time capture is the final decision:

- ✅ `viewport_capture` + `Read` PNG → Shape/scale/collision judgment
- ⚠️ dump_state.json → Coordinate value assistance, visual assistance subordinated

This session v5 round-1 example: The dump coordinates seemed OK, but visually Franka was the belt
mesh passed. catch in user visual verification.

## Related Boundaries

- Retired conveyor workshop observations are historical; current visual
  validation rules in this document are the SoT.
