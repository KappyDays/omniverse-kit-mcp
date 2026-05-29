# Office–DataCenter Network Demo

Isaac Sim 5.1 위에서 동작하는 **사무실 ↔ 데이터센터 네트워크 전송 시각화** 데모.

- **Scene** (`scenes/office_datacenter.usd`): `office.usd`(payload) 안의 열린 공간에
  데스크 + PC + 칸막이 + 서버랙(3대) + 스위치 + 케이블을 배치한 물리 포함 씬.
- **Extension** (`omni.office_mcp.network_demo`): Load Scene 버튼 + 상태 Label.
  play 중 PC 전원 버튼을 뷰포트에서 클릭하면 케이블이 `net:order` 순서로 emissive
  진행파(cyan)로 흐르고, 각 서버 LED 가 순차 점등(green)된다.

설계 원문(확정): [`SPEC.md`](SPEC.md). 새 세션 진입 프롬프트: [`GOAL.md`](GOAL.md).

---

## 디렉토리

```
office_mcp/
├─ SPEC.md / GOAL.md / README.md
├─ scenes/office_datacenter.usd      # build_scene.py 산출물
├─ build/build_scene.py              # Kit USD SDK 로 씬 저작
├─ tests/                            # Kit 무의존 pytest (25 케이스)
│  ├─ conftest.py / test_transmission.py / test_telemetry.py / test_scene_tags.py
└─ exts/omni.office_mcp.network_demo/
   ├─ config/extension.toml · docs/CHANGELOG.md
   └─ omni/office_mcp/network_demo/
      ├─ __init__.py · extension.py        # IExt + UI + 이벤트 wiring
      ├─ scene_tags.py                      # net:role/net:order customData 발견 (pure organize)
      ├─ transmission.py                    # WaveModel(pure) + TransmissionController(emissive)
      ├─ telemetry.py                       # 상태 → Label 문자열 (pure, ASCII only)
      ├─ click_picker.py                    # 뷰포트 선택 → trigger 판정 (play gating)
      ├─ scene_loader.py · safe_load.py     # deadlock-safe Load Scene 흐름
      └─ selftest.py                        # /OfficeMcp/SelfTestResult stamp (async)
```

---

## 1. 단위 테스트 (Kit 불필요)

순수 로직(진행파 매핑 / Label 포맷 / 태그 정렬)은 Kit 없이 검증한다.

```bash
uv run pytest office_mcp/tests/ -v        # 25 passed
```

---

## 2. Scene 빌드 (`office_datacenter.usd`)

`build_scene.py` 는 **standalone `LoadNone` 스테이지**에 저작하므로 라이브 Kit 스테이지를
건드리지 않는다(office.usd MDL 미해소 → 빌드 시 deadlock 없음). 실행 중인 Kit 의
스크립트 컨텍스트(MCP `kit_python_run` 등)에서:

```python
import importlib.util, sys
sys.dont_write_bytecode = True          # stale __pycache__ 회피
spec = importlib.util.spec_from_file_location(
    "build_scene", r"<repo>/office_mcp/build/build_scene.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.build())   # -> scenes/office_datacenter.usd 저장 + 태그 9개 보고
```

> 라이브 Kit 이 `office_datacenter.usd` 를 열어둔 상태에서는 파일이 잠겨 재-Export 가
> 무시된다. 재빌드 전 `kit_app_restart`(또는 `stage_new`)로 스테이지를 비울 것.

**사용 실자산**(R1): `office.usd`(payload, instanceable) · `desk_01` · `case_a01`(PC + 서버 3대)
· `industrialsteelshelving_a01`(서버랙 proxy) · `cubebox_a01`(스위치 / 동적 prop).
케이블은 BasisCurves tube authored(문서화된 예외). 전용 monitor 실자산은 카탈로그에 없어
생략(primitive 대체는 R1 위반이라 안 함).

---

## 3. Extension 등록 + 활성화

`office_mcp/exts/` 는 `kkr-extensions/` 밖이므로 ext search path 에 추가해야 한다.

### (A) 런타임 등록 — 현재 MCP 기동(고정 `--ext-folder kkr-extensions`)에서 즉시 사용

실행 중인 Kit 의 스크립트 컨텍스트에서:

```python
import omni.kit.app
mgr = omni.kit.app.get_app().get_extension_manager()
mgr.add_path(r"<repo>/office_mcp/exts")
mgr.set_extension_enabled_immediate("omni.office_mcp.network_demo", True)
```

### (B) 영구 등록 — Kit 기동 인자

```
kit.exe ... --ext-folder <repo>/office_mcp/exts --enable omni.office_mcp.network_demo
```

> Extension `.py` 를 수정하면 hot-reload 로는 `sys.modules` 가 정리되지 않으므로
> **Kit 재시작**(`kit_app_restart`) 후 (A)/(B) 로 다시 활성화한다.

---

## 4. 사용법

1. **Load Scene** 버튼 클릭 → 깨끗한 스테이지에 `office_datacenter.usd` 를 deadlock-safe
   하게 reference(`run_coroutine` + `CreatePayloadCommand` + `_wait_stage_loading` tick).
   Label: `Scene loaded - press Play`.
2. Isaac Sim **네이티브 Play** 버튼 → Label: `Ready - click the PC power button`.
3. 뷰포트에서 **PC 전원 버튼(빨간 disc) 클릭** → 케이블이 PC→스위치→서버 순서로
   cyan 진행파, 서버 LED 가 순차 green 점등. Label: `Transmitting -> Server NN (NN%)`
   → `Delivered: 3/3 servers`. 재클릭 시 재시작.

play 가 아닐 때 클릭하면 무시 + `Press Play first` 힌트(R2). UI 문자열은 영어 only
(Kit 107 font atlas CJK 미지원).

> 클릭 판정은 Kit 네이티브 viewport pick(선택 → `SELECTION_CHANGED`)을 활용한다 —
> NDC raycast 직접 구현보다 견고하고, `get_selection().set_selected_prim_paths([...])` 로
> 그대로 테스트 가능하다(SPEC §7 "raycast / viewport API" 의 viewport-API 해석).

---

## 5. 검증 (self-test)

Load Scene 후 스크립트 컨텍스트에서:

```python
import omni.office_mcp.network_demo.selftest as st
st.run()     # async 스케줄(즉시 반환) — 틱을 양보하며 실행
# 잠시 후 /OfficeMcp/SelfTestResult customData 의 selftest_ok / selftest_json 확인
```

검증 항목: 태그 발견 · emissive 바인딩 · 진행파 순차성(monotonic) · delivered 전 서버 점등
· 케이블 emissive 저작. (실측 5/5 green, `cable_emissive=1.6`.)

> self-test 는 **async** 다 — office.usd 로드 상태에서 emissive 를 타이트한 동기 루프로
> 쓰면 MDL/Hydra 가 settle 할 틱이 없어 kit.exe 가 ~92 s freeze 한다. 코루틴이
> 각 emissive 쓰기 사이에 `next_update_async()` 로 틱을 양보한다(= per-frame update 와 동일 패턴).

---

## 6. 시각 검증(R3) — 확인된 결과

`ReviewCamera`(+`ReviewCameraB/C`)로 캡처:

| 상태 | 결과 |
|---|---|
| idle | 케이블 OFF, 데스크/PC(좌) + 서버랙(우) + 낮은 칸막이(중앙) |
| mid (progress 0.5) | PC→스위치→서버1 케이블 cyan, 서버1 LED green |
| delivered (1.0) | 전 케이블 cyan + 서버 3대로 fan-out, LED 3개 green |

---

## 7. 제약 준수 (SPEC §3)

- 독립 구조: Kit SDK 직접 호출, `validation_api` 의존 없음.
- USD 로드 deadlock 방어 3요소 복사(`safe_load.py`) — `on_startup` add_logger 금지 /
  `run_coroutine`+`wrap_future` / `CreatePayloadCommand` + tick 루프 / forward-slash /
  play 중 로드 금지. **outer 로드는 `instanceable=False`**(태그 순회·emissive 편집 가능),
  nested `office.usd` 만 `instanceable=True`.
- R1 실자산 우선(케이블/전원버튼/LED/칸막이만 authored geometry 예외).
- R2 클릭 trigger 는 play 중에만. R3 viewport_capture + Read 검증.
- 로깅 `carb.log_*` only, `__init__.py` 에 IExt import, uv 만 사용.
