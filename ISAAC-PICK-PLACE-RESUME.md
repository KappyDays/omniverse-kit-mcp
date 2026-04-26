# Isaac Pick-Place 워크샵 — 새 세션 인계 프롬프트

> 새 세션에서 이 파일을 그대로 붙여넣고 시작. 자율 진행 + 질문 금지 정책 유지.

---

## 핵심 미션

`isaac-pick-place` 브랜치에서 작업한 Pick-and-Place Workshop Extension 의
**미달성 부분 (cube 가 box 에 들어가는 end-to-end)** 을 완성하라.

지금까지 UI 동작 / scene build / cube spawn / belt drive / robot motion 까지는
검증됨. 단 PhysX gripper 가 실제 cube 를 잡아 box 안에 넣는 동작이 안정 작동 안 함
(직전 검증 결과 box 안 cube 0/29).

## 시작 즉시 read 할 것 (순서대로)

1. `isaac-pick-place/VALIDATION_REPORT.md` — 8 단계 시도한 fix + root cause + 미시도 영역 정리
2. `isaac-pick-place/plan.md` — 원래 설계 (좌표/state machine 등)
3. `isaac-pick-place/extension/omni.userext.pickplace/omni/userext/pickplace/pickplace_controller.py` — 현재 NVIDIA stack 사용 코드
4. `isaac-pick-place/extension/omni.userext.pickplace/omni/userext/pickplace/scene_builder.py` — scene + lights/camera + hollow box
5. `isaac-pick-place/extension/omni.userext.pickplace/omni/userext/pickplace/cube_spawner.py` — 4 segment random spawn
6. `docs/invariants/usd-load.md` — USD load 4 조건
7. `docs/invariants/ext-reload.md` — Extension reload 패턴
8. `docs/invariants/ui-invoke.md` — UI automation 시퀀스

## 환경 검증 (첫 1분)

```bash
# 브랜치 확인 (반드시 isaac-pick-place 위에서 작업)
git branch --show-current   # → isaac-pick-place

# Extension code SoT 확인
ls isaac-pick-place/extension/omni.userext.pickplace/omni/userext/pickplace/

# Kit 가 인식하는 경로 (Junction)
ls -la isaac_extension/omni.userext.pickplace
```

Junction 이 끊어져 있으면 (Windows directory junction 은 git checkout 시
종종 사라짐) PowerShell 로 재생성:

```powershell
New-Item -ItemType Junction `
  -Path "C:\Users\<you>\workspace\Isaac-sim-MCP\isaac_extension\omni.userext.pickplace" `
  -Target "C:\Users\<you>\workspace\Isaac-sim-MCP\isaac-pick-place\extension\omni.userext.pickplace"
```

## 검증 기준 (성공 정의)

`stage_capture_snapshot` 으로 모든 cube 의 `xformOp:translate` 추출 후 영역별
분류:

```python
# Box A: x∈[-0.62, -0.28], y∈[0.40, 0.70], z∈[0.00, 0.20]
# Box B: x∈[0.28, 0.62], y∈[-0.70, -0.40], z∈[0.00, 0.20]
```

**성공**: 90 초 simulation 후 `In Box A + In Box B ≥ 5개`. 이 조건 충족 시
end-to-end 작동 입증.

직전 검증 결과 (실패 baseline):
```
Total cubes: 29
In Box A: 0
In Box B: 0
On belt:   26
```

## 시도해야 할 fix (직전 보고서가 정직히 명시한 미시도 영역, 우선순위 순)

### F1. Franka articulation drive stiffness/damping 강화 (필수, 가장 효과 큼)

NVIDIA `Franka` 의 default joint drive 가 belt-위 cube + base offset 환경에서
부족. RMPFlow 가 IK 계산해도 PD 가 못 따라감 → EE 가 events_dt 시간 안에 cube
도달 못함.

`pickplace_controller.py::FrankaPicker.try_initialize` 에서 `franka.post_reset()`
직후 모든 arm joint drive 를 명시 보강:

```python
# 의사 코드 — 정확 API 는 isaacsim 5.1 docs 확인
import omni.usd
from pxr import UsdPhysics
stage = omni.usd.get_context().get_stage()
for jname in ["panda_joint1", ..., "panda_joint7"]:
    joint_path = f"{self.prim_path}/panda_link.../{jname}"  # 정확 경로
    drive = UsdPhysics.DriveAPI.Apply(stage.GetPrimAtPath(joint_path), "angular")
    drive.CreateStiffnessAttr(10000.0)  # default ~600
    drive.CreateDampingAttr(200.0)
```

또는 `articulation_controller.set_gains(kps, kds)` 가 NVIDIA 의 표준 — 이쪽이
더 simple. `isaacsim.core.api.controllers.ArticulationController` 참조.

### F2. Cube + finger 에 high-friction physics material

`cube_spawner.py` 에서 cube 생성 시 friction material 명시:

```python
# /World/Looks/CubeMaterial 에 다음 적용
# physics:dynamicFriction = 2.0
# physics:staticFriction  = 2.0
# physics:restitution     = 0.0
prim.CreateRelationship("material:binding:physics", custom=False) \
    .SetTargets([Sdf.Path("/World/Looks/CubeMaterial")])
```

`scene_builder.py::_ensure_belt_material` 패턴 참조 (이미 belt 에는 적용됨,
cube 에는 미적용).

### F3. Cube size 5cm → 4cm

ParallelGripper 의 finger gap (open=5cm, close=0cm) 와 cube 5cm 가 거의 같아서
1-2cm 어긋나면 finger 가 cube 옆을 밀어냄. 4cm 로 줄여 여유 확보.

`cube_spawner.py::CUBE_SIZE = 0.04`. SPAWN_Z 도 그에 따라 belt top 위치
재계산 (현재 belt top z=0.4, cube center z = 0.4 + 0.04/2 = 0.42).

### F4. NVIDIA `events_dt` 더 늘림

각 phase 시간 2 배. RMPFlow PD 가 충분한 ticks 동안 target 까지 수렴할 시간 확보:

```python
# pickplace_controller.py::FrankaPicker.try_initialize
events_dt = [0.002, 0.001, 0.05, 0.025, 0.01, 0.01, 0.0005, 0.5, 0.002, 0.02]
```

### F5. `end_effector_offset` 으로 EE target 미세 보정

`controller.forward(... end_effector_offset=np.array([0, 0, -0.02]))` —
panda_rightfinger origin 보다 cube 가 ~2cm 아래에 위치하도록 보정.

### F6. (최후 수단) `SurfaceGripper` 로 ParallelGripper 대체

`isaacsim.robot.surface_gripper.SurfaceGripper` — suction 기반 grasp. Friction
무관, finger collision 정확도 무관. NVIDIA Franka 의 `_gripper` 를 SurfaceGripper
로 교체 + EE prim_path 도 panda_hand 로 변경.

이건 cube 가 가까이 오기만 하면 무조건 잡힘. 사용자 요구 "물리 속성에 따라"
완전히 만족 안 할 수도 있으나 확실히 작동.

## 작업 순서 (recommended)

1. invariant 문서 + VALIDATION_REPORT.md 모두 read
2. F1 + F2 + F3 + F4 **동시 적용** (각 fix 가 독립적이라 합쳐 효과 측정)
3. `isaac_sim_restart` + `extension_activate(reload=True)` (코드 변경 반영)
4. `window_ui_show("Pick & Place Workshop")` + Build Scene click
5. 약 60-90 초 wait (Franka USD 다운로드 + scene build)
6. Start Simulation click + 90 초 wait
7. `stage_capture_snapshot` + python 분석 — Box A/B cube 카운트
8. 성공 시 `viewport_capture` + `window_capture` 캡쳐 → `isaac-pick-place/captures/06-end-to-end/`
9. 실패 시 F5 (offset) 추가 + 재검증
10. 또 실패 시 F6 (SurfaceGripper) 적용
11. 성공 후 `VALIDATION_REPORT.md` 갱신 + git commit

## 정책 (사용자 명시 — 변경 없음)

1. **자율 진행 + 질문 금지** — "완전하게 개발되고 검증 및 테스트까지 완료된 결과물만 원해"
2. **참고 금지** — 프로젝트 내 유사 구현 (`isaac_extension/omni.mycompany.conveyor_pick/` 등 Phase B 작업) 일체 보지 마라
3. **NVIDIA official extension 적극 활용** — `isaacsim.robot.manipulators.examples.franka` (Franka, PickPlaceController, RMPFlowController, ParallelGripper) — "유사 구현" 이 아닌 표준 컴포넌트 사용
4. **UI 직접 조작 검증** — MCP `extension_ui_invoke` 로 5 버튼 모두 click 으로 검증
5. **dual capture** — app 전체 + viewport 2장
6. **isaac-pick-place 폴더에 작업물 모음**
7. **kit-sdk-pitfalls + USD invariant** 문서 무조건 따름

## 환경 detail

| 항목 | 값 |
|------|---|
| 브랜치 | `isaac-pick-place` |
| Extension code SoT | `isaac-pick-place/extension/omni.userext.pickplace/` |
| Kit 인식 경로 | `isaac_extension/omni.userext.pickplace` (Junction) |
| Franka USD | `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd` |
| Belt 속도 | 0.02 m/s (4 segment 시계방향) |
| Robot 위치 | A: (-0.45, 0, 0), B: (+0.45, 0, 0) yaw 180° |
| Box 위치 | A: (-0.45, +0.55, 0.05), B: (+0.45, -0.55, 0.05). hollow 5-panel container |
| Cube spawn | 4 belt segment 위 random, mass 0.05 kg |
| Stage units | meters, Z up |

## 직전 commit 히스토리

```
1ddb389 fix(pickplace): NVIDIA PickPlaceController + 8-step tuning (grasp 미완 정직 보고)
4b07932 feat(isaac-pick-place): O자 컨베이어 + 듀얼 Franka pick&place 워크샵 extension
```

## 첫 응답 가이드

이 프롬프트와 `isaac-pick-place/VALIDATION_REPORT.md` 를 모두 read 한 후
진행 계획을 짧게 (3-5 줄) 알리고 즉시 작업 시작. 자율 진행 + 검증까지
end-to-end 책임.

성공 조건 (`Box A + Box B ≥ 5 cubes`) 을 명확히 머리에 두고 진행하라.
NVIDIA controller 의 cycle 카운터 (`pick=N, place=N`) 는 시간 기반으로 누적되니
**물리적 cube 위치만이 진실** 이다.
