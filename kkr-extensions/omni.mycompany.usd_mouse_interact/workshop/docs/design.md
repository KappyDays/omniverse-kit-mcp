# usd-mouse-interact — Design

## Goal

When you play timeline **Play** in USD Composer, you enter first-person (FPS) viewpoint control mode:

1. Change the yaw/pitch of the active camera just by moving the mouse (mouse capture)
2. Crosshair (+) displayed in the exact center of the viewport
3. Camera translation (forward/strafe/up-down) with WASD (option Q/E)
4. Highlight the prim indicated by the crosshair (update USD selection)
5. Release mode when Timeline **Stop/Pause** — restore cursor, hide crosshair, organize selection
6. As a user safety device, the mode is immediately released when **ESC** is pressed.

## Non-goals (YAGNI)

- gamepad/VR input
- prim drag / transform manipulation
- Camera physics collision (no-clip free flight)
- Simultaneous multi-viewport control (only 1 active viewport)

## Scope assumption (reconfirmed during verification stage)

- USD Composer (Kit 110.1.0) environment — `omni.timeline`, `omni.kit.viewport.utility`, `carb.input`, `omni.appwindow` available
- Active camera is `USDGeom.Camera` (prim of Stage) — read/write transform
- Supports both Y-up or Z-up stage (branched to `USDGeom.GetStageUpAxis`)

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

| module | responsibility | external dependence |
|------|------|-------|
| `extension.py` | `omni.ext.IExt` entry point, life cycle | `omni.ext` |
| `interaction_controller.py` | timeline event → active/inactive toggle, component orchestration | `omni.timeline`, `omni.kit.app` |
| `input_state.py` | WASD/Q/E/ESC key state + mouse dx/dy cumulative | `carb.input` |
| `camera_controller.py` | Apply yaw/pitch + translation of active viewport camera. Separate pure math into separate functions **Unit Test** | `omni.kit.viewport.utility`, `pxr.USDGeom`, `pxr.Gf` |
| `mouse_capture.py` | Hide cursor + warp cursor to viewport center every frame (after calculating delta) | `omni.appwindow`, `carb.input` |
| `crosshair_overlay.py` | Draw a + shape in the center of the viewport transparent `omni.ui.Window` | `omni.ui`, `omni.kit.viewport.utility` |
| `pick_highlighter.py` | viewport centered NDC → world ray → first hit prim → selection set | `omni.usd`, `omni.physx.scene_query` (1st round) / USD ray-AABB (fallback) |

## Data Flow (per-frame, active)

```
update tick
  │
  ▼
InputState.poll()           — carb.input updates key / mouse button state via
  │
  ▼
mouse_dx, mouse_dy = MouseCaptureSession.read_delta_and_warp()
  │
  ▼
CameraController.apply_yaw_pitch(dx, dy, dt)
  │
  ▼
CameraController.apply_translation(input_state, dt)   — handles WASD
  │
  ▼
PickHighlighter.update_at_center(viewport_api)        — center ray to prim path
  │
  ▼
omni.usd Selection.set_selected_prim_paths([path])    — outline highlight
```

## Key Decisions

1. **Mouse capture = cursor warp pattern**, OS-level raw input not used
   - Every frame (1) read current cursor position → (2) difference from viewport center = delta → (3) warp cursor to center
   - Only cross-platform, kit native API used. However, in Windows, try `omni.appwindow.get_default_app_window().get_window().set_cursor_mode("hidden")` to toggle the cursor visible/invisible → in case of failure, fallback to warping the cursor out of the viewport.
2. **Highlight = USD Selection** (no separate outline material created)
   - `omni.usd.get_context().get_selection().set_selected_prim_paths([path], True)` — Utilize Composer’s selection outline (orange)
   - 0 additional costs, intuitive for users
3. **Pick = PhysX raycast first, USD ray-AABB fallback**
   - During timeline play → Assuming PhysX is enabled. `omni.physx.scene_query.raycast_closest`
   - In a prim environment with PhysX disabled/no collider, fallback to USD `BBoxCache` based ray-AABB search (slow but accurate)
4. **ESC = soft release**
   - The timeline remains in the play state. Only turn off mode. Entering mode again occurs when the user clicks on the viewport — this is v2. In v1, only replay is supported after stopping the timeline.
5. **Camera up-axis automatic detection**
   - `USDGeom.GetStageUpAxis(stage)` → "Y" or "Z". yaw rotation axis determination
6. **dt clamp**
   - Prevent camera from bouncing with large dt when frame drops → clamp to max 0.1s

## Camera Math (unit test target)

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

Pure function — testable without Kit/USD.

## Error Handling| Scenario | Action |
|---------|------|
| No active viewport | `carb.log_warn` + activate noop |
| Active camera prim missing / wrong type | log_warn + activate noop |
| Mouse capture failed | log_warn + crosshair + only camera works (raycast/highlights are normal) |
| Raycast failed/no hit | selection clear (clear highlight) |
| timeline event subscription leak | explicit unsubscribe from `on_shutdown` + `_window.destroy()` |

## Testing Plan

### Unit tests (pytest, run without Kit)

- `test_camera_math.py` — yaw/pitch clamp, basis orthogonality, translation direction
- `test_input_state.py` — key press/release accumulation, double-press idempotency
- `test_interaction_state_machine.py` — IDLE → ACTIVE → IDLE transition, deactivate during ESC

### Manual + MCP Verification (USD Composer Live)

1. Timeline Play → Activate (app + viewport capture)
2. Crosshair visibility (app + viewport capture)
3. Mouse viewpoint conversion — Check viewport change after rotating left/right/up/down (capture before and after)
4. WASD movement — Check camera transform change after moving forward (capture before and after)
5. Prim highlight — When you point to prim with the mouse, a selection outline appears (capture before and after)
6. Timeline Stop → Disable + Restore cursor (Capture)Save 2 copies of `window_capture` (whole app) + `viewport_capture` (viewport) for each step.
`workshop/captures/` is a local verification output and does not commit to the public repo.

## File Layout

```
kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/
├── README.md
├── docs/
│   ├── design.md                      ← THIS
│   └── verification-report.md         (written after validation)
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

PhysX raycast is a standard package of USD Composer, so no separate dependency is required (use if available, fallback if not).

## Open Risks- What USD Composer's cursor mode API looks like in Kit 110.1.0 — Determined after actual measurement at the capture stage. fallback: Use only warp (cursor is visible but fixed in the exact center).
- `omni.physx.scene_query` is ready for timeline play immediately — race condition is possible. 1 frame delay allowed.
- USD Composer's active viewport camera path may be a non-stage camera such as the default `/OmniverseKit_Persp` — readonly when attempting to write. In this case, create a new `USDGeom.Camera` on stage and set it to active. In v1, leave the default persp as is, but guard whether transform write is possible with try/except.