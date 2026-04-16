<!-- Generated: 2026-04-08 | Updated: 2026-04-08 -->

# Isaac-sim-MCP

## Purpose
Isaac Sim 5.1 환경에서 Custom Extension이 Lakehouse와 통신하며 수행하는 USD Stage 변경(Prim 추가/삭제, Property 변경)을 자동 검증하는 MCP(Model Context Protocol) 서버 프로젝트. **구현 완료** — 50+ 파일, 14개 MCP Tool, 24개 unit test 통과.

## Key Files

| File | Description |
|------|-------------|
| `pyproject.toml` | 프로젝트 메타데이터, 의존성, 빌드/테스트 설정 |
| `.env.example` | 환경변수 템플릿 (Isaac Sim, Lakehouse, MCP 서버, 시나리오 경로) |
| `src/isaacsim_mcp/main.py` | 진입점 — `isaacsim-mcp` CLI 커맨드 |
| `src/isaacsim_mcp/mcp/server.py` | FastMCP 서버 생성 및 14개 Tool 등록 |
| `src/isaacsim_mcp/config.py` | pydantic-settings 기반 설정 (AppConfig) |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/isaacsim_mcp/` | MCP 서버 패키지 본체 |
| `isaac_extension/` | Isaac Sim에 설치할 Custom Extension (`omni.mycompany.validation_api`) — REST 스켈레톤 |
| `scenarios/` | YAML 검증 시나리오 파일 + JSON Schema |
| `tests/` | 24개 unit test (pytest-asyncio, mock 기반) |
| `docs/` | 아키텍처 블루프린트 + Deep Interview 요구사항 스펙 (see `docs/AGENTS.md`) |

## For AI Agents

### Working In This Directory

- 구현이 완료되었다. 신규 기능 추가 시 `docs/specs/deep-interview-isaacsim-mcp.md`의 Acceptance Criteria를 준수한다.
- 패키지 관리는 **uv** 사용 (`uv run`, `uv add`). pip 직접 사용 금지.
- 테스트 실행: `uv run pytest tests/` (asyncio_mode = "auto" 설정됨).
- 서버 실행: `uv run isaacsim-mcp` 또는 `uv run python -m isaacsim_mcp.main`.
- 설계도와 인터뷰 스펙 간 차이 시 **인터뷰 스펙 우선** (예: LakehouseModule은 query only).

### Architecture Overview

```
Claude (MCP Client) ──MCP──→ MCP Server (FastMCP, :8080)
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              Isaac Sim      Lakehouse     시나리오 YAML
           (REST :8011)    (REST :9000)   (Arrange→Act→Assert→Cleanup)
                ▲
        isaac_extension/
     omni.mycompany.validation_api
```

### Source Package Layout (`src/isaacsim_mcp/`)

| Subpackage | Contents |
|------------|----------|
| `clients/` | `IsaacRestClient`, `LakehouseClient` (httpx AsyncClient, retry/timeout) |
| `modules/` | `StageModule`, `ViewportModule`, `LakehouseModule`, `ExtensionModule` |
| `tools/` | `module_tools.py` (9개 Tool), `scenario_tools.py` (5개 Tool) |
| `scenario/` | `loader`, `compiler`, `runner`, `state_machine`, `reporters`, `action_registry`, `context` |
| `types/` | 모듈별 dataclass 타입 (common, stage, viewport, lakehouse, extension, scenario) |
| `mcp/` | `server.py` (FastMCP 조립), `prompts.py` (SYSTEM_PROMPT) |

### MCP Tools (14개)

**계층 1 — 모듈 단위 (9개)**
`stage_capture_snapshot`, `stage_diff_snapshots`, `stage_assert_prim_exists`, `stage_assert_property`, `viewport_capture`, `viewport_compare_ssim`, `lakehouse_query`, `extension_trigger`, `extension_get_state`

**계층 2 — 시나리오 단위 (5개)**
`scenario_validate`, `scenario_plan`, `scenario_list`, `scenario_schema`, `scenario_last_report`

### Key Constraints

- Isaac Sim과 MCP 서버는 같은 로컬 머신 (localhost only)
- MCP는 검증 전용 — 데이터 주입/삭제 안 함 (LakehouseModule은 query only)
- 모든 USD Property 타입 지원 (`UsdPropertyValue(type_name, value)`)
- float 비교 시 tolerance 허용, Extension idle 타임아웃 ~30초
- `scenario_path`는 `scenarios_dir` 밖으로 탈출 불가 (경로 순회 차단)

### Tech Stack

Python 3.11+, FastMCP (`mcp[cli]`), httpx, pydantic-settings, scikit-image (SSIM), PyYAML + jsonschema, uv, pytest + pytest-asyncio, ruff

## Dependencies

### External
- Isaac Sim 5.1 (`omni.services` REST, localhost:8011) — `isaac_extension/` 설치 필요
- Lakehouse (자체 REST API, localhost:9000, 조회 전용)

### Python
`mcp[cli]`, `httpx`, `pydantic`, `pydantic-settings`, `pyyaml`, `jsonschema`, `scikit-image`

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
