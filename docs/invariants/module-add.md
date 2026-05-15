<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: 새 도메인 module 추가 작업 시작 전 필수 숙지 -->
# Module 추가 — Invariants

새 도메인 module (`StageModule`, `RobotModule` 같은 단위) 추가 시 7곳 동시 수정
필요. action_registry / scenario schema / runner dispatch 가 정합 안 맞으면
scenario YAML 가 silent skip 되거나 runner KeyError.

## 7곳 동시 수정 체크리스트

새 module `<XYZ>Module` 추가 시:

1. **Module enum** — `src/omniverse_kit_mcp/types/common.py` 의 `ModuleName` enum 에 추가
2. **Module 구현** — `src/omniverse_kit_mcp/modules/` 에 신규 `<xyz>_module.py` (base.py
   패턴 따라 `ModuleResult[T]` 반환)
3. **Scenario schema (Python)** — `src/omniverse_kit_mcp/scenario/schema.py` 의 typed
   request 구조 추가
4. **Scenario schema (JSON)** — `scenarios/schema/scenario.schema.json` 의 action
   validator 갱신
5. **Runner dispatch** — `src/omniverse_kit_mcp/scenario/runner.py` 의 dispatch dict 에
   module 매핑 추가
6. **Tool 등록** — `src/omniverse_kit_mcp/tools/scenario_tools.py` 또는
   `src/omniverse_kit_mcp/tools/module_tools.py` 의 `@mcp.tool()` 함수 추가
7. **Server wiring** — `src/omniverse_kit_mcp/mcp/server.py` 의 module 인스턴스 생성
   + tool 등록 호출
8. **모듈 책임 매트릭스 갱신** — `src/omniverse_kit_mcp/modules/CLAUDE.md` 의 표에 1행 추가

## Module 메서드 추가 (existing module 의 새 method)

1. Module 메서드 구현
2. **Action registry** — `src/omniverse_kit_mcp/scenario/action_registry.py` 의 typed
   request 빌더 추가
3. Tests — `tests/unit/` 의 `test_<xyz>_module.py` 에 mock 기반 케이스 추가

## Scenario action 추가 (Module 메서드와 별도)

action 1개당 다음 파일 동시 수정:
1. `src/omniverse_kit_mcp/scenario/action_registry.py`
2. `scenarios/schema/scenario.schema.json`
3. `src/omniverse_kit_mcp/scenario/schema.py`
4. `tests/unit/test_scenario_integration.py` 에 케이스 추가
5. `scenarios/CLAUDE.md` 작성 가이드 갱신

## ASYNC Job pattern (long-running 동작)

`character.navigate_to` / `robot.navigate_path` 처럼 장시간 동작:
- `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/job_service.py::start_job` 사용 (coro_factory 인수)
- `try-except` 필수 (silent catch 금지)
- Tool 은 `job_id` 반환, MCP host (Claude Code / Codex CLI) 가 `job_status` 폴링

## 관련 경계

- Module 책임 매트릭스: `src/omniverse_kit_mcp/modules/CLAUDE.md`
- Scenario 엔진 (Arrange/Act/Assert/Cleanup, action_registry, context-aware dispatch):
  `src/omniverse_kit_mcp/scenario/CLAUDE.md`
- Scenario YAML 저작: `scenarios/CLAUDE.md`
- Scenario validation rules: `docs/invariants/scenario-validation.md`
- Tool 등록 규약 (7곳 동시 수정의 후속): `docs/invariants/mcp-tool-add.md`
- Test 전략: `tests/CLAUDE.md`
