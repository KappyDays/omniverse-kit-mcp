# Isaac-sim-MCP — Project Instructions

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

Phase C/D 에서도 이 원칙 유지: 새 도메인 (캐릭터/애니메이션, Extension UI 자동화 등) 도입 시, "GUI 유저가 할 수 있는 것 중 MCP 에 아직 없는 것"을 항상 먼저 식별하고 보완한다.

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
- 이 파일의 Phase 로드맵 상태 (`❌ 미시작` → `✅ 완료`)
- 새 tool/endpoint/module이 추가됐다면 변경 파급 매트릭스에 행 추가
- 관련 하위 CLAUDE.md의 tool 목록·endpoint 목록 동기화

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

## 변경 파급 매트릭스

새 기능 추가 시 함께 수정해야 하는 곳. 서브에이전트 프롬프트 작성 전 확인.

| 변경 대상 | 함께 수정해야 하는 곳 |
|-----------|----------------------|
| REST 엔드포인트 추가 (`isaac_extension/`) | `clients/isaac_rest_client.py` + `tools/` — MCP tool 등록 / `tests/` — tool 등록 테스트 |
| 새 module 추가 (`modules/`) | `types/common.py` ModuleName enum + `scenario/schema.py` + `scenarios/schema/scenario.schema.json` enum + `scenario/runner.py` dispatch dict + `scenario_tools.py` register 시그니처 + `mcp/server.py` wiring |
| 새 module 메서드 | `scenario/action_registry.py` (typed request 빌더) 또는 **kwargs 폴백 허용 / `tests/` |
| 새 MCP tool (`tools/`) | `isaac_extension/` — REST 엔드포인트 / `tests/unit/test_tools_registration.py` 의 expected count 와 list |
| scenario action 추가 | `action_registry.py` + `scenario.schema.json` + `schema.py` 3곳 동시 수정 / `tests/unit/test_scenario_integration.py` |
| context-aware action 추가 | `action_registry.py` `CONTEXT_AWARE_ACTIONS` + `runner._execute_context_aware` 분기 / 필요 시 ctx 에서 선행 step data 해소 |
| ASYNC Job 동작 추가 | Extension `services/job_service.py` 의 `start_job(coro_factory)` 사용 / try-except 필수 (silent catch 금지) / tool 은 job_id 반환, Claude Code 가 `job_status` 폴링 |
| CLAUDE.md에 새 디렉토리 추가 | 이 매트릭스 업데이트 + 관련 경계 양방향 확인 |

## Phase 로드맵

| Phase | 내용 | 상태 | 핵심 산출물 |
|-------|------|------|------------|
| **A** | Extension WRITE + REST 실구현 | ✅ 완료 (`docs/phase-a-validation-report.md`) | scenario 엔진, simulation 모듈 Stage WRITE 라우팅, viewport/process 호환성 |
| **B** | 로봇 제어 + ASYNC Job + Asset Browser + GUI 동등 (File/Selection/Camera) | ✅ 완료 (`docs/phase-b-validation-report.md`) | Robot/Job/Asset 모듈, `job.status` context-aware polling, articulation 사전 검증, `asset_list`, `stage_save/open/new`, `stage_get/set_selection`, `viewport_set_active_camera` |
| **C** | 캐릭터 + 애니메이션 (`CharacterUtil`, `AnimationGraph`) | ✅ 완료 (`docs/phase-c-validation-report.md`) | CharacterModule + ModuleName.CHARACTER, JobService 재사용, `extra_ext_ids` 로 anim/navigation/replicator bundle 자동 활성화 |
| **D** | Extension UI 자동화 (`omni.kit.ui_test`) — Goal 2 | ⏸ 대기 | — |

각 Phase의 상세 진행 프롬프트는 Notion "Isaac Sim MCP" 페이지 하단 참조. tool/endpoint 개수는 `tests/unit/test_tools_registration.py` 의 `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset 이 SoT.

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

각 Phase 진행은 별도 세션(컨텍스트 클린)에서 시작. 각 Step 프롬프트는 Notion **"Isaac Sim MCP"** 페이지 하단의 세부 페이지로 나뉘어 작성되어 있음. 다음은 **Phase D — Extension UI 자동화 + KKR-A 실전 테스트**.

새 세션 시작 시 작업 디렉토리(`~/workspace/Isaac-sim-MCP/`)의 이 CLAUDE.md가 자동 로드됨. testbed 의 `src/isaac_sim_testbed/CLAUDE.md` (API 특이사항 #1-#17) 는 로봇/캐릭터 도메인 작업 시 별도 참조.
