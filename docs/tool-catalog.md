# Isaac-sim MCP — Tool Catalog

Auto-generated from the live FastMCP server. Regenerate with `.venv/Scripts/python.exe scripts/generate_tool_catalog.py` after any tool addition / removal / signature change. `tests/unit/test_tool_catalog_sync.py` fails if this file drifts out of sync with the `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset SoT.

**Tool count**: 133

## Table of contents

- [Process — Kit app lifecycle](#process--kit-app-lifecycle) — 3 tools
- [Stage — READ / ASSERT / file & selection](#stage--read--assert--file--selection) — 6 tools
- [Stage — WRITE (mutations routed to SimulationModule)](#stage--write-mutations-routed-to-simulationmodule) — 7 tools
- [Simulation — timeline](#simulation--timeline) — 4 tools
- [Viewport — 3D renderer capture + camera](#viewport--3d-renderer-capture--camera) — 14 tools
- [Window — Kit GUI (app window / menus / omni.ui windows)](#window--kit-gui-app-window--menus--omniui-windows) — 7 tools
- [Extension — lifecycle / UI automation / carb log capture](#extension--lifecycle--ui-automation--carb-log-capture) — 13 tools
- [Lakehouse — query-only](#lakehouse--query-only) — 1 tools
- [Robot — articulation + navigation (ASYNC Job)](#robot--articulation--navigation-async-job) — 10 tools
- [Job — async job polling / cancel](#job--async-job-polling--cancel) — 2 tools
- [Asset — catalog browsing (GUI Asset Browser equivalent)](#asset--catalog-browsing-gui-asset-browser-equivalent) — 2 tools
- [Character — Biped_Setup + AnimationGraph + NavMesh (ASYNC Job)](#character--bipedsetup--animationgraph--navmesh-async-job) — 8 tools
- [Navigation — NavMesh bake / path query / exclude volume](#navigation--navmesh-bake--path-query--exclude-volume) — 5 tools
- [Scenario — YAML Arrange / Act / Assert / Cleanup runner](#scenario--yaml-arrange--act--assert--cleanup-runner) — 3 tools
- Unclassified (48)

## Process — Kit app lifecycle

### `kit_app_restart`

```python
kit_app_restart() -> 'str'
```

Restart the Kit application (stop → clear __pycache__ → start); use after modifying Extension
code.

### `kit_app_start`

```python
kit_app_start() -> 'str'
```

Start the Kit application for this MCP instance (Isaac Sim or USD Composer per
ISAAC_MCP_APP_PROFILE); waits for the validation REST health endpoint. Required before
stage/sim/viewport ops.

### `kit_app_stop`

```python
kit_app_stop() -> 'str'
```

Stop the Kit application (kit.exe) of this MCP instance only — other instances and other app
profiles are unaffected.

## Stage — READ / ASSERT / file & selection

### `stage_assert_prim_exists`

```python
stage_assert_prim_exists(prim_path: 'str', should_exist: 'bool' = True, expected_type_name: 'str | None' = None, expected_active: 'bool | None' = None) -> 'str'
```

Assert whether a specific Prim exists in the USD Stage. Checks existence, type name, and active
status.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `should_exist` | `boolean` | `True` |  |
| `expected_type_name` | `string \| None` | `None` |  |
| `expected_active` | `boolean \| None` | `None` |  |

### `stage_assert_property`

```python
stage_assert_property(prim_path: 'str', property_name: 'str', comparator: 'str' = 'equals', expected_value: 'Any' = None, expected_type_name: 'str | None' = None, tolerance: 'float | None' = None, property_kind: 'str' = 'attribute') -> 'str'
```

Assert a Prim attribute/relationship value. comparator ∈ {equals, not_equals, approx, gt, gte,
lt, lte, regex, contains, exists}; approx requires tolerance; set property_kind='relationship'
for rels.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `property_name` | `string` | `'—'` | ✓ |
| `comparator` | `string` | `'equals'` |  |
| `expected_value` | `Any` | `None` |  |
| `expected_type_name` | `string \| None` | `None` |  |
| `tolerance` | `number \| None` | `None` |  |
| `property_kind` | `string` | `'attribute'` |  |

### `stage_capture_snapshot`

```python
stage_capture_snapshot(include_prim_patterns: 'list[str] | None' = None, exclude_prim_patterns: 'list[str] | None' = None, include_properties: 'bool' = True, include_metadata: 'bool' = True, max_prim_count: 'int' = 10000) -> 'str'
```

Capture current USD Stage prim tree (prims + properties + relationships + metadata).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `include_prim_patterns` | `list[string] \| None` | `None` |  |
| `exclude_prim_patterns` | `list[string] \| None` | `None` |  |
| `include_properties` | `boolean` | `True` |  |
| `include_metadata` | `boolean` | `True` |  |
| `max_prim_count` | `integer` | `10000` |  |

### `stage_diff_snapshots`

```python
stage_diff_snapshots(before_snapshot_json: 'str', after_snapshot_json: 'str') -> 'str'
```

Diff two Stage snapshots (prims/properties added/removed/changed); pass two
stage_capture_snapshot JSON outputs.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `before_snapshot_json` | `string` | `'—'` | ✓ |
| `after_snapshot_json` | `string` | `'—'` | ✓ |

### `stage_get_selection`

```python
stage_get_selection() -> 'str'
```

Return the current Stage-panel selection (prim paths) — GUI Stage panel readout.

### `stage_set_selection`

```python
stage_set_selection(prim_paths: 'list[str]', expand_in_stage: 'bool' = True) -> 'str'
```

Replace the Stage-panel selection — GUI Stage panel click. *expand_in_stage* auto-expands the
tree to reveal selected prims.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_paths` | `list[string]` | `'—'` | ✓ |
| `expand_in_stage` | `boolean` | `True` |  |

## Stage — WRITE (mutations routed to SimulationModule)

### `stage_create_prim`

```python
stage_create_prim(prim_path: 'str', prim_type: 'str' = 'Xform', position: 'list[float] | None' = None) -> 'str'
```

Create a USD Prim. Types: Xform (empty transform), Cube, Sphere, Cylinder, Cone, Capsule,
Plane, etc. Optionally set position [x,y,z].

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `prim_type` | `string` | `'Xform'` |  |
| `position` | `list[number] \| None` | `None` |  |

### `stage_delete_prim`

```python
stage_delete_prim(prim_path: 'str') -> 'str'
```

Delete USD Prim (also removes children).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `stage_load_usd`

```python
stage_load_usd(usd_url: 'str', prim_path: 'str', position: 'list[float] | None' = None, rotation: 'list[float] | None' = None) -> 'str'
```

Add USD asset as payload at prim_path (multi-asset composition, not root replace). Optional
position/rotation.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `usd_url` | `string` | `'—'` | ✓ |
| `prim_path` | `string` | `'—'` | ✓ |
| `position` | `list[number] \| None` | `None` |  |
| `rotation` | `list[number] \| None` | `None` |  |

### `stage_new`

```python
stage_new() -> 'str'
```

Create empty stage (GUI File → New).

### `stage_open`

```python
stage_open(url: 'str') -> 'str'
```

Open (replace root) USD stage from local path or omniverse:// / https://; waits for load.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `url` | `string` | `'—'` | ✓ |

### `stage_save`

```python
stage_save(path: 'str | None' = None) -> 'str'
```

Save the current stage — GUI File → Save / Save As. Omit *path* for in-place save.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `path` | `string \| None` | `None` |  |

### `stage_set_property`

```python
stage_set_property(prim_path: 'str', property_name: 'str', value: 'Any', type_hint: 'str | None' = None) -> 'str'
```

Set a USD Prim attribute; type_hint specifies USD type
(Vec3d/Vec3f/Quatd/float/int/bool/string/asset).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `property_name` | `string` | `'—'` | ✓ |
| `value` | `Any` | `'—'` | ✓ |
| `type_hint` | `string \| None` | `None` |  |

## Simulation — timeline

### `simulation_get_status`

```python
simulation_get_status() -> 'str'
```

Get simulation timeline status: is_playing, current_time, fps, etc.

### `simulation_pause`

```python
simulation_pause() -> 'str'
```

Pause simulation timeline.

### `simulation_play`

```python
simulation_play() -> 'str'
```

Start simulation timeline (play button). Does NOT launch the Kit application — use
kit_app_start for that.

### `simulation_stop`

```python
simulation_stop() -> 'str'
```

Stop simulation timeline and reset time to 0 (stop button). Does NOT terminate the Kit
application — use kit_app_stop for that.

## Viewport — 3D renderer capture + camera

### `viewport_capture`

```python
viewport_capture(viewport_name: 'str' = 'Viewport', camera_prim_path: 'str | None' = None, renderer: 'str' = 'rtx', width: 'int' = 1280, height: 'int' = 720, output_format: 'str' = 'png', warmup_frames: 'int' = 0, return_stats: 'bool' = False) -> 'str'
```

Capture the 3D RTX render only (no Kit chrome) to PNG; returns artifact path. For the whole app
window (menus + panels + viewport) use window_capture instead. warmup_frames=N ticks extra
frames before grab (cold-RTX black fix); return_stats=True adds pixel_mean/pixel_variance per
channel so you can auto-detect a blank/black frame without reading the PNG.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'Viewport'` |  |
| `camera_prim_path` | `string \| None` | `None` |  |
| `renderer` | `string` | `'rtx'` |  |
| `width` | `integer` | `1280` |  |
| `height` | `integer` | `720` |  |
| `output_format` | `string` | `'png'` |  |
| `warmup_frames` | `integer` | `0` |  |
| `return_stats` | `boolean` | `False` |  |

### `viewport_capture_assert`

```python
viewport_capture_assert(viewport_name: 'str' = 'Viewport', camera_prim_path: 'str | None' = None, renderer: 'str' = 'rtx', width: 'int' = 1280, height: 'int' = 720, output_format: 'str' = 'png', warmup_frames: 'int' = 0, min_mean: 'float' = 8.0, min_variance: 'float' = 1.0) -> 'str'
```

Capture the 3D viewport with return_stats=True and fail fast on likely black/blank frames using
pixel mean/variance thresholds. Lower-stress precheck before visual Read.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'Viewport'` |  |
| `camera_prim_path` | `string \| None` | `None` |  |
| `renderer` | `string` | `'rtx'` |  |
| `width` | `integer` | `1280` |  |
| `height` | `integer` | `720` |  |
| `output_format` | `string` | `'png'` |  |
| `warmup_frames` | `integer` | `0` |  |
| `min_mean` | `number` | `8.0` |  |
| `min_variance` | `number` | `1.0` |  |

### `viewport_compare_ssim`

```python
viewport_compare_ssim(baseline_artifact_path: 'str', candidate_artifact_path: 'str', min_ssim: 'float' = 0.99, crop: 'list[int] | None' = None) -> 'str'
```

Compare two viewport images via SSIM (score + pass/fail).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `baseline_artifact_path` | `string` | `'—'` | ✓ |
| `candidate_artifact_path` | `string` | `'—'` | ✓ |
| `min_ssim` | `number` | `0.99` |  |
| `crop` | `list[integer] \| None` | `None` |  |

### `viewport_create`

```python
viewport_create(viewport_name: 'str', camera_path: 'str | None' = None, width: 'int' = 1280, height: 'int' = 720, docked: 'bool' = False) -> 'str'
```

Create secondary omni.kit.viewport.window; bind to camera_path if provided. Reuses existing
viewport with same name (response.existed=true).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'—'` | ✓ |
| `camera_path` | `string \| None` | `None` |  |
| `width` | `integer` | `1280` |  |
| `height` | `integer` | `720` |  |
| `docked` | `boolean` | `False` |  |

### `viewport_destroy`

```python
viewport_destroy(viewport_name: 'str') -> 'str'
```

Destroy secondary viewport window by name. Idempotent — destroyed=False if not found.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'—'` | ✓ |

### `viewport_focus_prim`

```python
viewport_focus_prim(prim_path: 'str', viewport_name: 'str' = 'Viewport', camera_path: 'str | None' = None, padding: 'float' = 1.35, select: 'bool' = True) -> 'str'
```

Frame a prim in the viewport, matching the F-key workflow. Selects the prim by default and
falls back to authored camera look-at when Kit viewport utility is unavailable.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `viewport_name` | `string` | `'Viewport'` |  |
| `camera_path` | `string \| None` | `None` |  |
| `padding` | `number` | `1.35` |  |
| `select` | `boolean` | `True` |  |

### `viewport_frame_prims`

```python
viewport_frame_prims(prim_paths: 'list[str]', viewport_name: 'str' = 'Viewport', camera_path: 'str | None' = None, include_purposes: 'list[str] | None' = None, margin: 'float' = 0.15, fov_deg: 'float' = 60.0, view_direction: 'list[float] | None' = None, up: 'list[float] | None' = None, set_camera: 'bool' = True) -> 'str'
```

Compute a camera eye/target/up that frames the given prim bboxes and optionally author it to
the active camera. Reduces camera-placement trial-and-error before viewport_capture.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_paths` | `list[string]` | `'—'` | ✓ |
| `viewport_name` | `string` | `'Viewport'` |  |
| `camera_path` | `string \| None` | `None` |  |
| `include_purposes` | `list[string] \| None` | `None` |  |
| `margin` | `number` | `0.15` |  |
| `fov_deg` | `number` | `60.0` |  |
| `view_direction` | `list[number] \| None` | `None` |  |
| `up` | `list[number] \| None` | `None` |  |
| `set_camera` | `boolean` | `True` |  |

### `viewport_project_points`

```python
viewport_project_points(points: 'list[list[float]]', viewport_name: 'str' = 'Viewport', camera_path: 'str | None' = None, width: 'int' = 1280, height: 'int' = 720) -> 'str'
```

Project world-space XYZ points through the active camera into normalized and pixel viewport
coordinates. Use to check whether important prim corners should appear in frame before capture.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `points` | `list[list[number]]` | `'—'` | ✓ |
| `viewport_name` | `string` | `'Viewport'` |  |
| `camera_path` | `string \| None` | `None` |  |
| `width` | `integer` | `1280` |  |
| `height` | `integer` | `720` |  |

### `viewport_set_active_camera`

```python
viewport_set_active_camera(camera_path: 'str', viewport_name: 'str' = 'Viewport') -> 'str'
```

Switch the viewport's active camera — GUI viewport toolbar camera selector.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `camera_path` | `string` | `'—'` | ✓ |
| `viewport_name` | `string` | `'Viewport'` |  |

### `viewport_set_camera_lookat`

```python
viewport_set_camera_lookat(eye: 'list[float]', target: 'list[float]', up: 'list[float] | None' = None, viewport_name: 'str' = 'Viewport', camera_path: 'str | None' = None) -> 'str'
```

Aim a camera at a target via eye/target/up (deadlock-safe USD xformOp author on the REST path;
default up=+Z). Moves the active viewport camera (Perspective included) unless camera_path is
given. Use for live framing iteration without rebuilding the scene.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `eye` | `list[number]` | `'—'` | ✓ |
| `target` | `list[number]` | `'—'` | ✓ |
| `up` | `list[number] \| None` | `None` |  |
| `viewport_name` | `string` | `'Viewport'` |  |
| `camera_path` | `string \| None` | `None` |  |

### `viewport_set_fov`

```python
viewport_set_fov(viewport_name: 'str' = 'Viewport', fov_deg: 'float' = 60.0) -> 'str'
```

Set viewport camera horizontal FOV in degrees (converts to focalLength). Writes to active
camera prim (fallback: /OmniverseKit_Persp).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'Viewport'` |  |
| `fov_deg` | `number` | `60.0` |  |

### `viewport_set_render_mode`

```python
viewport_set_render_mode(viewport_name: 'str' = 'Viewport', mode: 'str' = 'RealTime') -> 'str'
```

Switch RTX renderer mode. mode ∈ {RealTime, PathTracing}; PathTracing is more accurate but
slower.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'Viewport'` |  |
| `mode` | `string` | `'RealTime'` |  |

### `viewport_set_render_quality`

```python
viewport_set_render_quality(samples: 'int' = 1, denoiser: 'str' = 'auto') -> 'str'
```

Tune RTX path-tracing render quality. *samples* = path-tracing samples per pixel (higher = less
noise, slower). *denoiser* ∈ {auto, DLSS, NRD, off}.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `samples` | `integer` | `1` |  |
| `denoiser` | `string` | `'auto'` |  |

### `viewport_toggle_overlay`

```python
viewport_toggle_overlay(viewport_name: 'str' = 'Viewport', overlay: 'str' = 'gridlines', visible: 'bool' = True) -> 'str'
```

Toggle viewport overlay. overlay ∈ {gridlines, axis, stats}; stats toggles RTX FPS overlay.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'Viewport'` |  |
| `overlay` | `string` | `'gridlines'` |  |
| `visible` | `boolean` | `True` |  |

## Window — Kit GUI (app window / menus / omni.ui windows)

### `window_capture`

```python
window_capture(mode: 'str' = 'kit', hwnd: 'int | None' = None, settle_frames: 'int' = 5, output_format: 'str' = 'png', bring_to_front: 'bool' = False, use_client_rect: 'bool' = False, wait_stable: 'bool' = False, stable_interval_s: 'float' = 2.0, stable_consecutive: 'int' = 2, stable_max_wait_s: 'float' = 45.0, stable_diff_threshold: 'float' = 0.01) -> 'str'
```

Capture Kit main window (app chrome: Stage+Property+Timeline+3D viewport), NOT the 3D render
alone (use viewport_capture). wait_stable polls pixel diffs for async UI.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `mode` | `string` | `'kit'` |  |
| `hwnd` | `integer \| None` | `None` |  |
| `settle_frames` | `integer` | `5` |  |
| `output_format` | `string` | `'png'` |  |
| `bring_to_front` | `boolean` | `False` |  |
| `use_client_rect` | `boolean` | `False` |  |
| `wait_stable` | `boolean` | `False` |  |
| `stable_interval_s` | `number` | `2.0` |  |
| `stable_consecutive` | `integer` | `2` |  |
| `stable_max_wait_s` | `number` | `45.0` |  |
| `stable_diff_threshold` | `number` | `0.01` |  |

### `window_capture_sequence`

```python
window_capture_sequence(num_frames: 'int' = 10, interval_s: 'float' = 0.5, hwnd: 'int | None' = None, bring_to_front: 'bool' = False, use_client_rect: 'bool' = False, settle_frames: 'int' = 3) -> 'str'
```

Capture N full-window frames at `interval_s` spacing for motion verification.  Wraps
window_capture in a fixed-rate loop — used to record dynamic scenes (robot pick sequence,
conveyor cube transit, hover highlight on/off) where a single PNG is insufficient. Works on
both Isaac Sim and USD Composer (window_capture's GLFW30 auto-detect).  Returns JSON: {frames:
[{frame, path, sha256, ok, error?}], ...}.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `num_frames` | `integer` | `10` |  |
| `interval_s` | `number` | `0.5` |  |
| `hwnd` | `integer \| None` | `None` |  |
| `bring_to_front` | `boolean` | `False` |  |
| `use_client_rect` | `boolean` | `False` |  |
| `settle_frames` | `integer` | `3` |  |

### `window_list`

```python
window_list() -> 'str'
```

List top-level kit.exe OS windows (Win32 EnumWindows) with HWND — for debugging window_capture
auto-detection.

### `window_menu_list`

```python
window_menu_list(menu_path: 'str | None' = None) -> 'str'
```

Walk Kit merged menu tree; menu_path limits to subtree. Each item has onclick_action for
window_menu_trigger.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `menu_path` | `string \| None` | `None` |  |

### `window_menu_trigger`

```python
window_menu_trigger(menu_path: 'str') -> 'str'
```

Click a menu item by path via omni.kit.actions.core. Response includes created_prims (empty =
UI-only or no-op).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `menu_path` | `string` | `'—'` | ✓ |

### `window_ui_list`

```python
window_ui_list(name_filter: 'str | None' = None) -> 'str'
```

Enumerate registered omni.ui.Window instances. name_filter is case-insensitive substring. Lazy
windows (browsers) only appear after first show.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `name_filter` | `string \| None` | `None` |  |

### `window_ui_show`

```python
window_ui_show(name: 'str', visible: 'bool' = True, focus: 'bool' = True, settle_frames: 'int' = 5) -> 'str'
```

Toggle/focus omni.ui.Window by title; exact match then substring fallback. Response has
resolved_via and visible_after.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `name` | `string` | `'—'` | ✓ |
| `visible` | `boolean` | `True` |  |
| `focus` | `boolean` | `True` |  |
| `settle_frames` | `integer` | `5` |  |

## Extension — lifecycle / UI automation / carb log capture

### `extension_activate`

```python
extension_activate(ext_id: 'str', reload: 'bool' = False) -> 'str'
```

Enable Kit Extension by ext_id (Window → Extensions toggle). reload=True forces disable→enable
but does NOT clear sys.modules — for reliable .py reimport use extension_reload instead. 400 if
ext_id unknown.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string` | `'—'` | ✓ |
| `reload` | `boolean` | `False` |  |

### `extension_capture_logs`

```python
extension_capture_logs(ext_id: 'str | None' = None, since_ms: 'int | None' = None, level: 'str' = 'INFO', limit: 'int' = 1000) -> 'str'
```

Peek Extension carb.log ring buffer (maxlen 10000, does not drain). Filters: ext_id substring,
since_ms, level ∈ VERBOSE|INFO|WARN|ERROR|FATAL|ALL.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string \| None` | `None` |  |
| `since_ms` | `integer \| None` | `None` |  |
| `level` | `string` | `'INFO'` |  |
| `limit` | `integer` | `1000` |  |

### `extension_clear_logs`

```python
extension_clear_logs() -> 'str'
```

Empty the carb log ring buffer; returns removed count. Subsequent extension_capture_logs calls
will only see entries logged after this point.

### `extension_deactivate`

```python
extension_deactivate(ext_id: 'str') -> 'str'
```

Disable Kit Extension by id. Python module imports survive; for .py reimport rely on
omni.ext.plugin fswatcher auto-reload on file save (extension_activate(reload=True) only re-
toggles, does not clear sys.modules).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string` | `'—'` | ✓ |

### `extension_get_info`

```python
extension_get_info(ext_id: 'str') -> 'str'
```

Return ExtensionManager info for ext_id (bare id match). 404 if not registered.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string` | `'—'` | ✓ |

### `extension_get_state`

```python
extension_get_state() -> 'str'
```

Get the validation_api Extension's runtime state (enabled/busy/last_operation/errors) — this
MCP server's in-Kit companion, not an arbitrary Kit extension (use extension_get_info for
those).

### `extension_get_ui_tree`

```python
extension_get_ui_tree(ext_id: 'str | None' = None, window: 'str | None' = None, widget_types: 'list[str] | None' = None) -> 'str'
```

Return widget tree under an omni.ui.Window (omit to list all windows). widget.path →
extension_ui_invoke. widget_types overrides default allow-list.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string \| None` | `None` |  |
| `window` | `string \| None` | `None` |  |
| `widget_types` | `list[string] \| None` | `None` |  |

### `extension_list_all`

```python
extension_list_all(enabled_only: 'bool' = False) -> 'str'
```

Enumerate all Kit extensions known to ExtensionManager. enabled_only=True filters to active.
Item: {id, full_id, name, version, enabled, path, title}.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `enabled_only` | `boolean` | `False` |  |

### `extension_reload`

```python
extension_reload(ext_id: 'str') -> 'str'
```

Clean-reload a Kit Extension's Python code WITHOUT restarting Kit: disable -> purge sys.modules
tree (ext_id) -> invalidate import caches -> re-enable. Reflects .py edits + module-level
singletons. 400 for 'omni.mycompany.validation_api' (self-reload unsupported -> use
kit_app_restart) and unknown ext_id.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string` | `'—'` | ✓ |

### `extension_search`

```python
extension_search(keyword: 'str', app: 'str | None' = None, category: 'str | None' = None, limit: 'int' = 20) -> 'str'
```

Search docs/references/extensions.json (658 ext catalog) for candidates.  Matches `keyword`
(case-insensitive substring) against ext name / title / summary / mcp_research_hint /
raw_description / keywords. Empty keyword returns all entries matching optional filters.
Filters:   - app: "isaacsim" or "usd_composer" (include entries where that app key exists)   -
category: exact match on entry.category (case-insensitive)   - limit: max results (default 20)
Returns list of {name, title, summary, category, apps, key_symbols, mcp_research_hint}. Use
this when choosing a Kit Extension to wrap for a new MCP tool or to answer "which extension
handles X?" questions.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `keyword` | `string` | `'—'` | ✓ |
| `app` | `string \| None` | `None` |  |
| `category` | `string \| None` | `None` |  |
| `limit` | `integer` | `20` |  |

### `extension_trigger`

```python
extension_trigger(operation: 'str', payload: 'dict[str, Any] | None' = None, wait_for_idle: 'bool' = True, idle_timeout_s: 'float' = 30.0) -> 'str'
```

Trigger an operation on the validation_api Extension (this MCP server's in-Kit companion), e.g.
sync_from_lakehouse. Optionally waits for idle.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `operation` | `string` | `'—'` | ✓ |
| `payload` | `object \| None` | `None` |  |
| `wait_for_idle` | `boolean` | `True` |  |
| `idle_timeout_s` | `number` | `30.0` |  |

### `extension_ui_invoke`

```python
extension_ui_invoke(widget_path: 'str', action: 'str' = 'click', value: 'Any' = None) -> 'str'
```

Invoke widget by path. action ∈ {click, double_click, type, select, check, uncheck};
type/select take value. Returns post-action widget state.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `widget_path` | `string` | `'—'` | ✓ |
| `action` | `string` | `'click'` |  |
| `value` | `Any` | `None` |  |

### `extension_ui_run_and_wait`

```python
extension_ui_run_and_wait(widget_path: 'str', action: 'str' = 'click', value: 'Any' = None, wait_prim_path: 'str' = '', wait_property_name: 'str' = '', wait_expected_value: 'Any' = None, wait_comparator: 'str' = 'equals', wait_expected_type_name: 'str | None' = None, wait_property_kind: 'str' = 'attribute', wait_tolerance: 'float | None' = None, timeout_s: 'float' = 45.0, poll_interval_s: 'float' = 0.5) -> 'str'
```

Invoke an omni.ui widget, then poll a Stage property assertion until it passes or times out.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `widget_path` | `string` | `'—'` | ✓ |
| `action` | `string` | `'click'` |  |
| `value` | `Any` | `None` |  |
| `wait_prim_path` | `string` | `''` |  |
| `wait_property_name` | `string` | `''` |  |
| `wait_expected_value` | `Any` | `None` |  |
| `wait_comparator` | `string` | `'equals'` |  |
| `wait_expected_type_name` | `string \| None` | `None` |  |
| `wait_property_kind` | `string` | `'attribute'` |  |
| `wait_tolerance` | `number \| None` | `None` |  |
| `timeout_s` | `number` | `45.0` |  |
| `poll_interval_s` | `number` | `0.5` |  |

## Lakehouse — query-only

### `lakehouse_query`

```python
lakehouse_query(sql: 'str | None' = None, namespace: 'str | None' = None, dataset: 'str | None' = None, table: 'str | None' = None, filters: 'dict[str, Any] | None' = None, limit: 'int' = 1000) -> 'str'
```

Query Lakehouse REST for expected values; accepts raw SQL or namespace/dataset/table + filters.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `sql` | `string \| None` | `None` |  |
| `namespace` | `string \| None` | `None` |  |
| `dataset` | `string \| None` | `None` |  |
| `table` | `string \| None` | `None` |  |
| `filters` | `object \| None` | `None` |  |
| `limit` | `integer` | `1000` |  |

## Robot — articulation + navigation (ASYNC Job)

### `robot_drive_physics`

```python
robot_drive_physics(prim_path: 'str', waypoints: 'list[list[float]]', max_linear: 'float' = 1.0, max_angular: 'float' = 1.2, wheel_radius: 'float' = 0.14, wheel_base: 'float' = 0.413, arrival_tolerance: 'float' = 0.3, timeout_s: 'float' = 60.0, lookahead: 'float' = 0.8) -> 'str'
```

Drive a wheel-based articulation along ``waypoints`` using DifferentialController + Pure
Pursuit (physics-based, writes joint_velocities, spec §8.2).  ASYNC Job — returns ``{job_id}``;
poll ``job_status``. Requires timeline playing (R2). Wheel DOFs auto-resolved by name substring
scan (wheel_left/right or joint_wheel_*). Always zeros wheels on exit
(cancel/timeout/exception). Defaults are Nova Carter spec (wheel_radius=0.14,
wheel_base=0.413).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `waypoints` | `list[list[number]]` | `'—'` | ✓ |
| `max_linear` | `number` | `1.0` |  |
| `max_angular` | `number` | `1.2` |  |
| `wheel_radius` | `number` | `0.14` |  |
| `wheel_base` | `number` | `0.413` |  |
| `arrival_tolerance` | `number` | `0.3` |  |
| `timeout_s` | `number` | `60.0` |  |
| `lookahead` | `number` | `0.8` |  |

### `robot_get_ee_pose`

```python
robot_get_ee_pose(prim_path: 'str', end_effector_frame: 'str | None' = None) -> 'str'
```

Read the current end-effector world pose [position + qw,qx,qy,qz]. Prefer this for checking
whether a Franka controller is approaching the object before grasp.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `end_effector_frame` | `string \| None` | `None` |  |

### `robot_get_joint_config`

```python
robot_get_joint_config(prim_path: 'str') -> 'str'
```

Read drive stiffness/damping/max_force + position lower/upper limits + max joint velocity per
DOF. Symmetric readback for set_joint_positions — diagnose IK / drive_physics anomalies (drive
too soft, target outside limits, velocity capped). Source field reports backend (dof_properties
/ usd_drive_api fallback).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `robot_get_joint_positions`

```python
robot_get_joint_positions(prim_path: 'str') -> 'str'
```

Get joint positions of an articulation (via SingleArticulation).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `robot_gripper_control`

```python
robot_gripper_control(prim_path: 'str', action: 'str', target: 'float | None' = None) -> 'str'
```

Open/close/set gripper joints. action ∈ {open, close, set}; auto-detects finger/gripper DOF
names. Requires simulation playing.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `action` | `string` | `'—'` | ✓ |
| `target` | `number \| None` | `None` |  |

### `robot_load`

```python
robot_load(usd_url: 'str', prim_path: 'str', position: 'list[float] | None' = None, rotation: 'list[float] | None' = None) -> 'str'
```

Load robot USD at prim_path; detects PhysX ArticulationAPI for joint control. Optional initial
position/rotation.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `usd_url` | `string` | `'—'` | ✓ |
| `prim_path` | `string` | `'—'` | ✓ |
| `position` | `list[number] \| None` | `None` |  |
| `rotation` | `list[number] \| None` | `None` |  |

### `robot_navigate_path`

```python
robot_navigate_path(prim_path: 'str', waypoints: 'list[list[float]]', duration_s: 'float' = 5.0) -> 'str'
```

Dispatch multi-waypoint navigate as async Job; returns job_id. Each waypoint [x,y,z];
duration_s total (weighted by segment length). Requires timeline playing.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `waypoints` | `list[list[number]]` | `'—'` | ✓ |
| `duration_s` | `number` | `5.0` |  |

### `robot_navigate_to`

```python
robot_navigate_to(prim_path: 'str', target: 'list[float]', duration_s: 'float' = 1.0) -> 'str'
```

Dispatch a linear-interpolation navigate-to as an async Job. Returns a job_id — poll
job_status(job_id) until status='done'.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `target` | `list[number]` | `'—'` | ✓ |
| `duration_s` | `number` | `1.0` |  |

### `robot_set_ee_target`

```python
robot_set_ee_target(prim_path: 'str', target_pose: 'list[float]', robot_description: 'str' = 'Franka', end_effector_frame: 'str | None' = None) -> 'str'
```

Solve Lula IK for end-effector pose [x,y,z,qw,qx,qy,qz]; write joint positions. Franka-only;
other robot_description → 400. end_effector_frame overrides URDF frame.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `target_pose` | `list[number]` | `'—'` | ✓ |
| `robot_description` | `string` | `'Franka'` |  |
| `end_effector_frame` | `string \| None` | `None` |  |

### `robot_set_joint_positions`

```python
robot_set_joint_positions(prim_path: 'str', positions: 'list[float]') -> 'str'
```

Set articulation joint positions (SingleArticulation). Raises 400 if no PhysX articulation;
wrap in continueOnFailure for optional calls.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `positions` | `list[number]` | `'—'` | ✓ |

## Job — async job polling / cancel

### `job_cancel`

```python
job_cancel(job_id: 'str') -> 'str'
```

Cancel async Job (idempotent on terminal; 404 if unknown).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `job_id` | `string` | `'—'` | ✓ |

### `job_status`

```python
job_status(job_id: 'str') -> 'str'
```

Poll async Job status (returns status/progress/result/error).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `job_id` | `string` | `'—'` | ✓ |

## Asset — catalog browsing (GUI Asset Browser equivalent)

### `asset_list`

```python
asset_list(category: 'str | None' = None, subpath: 'str' = '', recursive: 'bool' = False, max_depth: 'int' = 2, max_entries: 'int' = 500) -> 'str'
```

Browse Isaac Sim asset catalog. No args → top-level categories; category → folder contents;
is_folder=false entries have spawnable url.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `category` | `string \| None` | `None` |  |
| `subpath` | `string` | `''` |  |
| `recursive` | `boolean` | `False` |  |
| `max_depth` | `integer` | `2` |  |
| `max_entries` | `integer` | `500` |  |

### `asset_search`

```python
asset_search(query: 'str', category: 'str | None' = None, limit: 'int' = 20) -> 'str'
```

Search the curated NVIDIA / Isaac Sim 5.1 asset catalog OFFLINE — no Isaac Sim required.  Maps
a natural-language need (e.g. "forklift", "warehouse", "franka", "police character", "pallet")
to concrete spawnable USD URLs by ranking the curated markdown catalog under docs/assets/isaac/
(robots 100+, environments, people/animations, props, SimReady 1000+). Use this at planning
time / before building a scene to pick a real asset (Validation Rule R1 — never substitute a
primitive); complements the live asset_list (which needs Isaac up) and content_browse.  Args:
query: free-text terms matched against asset name / catalog text.   category: optional filter —
one of robots / environments / people /     props / simready / other.   limit: max results
(default 20).  Returns a ranked list of {name, url, category, source_file}. Load a chosen url
with stage_load_usd / robot_load / character_load per docs/invariants/usd-load.md.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `query` | `string` | `'—'` | ✓ |
| `category` | `string \| None` | `None` |  |
| `limit` | `integer` | `20` |  |

## Character — Biped_Setup + AnimationGraph + NavMesh (ASYNC Job)

### `character_get_state`

```python
character_get_state(prim_path: 'str') -> 'str'
```

Return character position, rotation (scalar-first quaternion), active animation action,
is_navigating.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `character_load`

```python
character_load(usd_url: 'str', prim_path: 'str | None' = None, position: 'list[float] | None' = None, yaw: 'float' = 0.0) -> 'str'
```

Load character USD; auto-loads Biped_Setup rig, binds AnimationGraph. Returns prim_path +
skel_root. Sanitizes UUID filenames.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `usd_url` | `string` | `'—'` | ✓ |
| `prim_path` | `string \| None` | `None` |  |
| `position` | `list[number] \| None` | `None` |  |
| `yaw` | `number` | `0.0` |  |

### `character_load_crowd`

```python
character_load_crowd(count: 'int', layout: 'str' = 'grid', spacing: 'float' = 2.0, base_name: 'str' = 'Crowd', center: 'list[float] | None' = None, usd_url: 'str | None' = None) -> 'str'
```

Batch-load N characters (count 1-100) in layout ∈ {grid, line, random}. Defaults to
Biped_Setup.usd; override usd_url. Per-character failures in response.loaded.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `count` | `integer` | `'—'` | ✓ |
| `layout` | `string` | `'grid'` |  |
| `spacing` | `number` | `2.0` |  |
| `base_name` | `string` | `'Crowd'` |  |
| `center` | `list[number] \| None` | `None` |  |
| `usd_url` | `string \| None` | `None` |  |

### `character_navigate_to`

```python
character_navigate_to(prim_path: 'str', target: 'list[float]', speed: 'float' = 1.0) -> 'str'
```

Dispatch Walk-to-target as async Job; returns job_id. Character reverts to Idle on
cancel/timeout.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `target` | `list[number]` | `'—'` | ✓ |
| `speed` | `number` | `1.0` |  |

### `character_play_animation`

```python
character_play_animation(prim_path: 'str', animation_name: 'str', speed: 'float' = 1.0, target_position: 'list[float] | None' = None) -> 'str'
```

Play animation clip on character. animation_name ∈ {Idle, Walk, Run, Sit}; Walk/Run accept
target_position [x,y,z] for path-following.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `animation_name` | `string` | `'—'` | ✓ |
| `speed` | `number` | `1.0` |  |
| `target_position` | `list[number] \| None` | `None` |  |

### `character_play_animation_variant`

```python
character_play_animation_variant(prim_path: 'str', variant: 'str', speed: 'float' = 1.0, target_position: 'list[float] | None' = None) -> 'str'
```

Play AnimationGraph BlendSpace variant
(SitIdle/SitTalk/SitReading/WalkFast/WalkSlow/RunLow/RunHigh or plain Sit/Walk/Run/Idle).
response.variables_set lists applied keys.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `variant` | `string` | `'—'` | ✓ |
| `speed` | `number` | `1.0` |  |
| `target_position` | `list[number] \| None` | `None` |  |

### `character_set_position`

```python
character_set_position(prim_path: 'str', position: 'list[float]', orientation: 'list[float] | None' = None) -> 'str'
```

Write character world pose to USD (xformOp:translate + orientation, scalar-first
[qw,qx,qy,qz]). AnimGraph overrides the visual pose on the next tick, so get_state.position
will not reflect this — for visible motion use character_navigate_to; for initial placement use
character_load(position=...).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `position` | `list[number]` | `'—'` | ✓ |
| `orientation` | `list[number] \| None` | `None` |  |

### `character_stop_animation`

```python
character_stop_animation(prim_path: 'str') -> 'str'
```

Stop any active animation by switching the character to Idle (speed 0). Safe to call when
already Idle.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

## Navigation — NavMesh bake / path query / exclude volume

### `navigation_add_exclude_volume`

```python
navigation_add_exclude_volume(prim_path: 'str | None' = None, padding: 'float' = 0.1) -> 'str'
```

Add NavMeshVolume(Exclude) around prim's world-aligned bbox to block agent step-up. Requires
re-bake (navigation_bake) to take effect.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string \| None` | `None` |  |
| `padding` | `number` | `0.1` |  |

### `navigation_bake`

```python
navigation_bake(volume_scale: 'float' = 40.0, timeout_s: 'float' = 300.0) -> 'str'
```

Bake Stage NavMesh (creates NavMeshVolume if absent). Requires timeline stopped — playing
returns ok=True but get_navmesh()=None (false positive).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `volume_scale` | `number` | `40.0` |  |
| `timeout_s` | `number` | `300.0` |  |

### `navigation_query_path`

```python
navigation_query_path(start: 'list[float]', end: 'list[float]', agent_radius: 'float' = 0.25, agent_height: 'float' = 1.8, straighten: 'bool' = True) -> 'str'
```

Query shortest NavMesh path between two world-space points. Auto-bakes if needed
(response.auto_baked=true). straighten=True collapses straight runs.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `start` | `list[number]` | `'—'` | ✓ |
| `end` | `list[number]` | `'—'` | ✓ |
| `agent_radius` | `number` | `0.25` |  |
| `agent_height` | `number` | `1.8` |  |
| `straighten` | `boolean` | `True` |  |

### `navigation_sample_walkable_points`

```python
navigation_sample_walkable_points(count: 'int', bounds_min: 'list[float] | None' = None, bounds_max: 'list[float] | None' = None, seed: 'int | None' = None) -> 'str'
```

Sample N random walkable points on the baked NavMesh (area-weighted barycentric, spec §8.1).
count ∈ [1, 1000]. Optional [x,y,z] bounds_min/max restrict to AABB (both must be set or both
null). When triangle iteration API is unavailable on this Kit build, falls back to bbox-
rejection (random-in-bbox + reachability via query_shortest_path) — response ``method`` field
reports which path won. Requires prior navigation_bake.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `count` | `integer` | `'—'` | ✓ |
| `bounds_min` | `list[number] \| None` | `None` |  |
| `bounds_max` | `list[number] \| None` | `None` |  |
| `seed` | `integer \| None` | `None` |  |

### `navigation_set_visualization`

```python
navigation_set_visualization(mode: 'str') -> 'str'
```

Toggle NavMesh viewport overlay. mode ∈ {walkable, obstacles, off}. walkable shows baked
surface; obstacles shows excluded regions; off hides overlay.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `mode` | `string` | `'—'` | ✓ |

## Scenario — YAML Arrange / Act / Assert / Cleanup runner

### `scenario_last_report`

```python
scenario_last_report(scenario_id: 'str') -> 'str'
```

Get last execution report for a scenario_id from the most recent scenario_validate run.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `scenario_id` | `string` | `'—'` | ✓ |

### `scenario_plan`

```python
scenario_plan(scenario_path: 'str') -> 'str'
```

Compile scenario YAML and show execution plan (variables, phases, step graph) without running
it.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `scenario_path` | `string` | `'—'` | ✓ |

### `scenario_validate`

```python
scenario_validate(scenario_path: 'str', dry_run: 'bool' = False, fail_fast: 'bool | None' = None, input_overrides: 'dict[str, Any] | None' = None) -> 'str'
```

Execute YAML validation scenario (Arrange→Act→Assert→Cleanup). Returns step-level pass/fail
summary. input_overrides substitutes scenario variables.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `scenario_path` | `string` | `'—'` | ✓ |
| `dry_run` | `boolean` | `False` |  |
| `fail_fast` | `boolean \| None` | `None` |  |
| `input_overrides` | `object \| None` | `None` |  |

## Unclassified

### `content_browse`

```python
content_browse(url: 'str', recursive: 'bool' = False, max_depth: 'int' = 2, max_entries: 'int' = 500) -> 'str'
```

List URL children (omniverse://, https://, s3://, file:///). recursive walks up to max_depth.
Entry: {url, name, is_folder, size, modified_time_ns, flags}.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `url` | `string` | `'—'` | ✓ |
| `recursive` | `boolean` | `False` |  |
| `max_depth` | `integer` | `2` |  |
| `max_entries` | `integer` | `500` |  |

### `content_inspect`

```python
content_inspect(url: 'str') -> 'str'
```

Inspect a USD asset's GEOMETRY without adding it to the stage: opens the USD off the main
thread and returns default_prim, world bbox (bbox_min/bbox_max), meters_per_unit, up_axis, and
prim_count. Use at planning time to size/place an asset — content_preview only gives file
metadata (size/mtime). Needs the Omniverse/HTTP resolver, so values are produced live; off-
thread open keeps the Kit event loop unblocked.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `url` | `string` | `'—'` | ✓ |

### `content_preview`

```python
content_preview(url: 'str') -> 'str'
```

Stat a single URL; returns same entry shape as content_browse (size, mtime, is_folder, flags).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `url` | `string` | `'—'` | ✓ |

### `content_resolve`

```python
content_resolve(url: 'str') -> 'str'
```

Normalize URL via omni.client; collapses relative components, canonicalizes scheme, resolves
Nucleus prefix.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `url` | `string` | `'—'` | ✓ |

### `kit_command_execute`

```python
kit_command_execute(name: 'str', payload: 'dict | None' = None, expect_undo: 'bool' = False) -> 'str'
```

Execute an omni.kit.commands registered command.  Dispatches to the currently-active Kit app's
command registry. Common examples:   - CreateConveyorBelt (Isaac, isaacsim.asset.gen.conveyor)
- CreatePrimWithDefaultXform (common)   - ChangeProperty (common)  Unknown command names on the
current app return ok=false with error=command_exception (not a tool failure — parseable
result).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `name` | `string` | `'—'` | ✓ |
| `payload` | `object \| None` | `None` |  |
| `expect_undo` | `boolean` | `False` |  |

### `kit_python_run`

```python
kit_python_run(code: 'str', return_keys: 'list[str] | None' = None) -> 'str'
```

Run arbitrary Python source in the Kit main thread.  Fills the gap the Kit command registry
leaves — when the operation you need isn't a registered Kit command (USD relationship edits,
``Usd.EditContext`` walks, ``omni.client`` direct calls, bulk attribute author patterns), use
this instead of pasting code into the GUI Script Editor.  Args:   code: Python source.
Statements run in a fresh ``__main__``-style         namespace, so ``import omni.usd`` / ``from
pxr import ...``         work without setup.   return_keys: Optional list of namespace variable
names whose                final values are returned in the response. Empty =
stdout-only communication. Non-JSON-safe values are                coerced via str() fallback.
Returns: dict with ``ok`` / ``stdout`` / ``stderr`` / ``error`` / ``traceback`` / ``returned``.
Script exceptions become an ``error`` + ``traceback`` payload (the MCP call still succeeds —
caller inspects ``ok`` to decide).  Tool naming note: REST/internal names use ``python_run`` to
avoid the project's pre-tool security hook (which flags the literal substring ``exec`` followed
by ``(``); the user-facing tool name is also ``kit_python_run`` for consistency.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `code` | `string` | `'—'` | ✓ |
| `return_keys` | `list[string] \| None` | `None` |  |

### `lighting_create_disk`

```python
lighting_create_disk(prim_path: 'str', intensity: 'float' = 1000.0, radius: 'float' = 1.0) -> 'str'
```

Create a UsdLux.DiskLight at *prim_path*. Emission originates from a disk of radius *radius*
(meters).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `intensity` | `number` | `1000.0` |  |
| `radius` | `number` | `1.0` |  |

### `lighting_create_distant`

```python
lighting_create_distant(prim_path: 'str', intensity: 'float' = 1000.0, angle_deg: 'float' = 0.53) -> 'str'
```

Create a UsdLux.DistantLight (directional) at *prim_path*. *angle_deg* widens the shadow
penumbra (sun ≈ 0.53°).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `intensity` | `number` | `1000.0` |  |
| `angle_deg` | `number` | `0.53` |  |

### `lighting_create_dome`

```python
lighting_create_dome(prim_path: 'str', intensity: 'float' = 1000.0, texture: 'str | None' = None) -> 'str'
```

Create a UsdLux.DomeLight at *prim_path* for HDRI environment lighting. Optionally bind a
*texture* (HDR/EXR URL or local path).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `intensity` | `number` | `1000.0` |  |
| `texture` | `string \| None` | `None` |  |

### `lighting_create_rect`

```python
lighting_create_rect(prim_path: 'str', intensity: 'float' = 1000.0, width: 'float' = 1.0, height: 'float' = 1.0) -> 'str'
```

Create a UsdLux.RectLight at *prim_path* with a *width* × *height* emission surface (meters).
Typical softbox / window light.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `intensity` | `number` | `1000.0` |  |
| `width` | `number` | `1.0` |  |
| `height` | `number` | `1.0` |  |

### `lighting_create_sphere`

```python
lighting_create_sphere(prim_path: 'str', intensity: 'float' = 1000.0, radius: 'float' = 1.0) -> 'str'
```

Create a UsdLux.SphereLight at *prim_path* with *radius* (meters). Represents a point-ish bulb
with finite area for soft shadows.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `intensity` | `number` | `1000.0` |  |
| `radius` | `number` | `1.0` |  |

### `lighting_set_exposure`

```python
lighting_set_exposure(exposure: 'float') -> 'str'
```

Set RTX tonemap exposure globally (carb /rtx/post/tonemap/exposure); positive brightens,
negative darkens.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `exposure` | `number` | `'—'` | ✓ |

### `material_assign_mdl`

```python
material_assign_mdl(prim_path: 'str', mdl_url: 'str', material_name: 'str') -> 'str'
```

Create MDL-backed UsdShade.Material under /World/Materials and bind to prim_path
(strongerThanDescendants).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `mdl_url` | `string` | `'—'` | ✓ |
| `material_name` | `string` | `'—'` | ✓ |

### `material_get_bound`

```python
material_get_bound(prim_path: 'str') -> 'str'
```

Read direct material binding for prim_path; returns {material_path, binding_strength} (None
when unbound).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `material_list_mdl`

```python
material_list_mdl(library: 'str' = 'default') -> 'str'
```

Enumerate .mdl modules under Kit install; library is alias or absolute path. Returns {name,
url, library} entries.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `library` | `string` | `'default'` |  |

### `omnigraph_connect`

```python
omnigraph_connect(src_attr: 'str', dst_attr: 'str') -> 'str'
```

Connect OmniGraph attributes: '/Graph/Node.outputs:<attr>' → '/Graph/Node.inputs:<attr>'. Works
for compute and execution edges.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `src_attr` | `string` | `'—'` | ✓ |
| `dst_attr` | `string` | `'—'` | ✓ |

### `omnigraph_create_node`

```python
omnigraph_create_node(graph_path: 'str', node_type: 'str', node_name: 'str | None' = None) -> 'str'
```

Create OmniGraph node inside graph_path (auto-creates graph if absent). node_type e.g.
'omni.graph.action.OnTick'. node_name defaults to last segment.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `graph_path` | `string` | `'—'` | ✓ |
| `node_type` | `string` | `'—'` | ✓ |
| `node_name` | `string \| None` | `None` |  |

### `omnigraph_create_ros2_publisher`

```python
omnigraph_create_ros2_publisher(graph_path: 'str', topic: 'str', source_prim: 'str', msg_type: 'str' = 'sensor_msgs/msg/Image') -> 'str'
```

Assemble ActionGraph (OnTick→RenderProduct→ROS2PublishImage) for camera publishing. rclpy
unavailable → graph only (response.ros2_available=false).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `graph_path` | `string` | `'—'` | ✓ |
| `topic` | `string` | `'—'` | ✓ |
| `source_prim` | `string` | `'—'` | ✓ |
| `msg_type` | `string` | `'sensor_msgs/msg/Image'` |  |

### `omnigraph_create_script_controller`

```python
omnigraph_create_script_controller(script_path: 'str', graph_path: 'str' = '/World/ActionGraph', node_name: 'str' = 'ScriptNode', tick_node_name: 'str' = 'OnPlaybackTick', evaluator: 'str' = 'execution', reset_state: 'bool' = True) -> 'str'
```

Create ActionGraph OnPlaybackTick→ScriptNode and bind script_path. This mirrors Isaac Sim
example style: MCP builds wiring; controller logic runs in Kit on playback ticks.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `script_path` | `string` | `'—'` | ✓ |
| `graph_path` | `string` | `'/World/ActionGraph'` |  |
| `node_name` | `string` | `'ScriptNode'` |  |
| `tick_node_name` | `string` | `'OnPlaybackTick'` |  |
| `evaluator` | `string` | `'execution'` |  |
| `reset_state` | `boolean` | `True` |  |

### `omnigraph_execute`

```python
omnigraph_execute(graph_path: 'str') -> 'str'
```

Evaluate graph_path once; fires OnTick + downstream manually for ActionGraphs when scene event
is unavailable.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `graph_path` | `string` | `'—'` | ✓ |

### `physics_apply_collider`

```python
physics_apply_collider(prim_path: 'str', approximation: 'str' = 'convexHull') -> 'str'
```

Apply UsdPhysics.CollisionAPI to prim_path; also MeshCollisionAPI with approximation ∈
{convexHull, triangleMesh, sdf, box, sphere, none}.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `approximation` | `string` | `'convexHull'` |  |

### `physics_apply_material`

```python
physics_apply_material(prim_path: 'str', friction: 'float' = 0.5, restitution: 'float' = 0.0, density: 'float' = 1000.0, material_name: 'str | None' = None) -> 'str'
```

Create PhysicsMaterial under /World/PhysicsMaterials and bind to prim_path. friction =
static+dynamic; restitution ∈ [0,1].

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `friction` | `number` | `0.5` |  |
| `restitution` | `number` | `0.0` |  |
| `density` | `number` | `1000.0` |  |
| `material_name` | `string \| None` | `None` |  |

### `physics_apply_rigid_body`

```python
physics_apply_rigid_body(prim_path: 'str', mass: 'float' = 1.0, dynamic: 'bool' = True) -> 'str'
```

Apply UsdPhysics.RigidBodyAPI + MassAPI to prim_path. dynamic=False → kinematic/static.
Requires physics_set_scene before simulation_play.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `mass` | `number` | `1.0` |  |
| `dynamic` | `boolean` | `True` |  |

### `physics_create_joint`

```python
physics_create_joint(joint_type: 'str', body_a: 'str', body_b: 'str', anchor: 'list[float] | None' = None, axis: 'list[float] | None' = None, joint_prim_path: 'str | None' = None) -> 'str'
```

Create UsdPhysics joint (Fixed/Revolute/Prismatic/Spherical) between body_a and body_b.
anchor=localPos0; axis selects X/Y/Z for Revolute/Prismatic.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `joint_type` | `string` | `'—'` | ✓ |
| `body_a` | `string` | `'—'` | ✓ |
| `body_b` | `string` | `'—'` | ✓ |
| `anchor` | `list[number] \| None` | `None` |  |
| `axis` | `list[number] \| None` | `None` |  |
| `joint_prim_path` | `string \| None` | `None` |  |

### `physics_get_rigid_body_state`

```python
physics_get_rigid_body_state(prim_path: 'str') -> 'str'
```

Read PhysX runtime state — linear/angular velocity, mass, COM, kinematic/enabled flags.
Symmetric readback for physics_apply_rigid_body. source='physx_runtime' (live PhysX via
SingleRigidPrim, requires simulation.play to have ticked) or 'usd_initial' (USD authored
values, velocities reflect pre-play state but mass/COM always accurate).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `physics_set_joint_drive`

```python
physics_set_joint_drive(joint_prim_path: 'str', drive_type: 'str' = 'angular', target_position: 'float' = 0.0, target_velocity: 'float' = 0.0, stiffness: 'float' = 0.0, damping: 'float' = 0.0, max_force: 'float | None' = None) -> 'str'
```

Configure a UsdPhysics DriveAPI on an existing joint so it actuates (physics_create_joint only
creates the joint). drive_type ∈ {linear (Prismatic), angular (Revolute)}; target_position
drives toward a pose (deg for angular, distance for linear), stiffness/damping form the PD
gains, max_force=None leaves the PhysX default (unbounded). Body needs RigidBodyAPI +
physics_set_scene + simulation_play to move.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `joint_prim_path` | `string` | `'—'` | ✓ |
| `drive_type` | `string` | `'angular'` |  |
| `target_position` | `number` | `0.0` |  |
| `target_velocity` | `number` | `0.0` |  |
| `stiffness` | `number` | `0.0` |  |
| `damping` | `number` | `0.0` |  |
| `max_force` | `number \| None` | `None` |  |

### `physics_set_scene`

```python
physics_set_scene(gravity: 'list[float] | None' = None, timestep: 'float' = 0.016666666666666666, solver_iter_pos: 'int' = 4, solver_iter_vel: 'int' = 1, scene_prim_path: 'str' = '/World/PhysicsScene') -> 'str'
```

Define UsdPhysics.Scene; configure gravity [gx,gy,gz] m/s² (default [0,0,-9.81]) + solver
iterations. Required once before gravity acts on rigid bodies.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `gravity` | `list[number] \| None` | `None` |  |
| `timestep` | `number` | `0.016666666666666666` |  |
| `solver_iter_pos` | `integer` | `4` |  |
| `solver_iter_vel` | `integer` | `1` |  |
| `scene_prim_path` | `string` | `'/World/PhysicsScene'` |  |

### `physics_visualize`

```python
physics_visualize(mode: 'str') -> 'str'
```

Toggle PhysX debug visualization. mode ∈ {collision, joint, mass, off}; clears all carb
/physics/visualization* keys then enables requested channel.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `mode` | `string` | `'—'` | ✓ |

### `process_list_kit_instances`

```python
process_list_kit_instances() -> 'str'
```

Enumerate ALL running kit.exe processes (read-only). Includes MCP-spawned, other MCP servers,
and user GUI launches. Per-instance: pid, command_line, start_time_utc, ext_port, app_profile,
is_this_mcp_instance. Use BEFORE destructive ops (Kit user.config.json edit, settings reset,
force reload) — external instances overwrite settings on shutdown. Windows-only.

### `replicator_create_writer`

```python
replicator_create_writer(writer_type: 'str', output_dir: 'str', rgb: 'bool' = True, depth: 'bool' = False, semantic_segmentation: 'bool' = False) -> 'str'
```

Create replicator writer (BasicWriter/KittiWriter/CocoWriter); writes to output_dir on each
orchestrator step. Requires omni.replicator.core enabled.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `writer_type` | `string` | `'—'` | ✓ |
| `output_dir` | `string` | `'—'` | ✓ |
| `rgb` | `boolean` | `True` |  |
| `depth` | `boolean` | `False` |  |
| `semantic_segmentation` | `boolean` | `False` |  |

### `replicator_register_randomizer`

```python
replicator_register_randomizer(type: 'str', target: 'str', config: 'dict[str, Any] | None' = None) -> 'str'
```

Register randomizer for orchestrator frames. type ∈ {position, rotation, lighting}; target is a
prim glob. Returns randomizer_id.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `type` | `string` | `'—'` | ✓ |
| `target` | `string` | `'—'` | ✓ |
| `config` | `object \| None` | `None` |  |

### `replicator_trigger_on_time`

```python
replicator_trigger_on_time(interval_s: 'float') -> 'str'
```

Register periodic orchestrator trigger at interval_s; keep > 0.016 s to avoid queue buildup.
Returns trigger_id.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `interval_s` | `number` | `'—'` | ✓ |

### `replicator_trigger_once`

```python
replicator_trigger_once(num_frames: 'int' = 1) -> 'str'
```

Run replicator orchestrator for N frames (fires randomizers + writers). Timeline play alone
does NOT trigger writers.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `num_frames` | `integer` | `1` |  |

### `sensor_attach_contact`

```python
sensor_attach_contact(prim_path: 'str', sensor_name: 'str' = 'ContactSensor', frequency: 'int' = 60, translation: 'list[float] | None' = None, radius: 'float' = -1.0) -> 'str'
```

Attach PhysX ContactSensor child prim; reports contact forces/collisions once playing. Xform
fallback when module unavailable (response.backend).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `sensor_name` | `string` | `'ContactSensor'` |  |
| `frequency` | `integer` | `60` |  |
| `translation` | `list[number] \| None` | `None` |  |
| `radius` | `number` | `-1.0` |  |

### `sensor_attach_imu`

```python
sensor_attach_imu(prim_path: 'str', sensor_name: 'str' = 'IMUSensor', frequency: 'int' = 200, mount_offset: 'list[float] | None' = None, mount_orientation: 'list[float] | None' = None) -> 'str'
```

Attach IMU sensor (accel+gyro+orient) at frequency. mount_offset/mount_orientation in parent
frame. Same Xform fallback as sensor_attach_contact.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `sensor_name` | `string` | `'IMUSensor'` |  |
| `frequency` | `integer` | `200` |  |
| `mount_offset` | `list[number] \| None` | `None` |  |
| `mount_orientation` | `list[number] \| None` | `None` |  |

### `sensor_attach_rtx_camera`

```python
sensor_attach_rtx_camera(robot_prim: 'str', mount_offset: 'list[float]', mount_rotation: 'list[float]', resolution: 'list[int] | None' = None, sensor_name: 'str' = 'RtxCamera') -> 'str'
```

Attach RTX Camera (RGB) as child xform under robot. mount_offset/mount_rotation relative to
parent. Returns sensor prim path.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `robot_prim` | `string` | `'—'` | ✓ |
| `mount_offset` | `list[number]` | `'—'` | ✓ |
| `mount_rotation` | `list[number]` | `'—'` | ✓ |
| `resolution` | `list[integer] \| None` | `None` |  |
| `sensor_name` | `string` | `'RtxCamera'` |  |

### `sensor_attach_rtx_depth_camera`

```python
sensor_attach_rtx_depth_camera(robot_prim: 'str', mount_offset: 'list[float]', mount_rotation: 'list[float]', resolution: 'list[int] | None' = None, sensor_name: 'str' = 'RtxDepthCamera') -> 'str'
```

Attach RTX Camera with depth annotator (distance_to_camera); output is grayscale distance map,
not RGB. Same mount convention as sensor_attach_rtx_camera.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `robot_prim` | `string` | `'—'` | ✓ |
| `mount_offset` | `list[number]` | `'—'` | ✓ |
| `mount_rotation` | `list[number]` | `'—'` | ✓ |
| `resolution` | `list[integer] \| None` | `None` |  |
| `sensor_name` | `string` | `'RtxDepthCamera'` |  |

### `sensor_attach_rtx_lidar`

```python
sensor_attach_rtx_lidar(robot_prim: 'str', mount_offset: 'list[float]', mount_rotation: 'list[float]', config_preset: 'str' = 'Example_Rotary', sensor_name: 'str' = 'RtxLidar') -> 'str'
```

Attach RTX Lidar for point-cloud capture; config_preset selects profile
(Example_Rotary/Velodyne_VLS128/…). Returns sensor prim path and annotator id.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `robot_prim` | `string` | `'—'` | ✓ |
| `mount_offset` | `list[number]` | `'—'` | ✓ |
| `mount_rotation` | `list[number]` | `'—'` | ✓ |
| `config_preset` | `string` | `'Example_Rotary'` |  |
| `sensor_name` | `string` | `'RtxLidar'` |  |

### `sensor_lidar_get_point_cloud`

```python
sensor_lidar_get_point_cloud(sensor_prim: 'str', max_points: 'int' = 1000, frames_to_wait: 'int' = 2) -> 'str'
```

Read one frame of RTX Lidar XYZ point cloud (symmetric readback for sensor_attach_rtx_lidar).
Reuses annotator stamped on sensor prim. Empty cloud → response.warning explains (typically
"call simulation_play & wait for spin"). Truncates to max_points (≤100000).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `sensor_prim` | `string` | `'—'` | ✓ |
| `max_points` | `integer` | `1000` |  |
| `frames_to_wait` | `integer` | `2` |  |

### `sensor_set_annotator`

```python
sensor_set_annotator(sensor_prim: 'str', annotators: 'list[str]', resolution: 'list[int] | None' = None) -> 'str'
```

Attach replicator annotators to camera prim. Valid: rgb, depth, normals, motion_vectors,
semantic/instance_segmentation, distance_to_camera/image_plane. response.skipped lists
failures.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `sensor_prim` | `string` | `'—'` | ✓ |
| `annotators` | `list[string]` | `'—'` | ✓ |
| `resolution` | `list[integer] \| None` | `None` |  |

### `sensor_set_visualization`

```python
sensor_set_visualization(sensor_prim: 'str', mode: 'str' = 'on') -> 'str'
```

Toggle debug draw overlay for a sensor. mode ∈ {on, off}. Lidar → point cloud; Camera/Depth →
frustum+preview. Response includes sensor_type.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `sensor_prim` | `string` | `'—'` | ✓ |
| `mode` | `string` | `'on'` |  |

### `simulation_set_time`

```python
simulation_set_time(time_seconds: 'float') -> 'str'
```

Seek timeline to time_seconds; preserves current play/stop state.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `time_seconds` | `number` | `'—'` | ✓ |

### `simulation_step`

```python
simulation_step(frames: 'int' = 1) -> 'str'
```

Advance timeline by N frames deterministically (forward_one_frame() or play-burst fallback);
preserves prior play state.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `frames` | `integer` | `1` |  |

### `simulation_step_observe`

```python
simulation_step_observe(frames: 'int' = 1, observe_prims: 'list[str] | None' = None, observe_joints: 'list[str] | None' = None, observe_ee: 'list[dict[str, Any]] | None' = None) -> 'str'
```

Advance N frames, then return synchronized prim/joint/end-effector observations. Use this for
deterministic ScriptNode/controller debugging instead of sleep+separate polling.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `frames` | `integer` | `1` |  |
| `observe_prims` | `list[string] \| None` | `None` |  |
| `observe_joints` | `list[string] \| None` | `None` |  |
| `observe_ee` | `list[object] \| None` | `None` |  |

### `simulation_wait_until`

```python
simulation_wait_until(until_time: 'float', timeout_s: 'float' = 30.0) -> 'str'
```

Tick the timeline until current_time >= until_time (or timeout_s wall-clock elapses), then
return final status + reached/timed_out/elapsed_s/frames_waited. Ticks via next_update_async on
the Kit loop (deadlock-safe, non-blocking). Replaces sleep+poll loops for sim_time-precise
timing (e.g. trigger an event at t=12s). Requires the timeline PLAYING to advance — otherwise
it times out.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `until_time` | `number` | `'—'` | ✓ |
| `timeout_s` | `number` | `30.0` |  |

### `stage_compute_world_bbox`

```python
stage_compute_world_bbox(prim_path: 'str', include_purposes: 'list[str] | None' = None) -> 'str'
```

Compute a prim's world-space aligned bbox via USD BBoxCache. Returns min/max/center/size plus
world translate/orientation; use before camera framing or layout checks.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `include_purposes` | `list[string] \| None` | `None` |  |

### `stage_set_semantic_label`

```python
stage_set_semantic_label(prim_path: 'str', label_class: 'str', label_type: 'str' = 'class') -> 'str'
```

Apply a semantic label to a prim (inherits to its subtree) so Replicator segmentation / bbox
annotators classify it. Authors UsdSemantics.LabelsAPI (semantics:labels:<label_type>) + best-
effort legacy Semantics schema. Fills the gap left by sensor_set_annotator (which attaches
annotators but cannot label the props). 400 if prim_path not found.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `label_class` | `string` | `'—'` | ✓ |
| `label_type` | `string` | `'class'` |  |

### `stage_visual_alignment_report`

```python
stage_visual_alignment_report(reference_prim_path: 'str', candidate_prim_paths: 'list[str]', min_iou_xy: 'float' = 0.5, max_center_delta_m: 'float' = 0.05, include_purposes: 'list[str] | None' = None) -> 'str'
```

Compare candidate prim world bboxes against a reference bbox. Reports XY IoU and center deltas
to catch visual/physics/acceptance-volume misalignment.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `reference_prim_path` | `string` | `'—'` | ✓ |
| `candidate_prim_paths` | `list[string]` | `'—'` | ✓ |
| `min_iou_xy` | `number` | `0.5` |  |
| `max_center_delta_m` | `number` | `0.05` |  |
| `include_purposes` | `list[string] \| None` | `None` |  |
