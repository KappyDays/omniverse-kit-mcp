# Stage Compass HUD

Floating top-down radar window for interactive stage exploration in
Isaac Sim 5.1 / USD Composer 2026.x.

## What it does

A small circular HUD docks in the top-right corner of the workspace and
re-renders ~12 times per second to show:

* Concentric range rings around the active viewport camera
* Coloured dot per tracked prim (mesh = green, camera = blue, light =
  yellow, articulation = orange, …) — projected onto the stage's floor
  plane (`Y`-up or `Z`-up auto-detected from `UsdGeomGetStageUpAxis`)
* World-fixed cardinal labels (N / E / S / W) that rotate with your
  heading so they always point in their actual world direction
* Camera marker triangle pointing in your current viewing direction
* Persistent waypoint flags you can save with one click
* Live world coordinates + heading degrees + cardinal tag

## Compatibility

| Host                                  | Status |
|---------------------------------------|--------|
| Isaac Sim 5.1 (`isaacsim.exp.full`)   | Verified — scanner / teleport / waypoint round-trip green via self-test |
| USD Composer 2026.x / Kit 110.x       | Verified — same self-test green; was the primary live target |
| Kit 107.x SDK                         | Source-compatible (uses only `omni.ui` 2.x + Pythonic USD APIs) |

Python: 3.11 (Kit 107) or 3.12 (Kit 110). No third-party PyPI packages.

## Dependencies

Declared in `config/extension.toml` (every entry is part of stock Kit —
**no external pip / conda / Nucleus dependencies**):

| Module                       | Used for                                        |
|------------------------------|-------------------------------------------------|
| `omni.kit.uiapp`             | Window / widget host                            |
| `omni.usd`                   | Stage access, selection, stage events           |
| `omni.ui`                    | All radar / panel widget composition            |
| `omni.kit.viewport.utility`  | Active viewport + camera path lookup            |
| `omni.kit.viewport.window`   | Viewport widget interop (kept for parity)       |
| `omni.timeline`              | Timeline event subscription (mark stage dirty)  |

Project policy: extension is **independent** — no `omni.mycompany.validation_api`
import, no in-process REST calls. Drop-in usable in any Kit 107 / 110
app that loads the modules above.

## Installation / activation

You have four equivalent ways to load this extension; pick whichever
fits your workflow best.

### 1. Drop the folder under an `--ext-folder`

The simplest path. Copy `omni.mycompany.stage_compass/` to any folder
you've registered with Kit and Kit will discover it on next boot:

```cmd
kit.exe ^
  --ext-folder C:/path/to/your/extensions ^
  --enable omni.mycompany.stage_compass
```

For long-term install, place the folder under the user-data extensions
path (e.g. `%LOCALAPPDATA%/ov/data/exts/v2/`) — Kit auto-scans that on
boot too.

### 2. Add to the project's `.env`

This repo's `setup-isaacsim-mcp.bat` reads `ISAAC_SIM_EXTRA_EXT_IDS` (a
JSON array) and forwards each id as `--enable …` to Kit. Append the
extension id:

```env
ISAAC_SIM_EXTRA_EXT_IDS=[..., "omni.mycompany.stage_compass"]
```

### 3. Window → Extensions UI (interactive)

Open the Extensions Manager (`Window → Extensions`), search for
"Stage Compass", flip the toggle. Effective immediately, persists in the
current session config.

### 4. MCP `extension_activate` (headless / scripted)

```python
extension_activate(ext_id="omni.mycompany.stage_compass")
# returns {"enabled": true}, two ui.Windows appear
```

For a code reload during development:
```python
extension_activate(ext_id="omni.mycompany.stage_compass", reload=True)
```

## How to use

1. Activate the extension via `Window → Extensions → Stage Compass HUD`
   or programmatically with `extension_activate`.
2. Two windows appear: **Stage Compass** (the HUD) and
   **Stage Compass — Settings**.
3. Tour the stage with normal viewport controls. The radar updates
   automatically.
4. **Click** anywhere inside the radar disc → camera teleports to the
   floor-plane location under the cursor (altitude unchanged).
5. **Mouse-wheel** over the radar → zoom range in / out.
6. **Zoom −/+** buttons step zoom by 1.5×. **Fit** auto-sizes the
   radar to fit the full stage extent. **Pin** drops a waypoint at the
   current camera location.
7. In the settings panel: toggle prim-type filters with the legend
   checkboxes, manage waypoints (rename / Go / delete), and read
   compact stage stats.

## Persistence

Waypoints are saved as a JSON blob in the stage's root-layer
`customLayerData` under the key `stage_compass:waypoints`. They round-
trip through USD save/load and survive between sessions.

## Hot-reload caveat

Module-level code changes need either `extension_activate(reload=True)`
or a Kit process restart. Following the project's standard reload
practice, the extension does not keep module-level singletons so a
re-enable cycle resets state cleanly.

## Layout

```
omni.mycompany.stage_compass/
├── config/extension.toml
└── omni/mycompany/stage_compass/
    ├── __init__.py
    ├── extension.py        # IExt entry point + self-test
    ├── stage_scanner.py    # Stage traversal + bbox cache
    ├── camera_helper.py    # Camera read / teleport / projection
    ├── compass_hud.py      # Radar window
    ├── settings_panel.py   # Filter + waypoints + stats window
    └── waypoint_store.py   # JSON-backed waypoint persistence
```

## Self-test

`on_startup` schedules an asynchronous self-test that

1. spawns a `/Compass/TestCube` and verifies the scanner picks it up,
2. teleports a dedicated `/Compass/TestCamera` (avoiding the Kit-
   manipulated `/OmniverseKit_Persp` whose session-layer state would
   shadow a root-layer write) and verifies the resulting transform
   delta,
3. round-trips a waypoint through the store.

Pass / fail booleans + diagnostic strings are stamped on
`/Compass/SelfTestResult` so headless MCP-driven validation can read
them without a UI-test harness:

```
stage_assert_property(
    "/Compass/SelfTestResult", "scan_ok",     expected_value=true
)
stage_assert_property(
    "/Compass/SelfTestResult", "teleport_ok", expected_value=true
)
stage_assert_property(
    "/Compass/SelfTestResult", "waypoint_ok", expected_value=true
)
```

## Known limitations

* Click-to-teleport on `/OmniverseKit_Persp` is best-effort — the helper
  authors both the rootLayer xformOp and a session-layer override so
  the manipulator picks up the new value next tick. For complex camera
  setups (with active animation curves on translate) the override may
  be re-asserted; using a user-defined camera prim avoids this.
* The radar caps at 600 dots per frame — enough for typical industrial
  scenes; further prims are culled by distance from the camera.
