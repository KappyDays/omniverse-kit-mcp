<!-- Parent: ../CLAUDE.md -->
<!-- Scope: YAML 시나리오 저작 가이드 (엔진 내부 지식 불필요) -->

# scenarios — YAML 시나리오 저작

Isaac Sim + Extension 동작을 end-to-end 로 검증하는 YAML 시나리오들. 엔진 내부를 몰라도 이 디렉토리 지침만으로 새 시나리오를 작성할 수 있다.

## ⚠️ 저작 전 필독

- R1/R1a/R2/R3 Validation Rules: `../docs/invariants/scenario-validation.md`
- 도메인별 런타임 함정: `../src/omniverse_kit_mcp/modules/integration-facts.md`
- MCP tool 시그니처: `../src/omniverse_kit_mcp/tools/CLAUDE.md`

## Source of truth

- **스키마**: `schema/scenario.schema.json` — 모든 필드 정의의 원천. MCP tool `scenario_schema()` 로도 조회
- YAML 경로 기준: 환경 변수 `SCENARIOS_DIR` (기본 `scenarios/`). 루트 탈출 경로는 `_resolve_safe_path()` 가 거부

## 디렉토리

```
scenarios/
├── schema/scenario.schema.json        # JSON Schema (SoT)
└── smoke/                             # canonical 예시
    ├── full_pipeline.yaml             # Cube lifecycle (create → move → play/stop → assert → diff → cleanup)
    ├── state_check_property.yaml      # state-check 모드 예시
    ├── trigger_sync_cube.yaml         # Trigger 모드 (Extension 동기화)
    ├── usd_load_robot.yaml            # 로컬 USD 로드 → prim/position 검증
    ├── robot_joint_control.yaml       # Phase B+: asset_list → load → warm-up → joints → navigate → viewport
    └── character_control.yaml         # Character load → play → navigate → cleanup (shutdown hang 방지 canonical)
```

`full_pipeline.yaml` 은 stage WRITE + timeline + diff_snapshots 를 한 번에 다루므로 새 시나리오 작성 시 참조하기 좋다.

## YAML 구조

```yaml
apiVersion: isaacsim.validation/v1
kind: Scenario
metadata:
  id: <scenario_id>
  name: <display name>
  tags: [<tag>, ...]

spec:
  defaults: { stepTimeoutSeconds: 60, failFast: true }
  variables: { prim_path: "/World/Cube" }
  arrange: [<step>, ...]
  act: [<step>, ...]
  assert:
    - id: cube_position
      module: stage
      action: assert_property
      args:
        prim_path: ${variables.prim_path}
        property_name: xformOp:translate
        comparator: approx
        expected_value: [1.0, 2.0, 3.0]
        tolerance: 0.001
  cleanup: [<step>, ...]
```

- `module` enum: `{stage, viewport, lakehouse, extension, simulation, robot, job, asset, character}` (9)
- `action` 매핑 규약: `../src/omniverse_kit_mcp/scenario/CLAUDE.md` 의 action_registry
- `args` 스키마: `schema/scenario.schema.json` 의 action 별 정의
- **Cleanup 은 assert 실패 여부와 무관하게 항상 실행** (finally)

## 모듈별 액션 가이드

| module | 역할 | 상세 |
|--------|------|------|
| `stage` | READ / ASSERT / DIFF (capture_snapshot, assert_*, diff_snapshots) | context-aware diff → 하단 |
| `simulation` | WRITE + timeline (stage_load_usd, create/set/delete_prim, play/pause/stop, stage_save/open/new) | **Stage WRITE 는 simulation 라우팅** (StageModule 아님) |
| `viewport` | capture / compare_ssim / set_active_camera | GUI 모드 필요 |
| `robot` / `character` | 도메인 tool (load / navigate / joints / play_animation 등) | R2 (playing 필수) + 자세한 caveat: `../src/omniverse_kit_mcp/tools/CLAUDE.md` |
| `asset` / `extension` / `job` / `lakehouse` | list / trigger / status / query | `lakehouse` 는 query only |

**GUI 동등 tool**: File menu (`stage_save/open/new`), Stage 패널 (`stage_get/set_selection`), Viewport 툴바 (`viewport_set_active_camera`). `stage_create_prim(prim_type=...)` 은 Cube/Sphere 외 Camera / DistantLight / DomeLight / SphereLight / RectLight 도 수용.

## Character scenario — YAML 저작 특화

BehaviorAgent/IRA / NavMesh / shutdown hang 상세는 `../src/omniverse_kit_mcp/modules/CLAUDE.md §"Character domain constraints"` + `../docs/invariants/scenario-validation.md §"Character 표준 sequence"`. YAML 관점 체크리스트:

1. **navigate_to 전후**: R2 (playing 필수). 순서: `play → navigate → job.status → pause`
2. **Viewport capture**: 6.0 character skin 은 자체 lighting/camera 를 보장하지 않음 → arrange 에 `DomeLight` + `viewport_set_active_camera("/OmniverseKit_Persp")`. 연속 호출 재캐시 회피는 사이 `simulation_play` 로 frame advance
3. **캐릭터 선택**: `asset_list(category="people")` 로 탐색. DH UUID 이름은 `character_load` 의 `_sanitize_prim_name` 자동 적용 → 후속 step 은 response `sanitized_prim_path` 기준
4. **Cleanup**: `simulation_play → simulation_stop` (최종 physics tick) 을 `kit_app_stop` 이전에 실행 — shutdown hang 방지

## Context-aware action: `stage.diff_snapshots`

선행 두 `capture_snapshot` step 결과를 ctx 에서 pull 해 diff 계산:

```yaml
- id: diff_move
  module: stage
  action: diff_snapshots
  args:
    before_step_id: snapshot_before_move   # 선행 capture_snapshot step id
    after_step_id: snapshot_after_move
    min_changes: 1     # optional: 미만이면 FAIL
    max_changes: 50    # optional: 초과 시 FAIL
```

## Context-aware action: `job.status`

ASYNC Job polling. 선행 job-생성 step (`robot_navigate_to`, `character_navigate_to` 등) 의 `job_id` 를 해소한 뒤 `/jobs/{job_id}` 를 폴링:

```yaml
- id: wait_nav
  module: job
  action: status
  args:
    navigate_step_id: nav          # 또는 job_id: "<literal>"
    expected_status: done          # optional — 불일치 시 FAIL
    poll_interval_s: 0.25
    max_polls: 30
```

`expected_status` 미지정 시 `error` 종결만 FAIL. terminal state: `done` / `error` / `canceled`.

## 기타 규칙

- **`continueOnFailure: true`** — 옵셔널 step (예: articulation 없는 USD 의 `robot_set_joint_positions`). FAILED 여도 phase terminal status 에서 제외 → scenario 최종 PASSED 유지. `failFast` 와 무관
- **Float 비교** — 기본 tolerance `0.001`. action 별 `args.tolerance` override
- **Lakehouse** — `lakehouse_query` 는 expected 값 pull 전용 (inject/cleanup 불가)

## 실행

```
scenario_validate(scenario_path="smoke/trigger_sync_cube.yaml")  # 실제 실행
scenario_plan(scenario_path="smoke/state_check_property.yaml")   # 계획 미리보기
scenario_list()                                                   # 사용 가능 시나리오 목록
scenario_last_report()                                            # 마지막 실행 보고서
```

## 새 시나리오 작성 절차

1. `smoke/` 의 가장 유사한 예시 복사
2. action / args 는 `scenario.schema.json` 또는 `scenario_schema()` 로 확인
3. 새 action 이 필요하면 `../src/omniverse_kit_mcp/scenario/CLAUDE.md §"새 action 추가 flow"` + `../docs/invariants/module-add.md`
4. `scenario_plan` 으로 컴파일 확인 → `scenario_validate` 로 실행

## 관련 경계

- Validation Rules (R1/R1a/R2/R3): `../docs/invariants/scenario-validation.md`
- 엔진 내부 (state_machine, action_registry, schema 동기화): `../src/omniverse_kit_mcp/scenario/CLAUDE.md`
- MCP tool 카탈로그 + 그룹별 caveat: `../src/omniverse_kit_mcp/tools/CLAUDE.md`
- 도메인 런타임 제약 (15 도메인): `../src/omniverse_kit_mcp/modules/integration-facts.md`
- Character 제약 (BehaviorAgent/IRA/NavMesh 실측): `../src/omniverse_kit_mcp/modules/CLAUDE.md`
- Asset URL 카탈로그: `../docs/assets/isaac/asset_inventory.md`
