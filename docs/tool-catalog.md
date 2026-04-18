# Isaac-sim MCP — Tool Catalog

Auto-generated from the live FastMCP server. Regenerate with `.venv/Scripts/python.exe scripts/generate_tool_catalog.py` after any tool addition / removal / signature change. `tests/unit/test_tool_catalog_sync.py` fails if this file drifts out of sync with the `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset SoT.

**Tool count**: 58

## Table of contents

- [Process — Isaac Sim kit.exe lifecycle](#process--isaac-sim-kitexe-lifecycle) — 3 tools
- [Stage — READ / ASSERT / file & selection](#stage--read--assert--file--selection) — 6 tools
- [Stage — WRITE (mutations routed to SimulationModule)](#stage--write-mutations-routed-to-simulationmodule) — 7 tools
- [Simulation — timeline](#simulation--timeline) — 4 tools
- [Viewport — 3D renderer capture + camera](#viewport--3d-renderer-capture--camera) — 3 tools
- [Window — Kit GUI (app window / menus / omni.ui windows)](#window--kit-gui-app-window--menus--omniui-windows) — 6 tools
- [Extension — lifecycle / UI automation / carb log capture](#extension--lifecycle--ui-automation--carb-log-capture) — 7 tools
- [Lakehouse — query-only](#lakehouse--query-only) — 1 tools
- [Robot — articulation + navigation (ASYNC Job)](#robot--articulation--navigation-async-job) — 4 tools
- [Job — async job polling / cancel](#job--async-job-polling--cancel) — 2 tools
- [Asset — catalog browsing (GUI Asset Browser equivalent)](#asset--catalog-browsing-gui-asset-browser-equivalent) — 1 tools
- [Character — Biped_Setup + AnimationGraph + NavMesh (ASYNC Job)](#character--bipedsetup--animationgraph--navmesh-async-job) — 6 tools
- [Navigation — NavMesh bake / path query / exclude volume](#navigation--navmesh-bake--path-query--exclude-volume) — 3 tools
- [Scenario — YAML Arrange / Act / Assert / Cleanup runner](#scenario--yaml-arrange--act--assert--cleanup-runner) — 5 tools

## Process — Isaac Sim kit.exe lifecycle

### `isaac_sim_restart`

```python
isaac_sim_restart() -> 'str'
```

Restart Isaac Sim: stop → clear __pycache__ → start. Use after modifying Extension code to
reload changes.

### `isaac_sim_start`

```python
isaac_sim_start() -> 'str'
```

Start Isaac Sim with the validation extension enabled. Waits until the health endpoint
responds. Use this before any stage/simulation/viewport operations.

### `isaac_sim_stop`

```python
isaac_sim_stop() -> 'str'
```

Stop the running Isaac Sim process.

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

Assert the value of a Prim's property. Supports exact match, approximate (float tolerance),
regex, contains, and existence checks. Use comparator='approx' with tolerance for float
comparisons. Set property_kind='relationship' for relationship assertions.

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

Capture a snapshot of the current USD Stage prim tree. Returns all prims with their properties,
relationships, and metadata. Use this to inspect the current state of the scene.

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

Compare two Stage snapshots and return the differences (prims added/removed/changed, properties
modified). Pass the JSON output from two stage_capture_snapshot calls.

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

Create a new USD Prim in the scene. Types: Xform (empty transform), Cube, Sphere, Cylinder,
Cone, Capsule, Plane, etc. Optionally set position [x,y,z].

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

Delete a USD Prim from the scene. This also removes all child prims.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `stage_load_usd`

```python
stage_load_usd(usd_url: 'str', prim_path: 'str', position: 'list[float] | None' = None, rotation: 'list[float] | None' = None) -> 'str'
```

Load a USD asset (robot, object, environment) into the scene. Specify *usd_url* (local path or
omniverse:// URL) and *prim_path* (where to place it in the stage hierarchy). Optionally set
initial position [x,y,z] and rotation [rx,ry,rz] in degrees.

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

Create a new empty stage — GUI File → New.

### `stage_open`

```python
stage_open(url: 'str') -> 'str'
```

Open a USD stage — GUI File → Open. Accepts local paths and omniverse:// / https:// URLs. Waits
for the stage to finish loading.

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

Set a property value on a USD Prim. Common properties: xformOp:translate ([x,y,z]),
xformOp:rotateXYZ ([rx,ry,rz]), radius (float), visibility (token). Use *type_hint* to specify
the USD type (Vec3d, Vec3f, Quatd, float, int, bool, string, asset).

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

Get the current simulation timeline status: is_playing, current_time, fps, etc.

### `simulation_pause`

```python
simulation_pause() -> 'str'
```

Pause the simulation timeline. Physics and animations freeze at current time.

### `simulation_play`

```python
simulation_play() -> 'str'
```

Start (play) the Isaac Sim simulation timeline. Physics and animations begin advancing.

### `simulation_stop`

```python
simulation_stop() -> 'str'
```

Stop the simulation timeline. Resets time to the beginning.

## Viewport — 3D renderer capture + camera

### `viewport_capture`

```python
viewport_capture(viewport_name: 'str' = 'Viewport', camera_prim_path: 'str | None' = None, renderer: 'str' = 'rtx', width: 'int' = 1280, height: 'int' = 720, output_format: 'str' = 'png') -> 'str'
```

Capture a screenshot of the Isaac Sim viewport. Returns the image artifact path and metadata.
Use before/after captures for visual comparison.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `viewport_name` | `string` | `'Viewport'` |  |
| `camera_prim_path` | `string \| None` | `None` |  |
| `renderer` | `string` | `'rtx'` |  |
| `width` | `integer` | `1280` |  |
| `height` | `integer` | `720` |  |
| `output_format` | `string` | `'png'` |  |

### `viewport_compare_ssim`

```python
viewport_compare_ssim(baseline_artifact_path: 'str', candidate_artifact_path: 'str', min_ssim: 'float' = 0.99, crop: 'list[int] | None' = None) -> 'str'
```

Compare two viewport images using SSIM (Structural Similarity Index). Returns the SSIM score
and pass/fail result. Use to verify visual changes or stability.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `baseline_artifact_path` | `string` | `'—'` | ✓ |
| `candidate_artifact_path` | `string` | `'—'` | ✓ |
| `min_ssim` | `number` | `0.99` |  |
| `crop` | `list[integer] \| None` | `None` |  |

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

## Window — Kit GUI (app window / menus / omni.ui windows)

### `window_capture`

```python
window_capture(mode: 'str' = 'kit', hwnd: 'int | None' = None, settle_frames: 'int' = 5, output_format: 'str' = 'png', bring_to_front: 'bool' = False, use_client_rect: 'bool' = False, wait_stable: 'bool' = False, stable_interval_s: 'float' = 2.0, stable_consecutive: 'int' = 2, stable_max_wait_s: 'float' = 45.0, stable_diff_threshold: 'float' = 0.01) -> 'str'
```

Capture the Kit main window (Stage panel + Property + Timeline + 3D viewport — the entire app
chrome), NOT the 3D render alone (that is viewport_capture). Modes: 'kit' auto-detects the
biggest visible kit.exe window, 'foreground' uses the currently focused window, or pass an
explicit hwnd. wait_stable polls consecutive pixel diffs to wait for async UI (browser
thumbnails, etc.) to settle — returns early once diffs stay below threshold, or after
stable_max_wait_s timeout with stabilized=False.

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

### `window_list`

```python
window_list() -> 'str'
```

Enumerate top-level OS windows belonging to the kit.exe process (Win32 EnumWindows). Useful for
debugging which HWND window_capture will pick up when mode='kit' auto-detection goes wrong.

### `window_menu_list`

```python
window_menu_list(menu_path: 'str | None' = None) -> 'str'
```

Walk Kit's merged menu tree (omni.kit.menu.utils). Pass menu_path like 'Window/Browsers' to
limit to a subtree, omit to list every menu item. Each item exposes onclick_action (2-list
[ext_id, action_id]) suitable for window_menu_trigger.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `menu_path` | `string \| None` | `None` |  |

### `window_menu_trigger`

```python
window_menu_trigger(menu_path: 'str') -> 'str'
```

Programmatically click a menu item (e.g. 'Window/Browsers/Asset Browser') via
omni.kit.actions.core.execute_action — same path a real click takes. Response includes
created_prims — the list of USD prims added by this action (empty list means the action did not
create any prim, i.e. it was UI-only or silently no-op).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `menu_path` | `string` | `'—'` | ✓ |

### `window_ui_list`

```python
window_ui_list(name_filter: 'str | None' = None) -> 'str'
```

Enumerate registered omni.ui.Window instances (Asset Browser, Stage, Content, Isaac Examples,
etc.). name_filter is a case-insensitive substring over the title. Browser windows are lazy-
instantiated: they only appear here after show_window was called at least once.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `name_filter` | `string \| None` | `None` |  |

### `window_ui_show`

```python
window_ui_show(name: 'str', visible: 'bool' = True, focus: 'bool' = True, settle_frames: 'int' = 5) -> 'str'
```

Toggle / focus an omni.ui.Window by title (Window menu item label). Uses exact match first,
then falls back to case-insensitive substring — handles cases like menu item 'Isaac Sim Assets'
opening a window actually titled 'Isaac Sim Assets [Beta]'. Response includes
resolved_via='exact'|'substring' and visible_after.

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

Enable a Kit Extension by id via the ExtensionManager (equivalent to toggling the checkbox in
Window → Extensions). Set reload=True to force a disable→enable cycle — re-imports the Python
package, useful when you edited an Extension in place. Fails with 400 if the ext_id is unknown
to Kit (check --ext-folder / package spelling).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string` | `'—'` | ✓ |
| `reload` | `boolean` | `False` |  |

### `extension_capture_logs`

```python
extension_capture_logs(ext_id: 'str | None' = None, since_ms: 'int | None' = None, level: 'str' = 'INFO', limit: 'int' = 1000) -> 'str'
```

Peek recent carb.log_* entries from the Extension's ring buffer (maxlen 10000). Filters: ext_id
(substring on log source), since_ms (drop earlier entries), level ∈
VERBOSE|INFO|WARN|ERROR|FATAL|ALL (includes entries at that level or higher). Peek-style —
calling again does not drain, so multiple consumers see the same window.

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

Drop every buffered carb log entry from the ring buffer. Returns the count removed. Use to mark
a "new session" so subsequent extension_capture_logs only sees entries from after this call.

### `extension_get_state`

```python
extension_get_state() -> 'str'
```

Get the current state of the Custom Extension. Shows whether it is enabled, busy, last
operation, and any errors.

### `extension_get_ui_tree`

```python
extension_get_ui_tree(ext_id: 'str | None' = None, window: 'str | None' = None, widget_types: 'list[str] | None' = None) -> 'str'
```

Return a widget tree under a specific omni.ui Window (click/type targets live in `widgets`).
Omit window to list all registered windows without walking their contents. window is matched
case-insensitively as a substring against the window title. Each widget exposes path (use this
as widget_path for extension_ui_invoke), label, type, enabled, visible, value
(StringField/ComboBox current value). Pass widget_types=["Button","TreeView",...] to override
the default allow-list — required for custom widget classes that the default enumeration
misses.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `ext_id` | `string \| None` | `None` |  |
| `window` | `string \| None` | `None` |  |
| `widget_types` | `list[string] \| None` | `None` |  |

### `extension_trigger`

```python
extension_trigger(operation: 'str', payload: 'dict[str, Any] | None' = None, wait_for_idle: 'bool' = True, idle_timeout_s: 'float' = 30.0) -> 'str'
```

Trigger the Custom Extension to perform a sync operation (e.g., sync_from_lakehouse).
Optionally waits for the extension to become idle. Returns the extension state after trigger.

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

Invoke a widget by path. action ∈ click|double_click|type|select|check|uncheck. For type pass
value as the string to type, for select pass an integer index. Returns the post-action widget
state so you can assert the change (e.g. Label text updated after Button click).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `widget_path` | `string` | `'—'` | ✓ |
| `action` | `string` | `'click'` |  |
| `value` | `Any` | `None` |  |

## Lakehouse — query-only

### `lakehouse_query`

```python
lakehouse_query(sql: 'str | None' = None, namespace: 'str | None' = None, dataset: 'str | None' = None, table: 'str | None' = None, filters: 'dict[str, Any] | None' = None, limit: 'int' = 1000) -> 'str'
```

Query the Lakehouse REST API for expected values. Use SQL or target (namespace/dataset/table)
with filters. Returns rows that can be compared against Stage property values.

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

### `robot_get_joint_positions`

```python
robot_get_joint_positions(prim_path: 'str') -> 'str'
```

Get the current joint positions of an articulation (via SingleArticulation).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `robot_load`

```python
robot_load(usd_url: 'str', prim_path: 'str', position: 'list[float] | None' = None, rotation: 'list[float] | None' = None) -> 'str'
```

Load a robot USD asset at *prim_path* with optional initial transform. Detects whether the
loaded prim has a PhysX Articulation API applied (required for joint control).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `usd_url` | `string` | `'—'` | ✓ |
| `prim_path` | `string` | `'—'` | ✓ |
| `position` | `list[number] \| None` | `None` |  |
| `rotation` | `list[number] \| None` | `None` |  |

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

### `robot_set_joint_positions`

```python
robot_set_joint_positions(prim_path: 'str', positions: 'list[float]') -> 'str'
```

Set joint positions on an articulation (via SingleArticulation). Raises a validation error if
the prim has no PhysX articulation API — use continueOnFailure for optional calls.

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

Cancel a running async Job. Safe on terminal-state jobs (returns current status). 404 if job_id
unknown.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `job_id` | `string` | `'—'` | ✓ |

### `job_status`

```python
job_status(job_id: 'str') -> 'str'
```

Poll the status of an async Job. Returns {status: pending|running|done|error|canceled,
progress: 0..1, result, error}.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `job_id` | `string` | `'—'` | ✓ |

## Asset — catalog browsing (GUI Asset Browser equivalent)

### `asset_list`

```python
asset_list(category: 'str | None' = None, subpath: 'str' = '', recursive: 'bool' = False, max_depth: 'int' = 2, max_entries: 'int' = 500) -> 'str'
```

Browse the Isaac Sim asset catalog (same tree the GUI Asset Browser shows).  Call with no
arguments to list categories (robots/environments/props/people/materials/isaaclab). Call with
*category* to list that folder's contents. Use *subpath* to drill into a sub-folder (e.g.
category='robots', subpath='FrankaRobotics/FrankaPanda'). Entries marked is_folder=false are
spawnable USDs — pass their `url` to stage_load_usd / robot_load.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `category` | `string \| None` | `None` |  |
| `subpath` | `string` | `''` |  |
| `recursive` | `boolean` | `False` |  |
| `max_depth` | `integer` | `2` |  |
| `max_entries` | `integer` | `500` |  |

## Character — Biped_Setup + AnimationGraph + NavMesh (ASYNC Job)

### `character_get_state`

```python
character_get_state(prim_path: 'str') -> 'str'
```

Return the character's current world position, rotation (scalar-first quaternion), active
animation action, and whether is_navigating (action in Walk/Run).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |

### `character_load`

```python
character_load(usd_url: 'str', prim_path: 'str | None' = None, position: 'list[float] | None' = None, yaw: 'float' = 0.0) -> 'str'
```

Load a character USD (from Isaac Sim People catalog or custom DH UUID asset). Automatically
loads Biped_Setup rig if missing, binds AnimationGraph, and returns the prim path + SkelRoot
path. Sanitizes UUID-based filenames to USD-legal prim names.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `usd_url` | `string` | `'—'` | ✓ |
| `prim_path` | `string \| None` | `None` |  |
| `position` | `list[number] \| None` | `None` |  |
| `yaw` | `number` | `0.0` |  |

### `character_navigate_to`

```python
character_navigate_to(prim_path: 'str', target: 'list[float]', speed: 'float' = 1.0) -> 'str'
```

Dispatch a Walk-to-target as an async Job. Returns a job_id — poll job_status(job_id) until
status='done'. On cancel/timeout the character automatically reverts to Idle.

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

Play a named animation clip on a loaded character. animation_name must be one of
Idle/Walk/Run/Sit. For Walk/Run, target_position [x,y,z] triggers path-following via
AnimationGraph PathPoints variable.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string` | `'—'` | ✓ |
| `animation_name` | `string` | `'—'` | ✓ |
| `speed` | `number` | `1.0` |  |
| `target_position` | `list[number] \| None` | `None` |  |

### `character_set_position`

```python
character_set_position(prim_path: 'str', position: 'list[float]', orientation: 'list[float] | None' = None) -> 'str'
```

Kinematically set the character's world pose. orientation is a scalar-first quaternion
[qw,qx,qy,qz]; omit to keep current. Reads back the stored pose so the response reflects any
quaternion normalization.

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

Add a NavMeshVolume(type=Exclude) around a prim's world-aligned bbox. Use to prevent characters
from stepping onto chairs / low props (default NavMesh step-up lets agents climb surfaces up to
agent_max_step_height). Requires a re-bake (navigation_bake) afterwards for the exclusion to
take effect.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `prim_path` | `string \| None` | `None` |  |
| `padding` | `number` | `0.1` |  |

### `navigation_bake`

```python
navigation_bake(volume_scale: 'float' = 40.0, timeout_s: 'float' = 300.0) -> 'str'
```

Bake the Stage NavMesh. Creates a default NavMeshVolume (Include) of the given scale if none
exists, otherwise reuses it. Uses the async `start_navmesh_baking()` + `is_navmesh_baking()`
polling pattern — yields to Kit's event loop every tick so the HTTP router stays responsive
(never calls the blocking `_and_wait` variant). IMPORTANT: timeline must be stopped
(simulation_stop) before calling — baking during play returns ok=True but get_navmesh() is None
(silent false positive). Canonical sequence: load_usd → simulation_stop → navigation_bake →
navigation_query_path → simulation_play → robot_navigate_path. timeout_s bounds the polling
loop (default 5 min).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `volume_scale` | `number` | `40.0` |  |
| `timeout_s` | `number` | `300.0` |  |

### `navigation_query_path`

```python
navigation_query_path(start: 'list[float]', end: 'list[float]', agent_radius: 'float' = 0.25, agent_height: 'float' = 1.8, straighten: 'bool' = True) -> 'str'
```

Query the shortest NavMesh path between two world-space points. If the NavMesh has not been
baked, the service auto-bakes (response auto_baked=true). straighten=True collapses straight-
line segments — shorter waypoint list for robot/character navigate_path callers.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `start` | `list[number]` | `'—'` | ✓ |
| `end` | `list[number]` | `'—'` | ✓ |
| `agent_radius` | `number` | `0.25` |  |
| `agent_height` | `number` | `1.8` |  |
| `straighten` | `boolean` | `True` |  |

## Scenario — YAML Arrange / Act / Assert / Cleanup runner

### `scenario_last_report`

```python
scenario_last_report(scenario_id: 'str') -> 'str'
```

Get the last execution report for a specific scenario. Returns the full JSON report from the
most recent run, including step results and artifacts.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `scenario_id` | `string` | `'—'` | ✓ |

### `scenario_list`

```python
scenario_list(root_dir: 'str | None' = None) -> 'str'
```

List all available validation scenarios. Returns scenario IDs, names, and tags. Scans the
configured scenarios directory for YAML files.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `root_dir` | `string \| None` | `None` |  |

### `scenario_plan`

```python
scenario_plan(scenario_path: 'str') -> 'str'
```

Compile a scenario YAML file and show the execution plan without running it. Shows the resolved
variables, compiled steps graph, and phase breakdown. Useful for previewing what a scenario
will do.

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `scenario_path` | `string` | `'—'` | ✓ |

### `scenario_schema`

```python
scenario_schema() -> 'str'
```

Return the JSON Schema for scenario YAML files. Use this to understand the required format for
writing new validation scenarios.

### `scenario_validate`

```python
scenario_validate(scenario_path: 'str', dry_run: 'bool' = False, fail_fast: 'bool | None' = None, input_overrides: 'dict[str, Any] | None' = None) -> 'str'
```

Execute a YAML validation scenario (Arrange → Act → Assert → Cleanup). The scenario file
defines steps that trigger extension sync, capture snapshots, and assert property values.
Returns a detailed run summary with pass/fail for each step. Use input_overrides to override
scenario variables (e.g. {"prim_path": "/World/Box"}).

**Parameters**

| name | type | default | required |
|------|------|---------|----------|
| `scenario_path` | `string` | `'—'` | ✓ |
| `dry_run` | `boolean` | `False` |  |
| `fail_fast` | `boolean \| None` | `None` |  |
| `input_overrides` | `object \| None` | `None` |  |
