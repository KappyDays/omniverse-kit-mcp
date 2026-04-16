# Isaac-sim-MCP — Project Instructions

## Quick Start

```bash
cp .env.example .env   # .env에서 URL 수정
uv sync                # 의존성 설치
uv run pytest tests/   # 테스트
uv run isaacsim-mcp    # MCP 서버 실행 (Claude Code가 자동 실행)
```

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

## Isaac Sim 실행

**버전:** Isaac Sim Full 5.1.0-rc.19 (Kit 106)
**Standalone 경로:** `C:\Users\<you>\workspace\branch\isaac-sim-standalone-5.1.0-windows-x86_64\`

**Extension 자동 활성화 실행:**
```bash
"C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64/kit/kit.exe" \
  "C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64/apps/isaacsim.exp.full.kit" \
  --ext-folder "C:/Users/<you>/workspace/branch/Isaac-sim-MCP/isaac_extension" \
  --enable omni.mycompany.validation_api
```

**Claude Code에서 Isaac Sim 제어:**
- 종료: `powershell.exe -NoProfile -Command "Stop-Process -Name kit -Force"`
- 실행: 위 kit.exe 명령을 `run_in_background`로 실행
- 기동 완료 기준: `curl -s http://localhost:8011/validation/v1/health` 응답 확인 (약 13초)
- Extension 코드 수정 후: `__pycache__` 삭제 → Isaac Sim **완전 재시작** (토글로는 반영 안 됨)
- viewport/capture는 GUI 모드(창 있음)에서만 동작, headless에서는 빈 데이터 반환

## Extension 개발 규칙

**`__init__.py`에서 반드시 Extension 클래스를 import:**
```python
# omni/mycompany/validation_api/__init__.py
from .extension import ValidationApiExtension  # noqa: F401
```
Kit은 `__init__.py`에서 `omni.ext.IExt` 서브클래스를 탐색. 이 import 없으면 `on_startup()` 호출 안 됨.

**직접 상속만 사용:**
```python
import omni.ext
class ValidationApiExtension(omni.ext.IExt):  # 동적 변수 아닌 직접 상속
```

**omni.services.core 라우터 등록 API:**
```python
import omni.services.core.main as svc
app = svc.get_app()                              # FastAPI app 인스턴스
app.include_router(router, prefix="/validation/v1")  # 표준 FastAPI include_router
```
출처: `omni.services.core-1.9.1/omni/services/core/main.py` (get_app → _singleton.app)

**로깅:** `carb.log_warn()` 사용 (Python `logging`은 Kit Console에 안 보임)

**코드 수정 후:** `__pycache__` 삭제 + Isaac Sim 완전 재시작 (토글 off/on으로는 반영 안 됨)

## Extension API 우선순위

1. `omni.kit.commands.execute(...)` — USD 조작 표준, 되돌리기 지원
2. `omni.usd.get_context().get_stage()` — Stage 직접 접근
3. `omni.timeline.get_timeline_interface()` — 시뮬레이션 제어
4. `pxr.*` (UsdGeom, Gf 등) — 저수준 USD 조작

**CreatePrimWithDefaultXformCommand** 로 생성된 prim은 이미 xformOps 포함 →
`AddTranslateOp()` 대신 `prim.GetAttribute("xformOp:translate").Set(...)` 사용

## Isaac Sim 5.1 API 실측 사항

- `omni.services.core` 버전 1.9.1 사용 중 (`C:\Users\<you>\AppData\Local\ov\data\exts\v2\omni.services.core-1.9.1\`)
- `register_router()`는 `routers.ServiceAPIRouter` 타입 힌트지만, 표준 `fastapi.APIRouter`도 동작
- `get_app()` 반환값은 `_app.OmniverseService` (FastAPI 서브클래스)
- `simulation/play` 응답 시점에 `is_playing=false`일 수 있음 — 비동기 반영. 1초 후 status 재확인 필요
- Isaac Sim Python 환경: Pydantic 2.12.5, FastAPI 포함 — Extension 내 Pydantic v2 모델 사용 가능
- MCP 서버 등록 위치: `~/.claude.json` (`~/.claude/settings.json`이 아님)

## Key Decisions

- LakehouseModule은 **query only** (inject/cleanup 없음) — 인터뷰 스펙 확정
- 내부 타입은 `dataclass(slots=True, frozen=True)`, REST 경계만 Pydantic
- 경로 순회 보안: `scenario_tools.py`의 `_resolve_safe_path()`가 scenarios_dir 경계 강제
- Cleanup은 assert 실패 시에도 항상 실행 (finally 블록)
- `action_registry.py`가 YAML args dict → typed request 매핑 담당

## Environment Variables

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ISAAC_SIM_BASE_URL` | `http://localhost:8011` | Isaac Sim REST API |
| `LAKEHOUSE_BASE_URL` | `http://localhost:9000` | Lakehouse REST API |
| `MCP_SERVER_PORT` | `8080` | MCP 서버 포트 |
| `SCENARIOS_DIR` | `scenarios` | 시나리오 YAML 루트 경로 |

## MCP Tools 전체 목록

**프로세스 제어 (MCP 서버에서 직접 실행, Extension 불필요)**
- `isaac_sim_start()` — kit.exe 실행 + health 폴링 대기
- `isaac_sim_stop()` — 프로세스 종료
- `isaac_sim_restart()` — 종료 → __pycache__ 삭제 → 재실행 → health 대기

**Stage READ/ASSERT (Extension REST 경유)**
- `stage_capture_snapshot` / `stage_diff_snapshots`
- `stage_assert_prim_exists` / `stage_assert_property`

**Stage WRITE (Extension REST 경유)**
- `stage_load_usd` / `stage_set_property` / `stage_create_prim` / `stage_delete_prim`

**Simulation 제어 (Extension REST 경유)**
- `simulation_play` / `simulation_pause` / `simulation_stop` / `simulation_get_status`

**Viewport (Extension REST 경유, GUI 모드 필요)**
- `viewport_capture` / `viewport_compare_ssim`

**Extension (Extension REST 경유)**
- `extension_trigger` / `extension_get_state`

**Lakehouse (Lakehouse REST 경유)**
- `lakehouse_query`

**Scenario (MCP 서버 내부)**
- `scenario_validate` / `scenario_plan` / `scenario_list` / `scenario_schema` / `scenario_last_report`

## REST Endpoints (17개)

```
GET  /validation/v1/health
POST /validation/v1/stage/snapshot
POST /validation/v1/stage/assert/prim-exists
POST /validation/v1/stage/assert/property
POST /validation/v1/stage/load_usd
POST /validation/v1/stage/set_property
POST /validation/v1/stage/create_prim
DEL  /validation/v1/stage/prim?prim_path=...
POST /validation/v1/simulation/play
POST /validation/v1/simulation/pause
POST /validation/v1/simulation/stop
GET  /validation/v1/simulation/status
POST /validation/v1/viewport/capture
POST /validation/v1/viewport/compare/ssim
GET  /validation/v1/extension/state
POST /validation/v1/extension/trigger
POST /validation/v1/extension/reset
```
