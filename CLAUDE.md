# Isaac-sim-MCP — Project Instructions

## 현재 MCP 표면 확인 (새 세션에서 먼저 볼 것)

| 무엇을 보려고 | 어디를 본다 |
|---------------|-------------|
| 지금 호출 가능한 모든 MCP tool 목록 + 시그니처 + 파라미터 | `docs/tool-catalog.md` — auto-generated, 사람이 읽는 카탈로그 |
| tool 이름의 단일 진실 (SoT) | `tests/unit/test_tools_registration.py` 의 `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset |
| Phase 별 구현 히스토리 (왜 / 어떻게 / 제약) | `docs/phase-a-validation-report.md` … `phase-e-validation-report.md` |
| 도메인별 비자명한 제약 | `src/isaacsim_mcp/modules/CLAUDE.md` (모듈 책임) · `isaac_extension/CLAUDE.md` (Kit SDK 실측) · `src/isaacsim_mcp/tools/CLAUDE.md` (tool group caveat) |

세션 시작 절차:
1. 루트 CLAUDE.md (이 파일) 로 전역 결정 / 검증 규칙 파악
2. `docs/tool-catalog.md` 로 지금 쓸 수 있는 tool 서피스 확인
3. 관련 도메인의 하위 CLAUDE.md 에서 제약 / 실측 사실 확인
4. Phase 히스토리 필요 시 해당 `phase-*-validation-report.md` 만 국소적으로 확인

## Quick Start

```bash
cp .env.example .env   # .env에서 URL 수정
uv sync                # 의존성 설치
uv run pytest tests/   # 테스트
uv run isaacsim-mcp    # MCP 서버 실행 (Claude Code가 자동 실행)
```

## Setup (신규 PC / clone 직후)

```bash
setup\setup-isaacsim-mcp.bat   # uv sync + .env 생성 + ~/.claude.json mcpServers 등록
```

설치 스크립트 상세 동작 및 Extension 활성화 절차는 `setup/CLAUDE.md` 참조.

## Package Management

- **uv만 사용** — `pip install` 직접 사용 금지
- 패키지 추가: `uv add <package>` / `uv add --dev <package>`

## Architecture

```
Claude Code CLI
  ↕ stdio (MCP 프로토콜)
isaacsim-mcp FastMCP 서버 [일반 Python, uv run isaacsim-mcp]
  ├─ HTTP REST (http://localhost:8011) → Extension endpoints
  └─ subprocess / OS 명령 → Isaac Sim 프로세스 제어 (start/stop/restart)
omni.mycompany.validation_api Extension [Isaac Sim GUI 내부]
  ↕
omni.kit.commands / omni.usd / omni.timeline / pxr.*
```

## 설계 원칙

**Isaac Sim GUI 유저가 할 수 있는 모든 것을 Claude Code 도 MCP tool 로 할 수 있어야 한다.**
Isaac Sim App 의 Asset Browser / Viewport Create menu / Stage 패널 / File menu / Simready Explorer 등 어떤 경로로든 유저가 수행하는 동작은 MCP tool 로 동등하게 제공하며, 없으면 Phase 진행 과정에서 필요 시점에 바로 추가한다. 프로세스 실행/종료, Scene 조작, 시뮬레이션 제어, Viewport 캡처, 파일 입출력, 선택 상태 모두 Claude Code 가 완전 자율 제어할 수 있어야 한다.

새 도메인 (캐릭터/애니메이션, Extension UI 자동화, 실전 Extension 검증 등) 도입 시 "GUI 유저가 할 수 있는 것 중 MCP 에 아직 없는 것"을 항상 먼저 식별하고 보완한다. 자연어로 받은 엔드투엔드 지시 (예: "새 Extension 만들고 버튼 클릭 동작을 스스로 검증") 는 MCP tool 조합만으로 실행 가능해야 한다.

## CLAUDE.md 작성 규칙

**포함 기준** — 코드를 읽어도 알 수 없는 내용만 적는다.
- 아키텍처 결정 + 그 이유 (이유 없는 결정은 판단 불가)
- 비명시적 제약과 위험한 함정
- 새 세션에서 이 디렉토리 작업을 시작할 때 반드시 먼저 알아야 하는 것

**제외 기준**
- 변경 이력 / 패치 노트 → git commit message
- 시점 스냅샷 데이터 (테스트 수, 측정값, 날짜 기준 수치) → 항상 부정확해짐
- 코드를 읽으면 알 수 있는 내용 → 코드 주석

**각 하위 CLAUDE.md 구조**
```
1. 이 디렉토리가 하는 일 (1-2 문장)
2. 비명시적 규칙 / 제약 / 결정 (이유 포함)
3. 관련 경계 (다른 CLAUDE.md 포인터)
```

**Phase 완료 시 필수 업데이트**
- 이 파일의 Phase 로드맵 상태 (`❌ 미시작` → `✅ 완료`) + 핵심 산출물 열
- 새 tool/endpoint/module 이 추가됐다면 변경 파급 매트릭스에 행 추가
- 관련 하위 CLAUDE.md 의 tool 목록·endpoint 목록 동기화
- `docs/phase-{N}-validation-report.md` 신규 — 해당 Phase 의 구현 결정 / 라이브 검증 결과 / 남은 한계
- `scripts/generate_tool_catalog.py` 재실행 (`docs/tool-catalog.md` 갱신) — 또는 `scripts/verify_mcp_sync.py` 가 이를 자동으로 수행
- `uv run pytest tests/` 전체 PASS 확인

## Scope-specific CLAUDE.md

디렉토리별 세부 지침은 해당 `CLAUDE.md`를 참조. 서브 에이전트는 작업 디렉토리의 파일을 자동 로드한다.

| 파일 | 작업 컨텍스트 |
|------|--------------|
| `isaac_extension/CLAUDE.md` | Kit Extension 내부 (FastAPI router, Pydantic 모델, Kit SDK 실측 사항, REST endpoints) |
| `src/isaacsim_mcp/CLAUDE.md` | FastMCP 서버 패키지 루트 (entry flow, 타입 경계, clients 통신 규약) |
| `src/isaacsim_mcp/modules/CLAUDE.md` | 도메인 모듈 — 모듈 책임 매트릭스, REST 응답 특성(Integration Facts), kit.exe 런타임 플래그 |
| `src/isaacsim_mcp/scenario/CLAUDE.md` | 시나리오 엔진 — Arrange/Act/Assert/Cleanup 내부 |
| `src/isaacsim_mcp/tools/CLAUDE.md` | MCP tool 등록 규약 + tool 그룹별 caveat (전체 tool 목록은 `tests/unit/test_tools_registration.py` frozenset SoT) |
| `tests/CLAUDE.md` | pytest 단위 테스트 (mock 기반, live E2E 제외) |
| `scenarios/CLAUDE.md` | YAML 시나리오 저작 가이드 |
| `setup/CLAUDE.md` | 설치 스크립트 (`.env`, `~/.claude.json` 등록, Extension 활성화) |
| `docs/references/CLAUDE.md` | Isaac Sim 레퍼런스 — ext 카탈로그 + testbed 스냅샷 + nvidia-docs |
| `docs/CLAUDE.md` | 문서 루트 — Phase 히스토리 vs live tool 카탈로그 분리, phase report 작성 규칙, tool-catalog regen 절차 |
| `docs/tool-catalog.md` | MCP tool 전체 카탈로그 (signature + description + 파라미터) — `scripts/generate_tool_catalog.py` 로 auto-generate, `tests/unit/test_tool_catalog_sync.py` 가 frozenset SoT 와 동기화 검증. 외부 세션에서 "쓸 수 있는 tool 목록 한눈에 보기" 용 |
| `docs/phase-progress.md` | Phase E~H + PPTX 세션의 Task 별 체크박스 + 타임스탬프. 각 세션은 시작 시 여기서 현재 위치 파악, 완료 시 해당 Task 를 ✅ 로 갱신 |
| `scripts/CLAUDE.md` | 개발 스크립트 (lifecycle / live 검증 / catalog regen / verify_mcp_sync) 목적 + 실행 조건 |
| `isaac_course/CLAUDE.md` | **Isaac Sim Digital Twin 튜토리얼 프로젝트** (28-슬라이드 PPTX + 3 Twin USD + 전 캡처) 루트 규칙 (R1~R9). 산출물은 세션 2 에서 생성 |
| `isaac_course/docs/asset_inventory.md` | 3 Twin 에 사용하는 Isaac Sim 공식 S3 + SimReady Explorer asset 의 확정 USD 경로 단일 원천. 세션 1 실측, 세션 2 참조 |
| `last-prompt.md` | Phase E~H + PPTX 전체 마스터 네비게이션 — 5 세션 구조·공통 규칙·문서 맵 |
| `prompts/{phase-e,pptx,phase-f,phase-g,phase-h}.md` | **각 세션 전용 주입 프롬프트** — 새 세션에 해당 파일을 주입하면 해당 Phase/PPTX 를 end-to-end 자율 수행. 각 프롬프트가 프로젝트 전체 맥락·이전/다음 Phase 관계·자율 규칙을 포함해 문맥 연결성 보장 |

## 변경 파급 매트릭스

새 기능 추가 시 함께 수정해야 하는 곳. 서브에이전트 프롬프트 작성 전 확인.

| 변경 대상 | 함께 수정해야 하는 곳 |
|-----------|----------------------|
| REST 엔드포인트 추가 (`isaac_extension/`) | `clients/isaac_rest_client.py` + `tools/` — MCP tool 등록 / `tests/` — tool 등록 테스트 / `isaac_extension/CLAUDE.md` 관련 섹션 (HTTP status · 비자명한 제약) |
| 새 module 추가 (`modules/`) | `types/common.py` ModuleName enum + `scenario/schema.py` + `scenarios/schema/scenario.schema.json` enum + `scenario/runner.py` dispatch dict + `scenario_tools.py` register 시그니처 + `mcp/server.py` wiring + `modules/CLAUDE.md` 책임 매트릭스 |
| 새 module 메서드 | `scenario/action_registry.py` (typed request 빌더) 또는 **kwargs 폴백 허용 / `tests/` |
| **새 MCP tool (`tools/`)** | **⓵ `isaac_extension/` REST 엔드포인트 · `clients/isaac_rest_client.py` · `tools/module_tools.py` @mcp.tool() · `tests/conftest.py` MockIsaacRestClient +메서드 · `tests/unit/test_tools_registration.py` EXPECTED_{MODULE,SCENARIO}_TOOLS frozenset · `tools/CLAUDE.md` 그룹 caveat**<br>**⓶ 반드시 재생성**: `.venv/Scripts/python.exe scripts/generate_tool_catalog.py` (또는 `scripts/verify_mcp_sync.py`)<br>**⓷ drift 검증**: `uv run pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py` |
| scenario action 추가 | `action_registry.py` + `scenario.schema.json` + `schema.py` 3곳 동시 수정 / `tests/unit/test_scenario_integration.py` / `scenarios/CLAUDE.md` 모듈별 액션 가이드 |
| context-aware action 추가 | `action_registry.py` `CONTEXT_AWARE_ACTIONS` + `runner._execute_context_aware` 분기 / 필요 시 ctx 에서 선행 step data 해소 |
| ASYNC Job 동작 추가 | Extension `services/job_service.py` 의 `start_job(coro_factory)` 사용 / try-except 필수 (silent catch 금지) / tool 은 job_id 반환, Claude Code 가 `job_status` 폴링 |
| CLAUDE.md에 새 디렉토리 추가 | 이 매트릭스 업데이트 + 관련 경계 양방향 확인 + 루트 CLAUDE.md "Scope-specific CLAUDE.md" 표 갱신 |
| Phase 완료 | `docs/phase-{N}-validation-report.md` 신규 · 이 파일의 Phase 로드맵 표 행 갱신 · `scripts/generate_tool_catalog.py` 재실행 · 관련 하위 CLAUDE.md tool/endpoint 목록 동기화 · `uv run pytest tests/` 전체 green |

**한 줄 요약**: "새 tool 등록 = 서피스 변경 + auto-regen 카탈로그 + drift test 통과". 이 세 가지 중 하나라도 빠지면 `test_tool_catalog_sync` 또는 `test_tools_registration` 이 fail 한다. 배경 자동화가 없으므로 개발자가 `scripts/verify_mcp_sync.py` 를 **반드시** 수동으로 1 회 실행해야 한다 (이 스크립트는 regen + drift test 를 한 번에 돌린다).

## Phase 로드맵

| Phase | 내용 | 상태 | 핵심 산출물 |
|-------|------|------|------------|
| **A** | Extension WRITE + REST 실구현 | ✅ 완료 (`docs/phase-a-validation-report.md`) | scenario 엔진, simulation 모듈 Stage WRITE 라우팅, viewport/process 호환성 |
| **B** | 로봇 제어 + ASYNC Job + Asset Browser + GUI 동등 (File/Selection/Camera) | ✅ 완료 (`docs/phase-b-validation-report.md`) | Robot/Job/Asset 모듈, `job.status` context-aware polling, articulation 사전 검증, `asset_list`, `stage_save/open/new`, `stage_get/set_selection`, `viewport_set_active_camera` |
| **C** | 캐릭터 + 애니메이션 (`CharacterUtil`, `AnimationGraph`) | ✅ 완료 (`docs/phase-c-validation-report.md`) | CharacterModule + ModuleName.CHARACTER, JobService 재사용, `extra_ext_ids` 로 anim/navigation/replicator bundle 자동 활성화 |
| **D** | Extension UI 자동화 (`omni.kit.ui_test`, `carb.logging` 캡처) — Goal 2 | ✅ 완료 (`docs/phase-d-validation-report.md`) | ExtensionModule +4 method (`activate` / `get_ui_tree` / `ui_invoke` / `capture_logs`), `services/ui_service.py` + `services/log_capture_service.py`, `omni.mycompany.ui_demo` 데모 extension, `omni.kit.ui_test` + `omni.mycompany.ui_demo` 를 `extra_ext_ids` 기본 포함 |
| **E** | Sensor + Multi-viewport + NavMesh Viz (58 → 65) | ✅ 완료 (`docs/phase-e-validation-report.md`, Part 1 = Sensor/Viewport/NavMesh Viz, Part 2 = Window/Navigation/log clear) | SensorModule 신규 (+ModuleName.SENSOR) + Camera prim 기반 RTX attach, ViewportModule `create/destroy` (idempotent), NavigationModule `set_visualization` (carb.settings + prim visibility 폴백). 관련 scenario 6 (smoke 5 + integration 1), live scripts 3 (heavy/minimal dual-mode, `LIVE_HEAVY_ENV` env 토글). 채택 근거: `isaac_course/docs/navmesh_viz_research.md` |

각 Phase의 상세 진행 프롬프트는 Notion "Isaac Sim MCP" 페이지 하단 참조. tool/endpoint 개수는 `tests/unit/test_tools_registration.py` 의 `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset 이 SoT. 사람이 읽는 카탈로그는 `docs/tool-catalog.md` (auto-generated; 변경 후 `.venv/Scripts/python.exe scripts/generate_tool_catalog.py` 실행).

## Project-wide Validation Rules (필수 준수)

**R1. 모든 Isaac Sim 검증은 실제 로드 가능한 asset 으로 수행.** `Cube` / `Sphere` 같은 primitive 를 "의자 대용 / 로봇 대용" 으로 사용한 검증은 **무효**. 동작 확인은 반드시 `/assets/list` 로 탐색하거나 알려진 S3 경로 (예: `.../Environments/Office/Props/SM_Armchair.usd`, `.../Robots/NVIDIA/NovaCarter/nova_carter.usd`, `.../People/Characters/Biped_Setup.usd`) 에서 로드한 실제 USD 로. 이유: primitive 는 bbox · pivot · forward axis · physics material · mesh topology 특성이 실 asset 과 전혀 다르다 → Cube 로 통과한 로직이 실제 asset 에서 실패하는 False Positive 를 빈번히 발생시킨다. 해당 실패는 예전 세션의 chair sit 검증에서 실측됨 (Cube 에선 동작, 실 Armchair 에선 NavMesh step-up 문제 노출).

**R1a. NavMesh bake 는 R2 와 정반대로 timeline stopped 상태에서만 성공.** `navigation.bake` 는 playing 중엔 `get_navmesh()` 가 None (bake 자체는 True 반환하는 False Positive 존재). `stage.load_usd` · `robot.load` · `stage.create_prim` · `stage.set_property` · `viewport.capture`(settle_frames) · `window.capture` 는 모두 timeline 을 advance 시키므로, stage mutation 이후 bake 직전에 반드시 `simulation.stop` 을 한 번 더 호출. 표준 Robot navigation 시퀀스: `load → stop → bake → query_path → play → navigate_path`. Extension 내부에 precondition 체크 없음 — 호출자 (scenario / script) 책임.

**R2. Robot 관련 모든 동작은 `simulation.play` 상태에서만 검증.** `robot.load` 는 예외지만, `robot.set_joint_positions` / `robot.navigate_to` / `robot.navigate_path` 등 **움직임 / 관절 / 물리 상호작용 모든 동작** 은 timeline 이 playing 일 때만 실행한다. 이유: PhysX articulation view 는 physics step 이 돌아야 populate 되고, 휠 회전·마찰·충돌·중력이 active 하지 않으면 결과가 실제 시뮬레이션과 괴리된다. Extension `robot_service.navigate_path` 는 `omni.timeline.is_playing()` 을 사전 검증하고 아니면 HTTP 400 으로 거부한다. scenario 는 `act` 단계 진입 전 `simulation.play` 를 arrange 에 필수 배치. 참고: 현재 `navigate_path` 는 `xformOp:translate` kinematic override 방식이므로 physics 가 active 해도 robot 자체는 kinematic 이동 — 진정한 wheel torque 기반 navigation 은 Phase D+ 에서 OmniGraph Differential Controller 로 확장 예정.

## Key Decisions

- LakehouseModule은 **query only** (inject/cleanup 없음) — 인터뷰 스펙 확정
- 내부 타입은 `dataclass(slots=True, frozen=True)`, REST 경계만 Pydantic
- 경로 순회 보안: `scenario_tools.py`의 `_resolve_safe_path()`가 scenarios_dir 경계 강제
- Cleanup은 assert 실패 시에도 항상 실행 (finally 블록)
- `action_registry.py`가 YAML args dict → typed request 매핑 담당 + `CONTEXT_AWARE_ACTIONS` 집합에 포함된 액션은 runner 가 ctx 에서 선행 step data 를 해소하여 dispatch
- Stage WRITE 액션(`stage_load_usd`, `stage_set_property`, `stage_create_prim`, `stage_delete_prim`)은 `ModuleName.SIMULATION` 아래 등록 — 툴 layer 와 일치(SimulationModule 이 실제 구현)
- **MCP server 는 Claude Code 세션 시작 시 Python import 를 캐시**. `src/isaacsim_mcp/` 코드 변경은 Claude Code 재시작 전까지 반영 안 됨. 세션 중 검증하려면 `scripts/run_scenario_standalone.py` / `scripts/run_process_module_standalone.py` 사용 (Extension 코드는 kit.exe 재기동으로 즉시 반영)
- ProcessModule 은 kit.exe stdout/stderr 를 `%TEMP%/isaacsim_mcp/kit_<epoch>.log` 로 리다이렉트 — OS pipe 버퍼 포화로 인한 기동 정지 방지
- **`continueOnFailure: true` 는 phase terminal status 에 영향 주지 않음**. 해당 step 이 FAILED/ERROR 여도 phase 는 계속 진행하고 terminal 판정에서 제외 — 옵셔널 동작 (articulation 없는 USD 에 `robot.set_joint_positions` 시도 등) 을 표현할 때 사용
- **ASYNC Job 패턴**: Extension `JobService` 가 `asyncio.create_task` 로 background 실행, in-memory dict + TTL 1h cleanup. MCP tool `robot_navigate_to` / `character_navigate_to` 는 job_id 즉시 반환, `job_status` polling, `job_cancel` 로 취소. Scenario 에서는 `job.status` (context-aware) 가 `navigate_step_id` 로 ctx 의 `*NavigateResult.job_id` 를 resolve (Robot/Character 동일 경로). Extension 재시작 시 in-flight job 전부 손실 (REST 404) — 장기 작업은 MCP 측에서 재시도 책임
- **Articulation strict**: `robot.get/set_joint_positions` 는 Extension `robot_service._assert_articulation()` 으로 PhysxArticulationAPI 없으면 HTTP 400. Silent no-op 방지. PhysX 가 articulation view 를 populate 하려면 최소 1회 physics step 이 돌아야 하므로 scenario arrange 에 `simulation.play → pause` 를 넣어 warm-up. 옵셔널 step 은 `continueOnFailure: true` 로 감쌀 것
- **Test SoT 전환**: `test_tools_registration.py` 는 `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset 을 SoT 로 두고 count assertion 은 `len()` 으로 유도. Phase 추가 시 list 만 수정 → literal count 추적 불필요
- **Asset catalog 접근**: Isaac Sim 5.1 의 `isaacsim.storage.native.get_assets_root_path()` 가 기본으로 공개 S3 bucket 반환 — Nucleus 없이 Franka / UR / Jetbot 등 공식 USD 접근 가능. `asset_list` MCP tool 이 `omni.client.list` 로 디렉토리 listing 을 MCP 경계로 노출 → GUI Asset Browser 와 동일한 카탈로그를 Claude Code 가 탐색 가능. 카테고리: `robots` / `environments` / `props` / `people` / `materials` / `isaaclab` (`isaacsim.asset.browser` config mirror)
- **Character placement**: `character.load` 는 항상 `/World/Characters/<sanitized_name>` 아래에 prim 을 배치 (`CharacterUtil.load_character_usd_to_stage` 내부 규약). response 의 `sanitized_prim_path` 가 실제 배치 경로이고, `prim_path` 는 caller 요청 echo. 후속 `set_position` / `play_animation` / `get_state` 는 `sanitized_prim_path` 기준. Biped_Setup rig 은 `/World/Characters/Biped_Setup` 에 1회 로드 후 모든 캐릭터 공유 (상세: `src/isaacsim_mcp/modules/CLAUDE.md` "CharacterModule behavioural limits")
- **Character scenario 는 shutdown tick 필수 (testbed #14)**: scenario cleanup 에 `simulation.play → step → stop` 을 `isaac_sim_stop` 이전에 반드시 실행. 생략 시 AnimGraph / NavMesh 내부 핸들 정리 타이밍 문제로 kit.exe 셔다운 hang. `scenarios/smoke/character_control.yaml` 이 canonical pattern
- **AnimGraph ready retry (testbed #13)**: `ag.get_character(prim_path)` 는 `world.reset` 직후 graph registry populate 지연으로 None 을 반환할 수 있음. Extension `_ensure_animation_ready` 가 1-frame `simulation_play → pause` warm-up 후 재시도로 보완하지만, scenario arrange 에 `simulation.play → pause` 를 명시하는 것이 결정적 타이밍 확보상 권장
- **AnimGraph 가 root transform override**: character 가 `ApplyAnimationGraphAPICommand` 로 bound 되면 AnimGraph 가 매 tick `xformOp:translate` 를 덮어쓴다. `character.set_position` 은 USD 레벨 write 성공 + 다음 tick 에 AnimGraph 복원 (response 의 position 은 정상이지만 시각적 이동 X). visible move 가 필요하면 `character.navigate_to` 사용 또는 load 시 `position` 으로 초기 위치 지정
- **Character navigate 는 timeline playing 필수**: `character.navigate_to` Job 은 AnimGraph / NavMesh tick 에 의존. `simulation.stop` / `pause` 상태에서는 0m 이동 후 30s timeout → done. traversal 검증 시나리오는 navigate 전 `simulation.play`, 완료 후 `simulation.pause` 를 act 에 배치
- **Window capture vs Viewport capture 는 별개 도메인**: `/viewport/capture` 는 3D 카메라 RTX 렌더 (scene 검증용). `/window/capture` 는 kit.exe 메인 윈도우를 **Win32 PrintWindow** 로 OS 레벨 스크린샷 — Stage / Property / Content / Timeline 등 GUI chrome 전체 포함 (튜토리얼·문서·메뉴 검증용). 둘 다 GUI 모드 필수 (headless 는 빈 결과). 상세: `isaac_extension/CLAUDE.md` "Window capture & UI automation"
- **`isaacsim.exp.full.kit` preset 은 `isaacsim.asset.browser` 를 포함하지 않음**: `Window > Browsers > Isaac Sim Assets` 메뉴 항목은 존재하지만 창을 실제 생성하는 `isaacsim.asset.browser` 가 preset 에 없어서 기본 기동 시 창이 안 뜨고 `menu_trigger` 도 silent no-op. 이 창이 필요하면 `ISAAC_SIM_EXTRA_EXT_IDS` 에 `isaacsim.asset.browser` 추가 (ProcessModule 이 이를 `--enable` 플래그로 전개). 실제 창 title 은 `Isaac Sim Assets [Beta]` — 메뉴 label 과 상이하므로 아래 UI Window title 규칙 참조
- **UI Window title ≠ 메뉴 label**: Kit 의 Browser 계열 창은 자주 `[Beta]`/`[Experimental]` 등 suffix 를 달고 등록된다 (예: 메뉴 "Isaac Sim Assets" → 창 `Isaac Sim Assets [Beta]`). `/window/ui_show` 는 exact title 실패 시 case-insensitive substring fallback 을 자동 시도 (응답 `resolved_via: "exact"|"substring"`). 신규 UI 자동화 코드는 menu label 로 창을 가정하지 말고 fallback 결과를 신뢰할 것
- **Browser 창은 lazy-instantiated**: `omni.ui.Workspace.get_windows()` 는 이미 인스턴스화된 창만 반환. Browser 패널은 첫 `show_window` 호출 전까지 목록에 안 보인다. 전체 Browser 를 enumerate 하려면 `menu_list → menu_trigger 각 항목 → ui_list 재조회` 순서 필수
- **Browser 썸네일 로딩은 extension 별로 상이**: `isaacsim.asset.browser` (`Isaac Sim Assets [Beta]`) 는 첫 open 시 NVIDIA 공개 S3 를 실시간 crawl 하여 카테고리별 썸네일을 async fetch — 즉시 capture 시 빈 그리드로 찍힌다. `omni.kit.browser.asset` (`NVIDIA Assets`), `omni.simready.explorer` (`SimReady Explorer`) 는 cached catalog 포함 → 즉시 populate. S3-crawl 브라우저의 의미 있는 스크린샷은 show 후 10–30 s 추가 settle 또는 명시적 카테고리 click (Phase D UI automation 영역) 필요
- **Kit SDK 실측 사실 (`omni.kit.ui_test` path grammar · `ExtensionManager.set_extension_enabled_immediate` · `carb.logging` 5-arg 콜백 · `LogCaptureService` peek 규약) 은 `isaac_extension/CLAUDE.md` 가 authoritative** — Extension 코드 작업 시 해당 파일 로드

## Environment Variables

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ISAAC_SIM_BASE_URL` | `http://localhost:8011` | Isaac Sim REST API |
| `ISAAC_SIM_STARTUP_TIMEOUT` | `240.0` | `ProcessModule.start()` health 대기 상한(초) — Isaac Sim 첫 기동 셰이더 컴파일 고려 |
| `ISAAC_SIM_EXTRA_EXT_IDS` | `["omni.anim.graph.bundle","omni.anim.navigation.bundle","isaacsim.replicator.agent.core"]` | kit.exe 런치 시 추가 활성화 extension (JSON array only, pydantic-settings v2 limitation) |
| `LAKEHOUSE_BASE_URL` | `http://localhost:9000` | Lakehouse REST API |
| `MCP_SERVER_PORT` | `8080` | MCP 서버 포트 |
| `SCENARIOS_DIR` | `scenarios` | 시나리오 YAML 루트 경로 |

## 다음 세션 작업

새 세션 시작 시 작업 디렉토리(`~/workspace/Isaac-sim-MCP/`)의 이 CLAUDE.md가 자동 로드됨. testbed 의 `src/isaac_sim_testbed/CLAUDE.md` (API 특이사항 #1-#17) 는 로봇/캐릭터 도메인 작업 시 별도 참조.

후보 backlog (우선순위 순):

1. **Robot 진정한 wheel-torque navigation** — 현재 `robot.navigate_to` / `navigate_path` 는 `xformOp:translate` kinematic override. OmniGraph `DifferentialController` 통합으로 PhysX 휠 마찰 기반 주행. R2 주석 참조. 로봇별 articulation spec 매핑이 가장 큰 작업
2. **실전 Extension workflow 자동 검증** — `omni.mycompany.ui_demo` / `ui_demo_advanced` 가 아닌, KKR-A 같은 실제 생산용 Extension 에 `extension_get_ui_tree` / `extension_ui_invoke` / `window_menu_trigger` / `extension_capture_logs` 조합을 적용. `_WIDGET_TYPES` 가 커버 못 하는 custom widget class 를 실전에서 발견하고 allow-list 확장
3. **Scenario engine variable templating 강화** — 현재 `${variable}` 치환은 compile time. 실행 중 step output 을 다음 step args 에 주입하는 패턴 (예: `captured_artifact_path`) 이 아직 없음 — context-aware action 패턴 확대
