<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 프로젝트 문서 루트 — Phase 히스토리 + live tool catalog + references -->

# docs — 문서 루트

Isaac-sim-MCP 가 "지금 무엇을 할 수 있는가" (tool 카탈로그) 와 "어떻게 여기까지 왔는가" (phase 히스토리) 를 분리해서 기록한다. 루트 CLAUDE.md "현재 MCP 표면 확인" 섹션이 진입점.

## 파일 구조

| 파일 / 하위 디렉토리 | 역할 | 업데이트 규칙 |
|---------------------|------|--------------|
| `tool-catalog.md` | **지금 호출 가능한 모든 MCP tool** — signature, description, parameters. 외부 세션의 진입점 | **Auto-generated**. `scripts/generate_tool_catalog.py` 재실행 필요. `tests/unit/test_tool_catalog_sync.py` 가 drift 검출 |
| `invariants/` | **작업 전 필독 pull-doc** — USD 로드 / process lifecycle / MCP tool 추가 / module 추가 / extension reload / UI invoke / scenario validation 7 개. 루트 CLAUDE.md 의 "⚠️ 작업 전 필수 pull-doc" 표가 진입점 | 하드캡 ≤200 줄. 영구 규칙 신규 추가 시 여기 신설 |
| `runbooks/` | **장애 대응 pull-doc** — kit-stdin-deadlock / cold-boot-timeout / hub-orphan / env-sub-config 4 개. 정상 개발 흐름에서 무시, 장애 시에만 참조 | 하드캡 ≤300 줄. 신규 장애 유형 발생 시 신설 |
| `phase-a-validation-report.md` … `phase-h-validation-report.md` | Phase 별 구현 결정 / 실측 결과 / 남은 한계 (A-H 전 Phase 완료 상태) | Phase 완료 시 신규 작성. 이후 불변 (git log 스타일 히스토리) |
| `phase-progress.md` | 모든 Phase Task 체크박스 + 타임스탬프 + 프로젝트 완료 표기 | Task 완료 시 agent 가 실시간 갱신 |
| `references/` | Isaac Sim Kit SDK / ext 카탈로그 / testbed snapshot — 외부 레퍼런스 자료 | `scripts/sync_testbed_snapshot.py` 등으로 주기 갱신. 상세: `references/CLAUDE.md` |
| `blueprint/` | 초기 설계 문서 / 아키텍처 스케치 | 거의 변경 없음 (history) |
| `specs/` | 인터뷰 스펙 / 프로젝트 원본 요구사항 | 거의 변경 없음 (history) |
| `artifacts/` | Phase 별 live validation 산출물 (`phase-a/`, `phase-d/`, `phase-e/`, `phase-f/`) + 재구성 baseline (`restructure-baseline/{pre,post}/`). validation-report.md 의 참조 타겟 | live test 스크립트가 직접 쓰기 (각 `scripts/live_test_*.py` 의 `PHASE_*_DIR` 상수가 이 경로로 설정됨) |
| `superpowers/` | superpowers 관련 메모 / plans / specs (디자인 아티팩트 — forward ref 허용, `test_doc_integrity.py` A1 에서 제외) | 수동 작성 |

## Phase report 작성 규칙

- 파일명: `phase-{phase-id}-validation-report.md` (lowercase)
- 섹션 순서: **Summary → New MCP Tools → Design decisions → 구현 변경 요약 → Live validation → 단위 테스트 → 남은 한계**
- 수치 (tool 수, test 수) 는 Summary 표에만 기록. 본문 전반에 뿌리지 말 것 — drift 발생
- "변경 파급" 블록 필수: 어떤 파일이 함께 수정됐는지 체크리스트
- 라이브 검증 PNG / JSON 은 `docs/artifacts/phase-{id}/` 에 저장하고, 보고서에서 상대 경로 (`artifacts/phase-e/...`) 로 참조

## tool-catalog.md — auto-regeneration 룰

1. 새 `@mcp.tool()` 등록 or 기존 tool 시그니처 변경 시 **반드시 재생성**:
   ```
   .venv/Scripts/python.exe scripts/generate_tool_catalog.py
   ```
2. 또는 한 번에: `.venv/Scripts/python.exe scripts/verify_mcp_sync.py` (regen + pytest drift check 를 묶어서 실행)
3. Commit 에 `docs/tool-catalog.md` 변경이 함께 포함되어야 함. 없이 push 하면 `test_tool_catalog_sync` 가 fail.
4. 사람이 이 파일을 **수동 편집 금지** — 다음 regen 시 덮어씀. 오타 / 설명 개선이 필요하면 `tools/module_tools.py` docstring 을 수정하고 regen.

## 외부 세션에서 이 디렉토리를 참조하는 루트

- 다른 Claude Code 세션 / LLM 이 "Isaac-sim-MCP 로 뭘 할 수 있냐" 질문 → `docs/tool-catalog.md` 단 하나만 읽으면 전체 서피스 파악.
- "왜 Phase D 에서 carb log 훅이 5-arg 시그니처냐" 질문 → `docs/phase-d-validation-report.md` 의 Design decisions 섹션.
- Kit SDK 미공개 API 를 찾을 때 → `docs/references/extensions-catalog.md` 키워드 검색 → testbed-snapshot → 실제 Kit source.

## 관련 경계

- tool 등록 규약: `../src/isaacsim_mcp/tools/CLAUDE.md`
- tool 이름 SoT: `../tests/unit/test_tools_registration.py` 의 frozenset
- catalog regeneration: `../scripts/CLAUDE.md`
- Extension REST 계약: `../isaac_extension/CLAUDE.md`
