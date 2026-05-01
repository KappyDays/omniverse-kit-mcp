<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: viewport_capture / scene build / NVIDIA asset 사용 작업 시작 전 필수 -->
# Visual Validation — Invariants

`viewport_capture` 한 PNG 만으로 layout 정상성을 판단하려면 다음 5개
규칙 준수. 위반 시 사용자 시각 검증에서 즉발 (예: v5 round-1 의 "2층
belt", "Franka belt 통과", "ground 붙은 컨베이어").

## R1 — Ground = Grid (NVIDIA Flat Grid 사용)

Plain solid-color ground (회색 add_ground_plane) **금지**. 사용자가
belt / cube / robot 위치를 한눈에 측량 못 함 (belt 와 ground 모두 회색).

✅ **사용**: NVIDIA Flat Grid environment
```python
GRID_USD_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Grid/default_environment.usd"
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

| 변수 | 측정 |
|------|------|
| Robot reach radius | URDF / spec (Franka Panda = 0.855 m) |
| Robot footprint half-width | base link AABB (Franka ≈ 0.30 m) |
| Asset target surface z | Belt sub-prim translate.z (NVIDIA conveyor) |
| Asset half-width | segment AABB (handrail 포함, 0.55 m for A06) |

체크: `(robot - asset_target_xy 거리) ≤ reach_radius - clearance` ?
미달 시 robot stand 추가 또는 asset 위치 lower (ConveyorLoop translate.z).

## R4 — Ground / belt height = 산업 standard

Belt top z = 0.40 ~ 0.70 m (산업 standard "허리 높이"). 0.05 m 이하는
"ground 붙음" 시각, robot stand 없이는 reach 안 닿음. 1.0 m 이상은
ground-mount Franka EE saturate 가능.

NVIDIA ConveyorBelt 자산은 native belt top z=1.76 m (handrail + 다리).
LOOP_ROOT translate.z = -1.36 으로 내려서 belt top = 0.40 m 권장.

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

- 코드 위치: `isaac-pick-place/extension/omni.userext.pickplace/omni/userext/pickplace/scene_builder.py`
- 이번 프로젝트 conveyor 카탈로그: `isaac-pick-place/docs/conveyor-catalog.md`
- BBoxCache 정확성 한계: `isaac-pick-place/extension/omni.userext.pickplace/omni/userext/pickplace/layout_check.py` 모듈 docstring
