<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: scenario YAML 저작 / 검증 작업 시작 전 필수 숙지 -->
# Scenario Validation — Invariants

`scenarios/**/*.yaml` 저작 또는 `scenario_validate` 실행 전 이 파일 Read.
R1/R1a/R2/R3 위반 시 검증 결과는 무효.

## R1. 실제 asset 으로만 검증 (primitive 대용 금지)

- **금지**: primitive (Cube/Sphere 등) 를 의자·로봇·캐릭터 대용으로 사용한 검증
- **허용**: `asset_list` 또는 알려진 S3 경로의 실 USD 만
  - `.../Environments/Office/Props/SM_Armchair.usd`
  - `.../Robots/NVIDIA/NovaCarter/nova_carter.usd`
  - `.../People/Characters/Biped_Setup.usd`
- **SoT 카탈로그** (전체 S3 URL 목록): `docs/assets/isaac/asset_inventory.md` + `docs/assets/isaac/assets/*.md` — scenario 저작 전 후보 asset 선택 진입점

### 이유 (실측 False Positive)

primitive 는 bbox·pivot·forward axis·physics material·mesh topology 특성이 실 asset
과 달라 False Positive 빈발. 예: chair sit 검증에서 Cube 는 통과하지만 실 Armchair
는 NavMesh step-up 실패.

## R1a. NavMesh bake 는 timeline stopped 필수

`navigation_bake` 는 playing 중에 호출 시 `bake=True` 반환하지만 `get_navmesh()`
= None (silent False Positive).

`stage_load_usd` / `robot_load` / `stage_create_prim` / `stage_set_property` /
`viewport_capture(settle_frames)` / `window_capture` 는 모두 timeline advance
시키므로 bake 직전 `simulation_stop` **재호출** 필수.

표준 sequence:
```
load → stop → bake → query_path → play → navigate_path
```

## R2. Robot 동작은 `simulation_play` 에서만

- 예외: `robot_load`
- 필수 playing: `robot_set_joint_positions` / `robot_navigate_to` /
  `robot_navigate_path` / `robot_drive_physics` / `robot_gripper_control` /
  `robot_set_ee_target` 등 움직임·관절·물리 상호작용

이유: PhysX articulation view 는 physics step 이 돌아야 populate. Extension
`robot_service.navigate_path` 는 `omni.timeline.is_playing()` 미통과 시 HTTP 400
거부. scenario 는 `simulation_play` 를 arrange 에 필수 배치.

## R3. Viewport 캡처 시각 검증 의무

`viewport_capture` 후 반드시 `Read` tool 로 PNG 시각 확인.

**흰색/검은색 배경만** 보이거나 asset 이 점처럼 작으면 **실패 처리** — 아래 순서로
조정 후 재캡처:

1. **조명 추가/조정** — scene 에 `DistantLight` 또는 `DomeLight` 가 없으면
   `stage_create_prim(prim_type="DistantLight")` + `stage_set_property(inputs:intensity=3000)`.
   이미 있으면 intensity 2배 증가
2. **카메라 위치/각도 조정** — `stage_set_property("/OmniverseKit_Persp",
   "xformOp:translate", [x,y,z])` 로 asset bbox 기준 거리 재설정 (small asset 은
   1~3 m, large env 는 10~30 m 외부)
3. **Asset 위치 조정** — bounding box 를 참조하여 asset 중심이 viewport 정면이 되게
   asset 자체 또는 camera target 재배치
4. 조정 후 `viewport_capture` 재호출 + Read 재검증. 이 cycle 은 geometry 가 명확히
   보일 때까지 반복 — 2-3 회 시도 후에도 실패면 `docs/implementation_issues.md` 에 기록

## Character 표준 sequence (T-pose 방지)

`stage_load_usd` 로 character USD 를 raw reference 로드하면 AnimationGraph 미bind →
simulation_play 시 T-pose 유지. **반드시 `character_load`** (auto Biped rig bind +
`anim_graph_bound=true`).

표준 pattern:
```
character_load(...)
  → simulation_play
  → 1s sleep
  → simulation_pause
  → character_play_animation("Idle")
  → simulation_play
```

후속 호출은 반드시 응답의 `sanitized_prim_path` 사용 (F_Business_02 등 skin variant 는
`/World/Characters/{name}` 로 자동 이동).

## Scenario cleanup (kit.exe shutdown hang 방지)

scenario cleanup 은 `simulation_play → simulation_stop` (최종 physics tick) 을
`kit_app_stop` 이전에 반드시 실행. 생략 시 AnimGraph / NavMesh 내부 핸들 정리
타이밍 문제로 kit.exe 셔다운 hang. canonical pattern:
`scenarios/smoke/character_control.yaml`

## 관련 경계

- Scenario YAML 저작 가이드: `scenarios/CLAUDE.md`
- Scenario 엔진 (Arrange/Act/Assert/Cleanup, action_registry): `src/omniverse_kit_mcp/scenario/CLAUDE.md`
- Asset URL 카탈로그 진입점: `docs/assets/isaac/asset_inventory.md`
- Character domain constraints (실측): `src/omniverse_kit_mcp/modules/CLAUDE.md`
- USD 로드 4 조건: `docs/invariants/usd-load.md`
- Issue / 개선 항목 누적: `docs/implementation_issues.md`
