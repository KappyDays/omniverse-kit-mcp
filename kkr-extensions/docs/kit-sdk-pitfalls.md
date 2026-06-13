<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Isaac Sim / Kit SDK A collection of ground truth traps — 5.1 historical + 6.0 current deltas -->

# Kit SDK Trap Collection

Traps actually encountered in the Isaac Sim/Kit environment. 5.1 / Kit 107 historical items are preserved, and for items whose conclusions have changed based on 6.0 / Kit 110, the current delta is specified in the text. Start searching here when a new extension touches the domain API.

---

## Stage / USD load

### Viewport capture — `omni.syntheticdata._get_node_path` AttributeError

`omni.syntheticdata._get_node_path` in Isaac Sim 5.1 regards `render_product` (HydraTexture) as a string and calls `.split()`. However, since the error occurs inside `rgb_annot.get_data()` **after** `detach([rp])`, the data itself is secured.

Implementation conventions:
1. `get_data()` Results are stored separately
2. `detach([rp])` is wrapped with `try/except Exception` for non-fatal processing.
3. If data is None/empty, fallback to `capture_viewport_to_file` (save and read PNG)

### xformOps exists after `CreatePrimWithDefaultXformCommand`

The prim created with this command already has `xformOp:translate / rotate / scale` added → If `AddTranslateOp()` is called again, it will be duplicated. Use `prim.GetAttribute("xformOp:translate").Set(...)`.

### UsdLux intensity is `inputs:intensity`

The strength of UsdLux prim made with `stage_create_prim(prim_type="DistantLight"|"DomeLight"|...)` is **`inputs:intensity`** (USD 2023+ schema). If you call it `intensity`, it will get `"Attribute 'intensity' not found"`. Color `inputs:color`, temperature `inputs:colorTemperature`, etc. have the same prefix `inputs:*`.

### Plane prim trap — Vision vs Physics

`stage_create_prim(prim_type="Plane")` is UsdGeomPlane (**visual plane only, no collision**) → robot / character passes through plane at `simulation_play` and falls freely. For surfaces that require physics, call `window_menu_trigger("Create/Physics/Ground Plane")` — automatically create `CollisionPlane + CollisionMesh + PhysicsCollisionAPI` 3-prim (`omni.physxui` action).

### S3 MDL-heavy asset load deadlock

Refer to separate document → `usd-load-deadlock-recipe.md`.

---

## Articulation / Robot

### Isaac Sim 5.1 requires `SingleArticulation.initialize()`

Based on 4.x, "set/get OK without initialize" is no longer applicable in 5.1. `NoneType.link_names` internal error when performing joint I/O without initialization. Apply sequentially when the caller enters articulation:

1. `_assert_articulation(prim_path)` — prim validity + recursive search of PhysxArticulationAPI/Root to `Usd.PrimRange`. If not, `ValueError` → HTTP 400 (silent no-op blocking)
2. `_ensure_initialized(art)` — Automatically calls `SingleArticulation.initialize()`. Duplicate calls are safe since it is idempotent

In order for PhysX to populate the articulation view, **at least 1 physics step** must run, so the scenario is warmed up by placing `simulation_play → pause` in arrange. If not, `_ensure_initialized` may also fail → wrap it with `continueOnFailure: true`.

### Gripper DOF automatic detection

Automatically detects `SingleArticulation.dof_names` to `finger` / `gripper` substring matching. `action ∈ {open, close, set}`; open/close reads limits in the order `get_dof_limits()` → `dof_properties` and falls back to Franka-default 0.04 / 0.0.

### Lula IK — Two module paths

`_resolve_lula_modules()` selects the importable path among `isaacsim.robot_motion.motion_generation.lula` and `omni.isaac.motion_generation.lula`. If it fails, it returns `ValueError → 400`. Isaac Sim 5.1 obtains the URDF/robot_description path with `load_supported_motion_policy_config(robot_description, "RMPflow")`. `load_supported_robot_motion_policy_configs(...)` is also maintained as a fallback compatible with older versions.

---

## Character / AnimGraph

### SkelRoot pre-verification + AnimGraph ready retry

Apply sequentially when entering character-related API (`play_animation`, `navigate`, `set_position`, `get_state`):

1. `_assert_skel_root(prim_path)` — prim validity + `UsdSkel.Root` recursive search. If not, HTTP 400
2. `_ensure_animation_ready(prim_path)` — If `omni.anim.graph.core.get_character(prim_path)` is None (delay in graph registry populate), retry after 1-frame `simulation_play → pause` warm-up. If still None, HTTP 500

Immediately after executing `ApplyAnimationGraphAPICommand`, it has not yet been populated in the AnimGraph registry — it is recommended to specify `simulation.play → pause` in scenario arrange.

### Shutdown hang prevention

If there is no `simulation.play → step → stop` (the final physics tick) before `kit_app_stop`, kit.exe will hang due to timing issues with AnimGraph/NavMesh internal handle cleanup. Must be included in scenario cleanup.

### USD prim name `_sanitize_prim_name` required

USD prim name convention is **`[A-Za-z0-9_]`** only. If hyphen / dot / space / leading digit is entered, `Sdf.Path` / `CreatePrimCommand` becomes `"... is not a valid path"` HTTP 400. Representative case: DH_Characters_Extended UUID `02c80685-06e3-11ef-ae8a-f4b30194174e` → `c_02c80685_06e3_11ef_ae8a_f4b30194174e`.

Return both `prim_path` (caller echo) + `sanitized_prim_path` (actual USD placement path) in response — subsequent calls **must be based on `sanitized_prim_path`**.

### variable split of play_animation_variant

`_parse_variant(variant)` is split into prefix (Sit/Walk/Run/Idle). `SitReading` → base=`Sit`, style_var=`sit_style`, style_value=`reading`. The base is unconditionally set to `graph.set_variable("Action", base)`, and style_var is a silent no-op with try/except (if there is no variable in AnimGraph, the Kit fails silently). `response.variables_set` This is the actual applied key list.

---

## NavMesh

### Bake timeline stopped is required

Even if `start_navmesh_baking_and_wait()` returns True when called while playing, **`get_navmesh()` is None / empty mesh** (False Positive). `stage/load_usd`, `robot/load`, `stage/create_prim`, `stage/set_property`, `viewport/capture(settle_frames)`, and `window/capture` can all advance/regenerate the timeline, so specify `simulation/stop` one more time just before bake. There are no precondition checks inside the service — caller responsibility.

### standard sequence

`load assets → setup cameras → stop → bake → query_path → play → navigate_path`.

### Automatic creation of NavMeshVolume

If there is no `NavMeshVolume` prim in the Stage, `navigation_bake` automatically creates an Include volume as `CreateNavMeshVolumeCommand(volume_type=0, scale=40m)` and then `start_navmesh_baking_and_wait()`. Reuse existing volumes if you have them. Include `agent_max_radius` / `area_count` / `mesh_signature` in response — **bake fails if None**.

### Step-up caveat (misjudgment of chair walkable)

The basic NavMesh can determine chair / low prop as walkable (agent_max_step_height ≈ seat height). An artifact occurs where the character is played while standing on a chair.

evasion:
- (a) Automatic placement of bbox-based Exclude with `navigation/add_exclude_volume?prim_path=<chair>`
- (b) Lower NavMesh agent_max_step_height to chair seat or lower.

### set_visualization backend

Toggle `carb.settings.get_settings().set("/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh", mode=="walkable")` + obstacles key. On failure, fall back to the `visibility` toggle on `NavMeshVolume` prim. Report which path won with Response `backend: "carb_settings"|"prim_visibility"`.

---

## Sensor

### Stamp patterns by sensor type

`services/sensor_service.py` creates a camera prim under the parent robot with `CreatePrimWithDefaultXformCommand(prim_type="Camera")` + sets `mount_offset` / `mount_rotation` to xformOp. The sensor type is `customData.validation_api.sensor_type` ∈ {rtx_camera, rtx_lidar, rtx_depth_camera} stamp — `set_visualization` reads and dispatches only this tag when it revisits.

- **RTX Camera**: UsdGeom.Camera + `horizontalAperture=20.955`, `focalLength=24.0` default
- **RTX Lidar**: Based on Camera prim + `config_preset` (`Example_Rotary`, etc.) + `annotator: "RtxSensorCpuIsaacCreateRTXLidarScanBuffer"` customData recording. Actual Lidar data acquisition requires activation of `isaacsim.sensors.rtx` extension + annotator attach at the time of capture.
- **RTX Depth Camera**: Camera prim + `annotator: "distance_to_camera"` metadata. Viewport capture attaches a depth annotator to create a grayscale distance map

### Contact / IMU is a fallback pattern

Try `from isaacsim.sensors.physics import ContactSensor` → Upon success, call the ContactSensor constructor (automatically create prim). In case of ImportError / RuntimeError, set fallback to `CreatePrimWithDefaultXformCommand(prim_type="Xform")` + `xformOp:translate`. stamp `backend` (success path or `fallback_xform:<ErrorType>`) into customData.

IMU `mount_orientation` is converted to `[qw, qx, qy, qz]` **scalar-first** quaternion, `numpy.array` and then passed to `IMUSensor(..., orientation=np.array(quat))`.

---

## Replicator / Writers

### BasicWriter channel kwargs

`rep.WriterRegistry.get("BasicWriter")` + `writer.initialize(output_dir=..., rgb=True, distance_to_camera=True, semantic_segmentation=...)`. The writer instance is stored in the service internal dict (`self._writers[writer_id]`) — session lifetime. output_dir is automatically created by `os.makedirs(exist_ok=True)`.

> ⚠️ `depth` kwarg in validation_api REST is internally mapped to `distance_to_camera=True`. At the REST level, use `depth`, at the `rep.WriterRegistry` level, use `distance_to_camera`.

### Orchestrator trigger

- `trigger_once`: `rep.orchestrator.run_async(num_frames=N)` First, sync `run(num_frames=N)` falls back in unimplemented kit builds.
- `trigger_on_time`: `with rep.trigger.on_time(interval=s)` wrap. interval < simulation tick (0.016 s) cue buildup warning
- Timeline play alone does not flush the writer — **Explicit trigger required**

---

## OmniGraph

### ActionGraph creation + reuse

If `og.get_graph_by_path(graph_path)` is not found after checking, create ActionGraph with `og.Controller.edit({"graph_path": ..., "evaluator_name": "execution"}, {})`. If there is, reuse + `graph_existed=True`.

Node creation is `og.Controller.edit(graph, {Keys.CREATE_NODES: [(name, type)]})`. Attribute path: `/GraphPath/NodeName.outputs:<attr>` → `/GraphPath/NodeName.inputs:<attr>`.

### ROS2 publisher configuration

OnTick + `isaacsim.core.nodes.IsaacCreateRenderProduct` + `isaacsim.ros2.bridge.ROS2PublishImage` 3 nodes + 3 connections. An attempt to import `rclpy` results in `ros2_available`. If both extensions are inactive, the unknown node type is `og.Controller.edit`. Silent skip → response `nodes_created` Check the actual number of creations with the length. **Graph structure is created even without ROS2 runtime**.

### Running graph.evaluate() manually

Executes decisively once when ActionGraph is waiting for a scene event. The non-existent graph is `ValueError → 400`.

---

## Viewport/Window capture

### Viewport-owned overlay UI — single root required under `Frame`

`ui.Placer` / `ui.Button` / in the viewport overlay frame created with `viewport_window.get_frame(name)`
If you add multiple `ui.Image` directly, a symptom occurs where only the last child is visible depending on the kit build.
Actual symptom: Both Button A/B were created, but only Button B, which was drawn last, is displayed in the viewport.Safety pattern:
1. Place only a single root container directly below `with frame:`. Usually`ui.ZStack(width=ui.Fraction(1), height=ui.Fraction(1))`.
2. Multiple absolute-position widgets are placed as `ui.Placer(offset_x=..., offset_y=...)` within the root `ZStack`.
3. When changing state (Button HUD → Preview → Detail → Back), create a new root `ZStack` after `frame.clear()`.

### `omni.ui.Button` is not a context manager

In the Kit 107 / USD Composer series, the `ui.Button` instance does not support the `with button:` pattern.
If you use `with ui.Button(...): ui.Image(...)` or `with button:` to place an image as a child in a button,
`TypeError("'omni.ui._ui.Button' object does not support the context manager protocol")`.

Safety pattern when making an image tile clickable:
1. Create `ui.ZStack(width=..., height=...)`.
2. Place background `ui.Rectangle` + `ui.Image(..., width=ui.Pixel(w), height=ui.Pixel(h))`.
3. Place transparent `ui.Rectangle(opaque_for_mouse_events=True, style={"background_color": 0x00000000})` on top.
4. Connect `set_mouse_pressed_fn` or `set_mouse_released_fn` to the transparent rect.

### Viewport overlay buttons are `content_clipping=True` + `ui.Button`

If the button that appears above the viewport should prevent Stage prim selection, set `ui.Button` as the actual event target,
Surround it with a stack container such as `ui.ZStack(..., content_clipping=True)`.
The NVIDIA No-Code UI document also states that the Viewport UI does not block Prim selection by default and does not block content clipping of the Stack.
It is explained that it must be turned on to consume mouse clicks.

caution:
1. `ui.Rectangle + ui.Label + transparent ui.Rectangle(mouse callback)` composite button click callback can be executed,
It does not reliably block viewport selection and it is easy to lose the hover style.
2. For the button style, give a style dict to the parent stack and add `Button`, `Button:hovered`, `Button:pressed`,
Use `Button.Label` selector. `Button.Label` is a formula selector that controls text color / font size.
3. For areas where a Button child is not needed, such as the image preview tile, you can continue to use the transparent Rectangle hit layer pattern above.
Do not mix the event patterns of the actual HUD buttons and preview tiles.

### Color change UI uses `ColorWidget`

Settings where the user changes color or transparency in the extension panel are always exposed as `omni.ui.ColorWidget(r, g, b, a)`.
The combination of `StringField("RRGGBB")` + `IntDrag(alpha)` is not used as an operational UI due to input errors, commit timing, and lack of color preview.Safety pattern:
1. The internally stored value can be kept as ABGR int in line with the existing kit style.
2. When panel build/sync, convert ABGR int to RGBA float `(0.0..1.0)` and put it in `ColorWidget` child model.
3. Read the value of `r,g,b,a` of the child model from `ColorWidget.model.add_end_edit_fn(...)` and pack it back into ABGR int.
4. Several colors such as Button/Hover/Text/Panel/Overlay/Border share the same helper.

### Viewport point picking is prohibited from relying solely on `request_query`

`ViewportAPI.request_query(pixel, callback)` is an async callback, and the coordinate system/transmission timing may vary depending on Kit app/build.
If a new query is sent every frame and the previous callback is invalidated by generation, the callback is stale before it arrives.
The hover highlight / description overlay may not appear at all.

In modes where a fixed camera is set, such as top-view, a fallback is included:
1. Convert viewport-local pixel `(x, y)` to NDC based on camera projection.
2. Create a ray (origin, direction) directly using the world transform of USD camera prim.
3. For whitelist prim, hits are obtained in the order of PhysX raycast → USD BBox raycast.
4. `request_query` is set as the best-effort fast path, and the camera-ray path is set directly as the deterministic fallback.

### Create multi-viewport

Check the existence of a window with the same name as `omni.ui.Workspace.get_window(name)` → If it is `existed=true`, reuse. If it doesn't exist, try `omni.kit.viewport.window.ViewportWindow(name, width, height)`, if it fails, fallback to `omni.kit.viewport.utility.create_viewport_window`. 3 tick `next_update_async` wait for first frame to settle. destroy is idempotent (200 response even if it does not exist).

### Window capture strategy

- Target window: `kernel32.GetCurrentProcessId()` + `user32.EnumWindows`, which is the largest visible top-level (Kit main is class `GLFW30`, title includes "Isaac Sim" / "Omniverse" / "Kit")
- Capture: `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=0x2)` → `PrintWindow(.., 0)` on failure → final `BitBlt` fallback. DWM / RTX composite window must require **0x2 flag** (prevent black screen)
- Purely implemented with `ctypes` + PIL (not dependent on pywin32/mss)

### wait_stable mode — wait for async UI loading

If `wait_stable=true` is given, it will be recaptured at intervals of `stable_interval_s` and will be returned if **consecutive L1 pixel diff** (128×128 grayscale downsample, scale 0-1) is less than `stable_diff_threshold` (default 0.01) more than `stable_consecutive` times (default 2). `sha256` comparison is **not available** (FPS overlay / Timeline cursor changes pixels every frame). If `stable_max_wait_s` (default 45 s) is exceeded, `stabilized: false` + last capture is returned.

---

## UI Window / Menu Introspection

### How to use omni.kit.ui_test

- `omni.kit.ui_test.find/find_all()` is **sync**, `WidgetRef.click/double_click/input()` is **async**
- Path grammar requires the widget class to be specified, such as typed: `"Win Title//Frame/**/Button[*]"` to match. `**/*` matches 0 because `*` is interpreted only as an index wildcard.
- `ui_invoke(action=type)` is `WidgetRef.input(text, clear_before_input=True)` + `end_key=ENTER`. Omni ui `StringField` is committed with Enter — If omitted, the value is not reflected in the model. After typing, turn `app.next_update_async()` 4 frames to read post-state

### Menu introspection

- `get_menu_dict()` **None** in Kit 2.x. Use only `omni.kit.menu.utils.get_merged_menus()`
- Returns **flat dict**. The key is `_` delimiter hierarchy — Example: `"Window_Browsers"` ↔ `Window > Browsers` submenu. Not a nested structure
- The value is `{items: [MenuItemDescription], action_prefix: str, sub_menu: ..., delegate: ...}` wrapper dict — a list of actual leaf items within the `items` key. If you consider `top_items` as a list, it counts 0 incorrectly
- Menu item trigger is `omni.kit.actions.core.execute_action(ext_id, action_id)` — Same as actual click path. If there is no `onclick_action` tuple, `(action_prefix, item_name)` can be synthesized by convention, but it may not actually match the registered action → Do not judge based on the trigger success response alone.

### Browser window lazy instantiation

- `Workspace.get_window(name)` is **exact title match** only. The `[Beta]` / `[Experimental]` suffix in the browser window does not always match the menu label → fallback to case-insensitive substring scan
- Browser-type windows are **lazy-instantiated** — are not registered in `get_windows()` until the first `show_window` call. When automatically traversing the entire Browser set: `menu_list(Window/Browsers)` → each item `menu_trigger` → `ui_list` re-search order is required
- Browser thumbnail loading **different depending on extension** — `isaacsim.asset.browser` (`Isaac Sim Assets [Beta]`) crawls NVIDIA public S3 in real time when first opened. Empty grid upon immediate capture. `omni.kit.browser.asset` / `omni.simready.explorer` includes cached catalog → populate immediately. S3-crawl requires 10~30 s to settle after showing

### Browser / content browser is not deadlock root cause

The past `isaacsim.asset.browser` / `omni.kit.window.content_browser` prohibition hypothesis was invalidated by automatic verification on 2026-04-25. The deadlock causality is **carb log hook registration + MDL resolver combination**, and the latest baseline follows the conclusion of `docs/invariants/usd-load.md`.

Browser-type extensions may require a long UI settle time due to S3 thumbnail/catalog crawl when first opened. Therefore, consider 10-30 s settle in capture/test, but do not treat it as the root cause of USD load hang or manage it as a prohibition list in `.env`.

---

## Extension management / carb log

### ExtensionManager API pitfalls

- `manager.set_extension_enabled_immediate(ext_id, True)` **Return value is the Source of truth**
- `manager.get_extension_dict(bare_id)` returns **None** for bare id in Kit 107.3 (requires fully qualified `{name}-{version}`) — **Do not use** for validation purposes
- `activate` becomes `ValueError → 400` when the enable-immediate call result is False. Even in the enabled state, `reload=True` turns the off/on cycle to re-import the Python package.

### LogCaptureService Protocol

- `carb.logging.acquire_logging().add_logger(cb)` callback signature **5-arg** `(source, level, filename, line, msg)` — official documentation 6-arg (with tid) is outdated
- Level integer: VERBOSE=-2, INFO=-1, WARN=0, ERROR=1, FATAL=2
- The callback is called on the **carb thread**, so `_on_log` never raises (try/except swallow)
- `add_logger` handle is `on_shutdown` to `remove_logger` — If omitted, duplicate entries between extension reloads
- `query(since_ms, level, source_filter, limit)` is a thread-safe snapshot peek (not a drain) — returns the same entry in the same range when called repeatedly. Since the kit console is chatty, `ext_id` substring filter is required

---

## ASYNC Job Pattern

`JobService` of `services/job_service.py`:

- `start_job(coro_factory)` runs in the background as `asyncio.create_task` + keeps the task reference in `_tasks[job_id]` (for cancel)
- job dict: `{status, progress, result, error, created_at_ms, updated_at_ms}`. terminal state `done` / `error` / `canceled` sweep after TTL 1h (cleanup loop 120s)
- **All exceptions must be stored in the `error` state as try/except**. No silent catch (pass) — caller needs to determine cause of failure
- `cancel(job_id)` is `Task.cancel()` + `status=canceled`. If it is already a terminal, the current state is returned (idempotent). Navigate coroutine ensures `stop_animation` with `try/finally` (prevents mid-frame freeze after cancellation)
- When extension restarts, all in-flight jobs are lost → HTTP 404. Long-term jobs require a retry policy on the calling side.
- **`JobService.get_status`, `cancel` are sync methods** (not async). When reusing in-process import, do not use `await`
