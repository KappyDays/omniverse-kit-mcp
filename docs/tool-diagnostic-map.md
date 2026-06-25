<!-- Parent: ../CLAUDE.md -->
<!-- Scope: When an error/failure occurs, verify the hypothesis with a read-only MCP tool before modifying the code — Debugging first read -->
# Tool Diagnostic Map

When an error/unexpected operation occurs **Modify → Before the trial cycle** Read this document.
If the code modification + attempt with the same hypothesis fails twice → Hypothesis reexamination is forced (repeated attempts are prohibited).

## Diagnostic workflow (5 second cycle vs 10 minute cycle)

1. **Grep error message**: project source + Kit source (`C:/workspace/isaac-sim-standalone-*/exts/`) — Identify line of occurrence, narrow down hypothesis
2. **Call MCP read-only diagnostic tool** (~5 seconds each) — Verify hypothesis using the table below
3. **When environmental dependency is suspected**: `extension_search/activate` (lazy install) + `content_browse` (URL verification) + filesystem directly
4. Attempt to modify the code **only after confirming the hypothesis**. Same hypothesis fails twice = hypothesis discarded

## Question → MCP tool reverse index

| question | 1st MCP tool | Response field / validation method |
|------|---------------|---------------------|
| Is this prim this articulation? | `robot_load(usd_url, prim_path)` | `has_articulation` |
| Robot load failed? | `simulation_get_status` → `stage_capture_snapshot` → `official_asset_search` / `asset_search` → `robot_load` → `extension_capture_logs` | For `ROBOT_LOAD_ERROR` or `CAPABILITY_NOT_SUPPORTED`, inspect `diagnostics.reason=robot_load_error`, `diagnostics.usd_url`, `diagnostics.prim_path`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Robot joint readback failed? | `mcp_runtime_info` → `simulation_get_status` → `stage_capture_snapshot` → `robot_get_joint_config_static` → retry `robot_get_joint_positions` / `robot_get_joint_config` / `robot_get_joint_config_static` → `extension_capture_logs` | Inspect `diagnostics.reason=robot_get_joint_positions_error` / `robot_get_joint_config_error` / `robot_get_static_joint_config_error`, `diagnostics.prim_path`, `diagnostics.static`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Robot direct control failed? | `mcp_runtime_info` → `simulation_get_status` → `stage_capture_snapshot` → `robot_get_joint_config_static` if joint/IK-related → retry `robot_gripper_control` / `robot_set_ee_target` / `robot_set_joint_positions` → `extension_capture_logs` | Inspect `diagnostics.reason=robot_gripper_control_error` / `robot_set_ee_target_error` / `robot_set_joint_positions_error`, `diagnostics.prim_path`, action/target/target_pose/positions_count fields, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Robot navigation or EE pose failed? | `mcp_runtime_info` → `simulation_get_status` → `stage_capture_snapshot` → `robot_get_joint_config_static` if pose/drive-related → retry `robot_navigate_to` / `robot_navigate_path` / `robot_drive_physics` / `robot_get_ee_pose` → `job_status` if a job was created → `extension_capture_logs` | Inspect `diagnostics.reason=robot_navigate_to_error` / `robot_navigate_path_error` / `robot_drive_physics_error` / `robot_get_ee_pose_error`, requested target/waypoint/wheel/frame fields, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Franka pick-place run failed? | `mcp_runtime_info` → `simulation_get_status` → `stage_capture_snapshot` → retry `robot_run_franka_pick_place` → `extension_capture_logs` | Inspect `diagnostics.reason=robot_franka_pick_place_error`, requested robot/object/target fields, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Pick-place playback demo install/reset failed? | `mcp_runtime_info` → `simulation_get_status` → `stage_capture_snapshot` → retry `robot_install_pick_place_playback_demo` / `robot_reset_pick_place_demo` → `robot_get_pick_place_demo_status` → `extension_capture_logs` | Inspect `diagnostics.reason=pick_place_demo_install_error` / `pick_place_demo_reset_error`, requested robot/object/target/fit fields for install, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| RTX sensor attach failed? | `mcp_runtime_info` → `stage_capture_snapshot` → `simulation_get_status` → retry the same `sensor_attach_rtx_*` tool → `extension_capture_logs` | Inspect `diagnostics.reason=rtx_camera_attach_error` / `rtx_depth_camera_attach_error` / `rtx_lidar_attach_error`, `diagnostics.robot_prim`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| RTX camera annotator failed? | `mcp_runtime_info` → `stage_capture_snapshot` → `simulation_get_status` → retry `sensor_set_annotator` → `extension_capture_logs` | Inspect `diagnostics.reason=sensor_set_annotator_error`, `diagnostics.sensor_prim`, `diagnostics.annotators`, `diagnostics.resolution`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Physics sensor attach failed? | `mcp_runtime_info` → `stage_capture_snapshot` → `simulation_get_status` → retry `sensor_attach_contact` / `sensor_attach_imu` → `extension_capture_logs` | Inspect `diagnostics.reason=sensor_attach_contact_error` / `sensor_attach_imu_error`, requested prim/sensor/frequency/mount fields, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Sensor visualization failed? | `mcp_runtime_info` → `stage_capture_snapshot` → `simulation_get_status` → retry `sensor_set_visualization` → `extension_capture_logs` | Inspect `diagnostics.reason=sensor_set_visualization_error`, `diagnostics.sensor_prim`, `diagnostics.mode`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Timeline control failed? | `mcp_runtime_info` → `simulation_get_status` → retry `simulation_play` / `simulation_pause` / `simulation_stop` once → `extension_capture_logs` | Inspect `diagnostics.reason=simulation_control_error`, `diagnostics.action`, `diagnostics.tool_name`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Timeline step failed? | `mcp_runtime_info` → `simulation_get_status` → retry `simulation_step` / `simulation_step_observe` with fewer frames or targets → `extension_capture_logs` | Inspect `diagnostics.reason=simulation_step_error` / `simulation_step_observe_error`, `diagnostics.frames`, observe target fields, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Timeline wait failed? | `mcp_runtime_info` → `simulation_get_status` → retry `simulation_wait_until` with a nearer target time or shorter timeout → `extension_capture_logs` | Inspect `diagnostics.reason=simulation_wait_until_error`, `diagnostics.until_time`, `diagnostics.timeout_s`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Timeline seek failed? | `mcp_runtime_info` → `simulation_get_status` → retry `simulation_set_time` with a small non-negative time → `extension_capture_logs` | Inspect `diagnostics.reason=simulation_set_time_error`, `diagnostics.time_seconds`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Official asset catalog read failed? | `official_asset_sync_status` → retry the failing `official_asset_*` call → `asset_search` if the generated catalog remains unusable | For `OFFICIAL_ASSET_*_ERROR`, inspect `diagnostics.reason=catalog_parse_error` or the tool-specific reason, `diagnostics.checked_catalog_path`, `diagnostics.error_type`, `diagnostics.suggested_next`, and `diagnostics.fallback_tool_order` |
| USD stage load failed? | `mcp_runtime_info` → `simulation_get_status` → `content_browse(parent)` → `official_asset_search` / `asset_search` → retry `stage_load_usd` → `extension_capture_logs` | For `STAGE_LOAD_ERROR`, inspect `diagnostics.reason=stage_load_usd_error`, `diagnostics.usd_url`, `diagnostics.prim_path`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order`; do not substitute primitives for requested real assets |
| Root stage open failed? | `mcp_runtime_info` → `simulation_get_status` → verify the scene URL/path → retry `stage_open` → `extension_capture_logs` | For `STAGE_OPEN_ERROR`, inspect `diagnostics.reason=stage_open_error`, `diagnostics.path`, `diagnostics.upstream_error_code`, `diagnostics.suggested_next`, and `diagnostics.fallback_tool_order` before replacing the scene through another route |
| Is this USD URL real? | `content_browse(parent_dir)` | Items in `entries[]` (S3 catalog) |
| Ext registration? | `extension_search(keyword)` | result count > 0 |
| Enable Ext? | `extension_get_info(ext_id)` | `info.enabled` / `info.path` |
| Ext lazy install + activation? | `extension_activate(ext_id)` | `was_enabled` / `enabled` |
| Widget click effect? | `extension_ui_invoke` post-state + `extension_get_ui_tree` label change |
| Prim being? | `stage_assert_prim_exists(prim_path)` | `passed` |
| Prim attribute value? | `stage_assert_property(prim_path, property_name)` (expected omitted) | `actual.value` |
| Stage full prim? | `stage_capture_snapshot` → `data.prims` dict (larger response — Bash + jq/python recommended) |
| Timeline state? | `simulation_get_status` | `is_playing` / `current_time` |
| Window exists? | `window_list` | `windows[].class_name=GLFW30` |
| Window UI tree? | `extension_get_ui_tree(window=)` | `widgets[]` (USD Composer does not have `omni.kit.ui_test` → 0 widgets + walk_error) |
| Visual status? | `viewport_capture` / `window_capture` + `Read` tool | PNG (R3) |
| Viewport capture failed? | `mcp_runtime_info` → `simulation_get_status` → `viewport_frame_prims` → retry `viewport_capture` with `warmup_frames > 0` → `extension_capture_logs` | For `VIEWPORT_CAPTURE_ERROR`, inspect `diagnostics.reason=viewport_capture_error`, requested viewport/camera/size fields, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` before changing render or camera code |
| Viewport framing failed? | `stage_capture_snapshot` → `simulation_get_status` → `viewport_frame_prims` → `extension_capture_logs` | For `VIEWPORT_FRAME_PRIMS_ERROR`, inspect `diagnostics.reason=viewport_frame_prims_error`, requested `diagnostics.prim_paths`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` before changing camera code |
| Viewport focus/projection failed? | `stage_capture_snapshot` → `stage_compute_world_bbox` or `viewport_frame_prims` → retry `viewport_focus_prim` / `viewport_project_points` / `viewport_set_camera_lookat` → `extension_capture_logs` | Inspect `diagnostics.reason=viewport_focus_prim_error` / `viewport_project_points_error` / `viewport_set_camera_lookat_error`, requested prim/camera/point fields, and `diagnostics.fallback_tool_order` before changing camera code |
| Kit menu item? | `window_menu_list` / `window_menu_trigger` | `items[]` |
| Script Editor localhost REST timeout? | `simulation_get_status` from outside Script Editor | Same Kit process blocking on itself; do not call Kit REST synchronously from Script Editor |
| MDL deadlock? | `simulation_get_status` 92s timeout | → `runbooks/kit-stdin-deadlock.md` |

## Extension internal progress stamping pattern

Inside ext in an environment where `extension_capture_logs` is no-op (`invariants/usd-load.md`)
For external polling of progress, USD attribute stamp:

```python
# extension code (at each progress step)
from pxr import Sdf, USDGeom
prim = USDGeom.Xform.Define(stage, Sdf.Path("/World/MyExtStatus")).GetPrim()
prim.CreateAttribute("stage", Sdf.ValueTypeNames.String).Set("step_5_done")
prim.CreateAttribute("last_error", Sdf.ValueTypeNames.String).Set(str(exc))
```

```python
# MCP polling (external)
stage_assert_property(prim_path="/World/MyExtStatus", property_name="stage")
# response.actual.value to read the current step
```

## Self-test pattern (environment without UI automation)

USD Composer, etc. `omni.kit.ui_test` absent → `extension_ui_invoke` widget click not possible
(Externalized as `extension_get_ui_tree` widgets=0 + walk_error).

Alternative: self-test coroutine schedule, results in extension `on_startup`
stamp with `/World/<Ext>SelfTestResult` prim attribute → MCP `stage_assert_property`
read. Immediately after stamping to avoid side-effects (e.g. restore after highlight) and verification race.
Separate verification state (reset to highlighted_path = None, etc.).

## Comparison of hypothesis testing costs

| Action | time |
|------|------|
| 1 MCP read-only call | ~5 s |
| Grep (project/kit source) | ~5 s |
| Standalone python verification (`scripts/run_*_standalone.py`) | ~10 s |
| Kit restart + build + play + start cycle | ~10 min |

→ One cycle saved with one read-only verification before code modification. Accumulated 1 hour vs 25 s for 4-5 attempts.

## Related Boundaries

- Full MCP tool signature: `tool-catalog.md` (auto-generated, signature-oriented)
- Process lifecycle / hang: `invariants/process-lifecycle.md` + `runbooks/cold-boot-timeout.md`
- USD load trap (S3 URL / MDL deadlock): `invariants/usd-load.md`
- Ext reload (sys.modules cleanup limit): `invariants/ext-reload.md`
- Multi-app port / profile: `invariants/multi-app.md`
- Kit SDK domain trap: `../kkr-extensions/docs/kit-sdk-pitfalls.md`
