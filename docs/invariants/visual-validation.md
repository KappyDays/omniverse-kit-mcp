<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: viewport_capture / scene build / NVIDIA asset 사용 작업 시작 전 필수 -->
# Visual Validation — Invariants

`viewport_capture` 한 PNG 만으로 layout 정상성을 판단하려면 다음 5개
규칙 준수. 위반 시 사용자 시각 검증에서 즉발 (예: v5 round-1 의 "2층
belt", "Franka belt 통과", "ground 붙은 컨베이어").

## 검증 타이밍 — 일괄 검증 + 인라인 stats (2026-05-26)

(루트 CLAUDE.md Validation Rule R3 = "capture 후 Read 시각 검증 의무" 의 실행 워크플로.)

- **인라인 (구현 중)**: `viewport_capture(return_stats=true)` 의 `pixel_mean`/`pixel_variance`
  자동판정만 사용 — `pixel_mean` 채널 평균이 임계(예: < 8.0) 이하이거나 variance ≈ 0 이면
  black/미갱신 의심. **이때만** `Read` 로 실제 확인. 매 변경마다 Read 하지 말 것.
- **일괄 (기능 완료 후)**: 모든 기능 구현이 끝난 뒤 마지막에 `viewport_capture` → `Read` 시각
  검증을 일괄 수행.
- cold RTX 첫 프레임이 검으면 `viewport_capture(warmup_frames=N)`(예: 8) 또는
  `simulation_play` 로 연속 렌더 강제.
- **라이브 카메라 프레이밍**: `viewport_set_camera_lookat(eye, target, up)` — Perspective 포함
  active 카메라를 deadlock-safe(USD xformOp author, REST 경로) 로 이동. build_scene rebuild 불필요.

## R1 — Ground = Grid (NVIDIA Flat Grid 사용)

Plain solid-color ground (회색 add_ground_plane) **금지**. 사용자가
belt / cube / robot 위치를 한눈에 측량 못 함 (belt 와 ground 모두 회색).

✅ **사용**: NVIDIA Flat Grid environment
```python
GRID_USD_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Environments/Grid/default_environment.usd"
)
ground_prim = stage.DefinePrim(GROUND_PATH, "Xform")
ground_prim.GetReferences().AddReference(GRID_USD_URL)
UsdPhysics.CollisionAPI.Apply(ground_prim)  # cube collision
```

출처: `isaacsim.gui.menu.create_menu` Create → Environments → Flat Grid.

## R2 — 새 NVIDIA asset 사용 전 single-segment sample build 의무

새 asset (예: ConveyorBelt_A06, Franka, KLT) 처음 사용 시:
1. **1개만** build (chain 전, 다중 robot 전)
2. `viewport_capture` 2장: top-down + 45° tilt
3. `Read` tool 시각 확인 항목:
   - Smooth / rough / transparent (style 의도 부합?)
   - **단일 layer 또는 다층** (DUAL/ROLLER 같은 NVIDIA 산업 외관 자산은 2층)
   - Mesh local origin 위치 (handrail 포함 bias?)
   - Belt 표면 z (cube spawn 좌표 기준)

이 단계 없이 8-chain 진행하면 사용자 시각 검증에서 "2층 belt" 같은
즉발. v5 round-1 (A04 DUAL chain) 사례.

## R3 — Robot reach vs asset geometry 사전 계산

새 robot ↔ 새 asset 조합 layout 결정 전, 종이 위 계산:

| 변수 | 측정 (Franka Panda + ConveyorBelt_A06) |
|------|------|
| Robot reach radius | URDF / spec (0.855 m sphere from base) |
| Robot base footprint radius | panda_link0 AABB (≈ 0.115 m radius) |
| Robot arm-raised half-width | default-pose AABB (≈ 0.55 m, used for layout_check soft warn) |
| Asset target surface z | Belt sub-prim world z |
| Asset half-width (belt + handrail) | segment AABB (0.55 m for A06) |

3D reach 체크 (ground-mount robot, base z=0):

```
horizontal_max = √(reach² − (cube_z − base_z)²)
              = √(0.855² − 0.40² − 0.025²) ≈ 0.741 m  (cube on belt at z=0.40m)
```

Mesh-clearance 체크 (base 가 belt edge 안 부딪히도록):

```
REACH_OFFSET_min = belt_half + base_radius + clearance
                 = 0.55 + 0.115 + 0.055 ≈ 0.72 m
```

두 budget 동시 만족: REACH_OFFSET ≈ 0.72 m, belt_top_z ≈ 0.40 m. 어느 한 쪽
미달 시 robot stand 추가 또는 belt z lower (ConveyorLoop translate.z).
v5 round-4 (belt_top_z=0.85 m + REACH_OFFSET=0.85 m) 는 양쪽 모두 위반 → rate=0%.

## R4 — Ground / belt height = 산업 standard

Belt top z = 0.40 ~ 0.70 m (산업 standard "허리 높이"). 0.05 m 이하는
"ground 붙음" 시각, robot stand 없이는 reach 안 닿음. 1.0 m 이상은
ground-mount Franka EE saturate 가능.

NVIDIA ConveyorBelt 자산 native handrail + 다리 → ground_snap 만 적용 시
belt top z ≈ 0.85 m (다리 길이) → ground-mount Franka 안 닿음 (round-4 rate=0%).
v5 round-5 결정: `track_loop_builder._lower_loop_to_target_belt_z(target=0.40)`
로 LOOP_ROOT 추가 lowering. 다리가 ground 아래로 내려가는 시각 손실은 감수
(`check_ground_penetration` warning 예상). robot stand 추가는 layout 복잡도
증가하므로 보류.

## R6 — Ground anchor: BBoxCache로 bottom 측정, z=0 hardcode 금지

USD prim 의 `xformOp:translate` 는 prim **pivot** 위치만 지정. Pivot 이
asset 어디 있는지는 USD 마다 다름:

| Asset | Pivot |
|-------|-------|
| Franka Panda (URDF 변환) | base bottom (mount) → z=0 OK |
| KLT_Bin small | bin geometry **center** → z=0 면 절반 파묻힘 |
| ConveyorBelt | belt + handrail mesh AABB **center** → z=0 면 다리가 ground 뚫음 |

→ **z=0 으로 모든 asset 두면 안 됨.** 표준 패턴:

```python
from omni.userext.pickplace import ground_snap

# Asset USD load 후
ground_snap.place_on_ground(prim, ground_z=0.0)
# 내부: BBoxCache 측정 → pivot offset 계산 → translate.z 자동 set
# bottom = ground_z 보장
```

**Build 후 의무 검증** (build_layout_check 자동):
```python
layout_check.check_ground_penetration(
    prim_paths=[...all asset paths...],
    ground_z=0.0,
)  # bottom < -0.01 → warning, < -0.10 → error
```

## R5 — 시각 검증이 ground truth, dump_state 는 보조

`stage_capture_snapshot` 의 좌표값은 충돌 / intersection 검출 못함
(BBoxCache 가 anchor-chain transform 미반영). 시각 capture 가 최종 판단:

- ✅ `viewport_capture` + `Read` PNG → 모양 / scale / collision 판단
- ⚠️ dump_state.json → 좌표 값 보조, 시각 보조 후순위

이번 세션 v5 round-1 사례: dump 좌표는 OK 같았으나 시각상 Franka 가 belt
mesh 통과. 사용자 시각 검증에서 catch.

## 관련 경계

- Retired conveyor workshop observations are historical; current visual
  validation rules in this document are the SoT.
