# Isaac Sim 5.1 Custom Extension 검증용 MCP 서버 설계도

> CCG 합성 결과: Codex (아키텍처/타입 시스템) + Claude (DX/확장성/테스트 전략)
> Gemini는 API 쿼터 초과로 미참여

---

## 1. 프로젝트 디렉토리 구조

```
omniverse-kit-mcp/
├── pyproject.toml                          # 패키지 정의, 의존성
├── .env.example                            # 환경변수 템플릿
├── README.md
│
├── src/omniverse_kit_mcp/                       # MCP 서버 (외부)
│   ├── __init__.py
│   ├── main.py                             # 진입점: config 로드 → MCP 서버 기동
│   ├── config.py                           # 타입화된 설정 (Isaac REST URL, Lakehouse DSN, 타임아웃)
│   ├── logging.py                          # 구조화된 로깅 설정
│   ├── exceptions.py                       # 예외 계층 정의
│   │
│   ├── types/                              # 공유 타입 정의 (transport-neutral)
│   │   ├── common.py                       # JsonValue, ModuleResult, OperationMeta, 정책류
│   │   ├── stage.py                        # StageSnapshot, StageDiff, PrimSpec, 어설션 타입
│   │   ├── viewport.py                     # ViewportCaptureRequest, SSIMComparisonResult
│   │   ├── lakehouse.py                    # LakehouseDatasetRef, InjectionRequest, QueryResult
│   │   ├── extension.py                    # ExtensionState, TriggerRequest, ResetRequest
│   │   ├── scenario.py                     # CompiledStep, ScenarioRunSummary
│   │   └── tooling.py                      # MCP Tool 입출력 래퍼 타입
│   │
│   ├── clients/                            # 외부 통신 클라이언트
│   │   ├── isaac_rest_client.py            # httpx AsyncClient 래퍼 (재시도/타임아웃)
│   │   └── lakehouse_client.py             # Lakehouse REST/SDK 클라이언트
│   │
│   ├── modules/                            # 검증 기능 모듈
│   │   ├── base.py                         # ValidationModule ABC + ModuleResult 헬퍼
│   │   ├── stage_module.py                 # Prim/Property 스냅샷, diff, 어설션
│   │   ├── viewport_module.py              # 스크린샷 캡처, SSIM 비교
│   │   ├── lakehouse_module.py             # 테스트 데이터 주입/조회/정리
│   │   └── extension_module.py             # Extension 트리거/리셋/상태 조회
│   │
│   ├── scenario/                           # 시나리오 실행 엔진
│   │   ├── loader.py                       # YAML 로드 + JSON Schema 검증
│   │   ├── schema.py                       # 스키마 상수 및 검증 함수
│   │   ├── compiler.py                     # YAML → CompiledStep 그래프 변환
│   │   ├── context.py                      # 스텝 간 공유 컨텍스트 (스냅샷, 아티팩트)
│   │   ├── composer.py                     # 변수 치환, 레퍼런스 해석, 기본값 적용
│   │   ├── runner.py                       # Arrange→Act→Assert 실행 + 라이프사이클 관리
│   │   ├── state_machine.py                # 실행 상태 및 전이 정의
│   │   └── reporters.py                    # 결과 리포트 생성 (JSON/Markdown)
│   │
│   ├── tools/                              # MCP Tool 정의
│   │   ├── registry.py                     # 모듈 → Tool 매핑 레지스트리
│   │   ├── module_tools.py                 # 계층1: 모듈 단위 Tool (12개)
│   │   └── scenario_tools.py               # 계층2: 시나리오 단위 Tool (5개)
│   │
│   ├── mcp/                                # MCP 프로토콜 레이어
│   │   ├── server.py                       # FastMCP 기동, Tool 등록
│   │   ├── tool_adapter.py                 # 모듈 메서드 → MCP Tool 어댑터
│   │   └── prompts.py                      # Claude에게 제공할 Tool 사용 가이드
│   │
│   ├── retry.py                            # 지수 백오프 + 지터 재시도 로직
│   └── timeouts.py                         # 계층별 타임아웃 관리
│
├── scenarios/                              # 검증 시나리오 정의
│   ├── schema/
│   │   └── scenario.schema.json            # YAML 스키마 (JSON Schema)
│   ├── smoke/
│   │   └── prim_create.yaml                # 기본 Prim 생성 검증
│   └── regression/
│       └── lakehouse_roundtrip.yaml        # Lakehouse 왕복 통합 검증
│
├── tests/                                  # 테스트
│   ├── unit/
│   │   ├── test_stage_module.py
│   │   ├── test_viewport_module.py
│   │   ├── test_lakehouse_module.py
│   │   ├── test_extension_module.py
│   │   ├── test_compiler.py
│   │   └── test_state_machine.py
│   ├── integration/
│   │   ├── test_rest_contract.py           # Isaac REST 엔드포인트 계약 테스트
│   │   └── test_scenario_runner.py
│   └── fixtures/
│       ├── stage_snapshots/                # 테스트용 스냅샷 JSON
│       └── screenshots/                    # 베이스라인 이미지
│
└── kkr-extensions/                        # Isaac Sim 내부 Extension
    └── omni.mycompany.validation_api/
        ├── config/
        │   └── extension.toml              # Extension 메타데이터
        ├── omni/mycompany/validation_api/
        │   ├── __init__.py
        │   ├── extension.py                # Extension 라이프사이클 (startup/shutdown)
        │   ├── rest_router.py              # FastAPI 라우터 등록
        │   ├── services/
        │   │   ├── stage_service.py         # USD Stage 조작 (스냅샷, 어설션)
        │   │   ├── viewport_service.py      # Viewport 캡처
        │   │   ├── extension_service.py     # 커스텀 Extension 제어
        │   │   └── state_store.py           # 검증 세션 상태 관리
        │   ├── models/
        │   │   ├── common.py                # Pydantic 모델 (REST 요청/응답)
        │   │   ├── stage.py
        │   │   ├── viewport.py
        │   │   └── extension.py
        │   └── utils/
        │       ├── usd_serialization.py     # USD 타입 → JSON 직렬화
        │       └── image_capture.py         # omni.kit.viewport 캡처 유틸
        └── tests/
            └── test_rest_router.py
```

---

## 2. 핵심 타입 정의

### 2.1 공통 타입 (`types/common.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol, TypedDict, NotRequired

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class ModuleName(str, Enum):
    STAGE = "stage"
    VIEWPORT = "viewport"
    LAKEHOUSE = "lakehouse"
    EXTENSION = "extension"


class StepPhase(str, Enum):
    ARRANGE = "arrange"
    ACT = "act"
    ASSERT = "assert"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELED = "canceled"


@dataclass(slots=True, frozen=True)
class TimeoutPolicy:
    connect_s: float = 5.0
    read_s: float = 30.0
    write_s: float = 30.0
    pool_s: float = 5.0
    request_s: float = 30.0
    step_s: float = 60.0
    scenario_s: float = 600.0


@dataclass(slots=True, frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_s: float = 0.5
    max_backoff_s: float = 5.0
    multiplier: float = 2.0
    retry_on_status_codes: tuple[int, ...] = (408, 429, 500, 502, 503, 504)
    retry_on_exceptions: tuple[type[BaseException], ...] = (TimeoutError,)


@dataclass(slots=True, frozen=True)
class OperationMeta:
    request_id: str
    scenario_id: str | None = None
    step_id: str | None = None
    module: ModuleName | None = None
    started_at_epoch_ms: int | None = None


@dataclass(slots=True, frozen=True)
class ModuleResult[T]:
    ok: bool
    status: ExecutionStatus
    data: T | None
    message: str | None = None
    error_code: str | None = None
    duration_ms: int | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
```

### 2.2 Stage 타입 (`types/stage.py`)

```python
class PrimSpec(TypedDict):
    path: str
    type_name: str
    active: bool
    defined: bool
    instanceable: bool
    attributes: dict[str, JsonValue]
    relationships: dict[str, list[str]]
    metadata: dict[str, JsonValue]


class PropertySpec(TypedDict):
    prim_path: str
    property_name: str
    property_type: Literal["attribute", "relationship"]
    value: JsonValue
    value_type_name: str
    authored: bool


@dataclass(slots=True, frozen=True)
class StageCaptureFilter:
    include_prim_patterns: tuple[str, ...] = ("*",)
    exclude_prim_patterns: tuple[str, ...] = ()
    include_properties: bool = True
    include_metadata: bool = True
    max_prim_count: int = 10000


@dataclass(slots=True, frozen=True)
class StageSnapshot:
    root_layer_identifier: str
    stage_identifier: str
    default_prim: str | None
    prims: dict[str, PrimSpec]
    captured_at_epoch_ms: int
    capture_filter: StageCaptureFilter


class DiffKind(str, Enum):
    PRIM_ADDED = "prim_added"
    PRIM_REMOVED = "prim_removed"
    PRIM_CHANGED = "prim_changed"
    PROPERTY_ADDED = "property_added"
    PROPERTY_REMOVED = "property_removed"
    PROPERTY_CHANGED = "property_changed"


@dataclass(slots=True, frozen=True)
class StageDiffEntry:
    kind: DiffKind
    prim_path: str
    property_name: str | None
    before: JsonValue | PrimSpec | None
    after: JsonValue | PrimSpec | None
    details: str | None = None


@dataclass(slots=True, frozen=True)
class StageDiff:
    entries: tuple[StageDiffEntry, ...]
    before_snapshot_id: str | None
    after_snapshot_id: str | None
    total_changes: int


@dataclass(slots=True, frozen=True)
class PrimExistenceAssertion:
    prim_path: str
    should_exist: bool
    expected_type_name: str | None = None
    expected_active: bool | None = None


@dataclass(slots=True, frozen=True)
class PropertyAssertion:
    prim_path: str
    property_name: str
    property_type: Literal["attribute", "relationship"] = "attribute"
    comparator: Literal["equals", "not_equals", "contains", "regex", "approx", "exists"] = "equals"
    expected_value: JsonValue | None = None
    tolerance: float | None = None


@dataclass(slots=True, frozen=True)
class AssertionFailure:
    code: str
    message: str
    prim_path: str | None = None
    property_name: str | None = None
    actual_value: JsonValue | None = None
    expected_value: JsonValue | None = None


@dataclass(slots=True, frozen=True)
class AssertionReport:
    passed: bool
    failures: tuple[AssertionFailure, ...]
    checked_count: int
```

### 2.3 Viewport 타입 (`types/viewport.py`)

```python
@dataclass(slots=True, frozen=True)
class ViewportCaptureRequest:
    viewport_name: str = "Viewport"
    camera_prim_path: str | None = None
    renderer: Literal["rtx", "hydra"] = "rtx"
    width: int = 1280
    height: int = 720
    samples_per_pixel: int = 64
    settle_frames: int = 5
    output_format: Literal["png", "jpg"] = "png"
    transparent_background: bool = False


@dataclass(slots=True, frozen=True)
class ImageArtifact:
    artifact_id: str
    path: str
    width: int
    height: int
    sha256: str
    created_at_epoch_ms: int


@dataclass(slots=True, frozen=True)
class SSIMComparisonRequest:
    baseline_artifact_path: str
    candidate_artifact_path: str
    min_ssim: float = 0.99
    crop: tuple[int, int, int, int] | None = None   # (x, y, w, h) ROI


@dataclass(slots=True, frozen=True)
class SSIMComparisonResult:
    score: float
    passed: bool
    diff_heatmap_path: str | None = None
    compared_width: int | None = None
    compared_height: int | None = None
```

### 2.4 Lakehouse 타입 (`types/lakehouse.py`)

```python
@dataclass(slots=True, frozen=True)
class LakehouseDatasetRef:
    namespace: str
    dataset: str
    table: str | None = None
    version: str | None = None


@dataclass(slots=True, frozen=True)
class LakehouseRow:
    values: dict[str, JsonValue]


@dataclass(slots=True, frozen=True)
class LakehouseInjectionRequest:
    target: LakehouseDatasetRef
    rows: tuple[LakehouseRow, ...]
    mode: Literal["append", "replace", "merge"] = "append"
    merge_keys: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class LakehouseQueryRequest:
    sql: str | None = None
    target: LakehouseDatasetRef | None = None
    filters: dict[str, JsonValue] = field(default_factory=dict)
    limit: int = 1000


@dataclass(slots=True, frozen=True)
class LakehouseQueryResult:
    row_count: int
    rows: tuple[LakehouseRow, ...]
    schema: dict[str, str]


@dataclass(slots=True, frozen=True)
class LakehouseCleanupRequest:
    target: LakehouseDatasetRef
    filters: dict[str, JsonValue] = field(default_factory=dict)
    truncate: bool = False
```

### 2.5 Extension 타입 (`types/extension.py`)

```python
@dataclass(slots=True, frozen=True)
class ExtensionTriggerRequest:
    operation: str
    payload: dict[str, JsonValue] = field(default_factory=dict)
    wait_for_idle: bool = True
    idle_timeout_s: float = 30.0


@dataclass(slots=True, frozen=True)
class ExtensionState:
    enabled: bool
    busy: bool
    last_operation: str | None
    last_error: str | None
    reset_token: str | None
    state_version: int


@dataclass(slots=True, frozen=True)
class ExtensionResetRequest:
    reset_stage_changes: bool = False
    reset_internal_state: bool = True
    clear_caches: bool = True
    reload_config: bool = False
```

---

## 3. 모듈 인터페이스 (Protocol)

```python
class StageModuleProtocol(Protocol):
    async def capture_snapshot(
        self, meta: OperationMeta, capture_filter: StageCaptureFilter
    ) -> ModuleResult[StageSnapshot]: ...

    async def diff_snapshots(
        self, meta: OperationMeta, before: StageSnapshot, after: StageSnapshot
    ) -> ModuleResult[StageDiff]: ...

    async def assert_prim_exists(
        self, meta: OperationMeta, assertion: PrimExistenceAssertion
    ) -> ModuleResult[AssertionReport]: ...

    async def assert_property(
        self, meta: OperationMeta, assertion: PropertyAssertion
    ) -> ModuleResult[AssertionReport]: ...


class ViewportModuleProtocol(Protocol):
    async def capture(
        self, meta: OperationMeta, request: ViewportCaptureRequest
    ) -> ModuleResult[ImageArtifact]: ...

    async def compare_ssim(
        self, meta: OperationMeta, request: SSIMComparisonRequest
    ) -> ModuleResult[SSIMComparisonResult]: ...


class LakehouseModuleProtocol(Protocol):
    async def inject(
        self, meta: OperationMeta, request: LakehouseInjectionRequest
    ) -> ModuleResult[LakehouseQueryResult]: ...

    async def query(
        self, meta: OperationMeta, request: LakehouseQueryRequest
    ) -> ModuleResult[LakehouseQueryResult]: ...

    async def cleanup(
        self, meta: OperationMeta, request: LakehouseCleanupRequest
    ) -> ModuleResult[dict[str, JsonValue]]: ...


class ExtensionModuleProtocol(Protocol):
    async def trigger(
        self, meta: OperationMeta, request: ExtensionTriggerRequest
    ) -> ModuleResult[ExtensionState]: ...

    async def reset(
        self, meta: OperationMeta, request: ExtensionResetRequest
    ) -> ModuleResult[ExtensionState]: ...

    async def get_state(
        self, meta: OperationMeta
    ) -> ModuleResult[ExtensionState]: ...
```

---

## 4. Isaac Sim Extension REST 엔드포인트 스펙

**Base Path**: `/validation/v1`
**포트**: `8011` (omni.services 기본값)

### 4.1 Health & Extension 제어

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/validation/v1/health` | 서비스 상태 확인 |
| `GET` | `/validation/v1/extension/state` | Extension 현재 상태 |
| `POST` | `/validation/v1/extension/trigger` | Extension 동기화 트리거 |
| `POST` | `/validation/v1/extension/reset` | Extension 상태 초기화 |

#### Health Check

```http
GET /validation/v1/health
→ 200 OK
{
  "ok": true,
  "extension_enabled": true,
  "busy": false,
  "version": "1.0.0"
}
```

#### Extension Trigger

```http
POST /validation/v1/extension/trigger
Content-Type: application/json
{
  "operation": "sync_from_lakehouse",
  "payload": {"batch_id": "2026-04-07-001"},
  "wait_for_idle": true,
  "idle_timeout_s": 30.0
}
→ 200 OK  { ...ExtensionState... }
→ 409     Extension busy
→ 504     idle_timeout 초과
```

#### Extension Reset

```http
POST /validation/v1/extension/reset
{
  "reset_stage_changes": false,
  "reset_internal_state": true,
  "clear_caches": true,
  "reload_config": false
}
→ 200 OK  { ...ExtensionState... }
```

### 4.2 Stage 검증

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/validation/v1/stage/snapshot` | Stage 전체 Prim 트리 스냅샷 |
| `POST` | `/validation/v1/stage/assert/prim-exists` | Prim 존재 여부 어설션 |
| `POST` | `/validation/v1/stage/assert/property` | Property 값 어설션 |

#### Stage Snapshot

```http
POST /validation/v1/stage/snapshot
{
  "include_prim_patterns": ["/World/**"],
  "exclude_prim_patterns": ["/World/Ignore/**"],
  "include_properties": true,
  "include_metadata": true,
  "max_prim_count": 5000
}
→ 200 OK
{
  "root_layer_identifier": "anon:...",
  "stage_identifier": "anon:...",
  "default_prim": "/World",
  "prims": {
    "/World/Cube": {
      "path": "/World/Cube",
      "type_name": "Cube",
      "active": true,
      "defined": true,
      "instanceable": false,
      "attributes": {"xformOp:translate": [0,0,0], "size": 1.0},
      "relationships": {},
      "metadata": {}
    }
  },
  "captured_at_epoch_ms": 1775491200000,
  "capture_filter": { ... }
}
```

#### Prim Existence Assertion

```http
POST /validation/v1/stage/assert/prim-exists
{
  "prim_path": "/World/Cube",
  "should_exist": true,
  "expected_type_name": "Cube",
  "expected_active": true
}
→ 200 OK  { "passed": true, "failures": [], "checked_count": 1 }
```

#### Property Assertion

```http
POST /validation/v1/stage/assert/property
{
  "prim_path": "/World/Cube",
  "property_name": "xformOp:translate",
  "property_type": "attribute",
  "comparator": "approx",
  "expected_value": [1.0, 0.0, 0.5],
  "tolerance": 0.001
}
→ 200 OK  { "passed": true, "failures": [], "checked_count": 1 }
```

### 4.3 Viewport 검증

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/validation/v1/viewport/capture` | Viewport 스크린샷 캡처 |
| `POST` | `/validation/v1/viewport/compare/ssim` | SSIM 이미지 비교 |

#### Viewport Capture

```http
POST /validation/v1/viewport/capture
{
  "viewport_name": "Viewport",
  "camera_prim_path": "/World/Camera",
  "renderer": "rtx",
  "width": 1280,
  "height": 720,
  "samples_per_pixel": 64,
  "settle_frames": 5,
  "output_format": "png",
  "transparent_background": false
}
→ 200 OK
{
  "artifact_id": "img_abc123",
  "path": "/tmp/isaacsim/artifacts/img_abc123.png",
  "width": 1280,
  "height": 720,
  "sha256": "a1b2c3..."
}
```

#### SSIM Comparison

```http
POST /validation/v1/viewport/compare/ssim
{
  "baseline_artifact_path": "/baselines/cube.png",
  "candidate_artifact_path": "/tmp/isaacsim/artifacts/img_abc123.png",
  "min_ssim": 0.99,
  "crop": [0, 0, 1280, 720]
}
→ 200 OK
{
  "score": 0.9972,
  "passed": true,
  "diff_heatmap_path": "/tmp/isaacsim/artifacts/diff_abc.png",
  "compared_width": 1280,
  "compared_height": 720
}
```

### 4.4 에러 응답 공통 형식

```python
class RestErrorResponse(TypedDict):
    ok: bool           # False
    error_code: str    # "EXTENSION_BUSY", "PRIM_NOT_FOUND", ...
    message: str       # 사람이 읽을 수 있는 메시지
    request_id: str    # 추적용 ID
    retryable: bool    # 재시도 가능 여부
    details: dict      # 추가 정보
```

| HTTP 상태 | 의미 |
|-----------|------|
| `400` | 스키마/유효성 검증 실패 |
| `404` | Prim/Property/아티팩트 미발견 |
| `409` | Extension busy / 잘못된 라이프사이클 상태 |
| `422` | 어설션 실패 (의미적 실패) |
| `500` | Isaac 내부 오류 |
| `503` | 앱 미준비 / Stage 사용 불가 |
| `504` | idle 대기 또는 렌더링 타임아웃 |

---

## 5. MCP Tool 카탈로그

### 5.1 계층 1 — 모듈 단위 Tools (디버깅/단발 검증용)

| # | Tool 이름 | 파라미터 | 반환값 |
|---|-----------|----------|--------|
| 1 | `stage_capture_snapshot` | `capture_filter: StageCaptureFilter` | `ModuleResult[StageSnapshot]` |
| 2 | `stage_diff_snapshots` | `before: StageSnapshot, after: StageSnapshot` | `ModuleResult[StageDiff]` |
| 3 | `stage_assert_prim_exists` | `assertion: PrimExistenceAssertion` | `ModuleResult[AssertionReport]` |
| 4 | `stage_assert_property` | `assertion: PropertyAssertion` | `ModuleResult[AssertionReport]` |
| 5 | `viewport_capture` | `request: ViewportCaptureRequest` | `ModuleResult[ImageArtifact]` |
| 6 | `viewport_compare_ssim` | `request: SSIMComparisonRequest` | `ModuleResult[SSIMComparisonResult]` |
| 7 | `lakehouse_inject` | `request: LakehouseInjectionRequest` | `ModuleResult[LakehouseQueryResult]` |
| 8 | `lakehouse_query` | `request: LakehouseQueryRequest` | `ModuleResult[LakehouseQueryResult]` |
| 9 | `lakehouse_cleanup` | `request: LakehouseCleanupRequest` | `ModuleResult[dict]` |
| 10 | `extension_trigger` | `request: ExtensionTriggerRequest` | `ModuleResult[ExtensionState]` |
| 11 | `extension_reset` | `request: ExtensionResetRequest` | `ModuleResult[ExtensionState]` |
| 12 | `extension_get_state` | (없음) | `ModuleResult[ExtensionState]` |

### 5.2 계층 2 — 시나리오 단위 Tools (자동화용)

| # | Tool 이름 | 파라미터 | 반환값 |
|---|-----------|----------|--------|
| 1 | `scenario_validate` | `scenario_path, input_overrides?, dry_run?, fail_fast?` | `ScenarioRunSummary` |
| 2 | `scenario_plan` | `scenario_path, input_overrides?` | 컴파일된 스텝 그래프 + 변수 해석 결과 |
| 3 | `scenario_list` | `root_dir?: str = "scenarios/"` | 시나리오 목록 (id, name, tags) |
| 4 | `scenario_schema` | (없음) | YAML/JSON 스키마 |
| 5 | `scenario_last_report` | `scenario_id: str` | 마지막 실행의 전체 리포트 |

### 5.3 ScenarioRunSummary (scenario_validate 반환값)

```python
@dataclass(slots=True, frozen=True)
class ScenarioRunSummary:
    scenario_id: str
    status: ExecutionStatus       # PASSED | FAILED | ERROR | TIMEOUT
    passed_steps: int
    failed_steps: int
    skipped_steps: int
    started_at_epoch_ms: int
    ended_at_epoch_ms: int
    step_results: tuple[StepResult, ...]
    artifact_paths: tuple[str, ...]
```

---

## 6. Composer/Runner 상태 머신

### 6.1 상태 정의

```
SCENARIO_LOADED → SCHEMA_VALIDATED → COMPILED
    → ARRANGE_RUNNING → ARRANGE_DONE
    → ACT_RUNNING → ACT_DONE
    → ASSERT_RUNNING → ASSERT_DONE
    → PASSED
```

### 6.2 상태 전이 다이어그램

```
START
  │
  ▼
SCENARIO_LOADED ──── (스키마 검증 실패) ──→ ERROR_INTERNAL
  │
  ▼
SCHEMA_VALIDATED ─── (컴파일 실패) ──────→ ERROR_INTERNAL
  │
  ▼
COMPILED
  │
  ▼
ARRANGE_RUNNING ──┬─ (성공) ──→ ARRANGE_DONE
                  ├─ (실패) ──→ FAILED_OPERATION ──→ ROLLED_BACK
                  ├─ (타임아웃) → TIMEOUT_STEP ────→ ROLLED_BACK
                  └─ (예외) ──→ ERROR_INTERNAL
  │
  ▼
ACT_RUNNING ──────┬─ (성공) ──→ ACT_DONE
                  ├─ (실패) ──→ FAILED_OPERATION ──→ ROLLED_BACK
                  ├─ (타임아웃) → TIMEOUT_STEP ────→ ROLLED_BACK
                  └─ (예외) ──→ ERROR_INTERNAL
  │
  ▼
ASSERT_RUNNING ───┬─ (전부 통과) → ASSERT_DONE ──→ PASSED
                  ├─ (어설션 실패) → FAILED_ASSERTION ──→ ROLLED_BACK
                  ├─ (타임아웃) → TIMEOUT_STEP
                  └─ (예외) ──→ ERROR_INTERNAL
  │
  ▼
[모든 상태] ──────→ TIMEOUT_SCENARIO (시나리오 전체 타임아웃)
[모든 상태] ──────→ CANCELED (외부 취소 요청)
```

### 6.3 실행 규칙

| 규칙 | 설명 |
|------|------|
| Arrange 실패 | Act/Assert 건너뜀, 즉시 Cleanup |
| Act 실패 | Assert 건너뜀, 즉시 Cleanup |
| Assert `fail_fast=false` | 같은 phase 내 나머지 step 계속 실행 |
| Assert `fail_fast=true` (기본) | 첫 실패에서 중단 |
| Cleanup | `finally` 블록에서 항상 실행 |
| Rollback 실패 | secondary error로 첨부, primary error 유지 |

### 6.4 스텝 실행 모델

```python
@dataclass(slots=True, frozen=True)
class CompiledStep:
    id: str
    phase: StepPhase
    module: ModuleName
    action: str
    args: dict[str, JsonValue]
    timeout_s: float | None = None
    retry_policy: RetryPolicy | None = None
    continue_on_failure: bool = False
    idempotent: bool = False
```

---

## 7. 에러 처리 및 타임아웃 전략

### 7.1 계층별 타임아웃

```
┌─ Scenario 전체 ─────────────────── 600s (기본) ─────────┐
│  ┌─ Step 단위 ──────────────────── 60s (기본) ────────┐  │
│  │  ┌─ HTTP Request ───────────── 30s ──────────────┐ │  │
│  │  │  ┌─ HTTP Connect ──────── 5s ──────────────┐  │ │  │
│  │  │  └─────────────────────────────────────────┘  │ │  │
│  │  └───────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 7.2 모듈별 타임아웃 권장값

| 모듈/동작 | 타임아웃 | 비고 |
|-----------|----------|------|
| Stage snapshot/assert | 15s | Prim 수에 비례 |
| Viewport capture | 60~120s | RTX 렌더링 settle 포함 |
| SSIM compare | 10s | 이미지 크기에 비례 |
| Lakehouse inject/query/cleanup | 30s | 네트워크 상태 의존 |
| Extension trigger (wait_for_idle) | 30~90s | 동기화 복잡도 의존 |

### 7.3 재시도 정책

| 조건 | 재시도 여부 | 근거 |
|------|------------|------|
| HTTP 408/429/5xx | O (최대 3회) | 일시적 장애 |
| TimeoutError | O (최대 2회) | 네트워크 지연 |
| 어설션 실패 (SSIM, Prim) | X | 결정적 결과 |
| 422 Unprocessable | X | 의미적 실패 |
| Extension busy (409) | 조건부 (폴링 대기) | busy 해소 대기 후 재시도 |
| 비멱등 Act 스텝 | X (`idempotent: true` 아닌 한) | 부작용 방지 |

### 7.4 예외 계층

```python
class ValidationServerError(Exception): ...

# Transport
class TransportError(ValidationServerError): ...
class RemoteServiceError(ValidationServerError): ...

# 모듈별
class StageAssertionError(ValidationServerError): ...
class ViewportComparisonError(ValidationServerError): ...
class LakehouseError(ValidationServerError): ...
class ExtensionBusyError(ValidationServerError): ...

# 실행 엔진
class StepTimeoutError(ValidationServerError): ...
class ScenarioTimeoutError(ValidationServerError): ...
class ScenarioCompileError(ValidationServerError): ...
class ScenarioSchemaError(ValidationServerError): ...
```

---

## 8. 시나리오 YAML 스키마

### 8.1 예시 시나리오

```yaml
apiVersion: isaacsim.validation/v1
kind: Scenario
metadata:
  id: lakehouse_sync_add_cube
  name: "Lakehouse 동기화를 통한 Cube 생성 검증"
  tags: [smoke, prim-crud, viewport]

spec:
  defaults:
    stepTimeoutSeconds: 60
    failFast: true

  variables:
    batch_id: "2026-04-07-001"
    prim_path: "/World/Cube"

  arrange:
    - id: reset_extension
      module: extension
      action: reset
      args:
        reset_internal_state: true
        clear_caches: true

    - id: seed_lakehouse
      module: lakehouse
      action: inject
      args:
        target:
          namespace: qa
          dataset: stage_changes
        mode: replace
        rows:
          - values:
              prim_path: ${variables.prim_path}
              op: add
              type_name: Cube

    - id: capture_baseline
      module: viewport
      action: capture
      args:
        camera_prim_path: /World/Camera
        renderer: rtx
        settle_frames: 10

  act:
    - id: sync_extension
      module: extension
      action: trigger
      args:
        operation: sync_from_lakehouse
        payload:
          batch_id: ${variables.batch_id}
        wait_for_idle: true
        idle_timeout_s: 30

  assert:
    - id: cube_exists
      module: stage
      action: assert_prim_exists
      args:
        prim_path: ${variables.prim_path}
        should_exist: true
        expected_type_name: Cube

    - id: cube_position
      module: stage
      action: assert_property
      args:
        prim_path: ${variables.prim_path}
        property_name: xformOp:translate
        comparator: approx
        expected_value: [0, 0, 0]
        tolerance: 0.001

    - id: capture_after
      module: viewport
      action: capture
      args:
        camera_prim_path: /World/Camera
        renderer: rtx
        settle_frames: 10

    - id: visual_changed
      module: viewport
      action: compare_ssim
      args:
        baseline_from_step: capture_baseline    # 스텝 간 아티팩트 참조
        candidate_from_step: capture_after
        min_ssim: 0.50                          # 변화 있으므로 낮은 임계값
      continueOnFailure: true

  cleanup:                                       # 항상 실행
    - id: cleanup_lakehouse
      module: lakehouse
      action: cleanup
      args:
        target:
          namespace: qa
          dataset: stage_changes
        truncate: true
```

### 8.2 JSON Schema 정의

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/isaacsim/scenario.schema.json",
  "type": "object",
  "required": ["apiVersion", "kind", "metadata", "spec"],
  "additionalProperties": false,
  "properties": {
    "apiVersion": { "const": "isaacsim.validation/v1" },
    "kind": { "const": "Scenario" },
    "metadata": {
      "type": "object",
      "required": ["id", "name"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^[a-zA-Z0-9_.-]+$" },
        "name": { "type": "string", "minLength": 1 },
        "tags": { "type": "array", "items": { "type": "string" } }
      }
    },
    "spec": {
      "type": "object",
      "required": ["arrange", "act", "assert"],
      "additionalProperties": false,
      "properties": {
        "defaults": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "stepTimeoutSeconds": { "type": "number", "minimum": 1 },
            "failFast": { "type": "boolean" }
          }
        },
        "variables": {
          "type": "object",
          "additionalProperties": true
        },
        "arrange": { "$ref": "#/$defs/stepList" },
        "act":     { "$ref": "#/$defs/stepList" },
        "assert":  { "$ref": "#/$defs/stepList" },
        "cleanup": { "$ref": "#/$defs/stepList" }
      }
    }
  },
  "$defs": {
    "stepList": {
      "type": "array",
      "items": { "$ref": "#/$defs/step" }
    },
    "step": {
      "type": "object",
      "required": ["id", "module", "action", "args"],
      "additionalProperties": false,
      "properties": {
        "id":     { "type": "string" },
        "module": { "type": "string", "enum": ["stage", "viewport", "lakehouse", "extension"] },
        "action": { "type": "string" },
        "args":   { "type": "object" },
        "timeoutSeconds":    { "type": "number", "minimum": 1 },
        "continueOnFailure": { "type": "boolean" },
        "idempotent":        { "type": "boolean" },
        "retries": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "maxAttempts":          { "type": "integer", "minimum": 1 },
            "initialBackoffSeconds": { "type": "number", "minimum": 0 },
            "maxBackoffSeconds":     { "type": "number", "minimum": 0 }
          }
        }
      }
    }
  }
}
```

---

## 9. 향후 확장 모듈 예시

모든 새 모듈은 동일한 계약을 따릅니다:
- 타입화된 Request → `ModuleResult[T]` 반환
- 멱등성 메타데이터 지원
- 아티팩트 생성 가능
- YAML action 이름으로 시나리오에서 사용 가능

### 9.1 ROS 2 토픽 검증 모듈

```python
@dataclass(slots=True, frozen=True)
class Ros2MessageExpectation:
    topic: str                              # "/robot/joint_states"
    message_type: str                       # "sensor_msgs/msg/JointState"
    min_messages: int = 1
    timeout_s: float = 5.0
    predicates: tuple[str, ...] = ()        # JSONPath 식: "$.position[0] > 0.5"

class Ros2ModuleProtocol(Protocol):
    async def assert_topic_messages(
        self, meta: OperationMeta, expectation: Ros2MessageExpectation
    ) -> ModuleResult[AssertionReport]: ...

    async def get_topic_list(
        self, meta: OperationMeta
    ) -> ModuleResult[list[str]]: ...
```

**REST 엔드포인트**: `POST /validation/v1/ros2/assert/topic`

**YAML 사용 예시**:
```yaml
- id: joint_state_published
  module: ros2
  action: assert_topic_messages
  args:
    topic: /robot/joint_states
    message_type: sensor_msgs/msg/JointState
    min_messages: 1
    timeout_s: 5.0
    predicates:
      - "$.position[0] > 0.0"
```

### 9.2 물리 상태 검증 모듈

```python
@dataclass(slots=True, frozen=True)
class RigidBodyStateAssertion:
    prim_path: str
    position: tuple[float, float, float] | None = None
    orientation_xyzw: tuple[float, float, float, float] | None = None
    linear_velocity: tuple[float, float, float] | None = None
    angular_velocity: tuple[float, float, float] | None = None
    tolerance: float = 1e-3

@dataclass(slots=True, frozen=True)
class PhysicsSimulateRequest:
    duration_s: float = 1.0
    dt: float = 1.0 / 60.0
    gravity: tuple[float, float, float] = (0, -9.81, 0)

class PhysicsModuleProtocol(Protocol):
    async def simulate(
        self, meta: OperationMeta, request: PhysicsSimulateRequest
    ) -> ModuleResult[dict]: ...

    async def assert_rigid_body_state(
        self, meta: OperationMeta, assertion: RigidBodyStateAssertion
    ) -> ModuleResult[AssertionReport]: ...
```

**REST 엔드포인트**: `POST /validation/v1/physics/simulate`, `POST /validation/v1/physics/assert/rigid-body-state`

### 9.3 Sensor 데이터 검증 모듈 (미래)

```python
class SensorModuleProtocol(Protocol):
    async def assert_lidar_points(
        self, meta: OperationMeta, assertion: LidarAssertion
    ) -> ModuleResult[AssertionReport]: ...

    async def assert_camera_depth(
        self, meta: OperationMeta, assertion: DepthAssertion
    ) -> ModuleResult[AssertionReport]: ...
```

---

## 10. 테스트 전략 (Claude 보완)

> Gemini 미참여로 인해 Claude가 DX/테스트 관점을 보완합니다.

### 10.1 Isaac Sim 없이 MCP 서버 테스트하기

```
┌─ Unit Tests ─────────────────────────────────────────┐
│  모듈 로직 (diff 계산, SSIM, YAML 파싱) 단독 테스트   │
│  → Isaac REST 호출은 httpx.MockTransport로 스텁      │
└──────────────────────────────────────────────────────┘

┌─ Contract Tests ─────────────────────────────────────┐
│  fixtures/에 저장된 실제 응답 JSON으로 직렬화 검증     │
│  → Isaac Sim에서 한 번 녹화, 이후 반복 재생           │
└──────────────────────────────────────────────────────┘

┌─ Integration Tests (Isaac Sim 필요) ─────────────────┐
│  CI에서 Isaac Sim headless 컨테이너와 함께 실행       │
│  → docker-compose로 Isaac Sim + MCP 서버 구성        │
└──────────────────────────────────────────────────────┘
```

### 10.2 이미지 비교 확장 전략

| 기법 | 용도 | 구현 복잡도 |
|------|------|------------|
| **SSIM** (기본) | 전체 화면 유사도 | 낮음 |
| **ROI 마스킹** | 특정 영역만 비교 (crop 파라미터) | 낮음 |
| **Perceptual Hash** | 빠른 변화 감지 (phash) | 중간 |
| **Pixel Diff + 임계값** | 변경 픽셀 수/비율 기반 판단 | 중간 |
| **Semantic segmentation** | 3D 오브젝트별 영역 비교 (향후) | 높음 |

### 10.3 Observability

```python
# 구조화 로깅 예시
logger.info("step.execute",
    scenario_id="lakehouse_sync_add_cube",
    step_id="cube_exists",
    module="stage",
    action="assert_prim_exists",
    status="passed",
    duration_ms=142,
    request_id="req_abc123"
)
```

**Health Check Chain**:
```
MCP 서버 /health
  → Isaac REST /validation/v1/health
  → Lakehouse 연결 확인
  → 전체 상태 반환
```

---

## 11. 구현 우선순위 (권장)

| 단계 | 범위 | 산출물 |
|------|------|--------|
| **Phase 1** | Isaac Extension REST 엔드포인트 (health + stage snapshot + prim assert) | Extension이 외부에서 조회 가능한 상태 |
| **Phase 2** | MCP 서버 골격 + StageModule + 1개 시나리오 | 최소 E2E 동작 검증 |
| **Phase 3** | ViewportModule + 이미지 비교 | 시각적 검증 추가 |
| **Phase 4** | LakehouseModule + Composer/Runner | 전체 시나리오 자동화 |
| **Phase 5** | 확장 모듈 (ROS 2, Physics) | 도메인별 검증 |

---

## 참고

- Codex 분석 기반: Isaac Sim 5.1 `omni.services` 아키텍처 ([공식 문서](https://docs.omniverse.nvidia.com/services/latest/design/architecture.html))
- 기본 포트 `8011`은 omni.services 기본값
- 모든 타입은 Python 3.12+ 문법 기준 (제네릭 dataclass, `X | None` union)
