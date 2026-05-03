<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: FastMCP server package root — entry flow, type boundary, HTTP clients -->

# omniverse_kit_mcp — FastMCP 서버 패키지 루트

`uv run omniverse-kit-mcp`의 진입 패키지. Extension REST + Lakehouse REST + OS 프로세스 호출을 MCP tool 로 묶는다.

## Package Layout

```
src/omniverse_kit_mcp/
├── main.py                # CLI 진입점 (`uv run omniverse-kit-mcp` 에 연결)
├── config.py              # AppConfig — 환경 변수 → typed config
├── exceptions.py          # 커스텀 예외
├── mcp/
│   ├── server.py          # FastMCP 서버 조립 (AppConfig + SYSTEM_PROMPT + tool 등록)
│   └── prompts.py         # SYSTEM_PROMPT 정의
├── clients/
│   ├── isaac_rest_client.py   # → Extension REST (ISAAC_SIM_BASE_URL)
│   └── lakehouse_client.py    # → Lakehouse REST (LAKEHOUSE_BASE_URL)
├── modules/               # 도메인 모듈 → modules/CLAUDE.md
├── scenario/              # 시나리오 엔진 → scenario/CLAUDE.md
├── tools/                 # MCP tool 등록 → tools/CLAUDE.md
└── types/                 # 내부 dataclass 타입
    └── common / extension / lakehouse / scenario / simulation / stage / viewport / robot / job / character.py
```

## Entry Flow

```
uv run omniverse-kit-mcp
  → main.py                        (CLI bootstrap)
  → mcp/server.py
      ├─ AppConfig.load_from_env() (config.py)
      ├─ SYSTEM_PROMPT inject      (mcp/prompts.py)
      ├─ clients 초기화             (clients/*)
      ├─ modules 초기화             (modules/*)
      └─ tools 등록                  (tools/module_tools.py + tools/scenario_tools.py)
  → FastMCP stdio server start
```

## Type Boundary Convention (중요)

- **내부 타입**: `@dataclass(slots=True, frozen=True)` — `types/` 전부
- **Pydantic은 REST 경계에만**: Extension 내부 `kkr-extensions/.../models/` 만 사용
- MCP 서버 코드(`omniverse_kit_mcp` 패키지 전체)에서는 Pydantic 모델을 만들지 않는다 — REST 응답은 client 레이어에서 dict → dataclass 로 변환

## Clients 외부 통신 규약

| Client | Target | 환경 변수 |
|--------|--------|-----------|
| `isaac_rest_client.py` | Extension REST `/validation/v1` | `ISAAC_SIM_BASE_URL` (기본 `http://localhost:8011`) |
| `lakehouse_client.py` | Lakehouse REST | `LAKEHOUSE_BASE_URL` (기본 `http://localhost:9000`) |

- 모두 async (httpx 기반)
- Client는 네트워크 오류 시 예외 raise만 담당 — ModuleResult로 감싸는 일은 `modules/base.py`의 `error_result()` 가 담당
- Health 폴링은 `process_module.py`가 직접 수행 (MCP 서버 기동 자체는 Isaac Sim 상태와 무관)

## MCP server import cache (개발 시 필독)

Claude Code 는 세션 시작 시 stdio 로 `omniverse-kit-mcp` 서버를 1회 spawn 하고 Python import 를 캐시한다. 이 패키지 (`src/omniverse_kit_mcp/`) 내부 수정은 **Claude Code 재시작 전까지 MCP tool 호출에 반영되지 않음**. 세션 중 검증 시 standalone 스크립트 사용:

- `scripts/run_scenario_standalone.py <scenario_path>` — compiler/runner/modules 을 최신 코드로 실행. 상대경로는 `config.scenario.scenarios_dir` → 프로젝트 루트 순으로 해소
- `scripts/run_process_module_standalone.py <start|stop|restart>` — ProcessModule 만 별도 실행

Extension 코드 (`kkr-extensions/`) 는 MCP 서버와 별개 프로세스이므로 `isaac_sim_restart` / `__pycache__` 삭제로 즉시 반영.

## 관련 경계

- 모듈 책임/REST 응답 특성: `modules/CLAUDE.md`
- 시나리오 엔진: `scenario/CLAUDE.md`
- MCP tool 등록 규약: `tools/CLAUDE.md`
- Extension 내부(Pydantic models, REST 라우터): `../../kkr-extensions/CLAUDE.md`
