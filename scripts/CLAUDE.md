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
| `bootstrap_codex_worktree.ps1` | Codex worktree bootstrap — repo 밖 `local.env` 를 `.env` 로 복사, `uv sync`, local Isaac/Codex preflight 실행 | 새 Codex worktree 생성 직후 live MCP 작업 전 |
| `verify_local_isaac_env.py` | local Isaac Sim install path, derived port/base_url, optional `codex mcp list` preflight | `kit_app_start` / live MCP 작업 전 경로 누락 조기 실패 |
| `live_test_extension_ui.py` | Phase D — Extension UI 자동화(ui_invoke/ui_tree) + carb log capture live | Phase 검증 — `docs/artifacts/phase-d/` |
| `live_test_phase_e.py` · `live_test_sensor.py` · `live_test_navmesh_viz.py` · `live_test_viewport_multi.py` | Phase E — 센서(RTX cam/lidar/depth)·navmesh viz·멀티 뷰포트 live | → `docs/artifacts/phase-e/` |
| `live_test_physics.py` · `live_test_lighting.py` · `live_test_material.py` · `live_test_viewport_render.py` | Phase F — 물리·조명(6종)·머티리얼·렌더모드 live | → `docs/artifacts/phase-f/` |
| `live_test_character_crowd.py` · `live_test_robot_ext.py` · `live_test_sensor_contact_imu.py` · `live_test_timeline.py` | Phase G — 군중·로봇 ext(navigate/gripper/ee)·접촉/IMU·타임라인 live | Isaac Sim 기동 중 수동 실행 (stdout 리포트) |
| `live_test_replicator.py` · `live_test_omnigraph.py` · `live_test_content.py` · `live_test_extension_ext.py` | Phase H — replicator·omnigraph·content·extension mgmt live REST | → `docs/artifacts/phase-h/` |
| `live_test_gui_equiv.py` | GUI-equiv live — stage save/open/selection 등 **FS 의존**(mock 불가) 검증 | unit test 갭 보강 (tests/CLAUDE.md 참조) |
| `harvest_extension_metadata.py` · `render_catalog_md.py` · `sync_testbed_snapshot.py` | Kit Extension 레퍼런스 로컬 재수집 | ignored `docs/references/extensions*.json/md` 필요 시 |
| `diff_catalog.py` | 현재 local `extensions.json` vs fresh harvest 비교 (added / removed / version_bumped / category_changed) | Kit / app 버전 bump 후 local sync 필요 여부 판정 — workflow 는 `/omniverse-kit-extension-catalog-sync` skill |
| `diff_asset_inventory.py` | `docs/assets/isaac/assets/*.md` 의 모든 USD URL 을 NVIDIA S3 에 HTTP HEAD 검증. 404 / NET / 5xx 보고 | Asset 경로 fail 보고 시 또는 Isaac Sim 5.x 패치 후 — workflow 는 `/omniverse-asset-inventory-sync` skill |
| `rebuild_scene.py <builder.py> --out <out.usd> [--reopen]` | 씬 USD 를 anonymous-layer + `dont_write_bytecode` 로 재빌드(락/레지스트리/pycache 우회) | 라이브 Kit 이 USD 를 열어 re-export 가 silent 실패할 때. 상세: `../docs/runbooks/scene-reexport-lock.md` |

## 추가 규칙

- **MCP import cache 우회**: `src/omniverse_kit_mcp/` 코드를 수정하면 MCP host (Claude Code / Codex CLI) 재시작 전까지 MCP tool 호출로는 반영되지 않는다. `run_scenario_standalone.py` / `run_process_module_standalone.py` 는 매 실행마다 fresh Python process 로 import 하므로 최신 코드가 즉시 반영됨. Extension 코드 변경 (`kkr-extensions/`) 은 `kit_app_restart` 로 즉시 반영.
- **Codex worktree bootstrap**: ignored `.env` 는 새 worktree 에 자동 복사되지 않는다. live MCP 작업 전 `%USERPROFILE%\.config\omniverse-kit-mcp\local.env` 에 machine-local `ISAAC_SIM_KIT_EXE` / `ISAAC_SIM_KIT_FILE` 를 두고 `scripts/bootstrap_codex_worktree.ps1 -Profile isaac-sim -Instance N` 실행. stale `.env` 갱신은 `-RefreshEnv`. Public repo 에 개인 절대경로 커밋 금지.
- **Live 스크립트 산출물**: `docs/artifacts/phase-{id}/` (예: `docs/artifacts/phase-e/`) 에 저장. 각 스크립트의 `PHASE_*_DIR` 상수가 이 경로로 설정됨. `%TEMP%/validation_api_captures/` 에 저장된 원본 캡처를 의미 있는 이름으로 복사.
- **`live_test_*.py` 성격**: standalone httpx 로 `/validation/v1/*` 를 직접 때리는 **수동 ad-hoc phase 검증 도구** (pytest 미수집 — 테스트 신호 무영향). 도메인 회귀의 **공식 경로는 `scenarios/*.yaml` + `scenario_validate`** (Arrange→Act→Assert→Cleanup). live_test 는 scenario 가 안 덮는 표면(save/open·UI 자동화·뷰포트 create/destroy)이나 빠른 단발 점검용 — 신규 회귀는 scenario 로 추가할 것.
- **verify_mcp_sync.py 는 0 exit 필수**: 새 tool 을 커밋하기 전에 이 스크립트가 0 으로 끝나야 한다. Non-zero 면 regen 또는 frozenset 업데이트 누락.

## 새 스크립트 추가 절차

1. `scripts/` 에 파일 추가, `__init__.py` 는 비어 있어도 OK
2. 이 파일 표 에 한 행 추가 (목적 + 실행 조건)
3. 루트 CLAUDE.md 의 "Scope-specific CLAUDE.md" 표는 이미 `scripts/CLAUDE.md` pointer 가 있으므로 추가 수정 불필요
4. Codex/worktree bootstrap 또는 local env preflight 변경 시 `tests/unit/test_codex_worktree_bootstrap.py` 갱신

## 관련 경계

- Tool 카탈로그 생성물 규약: `../docs/CLAUDE.md`
- 새 MCP tool 추가 전체 흐름: 루트 `../CLAUDE.md` 의 "변경 파급 매트릭스" 행 "새 MCP tool"
- Scenario runner 내부: `../src/omniverse_kit_mcp/scenario/CLAUDE.md`
