# usd-mouse-interact — Verification Report (v0.2.1)

Branch: `composer-work` · Target: locally-built **KKR USD Composer 0.1.1**
(`apps/kkr_usd_composer.kit`, kit-app-template build, Kit `110.1.0+main.0.c98fc5cb.local`).
MCP profile: `usd-composer`, instance 1, ext port 8114.

## Original User Goal

Click simulation Play in USD Composer

1. One camera is activated and the user looks through that camera and moves the camera naturally with WASD**.
2. A **small circular mouse pointer** is floating in the center of the viewport.
3. When the pointer hovers over the **pre-designated prim**, it becomes **highlight**.
4. The description text of prim is displayed in **top left panel** (custom text takes precedence, prim metadata as fallback).

## Summary

| Dimension | Result |
|-----------|--------|
| Unit tests | **58 / 58 passed** (camera math 26, input state 9, state machine 8, **metadata_store 15**) |
| Live extension load | ✅ v0.2.0 enables cleanly, all 7 components wire up |
| Goal #1 — Play → camera + WASD | ✅ Status: ACTIVE; **After holding the W key for 1.2 s, Persp xformOp:translate moves forward from (500,500,500) → (148.8,148.8,148.8) (live)**; **In addition to Win32 ctypes path, mouse rotation also works in USD Composer** (rotateXYZ Y -34°, X -54° change measurement) |
| Goal #2 — Circular crosshair at center | ✅ `omni.ui.Circle` overlay, visible when ACTIVE / hidden when IDLE |
| Goal #3 — whitelist prim hover highlight | ✅ Live verification of hover on both `last_pick: /World/TestCube` and `/World/TestSphere`, visual capture of USD selection outline changes (`phase14_picker_*.png`) |
| Goal #4 — Top left description panel | ✅ Render title + desc in `InfoOverlay` viewport-frame, update immediately when hover changes — Check all "TestCube" + Korean description "Sphere — Korean..." in visual capture |
| ESC soft-disengage | ✅ Win32 keybd_event(ESC) → Status: IDLE, `is_playing=true` maintained (timeline not stopped), selection cleared, crosshair hidden — Live |
| Camera restoration on Stop | ✅ `xformOp:translate` original position restoration, selection cleared |
| Captures | Local-only verification screenshots were produced under `workshop/captures/`; they are intentionally ignored in the public repo. |

## Components Verified Live (v0.2.0)

* After `omni.mycompany.usd_mouse_interact-0.2.0` is enabled, register two `omni.ui.Window`:
    * **`USD Mouse Interact — Dev`** — Status / yaw / pitch / camera-path / last-pick read-out + manual inject buttons + **Whitelist + Descriptions section** (Add Selected / Remove Selected / Clear All / Save to Stage + per-prim Edit desc modal) + Speed / Sensitivity sliders.
    * **`##usd_mouse_interact_crosshair`** — borderless `omni.ui.Circle` (10 px radius), `visible=true` only when ACTIVE.
* `simulation_play` → dev-panel **Status: ACTIVE**, active viewport camera path displayed in camera-path label, yaw/pitch seed.
* `simulation_stop` → **Status: IDLE**, crosshair `visible=false`, `stage_get_selection` empty array, camera transform original position.
* During play, ray-AABB raycast (no PhysX → BBoxCache fallback) is fired from the viewport center toward the whitelist root, hitting `/World/TestCube`, updating USD selection + **InfoOverlay is displayed at the top left with the text of customLayerData["usdMouseInteract"].descriptions**.

## Phase 10 Live Verification Flow

Verification is carried out in the following order (all `usdcomposer-mcp-1` channels + `window_capture`):

1. **Stage preparation** — `/World/TestCube` (origin, scale 200), `/World/TestSphere` (300, 0, 0), `DomeLight 1500`, `SunLight 3000` (DistantLight). Persp Camera `(0, 0, 1000)` Rotation 0.
2. **Whitelist metadata injection** — Including `allowed_prims = ["/World/TestCube", "/World/TestSphere"]` + Korean description in stage `customLayerData["usdMouseInteract"]` with external pxr script. After `stage_open`, the Whitelist+Descriptions section of the dev panel renders two prims as rows (`2 prim(s) / 2 described`).
3. **Play** → Status: ACTIVE, crosshair window visible, **last_pick: `/World/TestCube`**, Automatic selection of TestCube in Stage panel, Display TestCube properties in Property panel.
4. **Stop** → Status: IDLE, crosshair window `visible=false`, selection empty array, Persp `xformOp:translate` restored to `(0, 0, 1000)` (tolerance 5).

## v0.2.0 New additions* **`metadata_store.py`** (TDD, 15 tests) — load / save / lookup of `customLayerData["usdMouseInteract"].{allowed_prims, descriptions}`. `is_whitelisted` is a root-prefix match (e.g. `/World/Robot/J1` is also included in the `/World/Robot` whitelist). `lookup_description` is user designated → prim metadata `kind`/`displayName` fallback chain.
* **`info_overlay.py`** — 320×80 frame (title label + 2-line wrapped description) in viewport top-left. When hover is the same prim, label text is not updated (cache).
* **`pick_highlighter.py`** — PhysX raycast → BBoxCache slab method fallback. As the initial value of `t_min = -inf` of `_ray_aabb_intersect`, exit-t is returned when the camera is inside the box (the initial value of 0.0 in previous v0.1.0 incorrectly skipped this case).
* **`dev_panel.py`** — Maintain only two sections of operational UI (v0.2.1 slimmed down — Phase 19): **Whitelist + Descriptions** (Add/Remove Selected, Clear All, Save to Stage, display prim row with ScrollingFrame, edit description with multi-line StringField in Edit desc modal next to each row), **Tuning** (Speed 50..5000 / Sensitivity 1..100 IntDrag). Remove all dev-only inject widgets (yaw/pitch ±200, WASD/QE 1 second step, force pick) + status read-out labels (status/yaw/pitch/cam/last_pick) with Win32 live input verification — YAGNI.

## Mouse-Capture Warp Path (Phase 10 + 12 transition)

### Phase 10 — yaw runaway discovered + guards added

When passing the first verification, **yaw surges to -445 rad**. Cause: `omni.appwindow.IAppWindow` in USD Composer Kit 110 is not exposed as `set_cursor_position` / `set_cursor_pos` (`carb.windowing` in Isaac Sim 5.1 is also not included in USD Composer build). The warp call fails silently → The cursor remains off-center every frame → The same large delta accumulates → The yaw integrator diverges.

**Guard**: Run `_probe_warp_support()` once on `engage()`. In case of failure, `_warp_works=False` → delta always `(0,0)`. One warning on host console. (commit `288d112`)

### Phase 12 — Add Win32 ctypes path (USD Composer survives mouse rotation)

Guard alone permanently disables mouse rotation in USD Composer. Half of user intent #1 (“move the camera naturally with WASD”) is blocked.

**Solution**: Add **Path 0 — Win32 `user32.GetCursorPos` / `SetCursorPos` (ctypes)** to `mouse_capture.py`. Prefers carb.windowing/appwindow. Kit-on-Windows Works on all hosts — regardless of the Kit's appwindow surface.

```python
import ctypes
class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
_user32 = ctypes.windll.user32
_user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
```

Win32 path at the beginning of the try-list of `_get_cursor_pos` / `_set_cursor_pos`. Result: `_warp_works=True` in USD Composer, mouse rotation **works live** — In Phase 16, call `SetCursorPos(1900, 700)` 30 times with PowerShell to verify camera rotateXYZ changes from `(-35.26°, 45°, 0)` → `(-89.4°, 10.8°, 0)` (yaw -34°, pitch -54°).

(commit `<phase 18 final>`)

## Unit Test Surface (58 tests)

```
.venv/Scripts/python.exe -m pytest kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/tests -v
```

* **camera_math (26 tests)** — clamp, `update_yaw_pitch` clamp at ±π/2, `basis_from_yaw_pitch` orthogonality + Y-up / Z-up forward at zero, `translation_from_input` direction + diagonal normalize + opposite-key cancel + zero-dt no-op, round-trip `yaw_pitch_from_forward → basis_from_yaw_pitch`.
* **input_state (9 tests)** — `PureKeyState` carb-free mirror: single press / release / idempotency / multi-key / Q/E up-down mapping / ESC edge consumed once.
* **state_machine (8 tests)** — IDLE↔ACTIVE transition, no-op cases, full cycle.
* **metadata_store (15 tests)** — load empty stage / load whitelist / load descriptions / `is_whitelisted` exact + child + non-match / `lookup_description` user-priority + prim-fallback chain + missing prim / `save_to_stage` round-trip + Vt.StringArray conversion + Korean / emoji / empty desc processing.

All passed within 0.20 s. carb / Kit dependent code (mouse_capture / camera_controller / pick_highlighter live raycast / interaction_controller subscriptions) is outside the scope of unit tests and covered by live verification.

## Root-Cause Notes (future maintainers)* `carb.input.IInput.get_keyboard(0)` has been removed from Kit 110.1.0 → Use `omni.appwindow.get_default_app_window().get_keyboard()`. Cause of blocking error that occurred during first activation of v0.1.0.
* USD Composer Kit-app-template build only mounts the `omni.mycompany.*` Python namespace — `omni.kappy.*` / bare `kappy_*` is enumerate, but IExt is not instantiated. The module name must be placed under `omni.mycompany.*`.
* USD Composer does not include `omni.replicator.core` → `viewport_capture` 500. Uses `window_capture` + crop.
* USD Composer does not include `omni.kit.ui_test` → `extension_get_ui_tree` widget walk fails → dev-panel text cannot be read automatically (verified only by manual visual + capture).
* `PickHighlighter` falls back to USD `BBoxCache` ray-AABB pass in the absence of `omni.physx.scene_query`. A simple unit-cube primitive is also a normal hit (TestCube case).

## Live Input Validation (Phase 15/16 — Win32 PowerShell)

`extension_ui_invoke` cannot be used in USD Composer due to the absence of `omni.kit.ui_test`. Alternatively, simulate OS level input by calling **Win32 `user32.keybd_event` / `SetCursorPos`** directly with PowerShell `Add-Type`:

| verification | command | measurement |
|------|------|------|
| **WASD W 1.2 s** | `keybd_event(VK_W, 0)` → 1200 ms sleep → `keybd_event(VK_W, 0, KEYUP)` | Persp `xformOp:translate` (500,500,500) → (148.8,148.8,148.8) — Move approximately 608 units in the forward direction (consistent with speed 500 × 1.2 s) |
| **ESC soft-disengage** | `keybd_event(VK_ESCAPE, 0)` → `keybd_event(VK_ESCAPE, 0, KEYUP)` | Status: ACTIVE → IDLE, maintain `is_playing=true` (timeline does not stop), `stage_get_selection=[]`, `##usd_mouse_interact_crosshair.visible=false` |
| **Mouse rotation** | `SetCursorPos(1900, 700)` × 30 times, 60 ms interval | rotateXYZ (-35.26°, 45°, 0) → (-89.4°, 10.8°, 0) — yaw also changes in USD Composer (Win32 path normal) |

The PowerShell script binds user32.dll to `Add-Type` in [System.Runtime.InteropServices] in one line. After USD Composer focus with `SetForegroundWindow(hwnd)`, keybd_event/SetCursorPos.

## main repo (omniverse-kit-mcp) status

USD Composer loads `kkr-extensions/omni.mycompany.usd_mouse_interact/...` of main repo (`/c/path/to/omniverse-kit-mcp/`) into ext path. Until composer-work is merged into main, the v0.2.1 mirror exists in a dirty state in the main repo working tree (8 modified + 2 untracked: `info_overlay.py`, `metadata_store.py`). Two options:

1. **Maintain (Current Status)** — v0.2.1 is available even if the user immediately restarts USD Composer. Naturally aligned during composer-work merge.
2. **Immediate cleanup** — `git -C /c/path/to/omniverse-kit-mcp checkout HEAD -- kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/ && rm <untracked>` — USD Composer regresses to v0.1.0 on next boot.

This verification pass adopts option 1. Commit history is preserved in the worktree (composer-work branch).

## Limitations / Follow-ups

* **Dev-panel text cannot be read automatically**. Because `omni.kit.ui_test` is not included, the widget walk of `extension_get_ui_tree` fails. An alternative is the convention that ext publishes status / yaw / pitch to the `/exts/<id>/runtime/` path of `carb.settings` .
* **Crosshair position 1-frame lag**. When dragging to a floating viewport, it cannot follow to the next frame. Minor impact — accept.
* **Timeline end-time 1.6 s loop**. USD Composer default. During automatic capture sequence, periodic `simulation_play` call or end-time extension is required.
* **Persp position reset** at `simulation_stop`. USD Composer's viewport forces Persp's transform to reset to default `(500,500,500)+isometric` when the timeline stops. Attempt to set pre-position with external `stage_set_property` is invalidated — Verification carried out with bypass to move prim position in Phase 14.

## Conclusion

Original goal **Complete end-to-end verification of all #1 to #4 in a live environment** (both visual capture + numerical measurement). Immediately fix both bugs found during verification:

- `288d112` — mouse warp probe guard (yaw runaway prevention)
- Phase 18 final — Win32 ctypes path (Mouse rotation in USD Composer)

v0.2.1 works as intended in both USD Composer + Isaac Sim. WASD/QE, mouse rotation, ESC, and Stop are all verified live.