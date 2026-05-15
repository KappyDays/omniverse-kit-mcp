<!-- Parent: ../CLAUDE.md -->
<!-- Scope: scripts/ — dev / live / sync helpers -->

# scripts — Developer Scripts

**카테고리**:

| 스크립트 | 목적 | 언제 쓰나 |
|----------|------|-----------|
| `generate_tool_catalog.py` | `docs/tool-catalog.md` 재생성 | 새 `@mcp.tool()` 등록 / 기존 tool 시그니처 변경 **직후 반드시** |
| `verify_mcp_sync.py` | regen + drift test 1 command | tool 변경 commit 전에 실행해 drift 사전 차단 |
| `run_process_module_standalone.py <start\|stop\|restart>` | kit.exe lifecycle 를 MCP 서버 import cache 없이 직접 제어 | Extension 코드 변경 후 Isaac Sim 재기동 필요할 때 (MCP 세션 재시작 회피) |
| `run_scenario_standalone.py <scenario_path>` | scenario runner 를 최신 `src/` 코드로 실행 | MCP import cache 를 우회하고 scenario 수정 live 검증 |
| `live_test_phase_d.py` · `live_test_phase_e.py` · `live_test_gui_equiv.py` · `live_test_extension_ui.py` | Phase 별 live E2E 검증 | Phase 완료 시 — `docs/artifacts/phase-{d,e}/` 에 아티팩트 저장 |
| `live_test_replicator.py` · `live_test_omnigraph.py` · `live_test_content.py` · `live_test_extension_ext.py` | Phase H 도메인 별 live REST 검증 | Isaac Sim 기동 중 14 신규 tool 의 Extension route 를 직접 호출 — 결과 JSON 은 `docs/artifacts/phase-h/` 디렉토리에 저장 |
| `harvest_extension_metadata.py` · `render_catalog_md.py` · `sync_testbed_snapshot.py` | Kit Extension 레퍼런스 재수집 | `docs/references/extensions-catalog.md` 업데이트 시 |
| `diff_catalog.py` | 현재 `extensions.json` vs fresh harvest 비교 (added / removed / version_bumped / category_changed) | Kit / app 버전 bump 후 sync 필요 여부 판정 — workflow 는 `/omniverse-kit-extension-catalog-sync` skill |
| `diff_asset_inventory.py` | `docs/assets/isaac/assets/*.md` 의 모든 USD URL 을 NVIDIA S3 에 HTTP HEAD 검증. 404 / NET / 5xx 보고 | Asset 경로 fail 보고 시 또는 Isaac Sim 5.x 패치 후 — workflow 는 `/omniverse-asset-inventory-sync` skill |

## 추가 규칙

- **MCP import cache 우회**: `src/omniverse_kit_mcp/` 코드를 수정하면 MCP host (Claude Code / Codex CLI) 재시작 전까지 MCP tool 호출로는 반영되지 않는다. `run_scenario_standalone.py` / `run_process_module_standalone.py` 는 매 실행마다 fresh Python process 로 import 하므로 최신 코드가 즉시 반영됨. Extension 코드 변경 (`kkr-extensions/`) 은 `kit_app_restart` 로 즉시 반영.
- **Live 스크립트 산출물**: `docs/artifacts/phase-{id}/` (예: `docs/artifacts/phase-e/`) 에 저장. 각 스크립트의 `PHASE_*_DIR` 상수가 이 경로로 설정됨. `%TEMP%/validation_api_captures/` 에 저장된 원본 캡처를 의미 있는 이름으로 복사.
- **verify_mcp_sync.py 는 0 exit 필수**: 새 tool 을 커밋하기 전에 이 스크립트가 0 으로 끝나야 한다. Non-zero 면 regen 또는 frozenset 업데이트 누락.

## 새 스크립트 추가 절차

1. `scripts/` 에 파일 추가, `__init__.py` 는 비어 있어도 OK
2. 이 파일 표 에 한 행 추가 (목적 + 실행 조건)
3. 루트 CLAUDE.md 의 "Scope-specific CLAUDE.md" 표는 이미 `scripts/CLAUDE.md` pointer 가 있으므로 추가 수정 불필요

## 관련 경계

- Tool 카탈로그 생성물 규약: `../docs/CLAUDE.md`
- 새 MCP tool 추가 전체 흐름: 루트 `../CLAUDE.md` 의 "변경 파급 매트릭스" 행 "새 MCP tool"
- Scenario runner 내부: `../src/omniverse_kit_mcp/scenario/CLAUDE.md`
