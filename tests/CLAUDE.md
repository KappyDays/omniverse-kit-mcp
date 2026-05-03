<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Unit tests — pytest 기반 mock 검증, live E2E 제외 -->

# tests — Unit Tests

Mock 기반 단위 테스트. 실제 Isaac Sim / Lakehouse 없이 모듈 로직과 tool 등록을 검증한다.

## 실행

```bash
uv run pytest tests/
uv run pytest tests/unit/test_stage_module.py -v    # 단일 파일
```

`pyproject.toml` 의 `[tool.pytest]` 설정에 따라 `tests/` 자동 수집.

## 구조

```
tests/
├── conftest.py                         # 공용 fixture (MockIsaacRestClient / MockLakehouseClient)
├── unit/
│   ├── test_*_module.py                # 각 도메인 모듈 단위 테스트 (mock HTTP client 기반)
│   ├── test_scenario_runner.py         # loader/compiler 단위
│   ├── test_scenario_integration.py    # runner 통합 (SimulationModule routing, diff_snapshots/job ctx)
│   └── test_tools_registration.py      # EXPECTED_MODULE_TOOLS / EXPECTED_SCENARIO_TOOLS frozenset SoT
└── fixtures/                           # JSON/YAML 스냅샷 — mock 반환값 소스
```

GUI-equiv live 검증은 `scripts/live_test_gui_equiv.py` — unit tests 는 mock 기반이라 save/open 등 파일시스템 의존 기능은 live 전용.

## 테스트 전략

- **Mock HTTP client**: `IsaacRestClient` / `LakehouseClient` 를 mock 하고 module 이 올바른 endpoint 를 호출 + 응답을 typed 결과로 변환하는지 검증
- **Fixture 파일**: 실 응답과 똑같은 JSON/YAML 스냅샷을 `fixtures/` 에 두고 mock 반환값으로 주입
- **Scenario runner**: 모든 모듈을 mock 한 상태로 state_machine 흐름 (Arrange→Act→Assert→Cleanup, Cleanup finally 보장) 검증. `continueOnFailure: true` 는 phase terminal 에 영향 주지 않음 (helper `_phase_has_fatal_failure()` 로 분기)
- **Tool registration**: `test_tools_registration.py` — `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset 을 SoT 로 두고 registered set 과 정확히 일치하는지 검증 (누락/초과 모두 FAIL). count assertion 은 `len()` 유도 → Phase 추가 시 literal 수정 불필요

## 범위 제한 (IMPORTANT)

- **`tests/` 에는 live Isaac Sim / Lakehouse 연동 테스트가 없다**
- 실제 end-to-end 검증은 `scenarios/*.yaml` + `scenario_validate` MCP tool 로 수행

## 테스트 추가

- 새 module 메서드 → 해당 `tests/unit/test_<domain>_module.py` 에 mock 기반 케이스 추가
- 새 MCP tool → `test_tools_registration.py` 에 tool 등록 확인 추가
- 새 scenario action → `test_scenario_runner.py` 에 action_registry 분기 및 state_machine 흐름 케이스 추가

## 관련 경계

- Module 구현: `../src/omniverse_kit_mcp/modules/CLAUDE.md`
- Tool 등록 규약: `../src/omniverse_kit_mcp/tools/CLAUDE.md`
- Scenario 엔진: `../src/omniverse_kit_mcp/scenario/CLAUDE.md`
