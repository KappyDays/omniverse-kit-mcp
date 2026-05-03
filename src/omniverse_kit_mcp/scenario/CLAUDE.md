<!-- Parent: ../../../CLAUDE.md -->
<!-- Scope: Scenario engine — YAML → Arrange/Act/Assert/Cleanup 실행 엔진 -->

# scenario — Scenario Engine

YAML 시나리오를 읽어 Arrange → Act → Assert → Cleanup 순서로 실행한다. MCP tool 레이어(`tools/scenario_tools.py`)가 이 엔진을 감싸서 `scenario_validate` 등의 tool로 노출한다.

## State machine

실행 단계는 고정 순서:

```
Arrange ─► Act ─► Assert ─► Cleanup (always, finally)
```

- **Arrange**: 사전 상태 준비 (stage_load_usd, stage_create_prim, lakehouse_query 등). Lakehouse 주입은 불가능 (query only)
- **Act**: 검증 대상 동작 (extension_trigger, simulation_play 등)
- **Assert**: 상태 검증 (stage_assert_prim_exists, stage_assert_property, viewport_compare_ssim 등)
- **Cleanup**: 리소스 정리 — **finally block으로 항상 실행** (assert 실패해도 보장, Key Decision)

## 파일 역할

| 파일 | 역할 |
|------|------|
| `loader.py` | YAML 파일 → raw dict |
| `schema.py` | JSON Schema (`SCENARIO_SCHEMA`) + module enum |
| `compiler.py` | raw dict → `CompiledScenario` (타입 검증 + 변수 치환) |
| `action_registry.py` | **YAML `args` dict → typed request 매핑** + `CONTEXT_AWARE_ACTIONS` 집합. 새 action 추가 시 반드시 여기 분기 추가 |
| `context.py` | 실행 컨텍스트 — step 간 artifact / step_data 공유 |
| `runner.py` | loader → compiler → state_machine → reporter 오케스트레이터. 모듈 dispatch dict 에 모든 ModuleName enum 을 등록해야 함. `_phase_has_fatal_failure()` 가 `continueOnFailure: true` step 을 phase terminal 에서 제외 |
| `state_machine.py` | Arrange/Act/Assert/Cleanup 단계 진행 |
| `reporters.py` | 실행 결과 → markdown / json 보고서 |

## 새 action 추가 flow

1. `modules/<domain>_module.py` 에 module 메서드 추가 (`ok_result` / `error_result` 반환)
2. `tools/module_tools.py` 에 `@mcp.tool()` 데코레이터로 MCP tool 등록
3. `scenario/action_registry.py` 에 YAML args → typed request 빌더 추가 (`_REGISTRY` dict)
4. context-aware 액션이라면 `CONTEXT_AWARE_ACTIONS` 에 `(ModuleName.X, "action")` 추가 + `runner._execute_context_aware` 에 분기 추가
5. `scenarios/schema/scenario.schema.json` 의 action enum + args 스키마 업데이트 (SoT)
6. `scenario/schema.py` 의 `SCENARIO_SCHEMA` 를 schema.json 과 동기화
7. `tests/unit/test_scenario_integration.py` 에 routing 회귀 테스트 추가

## Context-aware 액션 패턴

대부분의 action 은 `args` dict 만으로 실행되지만, 일부 action 은 이전 step 의 결과를 ctx 에서 pull 해야 한다:

| module | action | ctx 참조 |
|--------|--------|---------|
| `stage` | `diff_snapshots` | `before_step_id`, `after_step_id` → `ctx.get_step_data(step_id)` 로 StageSnapshot 2 개 해소 |
| `job` | `status` | `navigate_step_id` → 선행 `robot.navigate_to` / `character.navigate_to` 의 `*NavigateResult.job_id` 를 duck-typed `getattr(prior, "job_id", None)` 로 해소 후 polling (`poll_interval_s`, `max_polls`, `expected_status`). `job_id` 직접 지정도 가능. 취소는 `job.cancel` 또는 MCP tool `job_cancel` |

runner 흐름: 액션이 `CONTEXT_AWARE_ACTIONS` 에 있으면 `_execute_context_aware` 로 dispatch. 없으면 기존 경로 (`build_request` → typed request → module 메서드).

## 모듈 ↔ action 라우팅

Stage WRITE action(`stage_load_usd`, `stage_set_property`, `stage_create_prim`, `stage_delete_prim`)은 `SimulationModule` 에 실제 구현되어 있으므로 YAML / action_registry 에서 모두 **`module: simulation`** 이어야 한다. `module: stage` 는 READ/ASSERT/DIFF 만 해당 (StageModule 보유 메서드).

## 스키마 동기화 (중요)

- **Source of truth**: `scenarios/schema/scenario.schema.json`
- `scenario/schema.py`의 dataclass 타입은 schema.json과 항상 일치해야 함
- 불일치 시 `scenario_validate` 실행 중 런타임 에러로 드러난다 — 먼저 schema.json 수정 후 schema.py 반영

## 관련 경계

- **형제 CLAUDE.md**:
  - `../modules/CLAUDE.md` — 모듈 책임 매트릭스 + Character 제약 + base.py 패턴 (scenario runner 가 dispatch 할 모듈)
  - `../modules/integration-facts.md` — 15 도메인 런타임 제약 (비자명한 함정)
  - `../modules/process-ops.md` — ProcessModule 운영 매뉴얼 (hang / .env)
  - `../tools/CLAUDE.md` — MCP tool 등록 규약 + `_resolve_safe_path` 경계
  - `../CLAUDE.md` (src/omniverse_kit_mcp/) — 패키지 entry flow
- **YAML 저작자 관점**: `../../../scenarios/CLAUDE.md` (이 파일은 엔진 내부, 저 파일은 사용자 가이드)
- **상위**: root `CLAUDE.md`
