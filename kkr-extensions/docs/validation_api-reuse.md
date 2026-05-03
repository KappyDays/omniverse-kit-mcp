<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 이미 만들어진 Extension 의 validation_api 재사용 가이드 -->

# validation_api 재사용 가이드

> ⚠️ **이 문서는 이미 만들어진 Extension (예: `omni.mycompany.isaac_tutorial`) 전용입니다.**
>
> **신규 Extension 은 이 문서가 필요 없습니다**. 신규는 독립 구조 (Kit SDK 직접 호출) — `extension-basics.md` 의 스켈레톤 + 필요 시 `usd-load-deadlock-recipe.md` 만 따라가면 됩니다.

## validation_api 의 정체

`omni.mycompany.validation_api` 는 FastAPI 기반 **HTTP REST bridge Extension** 입니다:

1. Kit Extension 이라 kit.exe 내부에서 실행
2. `omni.services.core` 위에 `/validation/v1/**` REST 서버 등록 (기본 `localhost:8011`)
3. 각 endpoint 가 Kit SDK 호출 (`omni.kit.commands`, `omni.usd`, `omni.timeline`, `pxr.*`) 을 감싸 **외부 프로세스** (MCP 서버, `curl`, pytest HTTP client 등) 가 원격으로 Kit 을 조작할 수 있게 함
4. 이름의 "validation" 은 역사적 잔재 — 초기엔 "scene 상태 검증" (assert_prim_exists, viewport_compare_ssim 등) 전용이었다가 점차 일반 Kit 조작 bridge 로 확장됨

## 의존 그래프

```
Claude Code
  ↕ stdio (MCP protocol)
omniverse-kit-mcp           (별도 Python 프로세스, FastMCP 서버)
  └─ IsaacRestClient
  ↕ HTTP (localhost:8011/validation/v1/**)
validation_api         (kit.exe 내부, FastAPI router)
  ↕ in-process Python
Kit SDK                (omni.kit.commands / omni.usd / ...)
```

| 의존 주체 | 의존 대상 | 형태 | 비고 |
|----------|----------|------|------|
| `omniverse-kit-mcp` | `validation_api` | HTTP client | MCP tool 전부가 `validation_api` REST 에 의존. validation_api 없으면 MCP tool 호출 시 connection refused |
| `validation_api` | `omniverse-kit-mcp` | **없음** | validation_api 는 MCP 의 존재를 모름. `curl` / Postman / 브라우저 누구든 호출 가능한 순수 REST 서버 |
| `validation_api` | Kit SDK | in-process | |
| `isaac_tutorial` | `validation_api` | **Python module import** | 같은 kit.exe 내부 extension 끼리 싱글턴 공유. HTTP 왕복 없음 |
| `isaac_tutorial` | `omniverse-kit-mcp` | **없음** | 학생 PC 에 MCP 서버 없어도 동작 |

**omniverse-kit-mcp → validation_api → Kit SDK 한 방향 의존**. validation_api 는 업스트림 프로젝트의 일부가 아니라 **이 프로젝트 전용 bridge Extension**.

## 재사용 패턴 — rest_router 싱글턴 import

같은 kit.exe 프로세스 내 다른 Extension 이 validation_api 를 쓰는 올바른 방법:

```python
from omni.mycompany.validation_api import rest_router as vr

# 이미 의존성 그래프에 맞게 구성된 싱글턴들
vr._stage        # StageService()
vr._simulation   # SimulationService()
vr._job          # JobService()
vr._robot        # RobotService(_job)
vr._character    # CharacterService(_job, _stage)
vr._navigation   # NavigationService()
vr._sensor       # SensorService()
vr._replicator   # ReplicatorService()
# ... 기타
```

`isaac_tutorial/bindings/services.py` 가 이 패턴의 유일한 레퍼런스.

### 왜 직접 인스턴스화하지 않는가

```python
# ❌ 하지 마세요
from omni.mycompany.validation_api.services.robot_service import RobotService
robot = RobotService()  # TypeError: missing 'job_service'
```

- `RobotService(job_service)`, `CharacterService(job_service, stage_service)` 는 **의존성 체인** 있음
- rest_router 가 이미 올바른 순서로 생성해서 모듈 레벨에 보관
- 직접 인스턴스화하면 (a) 의존성 재현 필요 (b) 중복 JobService 생성 시 job 상태 분기 (REST 경로 job 과 재사용 job 이 서로 안 보임)

### 활성화 순서 보장

`extension.toml` 에 `"omni.mycompany.validation_api" = {}` 의존성 선언 → Extension Manager 가 **validation_api 먼저 activate** 보장. `get_services()` 는 lazy import 이므로 첫 호출 시점엔 이미 rest_router 모듈 로드 완료.

## 서비스 호출 규약 (⚠️ 실측 기반 — 어기면 TypeError)

### 1. 대부분 메서드는 단일 `request: dict` 인자

Pydantic request 모델의 `ConfigDict(extra="forbid")` 때문에 **낯선 키 하나라도 포함되면 TypeError**. 모델 키를 정확히 맞춰야 함.

대표 예시 ↓ (정확한 키 리스트는 `models/*.py` 직접 확인):

| 메서드 | 올바른 dict 키 | 자주 실수하는 오키 |
|--------|---------------|-------------------|
| `stage.load_usd({...})` | `usd_url`, `prim_path`, `position?`, `rotation?` | ❌ `url`, `translate` |
| `navigation.query_path({...})` | `start`, `end`, `agent_radius`, `agent_height`, `straighten` | |
| `navigation.set_visualization({...})` | `mode` (ex: `"walkable"`) | |
| `sensor.attach_rtx_camera({...})` | `robot_prim`, `mount_offset`, `mount_rotation`, `sensor_name?` | ❌ `parent_path`, `name` |
| `replicator.create_writer({...})` | `writer_type`, `output_dir`, `rgb`, `depth` | ❌ `distance_to_camera` (내부에서 `depth` → `distance_to_camera` 매핑) |
| `character.load({...})` | `usd_url`, `prim_path?` | ❌ `url` |
| `character.sit_on_prim({...})` | `character_prim_path`, `chair_prim_path`, `approach_distance?` | |
| `character.navigate_to({...})` | `prim_path`, `target`, `speed` | ❌ `character_prim_path` (sit 과 키 이름 다름 주의) |
| `character.play_animation_variant({...})` | `prim_path`, `variant` | |

### 2. 일부 메서드는 positional 인자

```python
await services.stage.open_stage(url)                    # str positional
await services.stage.compute_world_bbox(prim_path)      # str positional
await services.stage.delete_prim(prim_path)             # str positional
await services.robot.navigate_path(prim_path, points, duration_s)  # 3 positional
await services.robot.get_joint_positions(prim_path)     # str positional
await services.character.get_state(prim_path)           # str positional
```

### 3. JobService 메서드는 **sync** (async 아님)

```python
# JobService.get_status / cancel 은 sync — await 하지 말 것
status = services.jobs.get_status(job_id)   # ✓
services.jobs.cancel(job_id)                # ✓
```

### 4. 반환값은 plain dict — `.attr` 아닌 `["key"]`

```python
# ❌ 하지 마세요
bake = await services.navigation.bake()
if not bake.mesh_signature: ...    # AttributeError

# ✅
bake = await services.navigation.bake()
if not bake.get("mesh_signature"): ...
```

주요 응답 스키마:
- `stage.compute_world_bbox` → `{min, max, center, size, ...}` — `center` 는 list
- `navigation.bake` → `{mesh_signature, agent_max_radius, area_count, ...}` — `mesh_signature: None` 이면 실패
- `navigation.query_path` → `{points: list[list[float]], ...}` (not `waypoints`)
- `robot.navigate_path` → `{ok, job_id, prim_path, ...}` — async job 반환
- `character.load` → `{ok, prim_path, sanitized_prim_path, ...}` — **후속 호출은 `sanitized_prim_path` 기준**

### 호출 전 실측 절차 (⚠️ 반드시)

Plan 단계의 가정으로 호출 금지. 호출 전:

1. `grep "async def\|def " services/<name>_service.py` 로 메서드 시그니처 확인
2. `grep "class.*Request.*Model" models/<name>.py` 또는 해당 모델 코드 직접 열어 dict 키 확인
3. 반환부에서 `return {...}` 찾아 응답 키 확인

이 3 단계 없이 호출하면 live 에서 TypeError / KeyError 발생. `lessons-learned.md` 의 L1 사례 참조.

## HTTP / 서비스 에러 매핑

의존 코드가 validation_api 내부 에러를 재매핑하거나 HTTP 로도 호출하는 경우 참고:

| HTTP 상태 | 발생 상황 | 원인 예외 |
|----------|---------|----------|
| 400 Bad Request | 도메인 검증 실패 | `ValueError` (prim 미존재, articulation 미적용, target 길이 != 3 등) |
| 404 Not Found | 리소스 미존재 | `KeyError` (unknown job_id, missing prim_path 등) |
| 409 Conflict | 중복 호출 | `ExtensionBusyError` (`/extension/trigger` 중복) |
| 500 Internal Server Error | 예상 못한 상태 | Kit API 내부 오류. 로그에 `exc_info=True` 로 traceback |

MCP 측 `IsaacRestClient` 은 400/404/500 을 모두 `RemoteServiceError` + `HTTP_<code>` error_code 로 반환. module 이 이를 `error_result(..., error_code="DOMAIN_SPECIFIC_ERROR")` 로 재매핑.

## 신규 Extension 이 이 패턴을 쓰면 안 되는 이유

1. **학생 PC 배포 복잡도** — 2 Extension 설치 (validation_api + 신규)
2. **의존 그래프 증가** — 개별 업그레이드 어려움, validation_api 업데이트가 downstream 깨뜨릴 위험
3. **validation_api 의 목적 오용** — "REST bridge" 는 외부 프로세스용이지 내부 재사용용이 아님. `isaac_tutorial` 은 **예외 케이스** (office.usd / sit_on_prim 같은 고급 orchestration 이 필요했던 튜토리얼이라 재구현 비용 vs 의존 트레이드오프에서 의존 선택)
4. **독립 Extension 은 debug 명료** — 의존 0, `omni.kit.commands` 직접 호출이 stack trace 짧음

## 관련 경계

- validation_api 의 전체 REST endpoint 목록: `../omni.mycompany.validation_api/omni/mycompany/validation_api/rest_router.py` (단일 SoT)
- 도메인별 Kit SDK 함정: `kit-sdk-pitfalls.md`
- 독립 Extension 의 USD 로드 방어: `usd-load-deadlock-recipe.md`
- MCP 측 client 동작: `../../src/omniverse_kit_mcp/CLAUDE.md`
