<!-- Parent: ../CLAUDE.md -->
<!-- Scope: YAML 시나리오 저작 가이드 (엔진 내부 지식 불필요) -->

# scenarios — YAML 시나리오 저작

Isaac Sim + Extension 동작을 end-to-end 로 검증하는 YAML 시나리오들. 엔진 내부를 몰라도 이 디렉토리 지침만으로 새 시나리오를 작성할 수 있다.

## Source of truth

- **스키마 파일**: `schema/scenario.schema.json` — 모든 필드 정의의 원천
- MCP tool: `scenario_schema()` 로도 현재 스키마를 조회 가능
- 시나리오 YAML 경로 기준: 환경 변수 `SCENARIOS_DIR` (기본 `scenarios/`). 이 루트를 벗어나는 경로는 `_resolve_safe_path()` 가 거부한다

## 디렉토리

```
scenarios/
├── schema/scenario.schema.json        # JSON Schema (SoT)
└── smoke/                             # canonical 예시 (새 시나리오 작성 시 참고)
    ├── full_pipeline.yaml             # Cube lifecycle (create → move → play/stop → assert → diff → cleanup)
    ├── state_check_property.yaml      # state-check 모드 예시
    ├── trigger_sync_cube.yaml         # Trigger 모드 예시 (Extension 동기화)
    ├── usd_load_robot.yaml            # 로컬 USD 로드 → prim/position 검증
    └── robot_joint_control.yaml       # Phase B+: asset_list(Franka) → load → play/pause warm-up → joints(9 DOF) → navigate(job) → read-back → viewport
```

`robot_joint_control.yaml` 은 Phase B+ 완결 예시 — GUI 유저가 Asset Browser 로 Franka 찾아서 더블클릭 → joint control → 이동하는 흐름을 YAML 로 그대로 표현.

`smoke/` 가 표준 예시. `full_pipeline.yaml` 은 stage WRITE + simulation timeline + diff_snapshots 를 한 번에 다루므로 새 시나리오 작성 시 참조하기 좋다.

## YAML 구조 개요

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
  arrange:
    - id: <step_id>
      module: <module-enum>
      action: <action>
      args: { ... }
  act: [...]
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
  cleanup: [...]
```

- `module` 는 `{stage, viewport, lakehouse, extension, simulation, robot, job, asset}` 중 하나 — schema enum 기준
- `action` 은 해당 모듈의 메서드 이름. 매핑 규약은 `../src/isaacsim_mcp/scenario/CLAUDE.md` 의 action_registry 참조
- `args` 형식은 `schema/scenario.schema.json` 의 action별 정의를 그대로 따름
- **Cleanup 은 assert 실패 여부와 무관하게 항상 실행된다** (finally)

## 모듈별 액션 가이드

| module | 대표 action | 비고 |
|--------|-------------|------|
| `stage` | `capture_snapshot`, `assert_prim_exists`, `assert_property`, `diff_snapshots` | READ / ASSERT |
| `simulation` | `stage_load_usd`, `stage_set_property`, `stage_create_prim`, `stage_delete_prim`, `play`, `pause`, `stop`, `get_status` | WRITE + timeline (SimulationModule 에 구현) |
| `extension` | `trigger`, `reset` | 커스텀 Extension 제어 |
| `lakehouse` | `query` | query only — inject/cleanup 사용 불가 |
| `viewport` | `capture`, `compare_ssim` | GUI 모드 필요 |
| `robot` | `load`, `get_joint_positions`, `set_joint_positions`, `navigate_to` | navigate_to 는 ASYNC — job_id 즉시 반환. get/set_joint_positions 는 articulation 없으면 400 FAIL (Phase B strict). joint I/O 전에 `simulation.play → pause` 로 articulation 초기화 필수 |
| `job` | `status`, `cancel` | status 는 context-aware polling (navigate_step_id 또는 job_id). cancel 은 `robot.navigate_to` 등의 in-flight job 중단 |
| `asset` | `list` | GUI Asset Browser 동등 — category 없으면 카테고리 목록, 있으면 S3 directory listing. Franka 등 공식 asset URL 을 하드코드 없이 확보 가능 |

**Phase B+ 추가 — GUI 동등 File/Selection/Camera**: `simulation.stage_save` / `simulation.stage_open` / `simulation.stage_new` 로 File menu, `stage.get_selection` / `stage.set_selection` 으로 Stage 패널 선택, `viewport.set_active_camera` 로 viewport 툴바의 카메라 전환이 scenario step 에서 직접 가능. `stage.create_prim` 의 `prim_type` 은 Cube/Sphere 뿐 아니라 `Camera` / `DistantLight` / `DomeLight` / `SphereLight` / `RectLight` 등 UsdLux·UsdGeom 타입 전부 수용한다.

**주의**: Stage 상태를 바꾸는 모든 action(USD 로드, prim 생성/삭제, property 변경)은 `module: simulation` 으로 기록한다. `module: stage` 는 READ/ASSERT 전용. Robot USD 를 Articulation 과 함께 로드할 때도 동일하게 `module: robot`, `action: load` 사용 (내부적으로 `CreateReferenceCommand` 호출은 `SimulationModule.stage_load_usd` 와 같지만 application 의도가 다르므로 분리 — articulation 탐지 결과를 `has_articulation` 필드로 반환).

## Context-aware action: `stage.diff_snapshots`

선행 두 개의 `capture_snapshot` step 결과를 ctx 에서 pull 하여 diff 를 계산한다. schema 예시:

```yaml
- id: diff_move
  module: stage
  action: diff_snapshots
  args:
    before_step_id: snapshot_before_move   # 선행 capture_snapshot step id
    after_step_id: snapshot_after_move
    min_changes: 1     # optional: diff.total_changes 가 이 값 미만이면 FAIL
    max_changes: 50    # optional: 초과 시 FAIL
```

runner 가 `CONTEXT_AWARE_ACTIONS` 집합을 검사하여 해당 액션을 만나면 `ctx.get_step_data(<step_id>)` 로 snapshot dataclass 를 꺼내 `StageModule.diff_snapshots(meta, before, after)` 를 호출한다. 새 context-aware 액션 추가 규약은 `../src/isaacsim_mcp/scenario/CLAUDE.md` 참조.

## Context-aware action: `job.status` (Phase B)

ASYNC Job polling. 선행 `robot.navigate_to` (또는 다른 job-생성 step) 의 결과에서 `job_id` 를 해소한 뒤 Extension 의 `/jobs/{job_id}` 를 폴링한다. 예시:

```yaml
- id: nav
  module: robot
  action: navigate_to
  args: { prim_path: /World/R, target: [2.0, 1.0, 0.0], duration_s: 1.0 }

- id: wait_nav
  module: job
  action: status
  args:
    navigate_step_id: nav          # 또는 job_id: "<literal>"
    expected_status: done          # optional — 불일치 시 FAIL
    poll_interval_s: 0.25
    max_polls: 30
```

`expected_status` 를 지정하지 않으면 job 이 `error` 상태로 끝났을 때 step 이 FAIL 된다. terminal state 는 `done`/`error`/`canceled` 중 하나.

## `continueOnFailure: true` 의미 (Phase B 수정, 2026-04-18)

옵셔널 step (예: articulation 없는 USD 에 `robot.set_joint_positions` 시도) 을 표현할 때 사용. 해당 step 이 FAILED/ERROR 여도:
1. 같은 phase 의 다음 step 은 계속 실행 (기존 동작)
2. phase terminal status 에서도 제외 — scenario 최종 status 를 PASSED 로 유지 (2026-04-18 수정)

이전에는 (2) 가 없어서 continueOnFailure 가 "옵션처럼" 쓰이지 못하고 scenario 전체가 FAILED 되었다. 새 규약 하에서 failFast=false 와 무관하게 "이 step 이 실패해도 scenario 목적 관점에서는 괜찮다" 를 표현 가능.

## Float 비교

기본 tolerance `0.001`. action별로 `args.tolerance` 로 override 가능.

## Lakehouse 사용 규칙

LakehouseModule 은 **query only** — 시나리오에서 `lakehouse_query` 는 expected 값을 가져오는 용도로만 쓴다. 주입/정리는 불가능하므로 arrange/cleanup 에서 Lakehouse를 조작하려 하면 안 된다.

## 실행

Claude Code MCP tool 로 실행:

```
scenario_validate(scenario_path="smoke/trigger_sync_cube.yaml")  # 실제 실행
scenario_plan(scenario_path="smoke/state_check_property.yaml")   # 계획 미리보기 (실행 X)
scenario_list()                                                   # 사용 가능 시나리오 목록
scenario_last_report()                                            # 마지막 실행 보고서
```

scenario_validate 실행 후에는 `scenario_last_report()` 로 단계별 결과를 확인한다.

## 새 시나리오 작성 절차

1. `smoke/` 의 가장 유사한 예시를 복사해서 시작
2. action 이름과 args 는 `scenario.schema.json` 또는 `scenario_schema()` 로 확인
3. 새 action 이 필요하다면 엔진/모듈 수정 필요 → `../src/isaacsim_mcp/scenario/CLAUDE.md` 의 "새 action 추가 flow" 참조
4. 작성 후 `scenario_plan` 으로 계획이 컴파일되는지 먼저 확인, 그 다음 `scenario_validate` 로 실행

## 관련 경계

- 엔진 내부(state_machine, action_registry, schema 동기화): `../src/isaacsim_mcp/scenario/CLAUDE.md`
- 사용 가능한 tool 목록: `../src/isaacsim_mcp/tools/CLAUDE.md`
- 도메인 제약 (Lakehouse query-only, Viewport GUI 필요 등): `../src/isaacsim_mcp/modules/CLAUDE.md`
