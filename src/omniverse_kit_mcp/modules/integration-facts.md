<!-- Parent: CLAUDE.md -->
<!-- Scope: Domain-specific runtime constraints — Reference for searching when writing domain-specific code/scenarios -->

# Integration Facts — REST Consumer Perspective

Non-obvious runtime constraints per domain. Something you can’t figure out just by reading the module/service code.
When adding a new feature, add a bullet to the relevant domain sub-section. Required knowledge before work
See `../../../docs/invariants/*.md` pull-doc.

## ⚠️ Cross-cutting Hazards (always valid when reading this file)

- **USD asset load**: S3 URL required / `log_capture.start()` Always active prohibited / Only request-scoped Console capture allowed / Use payload path — Details: `../../../docs/invariants/usd-load.md`
- **NavMesh bake**: Valid only after `simulation_stop` bake (R1a) — Details: `../../../docs/invariants/scenario-validation.md`
- **Robot operation**: `simulation_play` state required (R2) — Details: `../../../docs/invariants/scenario-validation.md`

## Simulation / Timeline
- **`simulation/play|pause|stop` settled readback**: Control calls tick Kit at least once and return the observed post-action state plus `timeline_settled` / `timeline_settle_updates`. If `timeline_settled=false`, recheck `simulation_get_status` and capture WARN/ERROR logs before treating a later robot/sensor failure as root cause.
- **`simulation_step` advance mode**: In Isaac Sim 6.0, `omni.timeline.forward_one_frame()` may crash in the active Replicator/HydraTexture render product state, so the default value is play → `next_update_async()` until target time → pause (was_playing preserved). If the timeline does not advance the actual time in the replicator remaining state, the target time is set with `set_current_time` fallback, and the response `advance_mode` is `play_burst` or `set_time_fallback`.

##Viewport
- **GUI mode required**: `viewport_capture` is empty data in `--no-window` / headless
- **Replicator detach compatibility**: In some kit builds, `omni.replicator.core` annotator.detach is set to `AttributeError` in HydraTexture object (assuming `_get_node_path` string) → `viewport_service` wraps detach failure with try/except and falls back to `omni.kit.viewport.utility.capture_viewport_to_file`
- **Continuous capture re-cache**: Viewport capture can be repeated with the same PNG. Insert `simulation.play` between frames when necessary
- **`ViewportModule.create` idempotent**: When recalling the same `viewport_name`, `existed=True` + existing window is returned. `omni.kit.viewport.window.ViewportWindow` 1st → `create_viewport_window` fallback. `destroy` is also idempotent (`destroyed=false` if missing)
- **`viewport_set_fov` camera candidate walk**: `/OmniverseKit_Persp` resides in session layer in fresh stage → `GetPrimAtPath` IsValid=False. `ViewportRenderService._candidate_camera_paths` falls back to `get_viewport_from_window_name` → Kit built-in camera (Persp/Top/Front/Right) → `stage.Traverse()` to first `USDGeom.Camera`. `focalLength = (horizontalAperture/2) / tan(fov/2)` inversion
- **`viewport_toggle_overlay(overlay="axis")` user.config.json pollution prevention path required** (historical Kit 107 / Isaac Sim 5.1, measured on 2026-04-21): When saving `/persistent/app/viewport/displayOptions/axis = bool`, Kit permanently stores the parent key as dict in `user.config.json` → `_setup_viewport_options` of `omni.kit.viewport.window-107.2.0/legacy.py:226` uses the same key as **int Read with bitmask** Execute `settings & 0x1` → `TypeError: dict & int` → `ViewportWindow.__init__` fails → `_ViewportWindow__viewport_layers` is not created → viewport_widgets_manager / measure tool / physx.supportui successively fails in **all subsequent Kit startups**. Correct path: `/persistent/app/viewport/<viewport_name>/Viewport0/guide/axis/visible` (now `viewport_render_service._axis_key_for_viewport`). Recovery: `persistent.app.viewport.displayOptions` dict key deleted from `~/AppData/Local/ov/data/Kit/Isaac-Sim Full/<version>/user.config.json` → restored as int bitmask upon restart

## Process / Health / Code reload
- **Process termination**: `taskkill /f /im kit.exe` fails to parse options in Git Bash → Use `cmd //c "taskkill /F /IM kit.exe /T"` or `powershell.exe -NoProfile -Command "Stop-Process -Name kit -Force"`
- **kit.exe runtime flags**: `--ext-folder PATH` + `--enable EXT_ID` — both must be present to automatically enable without Extension Manager toggle
- **Health endpoint**: `GET http://127.0.0.1:8111/validation/v1/health` 200 response is based on ProcessModule readiness
- **Live entry default**: `kit_app_start` ends with attach/idempotent ready to the alive kit, so the live worker enters start-first. Use `stage_new` for fresh stage, use the reload path below to reflect code, and avoid restart for repeated verification other than crash/hang.
- **Code reload**: When modifying user/demo extension `.py`, not validation_api, `extension_reload(ext_id)` takes precedence. `omni.mycompany.validation_api` changes itself, changes extension.toml dependencies/native, and changes `kit_app_restart` only when marker verification fails.

## Stage / USD load protocol (no changes)
>`../../../docs/invariants/usd-load.md` is a 4-line summary. This section details the root cause + resolution 3 factors + diagnosis of recurrence.- **Root cause**: When historical Kit 107 / Isaac Sim 5.1 MDL resolver opens Materials.usd of S3 asset while `LogCaptureService`'s carb log callback is registered, `"Disabling base URL to resolve MDL identifier 'OmniPBR.mdl'"` is repeated → Python callback GIL contention in carb thread → Kit main event loop deadlock → All MCP tools 92 s timeout
- **Resolved 3 elements** (baseline — hang recurrence when changed):
  1. Extension `on_startup` to `self._log_capture = None` (NOT `get_log_capture_service().start()`) — If you need evidence of live failure, open a request-scoped capture window with `extension_clear_logs` and close it with `extension_capture_logs(..., stop_after_capture=True)`
  2. `stage_service.load_usd` is `omni.kit.async_engine.run_coroutine(_main_loop_impl())` + `asyncio.wrap_future(future)` — FastAPI event loop ≠ Kit main event loop, so explicit schedule in Kit main loop
  3. `omni.kit.commands.execute("CreatePayloadCommand", ...)` — Equivalent path to GUI drag&drop scene_drop_delegate. Static payload is `instanceable=True`; robot/articulation outer payload is `instanceable=False` because of runtime traversal/write
- **URL Policy**: S3 required (`file:///` prohibited). Prefix:
  -`https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/...`
  -`https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/...`
  -`https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/{ArchVis,DigitalTwin,Vegetation}/...`
  - SoT: `../../../docs/assets/isaac/asset_inventory.md`
- **`stage_open` vs `stage_load_usd`**: The former replaces the root stage (scene conversion), the latter adds `/World/<name>` Payload (multi-asset composition)
- **Actual measurement** (after hang resolution on 2026-04-20): Simple_Warehouse 2.4 s / NovaCarter 3.1 s / F_Business_02 2.6 s / SimReady cold 10~57 s / multi-asset composition OK
- **Diagnosis order in case of recurrence**:
  1. After Kit log `%USERPROFILE%\.nvidia-omniverse\logs\Kit\Isaac-Sim Full\6.0\kit_*.log` last entry repeats `"Disabling base URL to resolve MDL identifier"`, silent = deadlock is confirmed.
  2. `simulation_get_status` blocks 92 s timeout → Kit main loop
  3. `cmd //c "taskkill /F /IM kit.exe /T"` — PowerShell `Stop-Process` is Access Denied confirmed
  4. Fresh restart with `.venv/Scripts/python.exe scripts/run_process_module_standalone.py start`
- **Prohibited**: `log_capture.start()` constant reactivation / `file:///` local cache / MDL-heavy S3 scene synchronous load to `stage_open` / skip/fallback/placeholder when S3 load fails — all prohibited. Browser/content-browser presence itself is not a deadlock blocker.

## ASYNC Job
- **Convention**: Job-based endpoints (`/robot/navigate`, `/character/navigate`, `/robot/navigate_path`) immediately return `{job_id}`. Polling: `GET /jobs/{job_id}` / Stopping: `POST /jobs/{job_id}/cancel`. Details: `../../../kkr-extensions/CLAUDE.md §"ASYNC Job pattern"`

## Robot / IK
- **R2 (timeline playing required)**: `navigate_to` / `navigate_path` / `get/set_joint_positions` is required for `omni.timeline.is_playing()`. Extension `robot_service.navigate_path` receives HTTP 400 if not passed.
- **`RobotModule.navigate_to`**: `xformOp:translate` linear interp over `duration_s` (60 fps). Base movement only — joints/IK use `set_joint_positions`
- **`robot_load` 6.0 payload exception**: S3 robot USD loads as `CreatePayloadCommand(instanceable=False)`. Unlike static payload, the articulation runtime performs child prim traversal/write, so instanceable payload is prohibited. If there is a pending/running JobService job, HTTP 400 is received and the playing timeline stops before loading.
- **`robot_gripper_control` DOF automatic detection**: `SingleArticulation.dof_names` to `finger` / `gripper` substring. Franka match, UR10 mismatch → 400. `simulation_play → pause` called after warm-up
- **`robot_set_ee_target` Franka/FR3 Lula IK**: `_resolve_lula_modules()` uses 6.0 `isaacsim.robot_motion.motion_generation.lula` path. Unsupported robot_description should be wrapped with `continueOnFailure: true` in 400. scenario.

##Character/BehaviorAgent
> For detailed traps, refer to `CLAUDE.md §"Character domain constraints"` (sibling).

- **BehaviorAgent `custom_action` Isaac Sim 6.0 signature**: `IBehaviorAgent.custom_action(action, root_animation=..., duration=...)` positional action is required. Adapter is positional first, legacy `action_name=` fallback order. Calling kwargs-only throws 500 TypeError.
- **`character_play_animation_variant` unwired style tolerant**: Even if `sit_style` / `walk_style` / `run_style` is not in the character runtime, base Action is always set. `response.variables_set` is the actual applied key
- **BehaviorAgent handle availability optional**: Some 6.0 Replicator Agent skins pass the payload/render/prim assertion, but the BehaviorAgent handle may appear late or not appear even after warm-up. Variant demo/scenario is wrapped in `continueOnFailure: true`, and required verification is separated into character load/crowd/prim state.
- **`character_load_crowd` random seed fixed**: `_layout_positions("random", ...)` is `random.Random(0)` — test reproducibility. If a different seed is needed in Live, center offset shuffle or loader top wrap## Asset / Content
- **`AssetModule.list`**: `isaacsim.storage.native.get_assets_root_path()` returns public S3 by default (browse without Nucleus). Wrap `omni.client.list` with `asyncio.to_thread`. Category: `robots/environments/props/people/materials/isaaclab`
- **Verification asset rule (R1)**: `RobotModule.load` / `CharacterModule.load` / `stage_load_usd` tests do not substitute primitives. Only real USD, navigable by `AssetModule.list`. Details: `../../../docs/invariants/scenario-validation.md`
- **Content is based on `omni.client`**: Same API for S3 / local URL other than Nucleus. Nucleus URL is 403 if there is no login token → `backend=fallback_metadata:<ErrorType>` is reported at the MCP boundary. Content tools operate directly as `omni.client` without browser UI extension. Browser/content-browser has a lazy crawl when first opened, so it requires waiting for the UI to settle, but activation itself is not prohibited upon startup.

## NavMesh
- **R1a (canonical sequence)**: `load assets → simulation.stop → navigation.bake → navigation.query_path → simulation.play → robot.navigate_path`. `bake` returns True when called while playing, but `get_navmesh()` = None (silent False Positive) — The caller specifies `simulation.stop`
- **non-blocking polling**: `navigation_service.bake` / `_bake_if_needed` becomes `start_navmesh_baking()` + `is_navmesh_baking()` + `app.next_update_async()`. `_and_wait` variant absolutely prohibited (HTTP router starved with Kit Python single-threaded occupation). `timeout_s` (default 300 s) upper limit, progress to `elapsed_ticks`
- **Isaac Sim 6.0 `query_shortest_path` signature**: direct kwargs `agent_radius=` / `agent_height=` is TypeError. Use `NavAgentDesc(radius, height, collision_gap)` positional argument + empty `np.float32` area-cost array. Validation API and navmesh playground through wrapper 6.0 first, old kwargs fallback order.
- **cache lock recovery**: `"start_navmesh_baking returned False"` occurs frequently when repeating 5+ times in the same kit. ① `stage_delete_prim("/World/NavMeshVolume")` → Retry ② In case of failure, restart the kit. A fresh kit is recommended for repeated bake scenarios.
- **visualization backend priority**: `set_visualization` takes priority over `carb.settings /persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh` toggle. In case of failure, `NavMeshVolume` prim `visibility` fallback. response `backend` ∈ {`carb_settings`, `prim_visibility`}.
- **`add_exclude_volume(prim_path=...)`**: Automatic placement of bbox-based Exclude by calling `stage.compute_world_bbox` internally — avoiding chair / low prop step-up artifact

## Sensor
- **Sensor prim based**: RTX camera / depth camera has `USDGeom.Camera` + `customData.validation_api.sensor_type` tag. RTX Lidar is 6.0 OmniLidar/schema prim + same customData tag created by `isaacsim.sensors.experimental.rtx.Lidar.create`. Actual annotator attach/readback is dispatched by sensor type. `set_visualization(on|off)` has prim visibility/debug draw common toggle
- **RTX Lidar is not a viewport camera in 6.0**: `attach_rtx_lidar` creates an OmniLidar/schema prim, not a renderable `USDGeom.Camera`. Passing that prim as `viewport_create.camera_path` or `viewport_capture.camera_prim_path` can crash native `rtx.sensors.lidar.core`; `ViewportService` rejects it. Use `sensor_set_visualization` + normal camera capture, or `sensor_lidar_get_point_cloud`.
- **Physics sensor (Contact/IMU) The `response.backend` field is the actual path (`isaacsim.sensors.experimental.physics` | `fallback_xform:<ErrorType>`)
- **`sensor_set_annotator` MCP lax / Extension strict**: MCP passes `list[str]`, Extension verifies fixed set {rgb, depth, semantic_segmentation, instance_segmentation, normals, motion_vectors, distance_to_camera, distance_to_image_plane} membership. Unknown annotator is 400. Attach failure collects `response.skipped[name]`

## Physics / Material / Lighting
- **`USDPhysics.CollisionAPI` depends on `rigidBodyEnabled`**: Applies only to `physics_apply_collider` prim is a static collider — Add `physics_apply_rigid_body(dynamic=True)` if you want gravity/force response. The first `physics_set_scene` must be arranged
- **`MaterialBindingAPI.DirectBinding.GetBindingStrength` is AttributeError** in legacy kit Python binding: Acquiring rel with `binding.GetDirectBinding().GetBindingRel()` and then calling static `USDShade.MaterialBindingAPI.GetMaterialBindingStrength(rel)` is the correct answer. `MaterialService.get_bound` is this pattern — use the same when adding a new material operation

## Replicator / SDG
- **writer requires explicit orchestrator tick**: `create_writer` alone does not write files. A separate call to `trigger_once(num_frames=N)` or `trigger_on_time(interval_s=...)` is required. `simulation_play` only has PhysX ticks — separate from the orchestrator
- **Compatible with `trigger_once` version**: `rep.orchestrator.run_async` (new) first, if not, fallback to `run` (old)
- **Risk of deadlock when continuously triggered immediately after loading MDL heavy asset** — `log_capture` must be kept inactive by default (`_log_capture = None`)## OmniGraph
- **ActionGraph depends on scene event**: `omni.graph.action.OnTick` / `OnLoaded` does not fire if there is no scene event such as `simulation_play` tick. When deterministic execution is required in Scenario, manually call `graph.evaluate()` with `omnigraph_execute(graph_path)`
- **Can create `create_ros2_publisher` part**: `isaacsim.core.nodes.IsaacCreateRenderProduct` + `isaacsim.ros2.bridge.ROS2PublishImage` macro. When one ext is inactive, `og.Controller.edit` is unknown type silent skip → check the actual number of creations with the length of response `nodes_created`

## Extension Management
- **`get_info` iteration path priority**: For Kit 107.x, `get_extension_dict(bare_id)` is None. Traverse `get_extensions()` → Match `name==ext_id` → Configure summary → Reinforce dependencies/title by re-querying raw dict with `full_id`. Unregistered ext causes KeyError → HTTP 404
- **`deactivate`**: `set_extension_enabled_immediate(id, False)` — `was_enabled=False` idempotent if already inactive. Python module import is alive — combine `activate(id, reload=True)` when re-import is needed

## Window / UI
- **Separation of two domains**: `WindowModule` = Kit GUI level (`omni.ui.Window` / `omni.kit.menu.utils`), `ExtensionModule.ui_*` = widget level (`omni.kit.ui_test`). GUI operation sequence: `window_menu_trigger` → (lazy-instantiated browser re-queries `ui_list`) → `extension_get_ui_tree(window=...)` → `extension_ui_invoke` → `window_capture`. Details: `../../../kkr-extensions/CLAUDE.md §"Window capture & UI automation"`
- **headless caveat**: `get_ui_tree` / `ui_invoke` / `window_list` / `window_ui_list` / `window_capture` only in GUI mode. From `--no-window` to `omni.ui` no-op. `extension_activate` / `capture_logs` is headless OK
- **`isaacsim.exp.full.kit` preset does not include `isaacsim.asset.browser`**: `Window > Browsers > Isaac Sim Assets` menu exists, but window is not created (`menu_trigger` silent no-op). Add to `ISAAC_SIM_EXTRA_EXT_IDS` if necessary. Actual window title is `Isaac Sim Assets [Beta]` (different from menu label)

## Related Boundaries

- Module Responsibility Matrix + Character Constraints + base.py Pattern: `CLAUDE.md` (sibling)
- ProcessModule operation manual: `process-ops.md` (sibling)
-USD load invariants: `../../../docs/invariants/usd-load.md`
- Scenario validation (R1/R1a/R2/R3): `../../../docs/invariants/scenario-validation.md`
- Process lifecycle invariants: `../../../docs/invariants/process-lifecycle.md`
-UI automation invariants: `../../../docs/invariants/ui-invoke.md`
