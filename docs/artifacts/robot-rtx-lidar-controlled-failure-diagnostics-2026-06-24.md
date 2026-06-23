# Robot RTX Lidar Controlled Failure Diagnostics - 2026-06-24

## Purpose

Prove the golden robot + RTX lidar scenario can be run with bounded input
overrides to exercise the lidar failure/retry diagnostics without editing the
scenario file.

## Live Sequence

Workspace-local MCP worker from `workspaces/isaac/instance-1`:

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
extension_clear_logs -> scenario_plan(input_overrides={lidar_min_points: 513})
-> scenario_validate(input_overrides={lidar_min_points: 513},
redact_local_paths=true) -> scenario_last_report(json, redact_local_paths=true)
-> scenario_last_report(markdown, redact_local_paths=true) ->
extension_capture_logs(WARN) -> extension_capture_logs(ERROR) ->
simulation_get_status`.

## Evidence

- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`, 152 tools,
  `source_newer_than_import=false`.
- Plan key args for `read_lidar_point_cloud`: `min_points=513`,
  `max_points=512`, `frames_to_wait=180`, `fail_on_warning=true`.
- Scenario status: failed as expected; 25 passed, 1 failed, 5 skipped.
- Failed step: `read_lidar_point_cloud`, phase `act`, attempts 3/3,
  `error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`.
- Lidar data: `num_points=512`, backend
  `isaacsim.sensors.experimental.rtx.LidarSensor`, `truncated=true`.
- Diagnostics: `reason=point_count_below_minimum`, `min_points=513`,
  `num_points=512`, `readback_paths_attempted=[cached_lidar_sensor]`,
  `fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud,
  extension_capture_logs]`.
- Root `diagnostic_next_actions` included the final failed step plus retry
  attempts 1, 2, and 3, each carrying the lidar error code and fallback order.
- Cleanup ran; final `simulation_get_status` reported stopped at time 0.
- Logs after clear: WARN count 4, ERROR count 0. WARN entries were known
  Hydratexture release / USD stage close refcount warnings.

## Unit Guard

- `tests/unit/test_scenario_integration.py::test_scenario_runner_reports_diagnostic_actions_for_exhausted_lidar_retry`
  now locks the final-failed retry shape: the top-level
  `diagnostic_next_actions` queue includes the final failed step plus attempts
  1, 2, and 3, and each retry failure keeps machine-readable
  `diagnostic_next_actions` with point-count diagnostics and fallback order.

## Public Hygiene

No live worker IDs, process IDs, local absolute paths, raw Kit log paths, raw
capture paths, secrets, or unredacted generated catalog paths are recorded here.
