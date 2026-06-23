# Robot RTX Golden Live Report Shape - 2026-06-24

## Scope

Workspace-local Isaac Sim MCP smoke for
`scenarios/smoke/robot_rtx_sensor_golden_workflow.yaml`.

The smoke was executed from `workspaces/isaac/instance-1` through the
workspace-local stdio MCP entry. Kit was not launched from the repo root.

## Live Sequence

1. `mcp_runtime_info`
2. `kit_app_start`
3. `simulation_get_status`
4. `extension_clear_logs`
5. `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)`
6. `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml,
   redact_local_paths=true)`
7. `scenario_last_report(report_format="json", redact_local_paths=true)`
8. `scenario_last_report(report_format="markdown", redact_local_paths=true)`
9. `extension_capture_logs(level="WARN", stop_after_capture=true)`
10. `extension_capture_logs(level="ERROR", stop_after_capture=true)`

## Result

- MCP profile: `full`
- App profile: `isaac-sim`
- Registered tools: 152
- Source newer than import: `false`
- `kit_app_start`: attached to a healthy existing Isaac Sim instance on the
  workspace instance port.
- Scenario status: `passed`
- Steps: 32 passed, 0 failed, 0 skipped
- `diagnostic_next_actions`: `[]`

## Evidence Summary

| Step | Evidence | Result |
| --- | --- | --- |
| `read_lidar_point_cloud` | RTX lidar point cloud | `num_points=512`, `attempts=1/3`, `frames_waited=180`, backend `isaacsim.sensors.experimental.rtx.LidarSensor`, `truncated=true`, no warning |
| `frame_robot_and_sensors` | Viewport framing | camera `/OmniverseKit_Persp`, 4 prims framed, bbox non-empty |
| `capture_visible_result` | Visual capture assert | passed, SHA-256 `25ce4dcf85aaff07af035229edcd04fa2995caf5fc63927d46ba71eebd16a87c`, redacted artifact `<validation-api-capture>/capture_45a6753356da.png` |

Manual visual inspection of the capture confirmed a visible NovaCarter robot on
the grid between the four lidar target cubes.

## Log Summary

WARN capture returned 6 entries:

- repeated `omni.hydratexture.plugin` release warnings
- one USD stage close reference-count warning

ERROR capture returned 0 entries. The WARN entries did not contradict the
passed lidar/capture evidence.

## Refresh After Viewport Diagnostics

A follow-up live run after adding `viewport_capture_assert` diagnostics confirmed
the passing Robot/RTX report shape stayed stable and public-safe.

Run sequence:

```text
mcp_runtime_info
kit_app_start
simulation_get_status
extension_clear_logs
scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)
scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)
scenario_last_report(report_format="json", redact_local_paths=true)
scenario_last_report(report_format="markdown", redact_local_paths=true)
extension_capture_logs(level="WARN", limit=300)
extension_capture_logs(level="ERROR", limit=300)
simulation_get_status
```

Result shape:

- Scenario status: `passed`
- Steps: 32 passed, 0 failed, 0 skipped
- Phase counts: arrange `11`, act `9`, assert `5`, cleanup `7`
- Plan evidence steps: `read_lidar_point_cloud`,
  `frame_robot_and_sensors`, `capture_visible_result`
- Plan retry steps: `read_lidar_point_cloud`
- Top-level `diagnostic_next_actions`: `[]`
- Redacted Markdown report included `Data Summary Highlights` and
  `Evidence Summary`; it did not include `Diagnostic Next Actions` on the
  passing path.
- Final simulation status after cleanup: stopped at time `0.0`

Latest evidence summary:

| Step | Evidence | Result |
| --- | --- | --- |
| `read_lidar_point_cloud` | RTX lidar point cloud | `num_points=512`, `attempts=1/3`, `frames_waited=180`, backend `isaacsim.sensors.experimental.rtx.LidarSensor`, `truncated=true`, no warning, diagnostics `cached_lidar_instance=true`, `readback_paths_attempted=[cached_lidar_sensor]` |
| `frame_robot_and_sensors` | Viewport framing | camera `/OmniverseKit_Persp`, 4 prims framed, bbox non-empty, distance `12.495940213868709` |
| `capture_visible_result` | Visual capture assert | passed, redacted artifact `<validation-api-capture>/capture_88c92586847b.png`, SHA-256 `6907cbbb08a86d6d3df31e38675ad2912be9d3e363ab843ff7e787fcf6416582`, `1280x720`, `pixel_mean_average=145.69629340277777`, `pixel_variance_average=1102.576399772127`, `warmup_frames_used=8`, `failure_codes=[]` |

Manual visual inspection confirmed NovaCarter on the NVIDIA grid, the top RTX
lidar, and four surrounding lidar target cubes are visible. WARN capture returned
5 entries and ERROR capture returned 0 entries; the WARN payload was not copied
into this public artifact.

## Follow-Up

The latest report shape confirms the newly added top-level
`diagnostic_next_actions` metadata is non-disruptive on the passing Robot/RTX
golden path. Failure-path live evidence for viewport capture diagnostics is
recorded separately in
`docs/artifacts/viewport-capture-assert-diagnostics-2026-06-24.md`; a remaining
useful failure-path run is a controlled zero-point lidar attempt that exercises
retry metadata in `scenario_last_report`.
