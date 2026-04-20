# Isaac-sim-MCP — Project Instructions

## 세션 시작 절차 — 필독 CLAUDE.md

**모든 세션은 시작 시점에 아래 "필수 3 개" 를 먼저 읽는다.** 작업 종류가 정해진 세션은 해당 scope 파일도 **선제 로드** — 문제 발생 후에 뒤늦게 grep 으로 찾지 말 것. 이 프로젝트에서 이미 발생한 사례: `modules/CLAUDE.md` 의 "ProcessModule hang recovery" 섹션을 몰라 Isaac Sim 기동 이슈 debugging 에 불필요한 시간 낭비.

### 필수 (모든 세션)
- 루트 `CLAUDE.md` (이 파일)
- `docs/tool-catalog.md` — 지금 호출 가능한 모든 MCP tool (signature + parameters)
- `docs/phase-progress.md` — 현재 Phase / Task 진행 상태

### 작업 종류별 필독

| 작업 종류 | 필독 CLAUDE.md |
|-----------|----------------|
| Isaac Sim 기동 / 종료 / 라이프사이클 | `src/isaacsim_mcp/modules/CLAUDE.md` (**"ProcessModule hang recovery" 섹션 필독**) |
| **USD 로드 (stage_load_usd / stage_open / robot_load / character_load)** | **이 파일 "kit.exe USD 로드 — 근본 원인 + 해결 프로토콜 (변경 금지)" 섹션 필독** — S3 URL 필수 (`file:///` 금지), Extension `log_capture.start()` 는 MDL resolver loop 시 carb thread 와 Kit main loop deadlock 유발하므로 **반드시 disable 유지**, 좀비 시 `cmd //c "taskkill /F /IM kit.exe /T"` |
| MCP 코드 수정 (새 tool · module · client) | `src/isaacsim_mcp/CLAUDE.md` + `modules/CLAUDE.md` + `src/isaacsim_mcp/tools/CLAUDE.md` |
| Extension 내부 (REST router · service · Kit SDK) | `isaac_extension/CLAUDE.md` |
| Scenario YAML 저작 | `scenarios/CLAUDE.md` + `src/isaacsim_mcp/scenario/CLAUDE.md` |
| 테스트 작성 | `tests/CLAUDE.md` |
| Setup / `.env` / 새 PC | `setup/CLAUDE.md` |
| PPTX · 튜토리얼 산출물 | `isaac_course/CLAUDE.md` + `isaac_course/docs/asset_inventory.md` |

Phase 히스토리 / 구현 결정 / 과거 실측은 `docs/phase-{a..e}-validation-report.md` (필요시만). tool 이름 SoT 는 `tests/unit/test_tools_registration.py` 의 `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset.

## Foundation — Isaac Sim App 기동이 모든 MCP tool 의 전제

이 MCP 서버의 최종 목표는 **Isaac Sim App 을 LLM 이 자연어로 완전 조작** 할 수 있게 하는 것. 모든 stage / viewport / character / robot / sensor / scenario tool 은 `kit.exe` 가 기동되어 `GET /validation/v1/health` 가 200 을 응답할 때까지 의미가 없다.

| Tool | 동작 | 정상 시간 |
|------|------|----------|
| `isaac_sim_start` | kit.exe 런치 + health polling (2 s interval) | cold ≤30 s · warm ≤15 s (실측 15.4 / 12.1 s) |
| `isaac_sim_stop` | `powershell Stop-Process -Name kit -Force` + 종료 확인 | ≤10 s |
| `isaac_sim_restart` | stop → `isaac_extension/.../__pycache__` clear → start | stop + start 합 |

**핵심 구현**: `src/isaacsim_mcp/modules/process_module.py::_prepare_launch_env()` 가 NVIDIA 공식 `isaac-sim.bat` + `setup_ros_env.bat` 의 env setup (`ROS_DISTRO=humble` / `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` / `PATH` 에 `<ISAAC_SIM_ROOT>/exts/isaacsim.ros2.bridge/humble/lib` 추가) 을 Python 으로 재현해 `subprocess.Popen(env=env)` 로 전달한다. 이 step 을 생략하면 ROS2 bridge 의존 Kit extension 이 startup 훅에서 silent fail → kit.exe 이벤트 루프 정지 → `/health` 영영 미응답 → timeout. `.bat` 을 cmd wrapper 로 호출하지 않는 이유는 프로세스 트리를 평평하게 유지하기 위함 (`Get-Process -Name kit` 이 wrapper 와 실 프로세스를 헷갈리지 않도록).

`.env` 의 `ISAAC_SIM_STARTUP_TIMEOUT=600.0` — cold boot + 8 개 extra ext 조합의 안전 마진. 실측 15~30 s 이지만 상한은 넉넉히.

**검증 (세션 재시작 없이 최신 코드 확인)**:
```bash
.venv/Scripts/python.exe scripts/run_process_module_standalone.py stop
.venv/Scripts/python.exe scripts/run_process_module_standalone.py start
.venv/Scripts/python.exe scripts/run_process_module_standalone.py restart
```

**회복 절차 (timeout 재발)**: `src/isaacsim_mcp/modules/CLAUDE.md` 의 "ProcessModule hang recovery" — 좀비 판정 지표 · 강제 종료 · Minimal ext 수동 런치 · log 분석 순서 기록됨.

## kit.exe USD 로드 — 근본 원인 + 해결 프로토콜 (변경 금지)

> **2026-04-20 세션 2 근본 해결 확정**. 사용자 실증: isaac-sim.bat 기동 Kit (Extension 없음) + GUI drag&drop 성공 vs ProcessModule 기동 Kit (validation_api ext 포함) + GUI drag&drop **조차 hang**. → Extension 자체가 범인.

### 근본 원인 (재발 시 동일 증상 확인 필수)
**`LogCaptureService` 의 carb log callback** (`carb.logging.add_logger(cb)`) 이 등록된 상태에서 Kit 5.1 MDL resolver 가 S3 asset 의 Materials.usd 를 열면 `"Disabling base URL to resolve MDL identifier 'OmniPBR.mdl'"` 메시지를 수십 번 반복 → 매번 Python callback 이 carb thread 에 GIL 경합 → Kit main event loop 와 deadlock → 모든 MCP tool 92 s timeout.

### 해결 3 요소 (변경 금지)

**1. Extension `log_capture.start()` 호출 disable** (`isaac_extension/.../extension.py`):
```python
# on_startup 에서:
self._log_capture = None   # NOT: get_log_capture_service().start()
```
→ `extension_capture_logs` / `extension_clear_logs` MCP tool 은 **no-op 상태**. 필요 시 per-request start/peek/stop 으로 refactor.

**2. stage_service `load_usd` 는 run_coroutine + wrap_future** (`isaac_extension/.../services/stage_service.py`):
```python
import omni.kit.async_engine
future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
prim = await asyncio.wrap_future(future)
```
→ FastAPI event loop ≠ Kit main event loop. coroutine 을 Kit main loop 에 명시적 schedule + asyncio 방식 await → FastAPI loop 는 free, Kit main loop 는 자기 tick 진행.

**3. `CreatePayloadCommand(instanceable=True)` 사용** — GUI drag&drop scene_drop_delegate 와 동등:
```python
omni.kit.commands.execute(
    "CreatePayloadCommand",
    usd_context=ctx, path_to=prim_path, asset_path=s3_url, instanceable=True,
)
```

### 원칙

Isaac Sim MCP 로 GUI 를 유저처럼 조작할 때 **S3 URL 필수** (`file:///` 금지):
- Isaac Sim Assets: `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/...`
- SimReady: `https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/common_assets/props/...`
- NVIDIA Assets: `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/{ArchVis,DigitalTwin,Vegetation}/...`

URL SoT: `isaac_course/docs/asset_inventory.md` + `isaac_course/docs/user_asset_check.md`.

### stage_open vs stage_load_usd (용도 구분)

- **`stage_open(url)`** = root stage 전체 교체 (File → Open, **scene 전환**용). 단일 asset 을 새 stage 로 열기.
- **`stage_load_usd(url, prim_path)`** = 기존 stage 에 `/World/<name>` Payload 추가 (**multi-asset composition**). 한 stage 에 여러 asset 배치.

### 실측 (2026-04-20, hang 해결 후)

| Asset (size) | Load | 비고 |
|---|---|---|
| Simple_Warehouse (1.6 MB) | 2.4 s | MDL-heavy OK |
| NovaCarter | 3.1 s | Payload + multi-variant |
| Biped_Setup | 2.6 s | — |
| SimReady (cold) | 10~57 s | 첫 load 느림, 이후 2~3 s |
| multi-asset in same stage | ✅ | Warehouse + NovaCarter + Biped 3장 합성 확인 |

### 재발 시 진단

1. Kit log `C:\Users\<you>\.nvidia-omniverse\logs\Kit\Isaac-Sim Full\5.1\kit_*.log` 마지막 entry 가 `"Disabling base URL to resolve MDL identifier"` 반복 + 이후 silent = deadlock 확정
2. `simulation_get_status` 가 92 s timeout → Kit main loop 차단
3. Kit 좀비 복구: `cmd //c "taskkill /F /IM kit.exe /T"` 만 성공 (`powershell Stop-Process` 는 Access Denied 확정)
4. Fresh restart: `.venv/Scripts/python.exe scripts/run_process_module_standalone.py start`

### 금지 사항
- **`log_capture.start()` 재활성 금지** (request-scoped refactor 전에는 MDL-heavy asset load 불가)
- **`file:///` 로컬 캐시 경로 금지** (`isaac_course/cache_usd/` 재생성 금지)
- **`.env ISAAC_SIM_EXTRA_EXT_IDS` 에 browser ext (`isaacsim.asset.browser`, `omni.kit.window.content_browser`) 추가 금지** (background S3 crawl thread 경합)
- **S3 load 실패 시 skip/fallback/placeholder 대체 금지** — 근본 원인 분석 후 반드시 성공시킬 것

### 편의 스크립트
- `scripts/kill_kit_zombie.sh` — taskkill 래퍼
- `scripts/run_process_module_standalone.py start|stop|restart` — ProcessModule 직접 호출 (MCP 서버 재시작 없이 최신 Extension 코드 반영)
- `isaac_course/pre-test/run_pretest.py` — 50 asset S3 load 자동화 (근본 해결 후 16/16 성공 실측)

---

## Quick Start / Setup

```bash
cp .env.example .env && uv sync
uv run pytest tests/
uv run isaacsim-mcp            # Claude Code 가 세션 시작 시 자동 spawn
# 신규 PC:
setup/setup-isaacsim-mcp.bat   # 상세는 setup/CLAUDE.md
```

**uv 만 사용** (`pip install` 직접 금지). 패키지 추가는 `uv add` / `uv add --dev`.

## Architecture

```
Claude Code CLI
  ↕ stdio (MCP 프로토콜)
isaacsim-mcp FastMCP 서버 [uv run isaacsim-mcp]
  ├─ HTTP REST (http://localhost:8011/validation/v1) → Extension endpoints
  └─ subprocess / OS 명령 → kit.exe 프로세스 제어 (start/stop/restart)
omni.mycompany.validation_api Extension [Isaac Sim GUI 내부]
  ↕
omni.kit.commands / omni.usd / omni.timeline / pxr.*
```

## 설계 원칙

**Isaac Sim GUI 유저가 할 수 있는 모든 것을 Claude Code 도 MCP tool 로 할 수 있어야 한다.** Asset Browser · Viewport Create menu · Stage 패널 · File menu · Simready Explorer 등 어떤 경로로든 유저가 수행하는 동작은 MCP tool 로 동등하게 제공하며, 없으면 Phase 진행 과정에서 필요 시점에 바로 추가한다. 자연어 엔드투엔드 지시 ("새 Extension 만들고 버튼 클릭 동작을 자체 검증") 는 MCP tool 조합만으로 실행 가능해야 한다.

## CLAUDE.md 작성 규칙

**포함 기준** — 코드를 읽어도 알 수 없는 내용만.
- 아키텍처 결정 + 그 이유 (이유 없는 결정은 판단 불가)
- 비명시적 제약과 위험한 함정
- 새 세션에서 이 디렉토리 작업을 시작할 때 반드시 먼저 알아야 하는 것

**제외 기준**
- 변경 이력 / 패치 노트 → git commit message
- 시점 스냅샷 데이터 (테스트 수 · 측정값 · 날짜 기준 수치) → drift
- 코드를 읽으면 알 수 있는 내용 → 코드 주석

**각 하위 CLAUDE.md 구조**
```
1. 이 디렉토리가 하는 일 (1-2 문장)
2. 비명시적 규칙 / 제약 / 결정 (이유 포함)
3. 관련 경계 (다른 CLAUDE.md 포인터)
```

## Scope-specific CLAUDE.md 문서 맵

| 파일 | 담당 범위 |
|------|----------|
| `isaac_extension/CLAUDE.md` | Kit Extension (FastAPI router · Pydantic 모델 · Kit SDK 실측 · REST endpoints · **UI Window 3 규칙** · carb log capture) |
| `src/isaacsim_mcp/CLAUDE.md` | FastMCP 서버 패키지 루트 (entry flow · type 경계 · clients 통신 규약) |
| `src/isaacsim_mcp/modules/CLAUDE.md` | 도메인 모듈 — 모듈 책임 매트릭스 · **Integration Facts** · **ProcessModule hang recovery** · Character domain 제약 |
| `src/isaacsim_mcp/scenario/CLAUDE.md` | 시나리오 엔진 — Arrange/Act/Assert/Cleanup · action_registry · context-aware dispatch |
| `src/isaacsim_mcp/tools/CLAUDE.md` | MCP tool 등록 규약 + tool 그룹별 caveat |
| `tests/CLAUDE.md` | pytest 단위 테스트 (mock 기반, live E2E 제외) |
| `scenarios/CLAUDE.md` | YAML 시나리오 저작 가이드 |
| `setup/CLAUDE.md` | 설치 스크립트 (`.env` · `~/.claude.json` 등록 · Extension 활성화) |
| `docs/CLAUDE.md` | 문서 루트 — Phase 히스토리 vs live tool 카탈로그 분리, phase report 규칙, tool-catalog regen 절차 |
| `docs/references/CLAUDE.md` | Isaac Sim 레퍼런스 — ext 카탈로그 + testbed 스냅샷 |
| `docs/tool-catalog.md` | MCP tool 카탈로그 (auto-generated) |
| `docs/phase-progress.md` | 모든 Phase + PPTX 세션 Task 체크박스 + 타임스탬프 |
| `docs/references/sensor_menu_catalog.md` | Isaac Sim `Create > Sensors` 전체 센서 (RTX Lidar/Radar/Camera/Depth/PhysX/Contact/Imu/LightBeam · vendor × model) + `window_menu_trigger` menu_path. 사용자가 "특정 센서 써달라" 요청 시 SoT |
| `scripts/CLAUDE.md` | 개발 스크립트 (lifecycle · live 검증 · catalog regen · verify_mcp_sync) |
| `isaac_course/CLAUDE.md` | Digital Twin 튜토리얼 PPTX 루트 규칙 (R1~R9) |
| `isaac_course/docs/asset_inventory.md` | 3 Twin 사용 asset 의 확정 USD 경로 |
| `last-prompt.md` | Phase E~H + PPTX 전체 마스터 네비게이션 |
| `prompts/{pptx,phase-e,phase-f,phase-g,phase-h}.md` | 각 세션 전용 주입 프롬프트 (end-to-end 자율 실행) |

## 변경 파급 매트릭스

새 기능 추가 시 함께 수정해야 하는 곳. 서브에이전트 프롬프트 작성 전 확인.

| 변경 대상 | 함께 수정해야 하는 곳 |
|-----------|----------------------|
| REST 엔드포인트 추가 (`isaac_extension/`) | `clients/isaac_rest_client.py` + `tools/` MCP tool 등록 + `tests/` tool 등록 테스트 + `isaac_extension/CLAUDE.md` |
| 새 module 추가 (`modules/`) | `types/common.py` ModuleName enum + `scenario/schema.py` + `scenarios/schema/scenario.schema.json` + `scenario/runner.py` dispatch dict + `scenario_tools.py` register + `mcp/server.py` wiring + `modules/CLAUDE.md` 책임 매트릭스 |
| 새 module 메서드 | `scenario/action_registry.py` (typed request 빌더) / `tests/` |
| **새 MCP tool (`tools/`)** | **⓵ `isaac_extension/` REST · `clients/isaac_rest_client.py` · `tools/module_tools.py` @mcp.tool() · `tests/conftest.py` MockIsaacRestClient +메서드 · `tests/unit/test_tools_registration.py` EXPECTED_{MODULE,SCENARIO}_TOOLS frozenset · `tools/CLAUDE.md` 그룹 caveat**<br>**⓶ 재생성**: `.venv/Scripts/python.exe scripts/generate_tool_catalog.py` (또는 `scripts/verify_mcp_sync.py`)<br>**⓷ drift 검증**: `uv run pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py` |
| scenario action 추가 | `action_registry.py` + `scenario.schema.json` + `schema.py` 3곳 동시 + `tests/unit/test_scenario_integration.py` + `scenarios/CLAUDE.md` |
| ASYNC Job 동작 추가 | Extension `services/job_service.py` 의 `start_job(coro_factory)` 사용 / try-except 필수 (silent catch 금지) / tool 은 job_id 반환, Claude Code 가 `job_status` 폴링 |
| Phase 완료 | `docs/phase-{N}-validation-report.md` 신규 · `docs/phase-progress.md` 해당 Phase 행 ✅ · `scripts/generate_tool_catalog.py` 재실행 · 관련 하위 CLAUDE.md tool/endpoint 동기화 · `uv run pytest tests/` 전체 green |
| CLAUDE.md 에 새 디렉토리 추가 | 이 매트릭스 업데이트 + 관련 경계 양방향 확인 + "Scope-specific CLAUDE.md 문서 맵" 갱신 |

**한 줄**: "새 tool = 서피스 변경 + auto-regen 카탈로그 + drift test 통과". 개발자가 `scripts/verify_mcp_sync.py` 를 **반드시** 수동 1 회 실행해야 (regen + drift test 한 번에).

## Validation Rules (필수 준수)

- **R1. 실제 asset 으로만 검증**: primitive (Cube/Sphere 등) 를 의자·로봇 대용으로 사용한 검증은 **무효**. `asset_list` 또는 알려진 S3 경로 (`.../Environments/Office/Props/SM_Armchair.usd`, `.../Robots/NVIDIA/NovaCarter/nova_carter.usd`, `.../People/Characters/Biped_Setup.usd`) 의 실 USD 사용. 이유: primitive 는 bbox·pivot·forward axis·physics material·mesh topology 특성이 실 asset 과 달라 False Positive 빈발 (chair sit 검증에서 Cube 는 통과·실 Armchair 는 NavMesh step-up 실패 실측됨).
- **R1a. NavMesh bake 는 timeline stopped 필수**: `navigation.bake` 는 playing 중엔 `get_navmesh()=None` (bake 자체는 True 반환하는 False Positive). `stage.load_usd` · `robot.load` · `stage.create_prim/set_property` · `viewport.capture(settle_frames)` · `window.capture` 는 모두 timeline advance 시키므로 bake 직전 `simulation.stop` 재호출. 표준 sequence: `load → stop → bake → query_path → play → navigate_path`.
- **R2. Robot 동작은 `simulation.play` 에서만**: `robot.load` 는 예외. `robot.set_joint_positions` / `navigate_to` / `navigate_path` 등 움직임·관절·물리 상호작용은 playing 상태 필수. 이유: PhysX articulation view 는 physics step 이 돌아야 populate. Extension `robot_service.navigate_path` 는 `omni.timeline.is_playing()` 미통과 시 HTTP 400 거부. scenario 는 `simulation.play` 를 arrange 에 필수 배치. 참고: `navigate_path` 는 현재 `xformOp:translate` kinematic override — 진정한 wheel torque 기반 주행은 OmniGraph `DifferentialController` 통합 (후속).
- **R3. Viewport 캡처 시각 검증 의무**: `viewport_capture` 후 반드시 `Read` tool 로 PNG 시각 확인. **흰색/검은색 배경만** 보이거나 asset 이 점처럼 작으면 **실패 처리** — 아래 순서로 조정 후 재캡처:
  1. **조명 추가/조정** — scene 에 `DistantLight` 또는 `DomeLight` 가 없으면 `stage_create_prim(prim_type="DistantLight")` + `stage_set_property(inputs:intensity=3000)`. 이미 있으면 intensity 2배 증가
  2. **카메라 위치/각도 조정** — `stage_set_property("/OmniverseKit_Persp", "xformOp:translate", [x,y,z])` 로 asset bbox 기준 거리 재설정 (small asset 은 1~3 m, large env 는 10~30 m 외부)
  3. **Asset 위치 조정** — `stage_compute_world_bbox` 로 bbox 구한 후 asset 중심이 viewport 정면이 되게 asset 자체 또는 camera target 재배치
  4. 조정 후 `viewport_capture` 재호출 + Read 재검증. 이 cycle 은 **geometry 가 명확히 보일 때까지** 반복 — 2-3 회 시도 후에도 실패면 `implementation_issues.md` 기록

## Key Decisions (글로벌 — 하위 CLAUDE.md 에 없는 것만)

- **LakehouseModule 은 query only** (inject/cleanup 없음 — 인터뷰 스펙 확정)
- **Type boundary**: 내부 타입은 `dataclass(slots=True, frozen=True)`. REST 경계 (`isaac_extension` Pydantic) 에서만 Pydantic. MCP 서버 코드 내에서는 Pydantic 모델 금지 — client 레이어에서 dict → dataclass 변환
- **MCP server import cache**: Claude Code 는 세션 시작 시 stdio 로 `isaacsim-mcp` 를 1회 spawn 하고 Python import 를 캐시. `src/isaacsim_mcp/` 수정은 Claude Code 재시작 전까지 MCP tool 호출에 반영 안 됨. 세션 내 검증은 `scripts/run_process_module_standalone.py` / `scripts/run_scenario_standalone.py` 사용. Extension 코드 (`isaac_extension/`) 는 별개 프로세스라 `isaac_sim_restart` 로 즉시 반영
- **Test SoT**: `tests/unit/test_tools_registration.py` 의 `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset 이 SoT. count assertion 은 `len()` 유도 — Phase 추가 시 list 만 수정

## Environment Variables

| 변수 | 기본값 (config.py) | `.env` override | 설명 |
|------|-------------------|----------------|------|
| `ISAAC_SIM_BASE_URL` | `http://localhost:8011` | — | Isaac Sim REST API |
| `ISAAC_SIM_STARTUP_TIMEOUT` | `240.0` | `600.0` | ProcessModule health 대기 상한 |
| `ISAAC_SIM_EXTRA_EXT_IDS` | (6 개 Phase C-D bundle) | 8 개 (Phase E 포함: sensors.rtx / asset.browser / content_browser / graph.action / replicator.core 등) | kit.exe 런치 시 추가 활성화 ext — JSON array only (pydantic-settings v2 limitation) |
| `LAKEHOUSE_BASE_URL` | `http://localhost:9000` | — | Lakehouse REST API |
| `MCP_SERVER_PORT` | `8080` | — | MCP 서버 포트 |
| `SCENARIOS_DIR` | `scenarios` | — | 시나리오 YAML 루트 |
