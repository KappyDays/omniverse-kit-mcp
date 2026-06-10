<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 프로젝트 문서 루트 — live tool catalog + references + pull-docs -->

# docs — 문서 루트

omniverse-kit-mcp 가 "지금 무엇을 할 수 있는가" (tool 카탈로그) 와 "작업 전 무엇을 읽어야 하는가" (invariants / runbooks / references) 를 분리해서 기록한다. 루트 CLAUDE.md "작업 전 필수 pull-doc" 표가 진입점.

## 파일 구조

| 파일 / 하위 디렉토리 | 역할 | 업데이트 규칙 |
|---------------------|------|--------------|
| `tool-catalog.md` | **지금 호출 가능한 모든 MCP tool** — signature, description, parameters. 외부 세션의 진입점 | **Auto-generated**. `scripts/generate_tool_catalog.py` 재실행 필요. `tests/unit/test_tool_catalog_sync.py` 가 drift 검출 |
| `tool-diagnostic-map.md` | **에러/실패 진단** — 의문→MCP read-only tool 역색인 + 디버깅 워크플로 | 새 진단 패턴 발견 시 |
| `invariants/` | **작업 전 필독 pull-doc** — asset discovery / USD 로드 / process lifecycle / MCP tool 추가 / module 추가 / extension reload / UI invoke / scenario validation / multi-app / visual-validation 10 개. 루트 CLAUDE.md 의 "⚠️ 작업 전 필수 pull-doc" 표가 진입점 | 하드캡 ≤200 줄. 영구 규칙 신규 추가 시 여기 신설 |
| `runbooks/` | **장애 대응 pull-doc** — kit-stdin-deadlock / cold-boot-timeout / hub-orphan / env-sub-config / kit-dep-solver-fail / multi-app / scene-reexport-lock 7 개. 정상 개발 흐름에서 무시, 장애 시에만 참조 | 하드캡 ≤300 줄. 신규 장애 유형 발생 시 신설 |
| `references/` | public-safe curated refs. Local generated extension catalog / snapshots are ignored | 상세: `references/CLAUDE.md` |
| `artifacts/` | live validation 산출물. validation 스크립트가 쓰는 결과 저장소 | live test 스크립트가 직접 쓰기 |
| `oss-application-notes.md` | public OSS support application summary. 개인정보 없이 repo 목적 / 유지보수 신호 / public boundary 정리 | 신청서·README 용 짧은 공개 설명 갱신 시 |

## tool-catalog.md — auto-regeneration 룰

1. 새 `@mcp.tool()` 등록 or 기존 tool 시그니처 변경 시 **반드시 재생성**:
   ```
   .venv/Scripts/python.exe scripts/generate_tool_catalog.py
   ```
2. 또는 한 번에: `.venv/Scripts/python.exe scripts/verify_mcp_sync.py` (regen + pytest drift check 를 묶어서 실행)
3. Commit 에 `docs/tool-catalog.md` 변경이 함께 포함되어야 함. 없이 push 하면 `test_tool_catalog_sync` 가 fail.
4. 사람이 이 파일을 **수동 편집 금지** — 다음 regen 시 덮어씀. 오타 / 설명 개선이 필요하면 `tools/module_tools.py` docstring 을 수정하고 regen.

## 외부 세션에서 이 디렉토리를 참조하는 루트

- 다른 Claude Code 세션 / LLM 이 "omniverse-kit-mcp 로 뭘 할 수 있냐" 질문 → `docs/tool-catalog.md` 단 하나만 읽으면 전체 서피스 파악.
- Kit SDK 미공개 API 를 찾을 때 → 기존 `docs/tool-catalog.md` 중복 확인 → 로컬 generated catalog 가 있으면 `extension_search` → 실제 Kit source / 공식 문서.

## 관련 경계

- tool 등록 규약: `../src/omniverse_kit_mcp/tools/CLAUDE.md`
- tool 이름 SoT: `../tests/unit/test_tools_registration.py` 의 frozenset
- catalog regeneration: `../scripts/CLAUDE.md`
- Extension REST 계약: `../kkr-extensions/CLAUDE.md`
