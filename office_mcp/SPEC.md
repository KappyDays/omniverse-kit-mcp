# Office–DataCenter Network Demo — Design Spec

**Date**: 2026-05-25
**Status**: Approved design (brainstorming complete)
**Output root**: `office_mcp/` (all artifacts of this work live here)
**Runtime**: Isaac Sim 5.1.0 (Windows 11)

---

## 1. 목표 (What we are building)

Isaac Sim 5.1 위에서 동작하는 **2개 산출물**:

1. **Scene 파일** (`office_mcp/scenes/office_datacenter.usd`) — 기본 물리 시뮬레이션을 포함하는 상호작용 가능한 실내 사무실 + 인접 데이터센터 환경.
2. **Kit Extension** (`omni.office_mcp.network_demo`) — 사용자가 위 Scene 을 불러오고(Load Scene), 시뮬레이션 play 중 PC 의 버튼 Prim 을 뷰포트에서 클릭하면, 케이블이 진행파(progress wave)로 하이라이트되며 데이터센터의 서버 3대에 **순차적으로** 데이터가 전송되는 모습을 시각화.

### 사용자 스토리

> 시뮬레이션이 play 된 상태에서, 사용자가 사무실 PC 의 전원 버튼(Prim)을 뷰포트에서 클릭 → PC→스위치→서버 케이블이 `net:order` 순서로 한 끝에서 다른 끝까지 emissive 펄스로 흐르고, 진행파가 각 서버에 도달할 때마다 해당 서버 LED 가 순차 점등. Extension 패널의 status Label 이 진행 상태를 텍스트로 표시.

---

## 2. 확정된 결정 사항 (Brainstorming 결과)

| 항목 | 결정 | 근거 |
|---|---|---|
| 전송 시각화 | **케이블 진행파 펄스 + 서버 LED 순차 점등** (packet 구체 없음) | 가장 단순/안정적, GIL·렌더 부하 최소 |
| 공간 배치 | **인접 두 공간** — 벽으로 분리된 office ↔ datacenter, 케이블 벽 관통 | 현실적 네트워크 거리감 |
| 자산 조달 | **live 탐색 → 실자산 우선, 없으면 근접 proxy** (R1 준수). 케이블만 BasisCurves tube (authored geometry) | 카탈로그에 PC/모니터/서버랙 전용 자산 불명확 |
| 상호작용 | **뷰포트 직접 클릭 (raycast pick)** — `usd_mouse_interact` 패턴 | 직관적 몰입감 |
| 물리 | **PhysicsScene + collider + 일부 dynamic rigid body** | "기본적인 물리 시뮬레이션 포함" 요구 |
| Extension UI | **Load Scene 버튼 + 상태/텔레메트리 Label** (Start/Stop·Reset 버튼 없음). UI 영어 only | 미니멀 패널, Kit 107 font atlas CJK 미지원 (hard rule) |
| play 진입 | **Isaac Sim 네이티브 play 버튼** 사용. Extension 은 play 상태를 감지해 Label 반영 + 클릭 trigger gating | 별도 버튼 불필요 |
| 서버/순차 | **PC → 스위치 → 서버 3대**, 진행파가 `net:order` 0→1→2→3 순차 hop, 각 서버 LED 순차 점등 | "순차 전송" 명시 시각화 |
| 아키텍처 | **접근법 A** — 정적 USD Scene + 런타임 구동 Extension | 사용자 요구("Scene 파일 직접 생성 + Extension 으로 로드")에 정확히 부합 |
| 애니메이션 구동 | **Python update-loop 구독** (OmniGraph 아님) | 선형 진행파에 OmniGraph 는 과함, 기존 패턴 재사용 |

---

## 3. 프로젝트 제약 (반드시 준수)

- **독립 구조 정책 (2026-04-22 확정)**: Kit SDK (`omni.kit.commands`/`omni.usd`/`pxr.*`) **직접 호출**. `validation_api` 의존 **금지**.
- **USD 로드 deadlock 방어 (필수)**: office.usd(MDL-heavy) payload 해소 시 hang 방어 — `kkr-extensions/docs/usd-load-deadlock-recipe.md` 의 3요소를 **복사**:
  1. `on_startup` 에서 `carb.logging.add_logger()` 호출 금지
  2. `omni.kit.async_engine.run_coroutine` + `asyncio.wrap_future`
  3. `CreatePayloadCommand(instanceable=True)` 로 reference 후 `_wait_stage_loading` tick 루프 (검증된 recipe 경로 — `open_stage` 는 deadlock 안전성 미검증이라 사용 안 함)
  4. play 중 로드 금지, USD URL/경로 는 forward-slash
- **R1 (실자산)**: primitive(Cube/Sphere)로 씬 객체 대체 금지. 케이블은 예외 — 전용 실자산 부재로 BasisCurves tube authored.
- **R2 (play 상태)**: 클릭 trigger 는 timeline play 중에만 동작.
- **R3 (시각검증)**: `viewport_capture` 후 Read tool 로 검증 의무. blank/black 이면 조명·카메라 재조정.
- **UI 영어 only**: Window title / Button / Label / status 모두 영어 (Kit 107 font atlas CJK glyph 부재).
- **로깅**: `carb.log_warn/info/error` 만. Python `logging`/`print` 금지.
- **`__init__.py` 에 IExt 서브클래스 import 필수** (없으면 on_startup 미호출).
- **uv 만 사용** (테스트 의존성 추가 시 `uv add --dev`).

---

## 4. 디렉토리 구조

```
office_mcp/
├─ SPEC.md                           # 이 문서
├─ GOAL.md                           # 새 세션 /goal 프롬프트
├─ README.md                         # 사용법 (구현 단계에서 작성)
├─ scenes/
│  └─ office_datacenter.usd          # 산출 Scene 파일 (build_scene.py 출력)
├─ build/
│  └─ build_scene.py                 # Kit SDK 로 Scene USD 를 저작·저장
├─ tests/
│  ├─ test_transmission.py           # 진행파 progress→segment 매핑 (Kit 무의존)
│  ├─ test_telemetry.py              # 상태 문자열 포맷
│  └─ test_scene_tags.py             # customData 발견·정렬
└─ exts/
   └─ omni.office_mcp.network_demo/
      ├─ config/extension.toml
      ├─ docs/CHANGELOG.md
      └─ omni/office_mcp/network_demo/
         ├─ __init__.py              # IExt import (필수)
         ├─ extension.py             # on_startup/on_shutdown + UI 윈도우
         ├─ safe_load.py             # deadlock-recipe 복사본
         ├─ scene_loader.py          # Load Scene 흐름 (new_stage + reference + 태그 검증)
         ├─ click_picker.py          # 뷰포트 클릭 → raycast → trigger 판정
         ├─ transmission.py          # 진행파 + LED 순차 점등 (update-loop)
         ├─ scene_tags.py            # customData 키/role 상수 + 발견 helper
         └─ telemetry.py             # 상태 모델 → Label 문자열
```

`office_mcp/exts/` 는 `kkr-extensions/` 밖이므로 Kit ext search path 에 추가 등록 필요 (README + GOAL 에 명시). 예: app `.kit` 의 `app.exts.folders` 또는 기동 인자 `--ext-folder office_mcp/exts`.

---

## 5. 아키텍처 — 2 레이어 분리

**Scene 레이어 (정적 USD)**: 지오메트리·물리·케이블·LED·머티리얼·태그. 재현 가능한 산출물.
**Extension 레이어 (런타임 행위)**: 로드·클릭 판정·진행파 구동·텔레메트리.
**계약 (contract)**: 둘은 `scene_tags.py` 의 customData 키로만 연결. Extension 은 prim 경로를 하드코딩하지 않고 customData `net:role` 로 발견 → 씬 리네이밍에 강건.

### customData 태그 계약

| customData 키 | 값 | 의미 |
|---|---|---|
| `net:role` | `trigger` | 클릭 대상 PC 전원 버튼 (1개) |
| `net:role` | `cable` | 케이블 세그먼트 (BasisCurves) |
| `net:role` | `switch` | 네트워크 스위치 (분기점) |
| `net:role` | `server_led` | 서버 LED prim |
| `net:order` | `int` | 진행파 시퀀스 순서 (cable/server_led 에 부여, 0→N) |

> customData 는 **nested dict** 로 저작: `customData = { dictionary net = { token role = "trigger"; int order = 0 } }`. 발견 시 `prim.GetCustomDataByKey("net:role")` (`:` 가 nested 경로로 해석됨).

---

## 6. Scene USD 구조 (`build_scene.py` 산출물)

```
/World
├─ Office (payload → office.usd, instanceable=True)    # 기존 자산
├─ DataCenter
│  ├─ Wall_Partition  (collider)                       # office ↔ datacenter 경계벽
│  ├─ ServerRack (live 탐색 실자산 / proxy: industrialsteelshelving 등)
│  │  ├─ Server_01 / Server_02 / Server_03
│  │  └─ Server_0N/LED  (net:role=server_led, net:order=N)
│  └─ Switch          (net:role=switch)
├─ Desk (실자산)
│  ├─ Monitor
│  └─ Desktop_PC
│     └─ PowerButton  (net:role=trigger)               # 클릭 대상
├─ NetworkCable                                         # BasisCurves tube
│  ├─ Seg_PC_to_Switch     (net:role=cable, net:order=0)
│  ├─ Seg_Switch_Server01  (net:role=cable, net:order=1)
│  ├─ Seg_Switch_Server02  (net:role=cable, net:order=2)
│  └─ Seg_Switch_Server03  (net:role=cable, net:order=3)
├─ Looks
│  ├─ CableMat   (UsdPreviewSurface, emissiveColor 초기 (0,0,0))
│  └─ LedMat_01..03 (server LED, emissive 초기 off)
├─ PhysicsScene  (gravity -9.81 Z 또는 stage up-axis 기준)
└─ Lighting (DomeLight + 보조 — R3 시각검증 통과용)
```

- **물리**: 바닥·벽·책상·서버랙 = static collider. 책상 위 소품 1-2개(머그 등 실자산) = dynamic rigid body → play 시 안정 안착, 클릭/충돌 반응.
- **케이블 라우팅**: PC PowerButton → 책상 뒤 → 벽 관통점 → datacenter 스위치 → 서버 3대. `net:order` 순서로 진행파 흐름.
- **emissive 초기 상태**: 케이블·LED 모두 off(0). Extension 이 런타임에 점등.
- **build_scene.py 실행 컨텍스트**: Kit Python 컨텍스트(스크립트 에디터 / `kit --exec` / MCP 실행 경로). office.usd 는 payload arc 로만 기록(빌드 시 MDL 미해소) — 실제 해소는 Load 시점.

---

## 7. Extension 컴포넌트 & 데이터 흐름

### 컴포넌트

- **extension.py**: `on_startup` 에서 `omni.ui` 윈도우 빌드(Load Scene 버튼 + status Label), 컨트롤러 인스턴스화, update/timeline/stage 이벤트 구독. `on_shutdown` 에서 구독 None 처리 + UI destroy. self-test customData stamp (`/OfficeMcp/SelfTestResult`).
- **safe_load.py**: deadlock-recipe 복사본 (`safe_load_usd`). `run_coroutine` + `wrap_future` + `CreatePayloadCommand(instanceable=True)` + `_wait_stage_loading` tick 루프.
- **scene_loader.py**: Load Scene 버튼 콜백 → `omni.usd.get_context().new_stage()` (깨끗한 스테이지) → `safe_load_usd(scene_file_url, prim_path="/World/OfficeDemo", instanceable=True)` 로 `office_datacenter.usd` 를 reference (nested office.usd payload 가 transitively MDL 해소) → `scene_tags.discover()` 로 태그된 prim 수집 → 누락 시 에러 텔레메트리. 로컬 경로는 forward-slash.
- **click_picker.py**: 뷰포트 마우스 클릭 구독 → 클릭 NDC 에서 raycast (`omni.usd` query_pick / viewport API) → hit prim 의 `net:role` 확인 → `trigger` 면 `transmission.start()`. **play 중에만** 활성(R2).
- **transmission.py**: 상태 머신 `idle → transmitting → delivered`. `start()` 시 progress=0. `_on_update(dt)` 가 progress 를 0→1 로 설정 가능한 duration(기본 ~3s)에 걸쳐 진행. progress 를 `net:order` 세그먼트에 매핑 → 진행파 front 가 지나는 케이블 세그먼트 emissive lerp, 세그먼트 완료 시 해당 서버 LED 점등. progress=1 → `delivered`. 재클릭 시 재시작.
- **telemetry.py**: 상태 + 현재 서버 인덱스 + progress% → Label 문자열 ("Idle" / "Transmitting → Server 02 (45%)" / "Delivered: 3/3 servers").
- **scene_tags.py**: customData 키 상수 + `discover(stage)` (stage traverse, role별 group, order 정렬).

### 데이터 흐름

```
1. [Load Scene 클릭] new_stage() → safe_load_usd(office_datacenter.usd → /World/OfficeDemo)
   → nested office.usd payload MDL 해소 (deadlock-safe tick)
   → scene_tags.discover() → telemetry="Scene loaded — press Play"
2. [네이티브 Play] timeline PLAY 이벤트 → click_picker arm
   → telemetry="Ready — click PC power button"
3. [뷰포트 클릭] raycast hit → role==trigger → transmission.start()
4. [update loop] progress 증가 → 케이블 세그먼트 emissive + 서버 LED 순차 점등
   → telemetry 매 프레임 갱신
5. progress=1 → telemetry="Delivered: 3/3 servers". 재클릭 시 2단계 상태에서 재시작.
```

---

## 8. 에러 처리 & 엣지 케이스

- **Load Scene 재호출**: idempotent — 스테이지 재오픈.
- **play 아닐 때 클릭**: 무시 + 힌트 텔레메트리 ("Press Play first").
- **trigger 아닌 prim 클릭**: 무시.
- **씬 태그 누락 (malformed)**: 에러 텔레메트리 ("Scene tags not found — rebuild scene"), 크래시 금지.
- **모든 Kit 호출 try/except + carb.log_***: usd_mouse_interact 패턴.
- **deadlock 가드**: on_startup 에서 add_logger 금지, forward-slash URL, play 중 로드 금지.
- **hot-reload 안전**: on_shutdown 에서 모든 구독 None, UI destroy.
- **UI 영어 only**.

---

## 9. 테스트 & 검증

- **단위 테스트 (Kit 무의존, pytest)**:
  - `test_transmission.py`: progress→segment 매핑, 순차 LED 점등 순서, delivered 전이.
  - `test_telemetry.py`: 상태별 Label 문자열 포맷.
  - `test_scene_tags.py`: role group + order 정렬 (mock prim/customData).
  - 상태 로직은 Kit/USD import 없이 순수 함수/클래스로 분리 (usd_mouse_interact 의 state_machine 패턴).
- **self-test stamp**: Extension 이 `/OfficeMcp/SelfTestResult` customData 에 결과 기록 (robot_lidar/stage_annotator 패턴).
- **시각 검증 (R3)**: build → load → play → trigger 후 `viewport_capture` 3 시점(idle / mid-transmission / delivered) + Read tool 로 케이블 glow·LED 점등 확인. office 책상 + datacenter 랙이 함께 보이는 프레이밍(또는 2 캡처).
- **R1**: 실자산 live 검증. 케이블 authored geometry 는 문서화된 예외.
- **R2**: trigger 는 play 상태 필수 — 테스트로 gating 확인.

---

## 10. 구현 순서 (제안)

1. `office_mcp/` 스캐폴드 + extension.toml + `__init__.py`/extension.py 최소 윈도우 (Load 버튼 + Label) → Kit 에서 로드 확인.
2. `build/build_scene.py` — office.usd payload + datacenter/desk/cable/물리/태그 저작 → `scenes/office_datacenter.usd` 저장. R3 시각 검증.
3. `scene_loader.py` + `safe_load.py` — new_stage + CreatePayloadCommand reference 로 정상 로드 + 태그 발견 확인.
4. `click_picker.py` — 뷰포트 클릭 raycast → trigger 판정 (play gating).
5. `transmission.py` + `telemetry.py` — 진행파 + LED 순차 점등 + Label.
6. 단위 테스트 + self-test stamp + 최종 R3 3-시점 시각 검증.
7. `README.md` 작성 (ext search path 등록 + 사용법).

---

## 11. 범위 밖 (YAGNI)

- packet 구체 애니메이션, OmniGraph, multi-server 병렬 분기, Start/Stop·Reset UI 버튼, 데이터센터 냉각/랙 디테일, 실제 네트워크 프로토콜 시뮬레이션, FPS 카메라 워크어라운드 — 모두 이번 범위 밖.
