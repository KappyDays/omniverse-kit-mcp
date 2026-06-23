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

## Follow-Up

The latest report shape confirms the newly added top-level
`diagnostic_next_actions` metadata is non-disruptive on the passing Robot/RTX
golden path. A future failure-path live run should confirm the retry metadata
fields with a controlled zero-point lidar attempt.
