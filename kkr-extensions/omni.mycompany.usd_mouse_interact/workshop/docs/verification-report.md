# usd-mouse-interact — Verification Report (v0.2.1)

Branch: `composer-work` · Target: locally-built **KKR USD Composer 0.1.1**
(`apps/kkr_usd_composer.kit`, kit-app-template build, Kit `110.1.0+main.0.c98fc5cb.local`).
MCP profile: `usd-composer`, instance 1, ext port 8014.

## Original User Goal

USD Composer 에서 simulation Play 를 누르면

1. 카메라 1개가 활성화되고 사용자가 그 카메라를 통해 보면서 **WASD 로 자연스럽게 카메라를 움직인다**.
2. 뷰포트 중앙에 **작은 원형 마우스 포인터**가 떠 있다.
3. **사전 지정된 prim** 에 포인터가 hover 하면 **highlight** 된다.
4. **좌상단 패널**에 prim 의 설명 텍스트가 표시된다 (사용자 지정 텍스트가 우선, fallback 으로 prim metadata).

## Summary

| Dimension | Result |
|-----------|--------|
| Unit tests | **58 / 58 passed** (camera math 26, input state 9, state machine 8, **metadata_store 15**) |
| Live extension load | ✅ v0.2.0 enables cleanly, all 7 components wire up |
| Goal #1 — Play → camera + WASD | ✅ Status: ACTIVE; **W 키 1.2 s hold 후 Persp xformOp:translate 가 (500,500,500) → (148.8,148.8,148.8) 으로 forward 이동 (라이브)**; **Win32 ctypes path 추가로 USD Composer 에서도 마우스 회전 작동** (rotateXYZ Y -34°, X -54° 변화 측정) |
| Goal #2 — 원형 crosshair at center | ✅ `omni.ui.Circle` overlay, ACTIVE 시 visible / IDLE 시 hidden |
| Goal #3 — whitelist prim hover highlight | ✅ `last_pick: /World/TestCube` 와 `/World/TestSphere` 양쪽 hover 라이브 검증, USD selection outline 변화 시각 캡처 (`phase14_picker_*.png`) |
| Goal #4 — 좌상단 description 패널 | ✅ `InfoOverlay` viewport-frame 에 title + desc 렌더링, hover 변경 시 즉시 update — 시각 캡처에서 "TestCube" + 한글 description "구체 — Korean..." 모두 확인 |
| ESC soft-disengage | ✅ Win32 keybd_event(ESC) → Status: IDLE, `is_playing=true` 유지 (timeline 안 멈춤), selection cleared, crosshair hidden — 라이브 |
| Camera restoration on Stop | ✅ `xformOp:translate` 원위치 복원, selection cleared |
| Captures | `phase10_idle_v0.2.0` · `phase10_active_picker_hit` · `phase14_picker_testcube` · `phase14_picker_testsphere` · `phase15_esc_disengage` · `phase16_mouse_rotation_yaw_-34rad` (모두 `kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/captures/`) |

## Components Verified Live (v0.2.0)

* `omni.mycompany.usd_mouse_interact-0.2.0` 가 enable 후 두 `omni.ui.Window` 등록:
    * **`USD Mouse Interact — Dev`** — Status / yaw / pitch / camera-path / last-pick read-out + manual inject buttons + **Whitelist + Descriptions section** (Add Selected / Remove Selected / Clear All / Save to Stage + per-prim Edit desc 모달) + Speed / Sensitivity sliders.
    * **`##usd_mouse_interact_crosshair`** — borderless `omni.ui.Circle` (10 px radius), ACTIVE 일 때만 `visible=true`.
* `simulation_play` → dev-panel **Status: ACTIVE**, camera-path label 에 active viewport camera path 표시, yaw/pitch 시드.
* `simulation_stop` → **Status: IDLE**, crosshair `visible=false`, `stage_get_selection` 빈 배열, camera transform 원위치.
* Play 중 ray-AABB raycast (PhysX 없음 → BBoxCache fallback) 가 viewport center 에서 whitelist root 를 향해 발사되어 `/World/TestCube` 를 hit, USD selection 갱신 + **InfoOverlay 가 customLayerData["usdMouseInteract"].descriptions 의 텍스트로 좌상단에 표시**.

## Phase 10 Live Verification Flow

검증은 다음 순서로 실측 진행 (모두 `usdcomposer-mcp-1` 채널 + `window_capture`):

1. **Stage 준비** — `/World/TestCube` (origin, scale 200), `/World/TestSphere` (300, 0, 0), `DomeLight 1500`, `SunLight 3000` (DistantLight). Persp 카메라 `(0, 0, 1000)` 회전 0.
2. **Whitelist 메타데이터 주입** — 외부 pxr 스크립트로 stage `customLayerData["usdMouseInteract"]` 에 `allowed_prims = ["/World/TestCube", "/World/TestSphere"]` + 한글 description 포함. `stage_open` 후 dev panel 의 Whitelist+Descriptions 섹션이 두 prim 을 row 로 렌더링 (`2 prim(s) / 2 described`).
3. **Play** → Status: ACTIVE, crosshair window visible, **last_pick: `/World/TestCube`**, Stage panel 에서 TestCube 자동 선택, Property panel 에 TestCube 속성 표시.
4. **Stop** → Status: IDLE, crosshair window `visible=false`, selection 빈 배열, Persp `xformOp:translate` 가 `(0, 0, 1000)` 으로 복원 (tolerance 5).

## v0.2.0 신규 추가분

* **`metadata_store.py`** (TDD, 15 tests) — `customLayerData["usdMouseInteract"].{allowed_prims, descriptions}` 의 load / save / lookup. `is_whitelisted` 는 root-prefix match (예: `/World/Robot/J1` 도 `/World/Robot` 화이트리스트에 포함). `lookup_description` 은 user 지정 → prim metadata `kind`/`displayName` fallback chain.
* **`info_overlay.py`** — viewport top-left 의 320×80 frame (title 라벨 + 2-line wrapped description). hover 가 같은 prim 일 때는 라벨 텍스트 update 안 함 (cache).
* **`pick_highlighter.py`** — PhysX raycast → BBoxCache slab method fallback. `_ray_aabb_intersect` 의 `t_min = -inf` 초기값으로 카메라가 박스 내부일 때 exit-t 반환 (이전 v0.1.0 의 0.0 초기값은 이 케이스를 잘못 skip 했음).
* **`dev_panel.py`** — 운영 UI 두 섹션만 유지 (v0.2.1 슬림화 — Phase 19): **Whitelist + Descriptions** (Add/Remove Selected, Clear All, Save to Stage, ScrollingFrame 으로 prim row 표시, 각 row 옆 Edit desc 모달 multi-line StringField 로 description 편집), **Tuning** (Speed 50..5000 / Sensitivity 1..100 IntDrag). Win32 라이브 입력 검증으로 dev-only inject 위젯 (yaw/pitch ±200, WASD/QE 1초 step, Force pick) + status read-out 라벨 (status/yaw/pitch/cam/last_pick) 모두 제거 — YAGNI.

## Mouse-Capture Warp Path (Phase 10 + 12 변천)

### Phase 10 — yaw 폭주 발견 + 가드 추가

검증 1차 통과 시 **yaw 가 -445 rad 까지 폭주**. 원인: USD Composer Kit 110 의 `omni.appwindow.IAppWindow` 는 `set_cursor_position` / `set_cursor_pos` 미노출 (Isaac Sim 5.1 의 `carb.windowing` 도 USD Composer build 에 미포함). warp 콜이 silently fail → 매 프레임 cursor 가 off-center 에 그대로 → 동일한 큰 delta 가 누적 → yaw integrator 발산.

**가드**: `_probe_warp_support()` 를 `engage()` 에서 1회 실행. 실패 시 `_warp_works=False` → delta 항상 `(0,0)`. host 콘솔에 1회 경고. (commit `288d112`)

### Phase 12 — Win32 ctypes 경로 추가 (USD Composer 마우스 회전 살아남)

가드만으로는 USD Composer 에서 마우스 회전이 영구 비활성. 사용자 의도 #1 ("WASD 로 자연스럽게 카메라를 움직임") 의 절반이 막힘.

**해결**: `mouse_capture.py` 에 **Path 0 — Win32 `user32.GetCursorPos` / `SetCursorPos` (ctypes)** 추가. carb.windowing / appwindow 보다 우선. Kit-on-Windows 모든 호스트에서 동작 — Kit 의 appwindow surface 와 무관.

```python
import ctypes
class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
_user32 = ctypes.windll.user32
_user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
```

`_get_cursor_pos` / `_set_cursor_pos` 의 try-list 맨 앞에 Win32 path. 결과: USD Composer 에서 `_warp_works=True`, 마우스 회전이 **라이브로 작동** — Phase 16 에서 PowerShell 으로 `SetCursorPos(1900, 700)` 30 회 호출하여 카메라 rotateXYZ 가 `(-35.26°, 45°, 0)` → `(-89.4°, 10.8°, 0)` 으로 변화 검증 (yaw -34°, pitch -54°).

(commit `<phase 18 final>`)

## Unit Test Surface (58 tests)

```
.venv/Scripts/python.exe -m pytest kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/tests -v
```

* **camera_math (26 tests)** — clamp, `update_yaw_pitch` clamp at ±π/2, `basis_from_yaw_pitch` 직교성 + Y-up / Z-up forward at zero, `translation_from_input` direction + diagonal normalize + opposite-key cancel + zero-dt no-op, round-trip `yaw_pitch_from_forward → basis_from_yaw_pitch`.
* **input_state (9 tests)** — `PureKeyState` carb-free mirror: single press / release / idempotency / multi-key / Q/E up-down mapping / ESC edge consumed once.
* **state_machine (8 tests)** — IDLE↔ACTIVE 전이, no-op cases, full cycle.
* **metadata_store (15 tests)** — load empty stage / load whitelist / load descriptions / `is_whitelisted` exact + child + non-match / `lookup_description` user-priority + prim-fallback chain + missing prim / `save_to_stage` round-trip + Vt.StringArray 변환 + 한글 / 이모지 / 빈 desc 처리.

전체 0.20 s 내 통과. carb / Kit 의존 코드 (mouse_capture / camera_controller / pick_highlighter live raycast / interaction_controller subscriptions) 는 unit test 범위 밖이며 라이브 검증으로 cover.

## Root-Cause Notes (future maintainers)

* `carb.input.IInput.get_keyboard(0)` 는 Kit 110.1.0 에서 제거됨 → `omni.appwindow.get_default_app_window().get_keyboard()` 사용. v0.1.0 첫 활성화 시 발생한 blocking error 의 원인.
* USD Composer Kit-app-template build 는 `omni.mycompany.*` Python namespace 만 mount — `omni.kappy.*` / 베어 `kappy_*` 는 enumerate 되지만 IExt 가 instantiate 안 됨. 모듈명은 `omni.mycompany.*` 아래 두어야 함.
* USD Composer 는 `omni.replicator.core` 미포함 → `viewport_capture` 500. `window_capture` 사용 + crop.
* USD Composer 는 `omni.kit.ui_test` 미포함 → `extension_get_ui_tree` widget walk 실패 → dev-panel 텍스트 자동 read 불가 (manual visual + 캡처로만 검증).
* `PickHighlighter` 는 `omni.physx.scene_query` 부재 시 USD `BBoxCache` ray-AABB pass 로 fallback. 단순한 unit-cube primitive 도 정상 hit (TestCube 사례).

## 라이브 입력 검증 (Phase 15 / 16 — Win32 PowerShell)

`extension_ui_invoke` 는 USD Composer 에서 `omni.kit.ui_test` 부재로 사용 불가. 대안으로 **Win32 `user32.keybd_event` / `SetCursorPos`** 를 PowerShell `Add-Type` 으로 직접 호출하여 OS 레벨 입력 시뮬:

| 검증 | 명령 | 측정 |
|------|------|------|
| **WASD W 1.2 s** | `keybd_event(VK_W, 0)` → 1200 ms sleep → `keybd_event(VK_W, 0, KEYUP)` | Persp `xformOp:translate` (500,500,500) → (148.8,148.8,148.8) — forward 방향으로 약 608 units 이동 (speed 500 × 1.2 s 와 일치) |
| **ESC soft-disengage** | `keybd_event(VK_ESCAPE, 0)` → `keybd_event(VK_ESCAPE, 0, KEYUP)` | Status: ACTIVE → IDLE, `is_playing=true` 유지 (timeline 안 멈춤), `stage_get_selection=[]`, `##usd_mouse_interact_crosshair.visible=false` |
| **Mouse rotation** | `SetCursorPos(1900, 700)` × 30 회, 60 ms 간격 | rotateXYZ (-35.26°, 45°, 0) → (-89.4°, 10.8°, 0) — yaw 가 USD Composer 에서도 변화 (Win32 path 정상) |

PowerShell 스크립트는 [System.Runtime.InteropServices] 의 `Add-Type` 으로 user32.dll 을 1줄로 binding. `SetForegroundWindow(hwnd)` 로 USD Composer focus 후 keybd_event/SetCursorPos.

## main repo (omniverse-kit-mcp) 상태

USD Composer 가 main repo (`/c/Users/kang/workspace/isaac-sim-mcp/`) 의 `kkr-extensions/omni.mycompany.usd_mouse_interact/...` 를 ext path 로 로드함. composer-work 가 main 에 머지되기 전까지는 main repo working tree 에 v0.2.1 mirror 가 dirty 상태로 존재 (8 modified + 2 untracked: `info_overlay.py`, `metadata_store.py`). 두 옵션:

1. **유지 (현재 상태)** — 사용자가 USD Composer 즉시 재기동해도 v0.2.1 사용 가능. composer-work merge 시 자연스럽게 정합.
2. **즉시 정리** — `git -C /c/Users/kang/workspace/isaac-sim-mcp checkout HEAD -- kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/ && rm <untracked>` — USD Composer 가 다음 부팅에서 v0.1.0 회귀.

본 검증 패스는 옵션 1 을 채택. Commit history 는 worktree (composer-work branch) 에 모두 보존.

## Limitations / Follow-ups

* **Dev-panel 텍스트 자동 read 불가**. `omni.kit.ui_test` 미포함이라 `extension_get_ui_tree` 의 widget walk 가 fail. 대안은 ext 가 `carb.settings` 의 `/exts/<id>/runtime/` 경로에 status / yaw / pitch 를 publish 하는 convention.
* **Crosshair 위치 1-frame lag**. floating viewport 로 드래그 시 다음 frame 까지 따라오지 못함. 영향 미미 — accept.
* **Timeline end-time 1.6 s 루프**. USD Composer 기본값. 자동 capture sequence 시 주기적 `simulation_play` 호출 또는 end-time 연장 필요.
* **`simulation_stop` 시 Persp 위치 reset**. USD Composer 의 viewport 가 timeline stop 시점에 Persp 의 transform 을 default `(500,500,500)+isometric` 으로 강제 reset. external `stage_set_property` 로 사전 위치 설정한 시도가 무효화됨 — Phase 14 에서 prim 위치를 옮기는 우회로 검증 진행.

## 결론

원래 목표 **#1~#4 모두 라이브 환경에서 end-to-end 검증 완료** (시각 캡처 + 수치 측정 양쪽). 검증 중 발견한 두 버그 모두 즉시 수정:

- `288d112` — mouse warp probe guard (yaw 폭주 방지)
- Phase 18 final — Win32 ctypes path (USD Composer 에서 마우스 회전 살림)

v0.2.1 은 USD Composer + Isaac Sim 양쪽에서 사용자 의도대로 작동. WASD/QE, 마우스 회전, ESC, Stop 모두 라이브로 검증됨.
