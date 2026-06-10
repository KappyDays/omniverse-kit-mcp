# usd-mouse-interact — Design

## 목표

USD Composer 에서 timeline **Play** 시 1인칭(FPS) 시점 컨트롤 모드에 진입한다:

1. 마우스 이동 만으로 활성 카메라의 yaw/pitch 변경 (마우스 캡처)
2. Viewport 정중앙에 크로스헤어(+) 표시
3. WASD (옵션 Q/E) 로 카메라 평행 이동 (forward/strafe/up-down)
4. 크로스헤어가 가리키는 prim 을 하이라이트 (USD selection 갱신)
5. Timeline **Stop/Pause** 시 모드 해제 — cursor 복원, 크로스헤어 숨김, selection 정리
6. 사용자 안전장치로 **ESC** 시 즉시 mode 해제

## Non-goals (YAGNI)

- gamepad / VR 입력
- prim drag / transform manipulation
- 카메라 물리 충돌 (no-clip 자유 비행)
- 멀티 viewport 동시 컨트롤 (active viewport 1 개만)

## Scope 가정 (검증 단계에서 재확인)

- USD Composer (Kit 110.1.0) 환경 — `omni.timeline`, `omni.kit.viewport.utility`, `carb.input`, `omni.appwindow` 가용
- 활성 카메라가 `UsdGeom.Camera` (Stage 의 prim) — read/write 가능한 transform
- Y-up 또는 Z-up stage 모두 지원 (`UsdGeom.GetStageUpAxis` 로 분기)

## Architecture

```
TimelineWatcher                       (omni.timeline event sub)
  │
  ├─ on PLAY  ──►  InteractionController.activate()
  └─ on STOP  ──►  InteractionController.deactivate()
                       │
        ┌──────────────┼─────────────────────────┐
        ▼              ▼                         ▼
   CrosshairOverlay  MouseCaptureSession    PerFrameUpdater
   (omni.ui Window)  (cursor warp / hide)   (subscribe app update)
                                                  │
                            ┌─────────────────────┼─────────────┐
                            ▼                     ▼             ▼
                   CameraController        InputState     PickHighlighter
                   (yaw/pitch + WASD)     (key/mouse)    (raycast → selection)
```

## Components

| 모듈 | 책임 | 외부 의존 |
|------|------|-----------|
| `extension.py` | `omni.ext.IExt` 진입점, 라이프사이클 | `omni.ext` |
| `interaction_controller.py` | timeline event → 활성/비활성 토글, 컴포넌트 오케스트레이션 | `omni.timeline`, `omni.kit.app` |
| `input_state.py` | WASD/Q/E/ESC 키 상태 + 마우스 dx/dy 누적 | `carb.input` |
| `camera_controller.py` | active viewport camera 의 yaw/pitch + translation 적용. 순수 수학은 별도 함수로 분리해 **단위 테스트** | `omni.kit.viewport.utility`, `pxr.UsdGeom`, `pxr.Gf` |
| `mouse_capture.py` | cursor 숨김 + 매 프레임 cursor 를 viewport center 로 warp (delta 계산 후) | `omni.appwindow`, `carb.input` |
| `crosshair_overlay.py` | viewport 중앙에 + 모양 그리는 transparent `omni.ui.Window` | `omni.ui`, `omni.kit.viewport.utility` |
| `pick_highlighter.py` | viewport 중심 NDC → world ray → first hit prim → selection set | `omni.usd`, `omni.physx.scene_query` (1차) / USD ray-AABB (fallback) |

## Data Flow (per-frame, 활성 상태)

```
update tick
  │
  ▼
InputState.poll()           — carb.input 으로 키 / 마우스 button 상태 갱신
  │
  ▼
mouse_dx, mouse_dy = MouseCaptureSession.read_delta_and_warp()
  │
  ▼
CameraController.apply_yaw_pitch(dx, dy, dt)
  │
  ▼
CameraController.apply_translation(input_state, dt)   — WASD 처리
  │
  ▼
PickHighlighter.update_at_center(viewport_api)        — 중심 ray → prim path
  │
  ▼
omni.usd Selection.set_selected_prim_paths([path])    — outline highlight
```

## Key Decisions

1. **Mouse capture = cursor warp pattern**, OS-level raw input 미사용
   - 매 프레임 (1) 현재 cursor 위치 read → (2) viewport center 와의 차이 = delta → (3) cursor 를 center 로 warp
   - cross-platform, kit native API 만 사용. 단, Windows 에서 cursor visible/invisible 토글 위해 `omni.appwindow.get_default_app_window().get_window().set_cursor_mode("hidden")` 시도 → 실패 시 cursor 를 viewport 밖으로 warp 하는 방식 fallback
2. **Highlight = USD Selection** (별도 outline material 안 만듦)
   - `omni.usd.get_context().get_selection().set_selected_prim_paths([path], True)` — Composer 의 selection outline (orange) 활용
   - 추가 비용 0, 사용자에게 직관적
3. **Pick = PhysX raycast 우선, USD ray-AABB fallback**
   - timeline play 중 → PhysX 활성화 가정. `omni.physx.scene_query.raycast_closest`
   - PhysX 비활성 / collider 없는 prim 환경에서는 USD `BBoxCache` 기반 ray-AABB 검색으로 fallback (느리지만 정확성)
4. **ESC = soft 해제**
   - timeline 은 그대로 play 상태. mode 만 해제. 다시 mode 진입은 사용자가 viewport 클릭 시 — 이건 v2. v1 에서는 timeline stop 후 다시 play 만 지원
5. **Camera up-axis 자동 감지**
   - `UsdGeom.GetStageUpAxis(stage)` → "Y" or "Z". yaw 회전 축 결정
6. **dt clamp**
   - frame drop 시 큰 dt 로 카메라가 튀는 것 방지 → max 0.1s 로 clamp

## Camera Math (단위 테스트 대상)

```python
def update_yaw_pitch(yaw: float, pitch: float, dx_pixels: float, dy_pixels: float,
                    sensitivity: float = 0.0025) -> tuple[float, float]:
    new_yaw = yaw - dx_pixels * sensitivity            # right drag → look right
    new_pitch = clamp(pitch - dy_pixels * sensitivity, -PI/2 + 0.01, PI/2 - 0.01)
    return new_yaw, new_pitch

def basis_from_yaw_pitch(yaw: float, pitch: float, up_axis: str) -> tuple[Vec3, Vec3, Vec3]:
    # forward, right, up — orthonormal
    ...

def translation_from_input(forward: Vec3, right: Vec3, up: Vec3,
                           keys: InputState, speed: float, dt: float) -> Vec3:
    # W/S → ±forward, A/D → ∓right, E/Q → ±up
    ...
```

순수 함수 — Kit/USD 없이 테스트 가능.

## Error Handling

| 시나리오 | 동작 |
|---------|------|
| 활성 viewport 없음 | `carb.log_warn` + activate 노옵 |
| 활성 카메라 prim missing / 잘못된 type | log_warn + activate 노옵 |
| 마우스 캡처 실패 | log_warn + 크로스헤어 + 카메라만 동작 (raycast/하이라이트는 정상) |
| Raycast 실패 / hit 없음 | selection clear (highlight 해제) |
| timeline event subscription 누수 | `on_shutdown` 에서 명시적 unsubscribe + `_window.destroy()` |

## Testing Plan

### 단위 테스트 (pytest, Kit 없이 실행)

- `test_camera_math.py` — yaw/pitch clamp, basis 직교성, translation 방향
- `test_input_state.py` — 키 press/release 누적, double-press idempotency
- `test_interaction_state_machine.py` — IDLE → ACTIVE → IDLE 트랜지션, ESC 시 deactivate

### 수동 + MCP 검증 (USD Composer 라이브)

1. Timeline Play → 활성화 (app + viewport 캡처)
2. 크로스헤어 가시성 (app + viewport 캡처)
3. 마우스 시점 변환 — 좌/우/상/하 회전 후 viewport 변화 확인 (전후 캡처)
4. WASD 이동 — 전진 후 카메라 transform 변화 확인 (전후 캡처)
5. Prim highlight — 마우스 중심으로 prim 가리키면 selection outline 출현 (전후 캡처)
6. Timeline Stop → 비활성화 + cursor 복원 (캡처)

각 단계 `window_capture` (app 전체) + `viewport_capture` (viewport) 2 장씩 저장.
`workshop/captures/` 는 local verification output 이며 public repo 에 commit 하지 않는다.

## File Layout

```
kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/
├── README.md
├── docs/
│   ├── design.md                      ← THIS
│   └── verification-report.md         (검증 후 작성)
├── exts/
│   └── omni.mycompany.usd_mouse_interact/
│       ├── config/extension.toml
│       └── omni/kappy/usd_mouse_interact/
│           ├── __init__.py
│           ├── extension.py
│           ├── interaction_controller.py
│           ├── input_state.py
│           ├── camera_controller.py
│           ├── camera_math.py         (pure math, testable)
│           ├── mouse_capture.py
│           ├── crosshair_overlay.py
│           └── pick_highlighter.py
├── tests/
│   ├── conftest.py
│   ├── test_camera_math.py
│   ├── test_input_state.py
│   └── test_interaction_state_machine.py
└── captures/                         (local only; ignored)
```

## Dependencies (extension.toml)

```toml
[dependencies]
"omni.kit.uiapp" = {}
"omni.ui" = {}
"omni.kit.viewport.utility" = {}
"omni.timeline" = {}
"omni.usd" = {}
"omni.appwindow" = {}
```

PhysX raycast 는 USD Composer 의 standard package 이므로 별도 dependency 불필요 (있으면 사용, 없으면 fallback).

## Open Risks

- USD Composer 의 cursor mode API 가 Kit 110.1.0 에서 어떤 형태인지 — capture 단계에서 실측 후 결정. fallback: warp 만 사용 (cursor 는 보일 수 있지만 정중앙 고정).
- `omni.physx.scene_query` 가 timeline play 즉시 ready 인지 — race condition 가능. 1 frame 지연 허용.
- USD Composer 의 active viewport camera path 가 default `/OmniverseKit_Persp` 같은 비-stage 카메라일 가능 — write 시도 시 readonly. 이 경우 stage 에 새 `UsdGeom.Camera` 생성 후 active 로 set. v1 에서는 default persp 그대로 두되 transform write 가능 여부를 try/except 로 가드.
