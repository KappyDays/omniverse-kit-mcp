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

**Isaac Sim 조작과 관련된 모든 기능은 MCP tool로 제공한다.**
프로세스 실행/종료, Scene 조작, 시뮬레이션 제어, Viewport 캡처 등
Claude Code가 Isaac Sim을 완전 자율 제어할 수 있어야 한다.

## Scope-specific CLAUDE.md

디렉토리별 세부 지침은 해당 `CLAUDE.md`를 참조. 서브 에이전트는 작업 디렉토리의 파일을 자동 로드한다.

| 파일 | 작업 컨텍스트 |
|------|--------------|
| `isaac_extension/CLAUDE.md` | Kit Extension 내부 (FastAPI router, Pydantic 모델, Kit SDK 실측 사항, REST endpoints) |
| `src/isaacsim_mcp/CLAUDE.md` | FastMCP 서버 패키지 루트 (entry flow, 타입 경계, clients 통신 규약) |
| `src/isaacsim_mcp/modules/CLAUDE.md` | 도메인 모듈 — 모듈 책임 매트릭스, REST 응답 특성(Integration Facts), kit.exe 런타임 플래그 |
| `src/isaacsim_mcp/scenario/CLAUDE.md` | 시나리오 엔진 — Arrange/Act/Assert/Cleanup 내부 |
| `src/isaacsim_mcp/tools/CLAUDE.md` | MCP tool 등록 규약 + 전체 25개 tool 목록 |
| `tests/CLAUDE.md` | pytest 단위 테스트 (mock 기반, live E2E 제외) |
| `scenarios/CLAUDE.md` | YAML 시나리오 저작 가이드 |
| `setup/CLAUDE.md` | 설치 스크립트 (`.env`, `~/.claude.json` 등록, Extension 활성화) |
| `docs/references/CLAUDE.md` | Isaac Sim 레퍼런스 — 621 ext 카탈로그 + testbed 스냅샷 + nvidia-docs |

## Phase 로드맵

| Phase | 내용 | 상태 | 산출물 |
|-------|------|------|--------|
| **A** | Extension WRITE + REST 실구현, 25 MCP tool | ✅ 완료 + E2E 검증 (2026-04-17, `docs/phase-a-validation-report.md`) | 17 endpoint, 25 tool, scenario 엔진 simulation 모듈 주입, viewport/process 호환성 수정 |
| **B** | 로봇 제어 (`SingleArticulation`) + ASYNC Job 패턴 | ❌ 미시작 | +5 tool 예정 (총 30) |
| **C** | 캐릭터 + 애니메이션 (`CharacterUtil`, `AnimationGraph`) | ❌ 미시작 | +3 tool 예정 (총 33) |
| **D** | Extension UI 자동화 (`omni.kit.ui_test`) — Goal 2 | ❌ 미시작 | +4 tool 예정 (총 37) |

각 Phase의 상세 진행 프롬프트는 Notion "Isaac Sim MCP" 페이지 하단 참조.

## Key Decisions

- LakehouseModule은 **query only** (inject/cleanup 없음) — 인터뷰 스펙 확정
- 내부 타입은 `dataclass(slots=True, frozen=True)`, REST 경계만 Pydantic
- 경로 순회 보안: `scenario_tools.py`의 `_resolve_safe_path()`가 scenarios_dir 경계 강제
- Cleanup은 assert 실패 시에도 항상 실행 (finally 블록)
- `action_registry.py`가 YAML args dict → typed request 매핑 담당 + `CONTEXT_AWARE_ACTIONS` 집합에 포함된 액션은 runner 가 ctx 에서 선행 step data 를 해소하여 dispatch
- Stage WRITE 액션(`stage_load_usd`, `stage_set_property`, `stage_create_prim`, `stage_delete_prim`)은 `ModuleName.SIMULATION` 아래 등록 — 툴 layer 와 일치(SimulationModule 이 실제 구현)
- **MCP server 는 Claude Code 세션 시작 시 Python import 를 캐시**. `src/isaacsim_mcp/` 코드 변경은 Claude Code 재시작 전까지 반영 안 됨. 세션 중 검증하려면 `scripts/run_scenario_standalone.py` / `scripts/run_process_module_standalone.py` 사용 (Extension 코드는 kit.exe 재기동으로 즉시 반영)
- ProcessModule 은 kit.exe stdout/stderr 를 `%TEMP%/isaacsim_mcp/kit_<epoch>.log` 로 리다이렉트 — OS pipe 버퍼 포화로 인한 기동 정지 방지

## Environment Variables

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ISAAC_SIM_BASE_URL` | `http://localhost:8011` | Isaac Sim REST API |
| `ISAAC_SIM_STARTUP_TIMEOUT` | `240.0` | `ProcessModule.start()` health 대기 상한(초) — Isaac Sim 첫 기동 셰이더 컴파일 고려 |
| `LAKEHOUSE_BASE_URL` | `http://localhost:9000` | Lakehouse REST API |
| `MCP_SERVER_PORT` | `8080` | MCP 서버 포트 |
| `SCENARIOS_DIR` | `scenarios` | 시나리오 YAML 루트 경로 |

## 다음 세션 작업

각 Phase 진행은 별도 세션(컨텍스트 클린)에서 시작. 각 Step 프롬프트는 Notion **"Isaac Sim MCP"** 페이지 하단의 `# 다음 세션 프롬프트 — Phase A 검증 + Phase B/C/D 순차 진행 (2026-04-17)` 섹션 참조.

진행 순서:
- **Step 1** — Phase A 도구 end-to-end 검증 ✅ 완료 (`docs/phase-a-validation-report.md`)
- **Step 2** — Phase B 로봇 제어 + ASYNC Job 패턴  ← 다음 세션에서 여기서 시작
- **Step 3** — Phase C 캐릭터 + AnimationGraph
- **Step 4** — Phase D Extension UI 자동화 + KKR-A 실전 테스트

새 세션 시작 시 작업 디렉토리(`~/workspace/Isaac-sim-MCP/`)의 이 CLAUDE.md가 자동 로드됨. testbed의 `src/isaac_sim_testbed/CLAUDE.md` (API 특이사항 1-17)는 Phase B/C 진입 시 별도 참조 필요.
