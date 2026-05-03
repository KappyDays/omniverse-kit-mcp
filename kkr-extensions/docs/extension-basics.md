<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Kit Extension 작성 / 수정 / 디버깅 공통 기본 지식 -->

# Extension Basics

Kit Extension 을 새로 만들거나 기존 것을 수정할 때 공통으로 알아야 할 내용.

## IExt 상속 3 요소 (필수)

1. `config/extension.toml` 에 `[[python.module]]` 선언
2. `omni/<vendor>/<name>/__init__.py` 에서 `IExt` 서브클래스 **import** — 없으면 Kit 이 `on_startup` 호출 안 함
3. `omni.ext.IExt` 를 **직접** 상속 (동적 변수나 metaclass 트릭 금지)

## 코드 수정 반영

| 상황 | 반영 방식 |
|------|----------|
| 로컬 개발 (스트리밍 미사용) | **Hot-reload** — 파일 저장만으로 자동 재로드됨. 필요 시 Extension Manager 에서 비활성→활성 토글로 강제 reload. `__pycache__` 는 자동 처리 |
| 스트리밍 / 원격 환경 | `__pycache__` 삭제 + Kit 완전 재시작 권장 (경험적 안전) |
| `extension.toml` 의 `[dependencies]` 변경 | **Kit 완전 재시작 필수** — hot-reload 로 dependency 그래프 갱신 안 됨 |

## 로깅

- `carb.log_info / log_warn / log_error` 만 Kit Console 에 보임
- Python 표준 `logging`, `print` 은 Kit Console 에 안 찍힘 (디버깅 시 혼란 유의)

## Extension API 호출 우선순위

1. `omni.kit.commands.execute(...)` — USD 조작 표준, **undo/redo 자동 지원**
2. `omni.usd.get_context().get_stage()` — Stage 직접 접근 필요할 때
3. `omni.timeline.get_timeline_interface()` — 시뮬레이션 제어
4. `pxr.*` (UsdGeom, Gf, Sdf, UsdSkel 등) — 저수준 USD 조작

`omni.kit.commands.CreatePrimWithDefaultXformCommand` 로 생성된 prim 은 이미 `xformOp` 포함 → `AddTranslateOp()` 대신 `prim.GetAttribute("xformOp:translate").Set(...)` 사용.

## omni.ui 제약 (UI 기획 전 필독)

- **Kit 107 `omni.ui` font atlas 는 kit.exe 기동 시 고정**, ASCII + Latin glyph 만 로드됨
- **한글 / CJK 문자 UI 에 넣지 말 것** — mojibake 로 깨짐. label, tooltip, status 모두 영어
- `omni.ui` 는 pytest 환경에서 위젯 동작 검증 불가 (stub 수준) — 실 UI QA 는 **live Kit + QA_CHECKLIST 수동** 방식

## Kit Python 환경 (107.3 기준 실측)

- Python 3.11
- Pydantic 2.12.5 + FastAPI 포함 → Extension 내 Pydantic v2 모델 사용 가능
- `omni.services.core` 1.9.1 (`C:\Users\<you>\AppData\Local\ov\data\exts\v2\omni.services.core-1.9.1\`) — FastAPI 기반 router registration

## 신규 독립 Extension 스켈레톤 (copy-paste)

> ⚠️ 루트 `CLAUDE.md` 의 **"신규 Extension 은 독립 구조"** 정책에 따라, 신규 extension 은 `validation_api` 에 의존하지 말고 Kit SDK 를 직접 사용.

```
kkr-extensions/omni.mycompany.<my_ext>/
├── config/
│   └── extension.toml
└── omni/mycompany/<my_ext>/
    ├── __init__.py
    └── extension.py
```

**`config/extension.toml`**:
```toml
[package]
version = "0.1.0"
title = "My Extension"
description = "Short description of what this does."
category = "Tools"   # or Tutorial / Validation / ...
keywords = ["..."]

[dependencies]
"omni.kit.uiapp" = {}
"omni.ui" = {}
# ⚠️ 신규 extension 은 validation_api 의존 금지
# "omni.mycompany.validation_api" = {}  ← 쓰지 말 것

[[python.module]]
name = "omni.mycompany.<my_ext>"
```

**`__init__.py`**:
```python
from .extension import MyExtension  # noqa: F401 — Kit 이 IExt 서브클래스 탐색
```

**`extension.py`**:
```python
from __future__ import annotations

import carb
import omni.ext


_SOURCE = "omni.mycompany.<my_ext>"


class MyExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._ext_id = ext_id
        # TODO: UI 창 / scene 동작 구현

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        # TODO: UI 정리 / listener 해제
```

MDL-heavy S3 asset 을 직접 로드해야 하면 `docs/usd-load-deadlock-recipe.md` 의 방어 코드를 복사해 가 사용.

## Extension 활성화 경로

| 경로 | 사용 시점 |
|------|----------|
| `kit.exe --enable <ext_id>` | 프로세스 레벨 (1회성 실행) |
| `.env` 의 `ISAAC_SIM_EXTRA_EXT_IDS` JSON array | `setup-omniverse-kit-mcp.bat` 로 MCP 서버 기동 시 자동 (학생 PC 배포 시 권장) |
| Extension Manager UI 토글 | 로컬 개발 중 수동 |

학생 / 신규 PC 에 자동 활성화하려면 **`.env`** 방식 채택 + `setup/setup_omniverse_kit_mcp.ps1` 에 반영.
