# omniverse-kit-mcp — Project Instructions

<!-- 🛑 DO-NOT-EDIT 보호 영역 (축약 허용 / 목적 보존 / 자동 검증 G1-G7):
     (1) §"DO-NOT-EDIT Residual" 의 DO-NOT-EDIT-START/END 블록
     (2) §"Environment Variables" `ISAAC_SIM_EXTRA_EXT_IDS` 행 inline -->

## 세션 진입

- **이 파일만** 매 턴 자동 로드 (CC 동작) — cap / 작성 룰: §메타

## ⚠️ 작업 전 필수 pull-doc

| 작업 | 먼저 Read |
|---|---|
| USD 로드 (`stage_load_usd` / `robot_load` / `character_load` / `stage_open`) | `docs/invariants/usd-load.md` |
| Isaac Sim 기동/종료/hang | `docs/invariants/process-lifecycle.md` |
| 새 MCP tool 기능 research (사전) | `docs/references/CLAUDE.md` |
| 새 MCP tool 추가 | `docs/invariants/mcp-tool-add.md` |
| 새 module / scenario action | `docs/invariants/module-add.md` |
| Extension `.py` 수정 / reload | `docs/invariants/ext-reload.md` |
| Extension UI automation (`extension_ui_invoke`) | `docs/invariants/ui-invoke.md` |
| Scenario YAML 저작 | `docs/invariants/scenario-validation.md` |
| `viewport_capture` / scene build / 새 NVIDIA asset 사용 | `docs/invariants/visual-validation.md` |
| Multi-app 추가 / Kit app profile 수정 / repo·디렉토리 rename | `docs/invariants/multi-app.md` |
| Kit / app 버전 업뎃 후 catalog sync | skill `/omniverse-kit-extension-catalog-sync` (`.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md`) |
| Asset URL 404 / inventory 갱신 | skill `/omniverse-asset-inventory-sync` (`.claude/skills/omniverse-asset-inventory-sync/SKILL.md`) |
| 에러 / 실패 진단 (가설 검증 우선) | `docs/tool-diagnostic-map.md` |

장애 진단은 `docs/runbooks/` (kit-stdin-deadlock · cold-boot-timeout · hub-orphan · env-sub-config).

## ⚠️ DO-NOT-EDIT Residual

<!-- DO-NOT-EDIT-START: 본문 / 재현 / 복구 `docs/runbooks/kit-stdin-deadlock.md`. 자동 검증 G1-G7 -->
⚠️ **`subprocess.Popen(... stdin=subprocess.DEVNULL)` 필수** — 누락 시 MCP 자식 kit.exe cold boot hang (L17). 위치: `src/omniverse_kit_mcp/modules/process_module.py::start`. 검증 수치 240 s → 13 s. **"extra_ext_ids race" 진단은 잘못됨** — stdin pipe 가 실원인.
<!-- DO-NOT-EDIT-END -->

## Validation Rules

- **R1** 실 asset 만 — primitive (Cube/Sphere) 대체 금지 (False Positive). 상세: `docs/invariants/scenario-validation.md`
- **R1a** NavMesh bake 는 `simulation_stop` 재호출 후 (`load → stop → bake → query → play → navigate`) — 본문 `kkr-extensions/docs/kit-sdk-pitfalls.md` NavMesh §
- **R2** Robot 동작 (`set_joint_positions` / `navigate_*` / `drive_physics`) 은 `simulation_play` 상태 필수 (`robot_load` 예외) — 상세 `src/omniverse_kit_mcp/modules/CLAUDE.md` Robot
- **R3** `viewport_capture` 후 `Read` tool 시각 검증 의무 — blank/black 이면 조명·카메라·asset 조정 재시도

## 변경 파급 매트릭스

| 변경 대상 | 함께 수정 |
|-----------|----------|
| 새 MCP tool | 7 곳 (`docs/invariants/mcp-tool-add.md`) + `scripts/verify_mcp_sync.py` 수동 1 회 |
| 새 module / scenario action | `docs/invariants/module-add.md` |
| REST endpoint | client + tool 등록 + test + `kkr-extensions/CLAUDE.md` |
| MCP resource | `src/omniverse_kit_mcp/mcp/resources.py` + `tests/unit/test_resources_paths.py` + verify_mcp_sync |
| CLAUDE.md 새 디렉토리 | 이 매트릭스 + 문서 맵 양방향 갱신 |

## Key Decisions

- **LakehouseModule** query only (인터뷰 스펙 확정) — 본문 `src/omniverse_kit_mcp/modules/CLAUDE.md` LakehouseModule
- **Type boundary**: 내부 `@dataclass(slots=True, frozen=True)`, Pydantic 은 Extension REST 경계만. MCP 서버 코드 Pydantic 금지 — 본문 `src/omniverse_kit_mcp/CLAUDE.md` "Type Boundary Convention"
- **MCP server import cache**: 세션 시작 1 회 spawn + import 캐시. `src/omniverse_kit_mcp/` 수정은 Claude Code 재시작 전까지 미반영. 세션 내 검증은 `scripts/run_process_module_standalone.py` / `scripts/run_scenario_standalone.py`
- **Test SoT**: `tests/unit/test_tools_registration.py` 의 EXPECTED frozenset
- **uv 만 사용** (`pip install` 금지); 패키지 추가는 `uv add` / `uv add --dev` — 신규 PC 절차 `setup/CLAUDE.md`

## Environment Variables

| 변수 | 기본값 | 설명 |
|------|-------|------|
| `ISAAC_SIM_BASE_URL` | `http://localhost:8011` | Extension REST |
| `ISAAC_MCP_APP_PROFILE` | `isaac-sim` | Kit app profile — `isaac-sim` or `usd-composer`. 상세: `docs/invariants/multi-app.md` |
| `ISAAC_MCP_INSTANCE_ID` | `1` | 멀티 인스턴스 (1..3). profile base_port 에 offset (Isaac 8011+ / USD Composer 8014+) |
| `ISAAC_SIM_STARTUP_TIMEOUT` | `120.0` | ProcessModule health 대기 상한. 상세: `docs/invariants/process-lifecycle.md` |
| `ISAAC_SIM_EXTRA_EXT_IDS` | config.py bundle | <!-- ⛔ DO-NOT-EDIT: "extra_ext_ids race" 진단은 무효 (L17 참조 `docs/runbooks/kit-stdin-deadlock.md`) --> JSON array. stdin DEVNULL fix 후 8 개 13s 통과 |
| `LAKEHOUSE_BASE_URL` | `http://localhost:9000` | Lakehouse REST |

## Subagent 디스패치 패턴

Subagent 는 sub-CLAUDE.md 자동 로드 안 함. 디스패치 프롬프트에 `Read docs/invariants/<관련>.md first` 명시 또는 필수 맥락 직접 포함.

## 문서 맵

| 파일 | 담당 |
|------|------|
| `src/omniverse_kit_mcp/CLAUDE.md` | FastMCP 서버 루트 (entry / type 경계 / clients) |
| `src/omniverse_kit_mcp/modules/CLAUDE.md` | 모듈 매트릭스 + Character 제약 + base.py 패턴 (→ `integration-facts.md` · `process-ops.md`) |
| `src/omniverse_kit_mcp/scenario/CLAUDE.md` | 시나리오 엔진 (Arrange/Act/Assert/Cleanup + action_registry) |
| `src/omniverse_kit_mcp/tools/CLAUDE.md` | MCP tool 등록 규약 + 그룹별 caveat |
| `kkr-extensions/CLAUDE.md` | Extension 개발 nav hub (→ `docs/*` basics / pitfalls / recipe / reuse / lessons-learned) |
| `scenarios/CLAUDE.md` | YAML 저작 |
| `tests/CLAUDE.md` | pytest 단위 |
| `setup/CLAUDE.md` | 설치 / 신규 PC |
| `scripts/CLAUDE.md` | 개발 스크립트 |
| `docs/CLAUDE.md` | phase 히스토리 / tool-catalog / references |
| `docs/assets/isaac/` | NVIDIA Isaac Sim 5.1 asset URL 카탈로그 SoT (`asset_inventory.md` 진입점 + per-category `assets/*.md`) |

## 메타 — CLAUDE.md 작성 규칙

- **라인 하드캡**: 루트 ≤100 · sub-CLAUDE.md ≤150 · `docs/invariants/*.md` ≤200 · `docs/runbooks/*.md` ≤300 (`test_doc_integrity.py` A3/A4/A6 가드)
- **이관 / 삭제**: 증가 시 `docs/invariants/*.md` 이관 (작업 전 필독) + 위 pull-doc 표 갱신, 장애 대응은 `docs/runbooks/*.md`. **삭제는 stale 한정** (outdated / 중복 / 불용 pointer)
- **`lessons-learned.md` 는 historical incident log** (Phase 3 Task 3.3 확정) — 신규 영구 규칙 추가 금지. 사고 증거 / 재현 절차만 누적
- **sub-CLAUDE.md 규칙**: 디렉토리 고유 규칙만. 루트 / invariants 중복 금지 — cross-cutting 은 pointer 로 대체
