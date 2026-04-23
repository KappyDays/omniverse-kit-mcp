<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: 새 MCP tool 추가 작업 시작 전 필수 숙지 -->
# MCP Tool 추가 — Invariants

새 `@mcp.tool()` 추가는 **7곳 동시 수정 + auto-regen catalog + drift test 통과** 의
3-step. 한 곳이라도 누락하면 `verify_mcp_sync.py` / drift pytest fail.

## 7곳 동시 수정 체크리스트

새 MCP tool 한 개 추가 시 반드시 함께 변경:

1. **Extension REST endpoint** — `isaac_extension/omni.mycompany.validation_api/omni/mycompany/validation_api/services/` 또는 router
2. **REST client** — `src/isaacsim_mcp/clients/isaac_rest_client.py` 메서드 추가
3. **Module wrapper** — `src/isaacsim_mcp/modules/` 도메인 모듈의 typed async 메서드
4. **MCP tool 등록** — `src/isaacsim_mcp/tools/module_tools.py` 의 `@mcp.tool()` 데코레이터 함수
5. **Mock client** — `tests/conftest.py` 의 MockIsaacRestClient + 새 메서드
6. **Tool name SoT** — `tests/unit/test_tools_registration.py` 의 `EXPECTED_MODULE_TOOLS`
   또는 `EXPECTED_SCENARIO_TOOLS` frozenset 에 추가
7. **Tool group caveat** — `src/isaacsim_mcp/tools/CLAUDE.md` 해당 그룹 섹션에 한 줄

## 재생성 (필수 1회 수동 실행)

```bash
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

이 명령이 묶어서 실행:
1. `scripts/generate_tool_catalog.py` — `docs/tool-catalog.md` 재생성
2. `pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py` —
   drift 검사
3. `git status` — 생성 파일 unchanged 확인

## Drift 검증 (commit 전 필수)

```bash
uv run pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py
```

- `tests/unit/test_tools_registration.py` — 등록된 tool set ↔ EXPECTED_*_TOOLS frozenset
  정확히 일치 (누락/초과 모두 FAIL)
- `tests/unit/test_tool_catalog_sync.py` — `docs/tool-catalog.md` 가 현재 등록 상태와 동기

## MCP Resource 추가 / 이동 (별도 절차)

`@mcp.resource(uri=...)` 추가/이동 시:
1. `src/isaacsim_mcp/mcp/resources.py` 데코레이터 함수 + `RESOURCE_SOURCES` dict 매핑
   갱신 (file-backed = `Path`, Python-backed = `None`)
2. `tests/unit/test_resources_paths.py` 의 `EXPECTED_RESOURCES` 에 URI 추가/제거
3. `uv run pytest tests/unit/test_resources_paths.py` — 매핑 어긋나면 FAIL

## 재구성 작업 중 금지

CLAUDE.md Pull-First 재구성 진행 중에는 새 tool 추가 금지 (Operating Invariant —
MCP surface 불변).

## 관련 경계

- Tool 등록 규약 + 그룹별 caveat: `src/isaacsim_mcp/tools/CLAUDE.md`
- 모듈 책임 매트릭스: `src/isaacsim_mcp/modules/CLAUDE.md`
- Test 전략: `tests/CLAUDE.md`
- Catalog regen 스크립트 상세: `scripts/CLAUDE.md`
- Type boundary (dataclass vs Pydantic): `src/isaacsim_mcp/CLAUDE.md`
- 새 module / scenario action 추가는 별개: `docs/invariants/module-add.md`
