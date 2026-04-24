# Isaac-sim-MCP — Project Instructions

<!-- 🛑 DO-NOT-EDIT 보호 영역 (축약 허용 / 목적 보존 / 자동 검증 G1-G7):
     (1) §"DO-NOT-EDIT Residual" 의 DO-NOT-EDIT-START/END 블록
     (2) §"Environment Variables" `ISAAC_SIM_EXTRA_EXT_IDS` 행 inline -->

## 세션 진입

- **이 파일만** 매 턴 자동 로드 (CC 동작). 100 줄 하드캡
- Phase 진행 맥락 필요 시: `docs/phase-progress.md` Read
- MCP tool 탐색은 tool 호출로 충분 (`docs/tool-catalog.md` 는 human 레퍼런스)

## ⚠️ 작업 전 필수 pull-doc

| 작업 | 먼저 Read |
|---|---|
| USD 로드 (`stage_load_usd` / `robot_load` / `character_load` / `stage_open`) | `docs/invariants/usd-load.md` |
| Isaac Sim 기동/종료/hang | `docs/invariants/process-lifecycle.md` |
| 새 MCP tool 추가 | `docs/invariants/mcp-tool-add.md` |
| 새 module / scenario action | `docs/invariants/module-add.md` |
| Extension `.py` 수정 / reload | `docs/invariants/ext-reload.md` |
| Extension UI automation (`extension_ui_invoke`) | `docs/invariants/ui-invoke.md` |
| Scenario YAML 저작 | `docs/invariants/scenario-validation.md` |

장애 진단은 `docs/runbooks/` (kit-stdin-deadlock · cold-boot-timeout · hub-orphan · env-sub-config). Phase 히스토리는 `docs/phase-a-validation-report.md` … `docs/phase-h-validation-report.md`. Tool name SoT 는 `tests/unit/test_tools_registration.py` frozenset.

## ⚠️ DO-NOT-EDIT Residual (L17 4h 디버깅)

<!-- DO-NOT-EDIT-START: 본문 / 재현 / 복구 `docs/runbooks/kit-stdin-deadlock.md`. 자동 검증 G1-G7 -->
⚠️ **`subprocess.Popen(... stdin=subprocess.DEVNULL)` 필수** — 누락 시 MCP 자식 kit.exe cold boot hang (L17). 위치: `src/isaacsim_mcp/modules/process_module.py::start`. 검증 수치 240 s → 13 s. **"extra_ext_ids race" 진단은 잘못됨** — stdin pipe 가 실원인.
<!-- DO-NOT-EDIT-END -->

## Validation Rules

- **R1** 실 asset 만 — primitive (Cube/Sphere) 대체 금지 (False Positive). 상세: `docs/invariants/scenario-validation.md`
- **R1a** NavMesh bake 는 `simulation_stop` 재호출 후 (`load → stop → bake → query → play → navigate`)
- **R2** Robot 동작 (`set_joint_positions` / `navigate_*` / `drive_physics`) 은 `simulation_play` 상태 필수 (`robot_load` 예외)
- **R3** `viewport_capture` 후 `Read` tool 시각 검증 의무 — blank/black 이면 조명·카메라·asset 조정 재시도

## 변경 파급 매트릭스

| 변경 대상 | 함께 수정 |
|-----------|----------|
| 새 MCP tool | 7 곳 (`docs/invariants/mcp-tool-add.md`) + `scripts/verify_mcp_sync.py` 수동 1 회 |
| 새 module / scenario action | `docs/invariants/module-add.md` |
| REST endpoint | client + tool 등록 + test + `isaac_extension/CLAUDE.md` |
| MCP resource | `src/isaacsim_mcp/mcp/resources.py` + `tests/unit/test_resources_paths.py` + verify_mcp_sync |
| Phase 완료 | `docs/phase-<N>-validation-report.md` + `docs/phase-progress.md` + 전체 pytest green |
| CLAUDE.md 새 디렉토리 | 이 매트릭스 + 문서 맵 양방향 갱신 |

## Key Decisions

- **LakehouseModule** query only (인터뷰 스펙 확정)
- **Type boundary**: 내부 `@dataclass(slots=True, frozen=True)`, Pydantic 은 Extension REST 경계만. MCP 서버 코드 Pydantic 금지
- **MCP server import cache**: 세션 시작 1 회 spawn + import 캐시. `src/isaacsim_mcp/` 수정은 Claude Code 재시작 전까지 미반영. 세션 내 검증은 `scripts/run_process_module_standalone.py` / `scripts/run_scenario_standalone.py`
- **Test SoT**: `tests/unit/test_tools_registration.py` 의 EXPECTED frozenset
- **uv 만 사용** (`pip install` 금지); 패키지 추가는 `uv add` / `uv add --dev`

## Environment Variables

| 변수 | 기본값 | 설명 |
|------|-------|------|
| `ISAAC_SIM_BASE_URL` | `http://localhost:8011` | Extension REST |
| `ISAAC_SIM_STARTUP_TIMEOUT` | `120.0` | ProcessModule health 대기 상한. 상세: `docs/invariants/process-lifecycle.md` |
| `ISAAC_SIM_EXTRA_EXT_IDS` | config.py bundle | <!-- ⛔ DO-NOT-EDIT: "extra_ext_ids race" 진단은 무효 (L17 참조 `docs/runbooks/kit-stdin-deadlock.md`). browser ext 금지 — `docs/invariants/usd-load.md` --> JSON array. `isaacsim.asset.browser` / `omni.kit.window.content_browser` 금지. stdin DEVNULL fix 후 8 개 13s 통과 |
| `LAKEHOUSE_BASE_URL` | `http://localhost:9000` | Lakehouse REST |

## Subagent 디스패치 패턴

Subagent 는 sub-CLAUDE.md 자동 로드 안 함. 디스패치 프롬프트에 `Read docs/invariants/<관련>.md first` 명시 또는 필수 맥락 직접 포함.

## 문서 맵

| 파일 | 담당 |
|------|------|
| `src/isaacsim_mcp/CLAUDE.md` | FastMCP 서버 루트 (entry / type 경계 / clients) |
| `src/isaacsim_mcp/modules/CLAUDE.md` | 모듈 매트릭스 + Character 제약 + base.py 패턴 (→ `integration-facts.md` · `process-ops.md`) |
| `src/isaacsim_mcp/scenario/CLAUDE.md` | 시나리오 엔진 (Arrange/Act/Assert/Cleanup + action_registry) |
| `src/isaacsim_mcp/tools/CLAUDE.md` | MCP tool 등록 규약 + 그룹별 caveat |
| `isaac_extension/CLAUDE.md` | Extension 개발 nav hub (→ `docs/*` basics / pitfalls / recipe / reuse / lessons-learned) |
| `scenarios/CLAUDE.md` | YAML 저작 |
| `tests/CLAUDE.md` | pytest 단위 |
| `setup/CLAUDE.md` | 설치 / 신규 PC |
| `scripts/CLAUDE.md` | 개발 스크립트 |
| `docs/CLAUDE.md` | phase 히스토리 / tool-catalog / references |
| `isaac_course/CLAUDE.md` | Digital Twin 튜토리얼 + asset 카탈로그 (`docs/asset_inventory.md`) |

## 메타

- 이 파일 **≤100 줄 하드캡** (A3 자동 가드). 추가 내용은 `docs/invariants/` / `docs/runbooks/` 로 이관 — 삭제는 stale content 만
- sub-CLAUDE.md **≤150 줄** (Phase 3 적용). 영구 규칙은 `docs/invariants/`, 사고 기록은 `isaac_extension/docs/lessons-learned.md`
