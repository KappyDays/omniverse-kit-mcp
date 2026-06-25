# Robot RTX Lidar Controlled Failure Diagnostics - 2026-06-25

## Purpose

Refresh the live evidence for the Robot + RTX golden workflow controlled
failure path. The run verifies that the `lidar_min_points=513` override reaches
both `scenario_plan` and `scenario_validate(dry_run=true)` before the mutating
run, then proves the live scenario fails only at the bounded RTX lidar threshold.

## Live Sequence

Workspace-local MCP stdio entry from `workspaces/isaac/instance-1`:

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
scenario_plan(input_overrides={lidar_min_points: 513}) ->
scenario_validate(dry_run=true, input_overrides={lidar_min_points: 513}) ->
extension_clear_logs -> scenario_validate(input_overrides={lidar_min_points:
513}, report_format=json) -> scenario_last_report(markdown,
redact_local_paths=true) -> extension_capture_logs(WARN) ->
extension_capture_logs(ERROR) -> simulation_get_status`.

The scenario is `smoke/robot_rtx_sensor_golden_workflow.yaml`. It is a scratch
smoke run that starts with `stage_new`, performs cleanup, and does not preserve
the temporary robot/sensor stage content as a user scene.

## Evidence

- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`, 152 tools,
  `source_newer_than_import=false`,
  `restart_required_for_latest_mcp_code=false`.
- Startup/status: `kit_app_start` returned `status=started`; pre-run
  `simulation_get_status` passed with `is_playing=false`, `is_stopped=true`.
- Plan and dry-run validate:
  - `scenario_id=robot_rtx_sensor_golden_workflow`
  - `total_steps=32`
  - `scratch_stage_required=true`
  - `log_capture_recommended=true`
  - retry step `read_lidar_point_cloud`
  - retry `key_args.min_points=513`, `max_points=512`,
    `frames_to_wait=180`, `fail_on_warning=true`
- Mutating validation result:
  - status: failed as expected
  - steps: 25 passed, 1 failed, 5 skipped
  - failed step: `read_lidar_point_cloud`
  - error code: `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
  - attempts: 3/3
  - cleanup failure count: 0
- Lidar diagnostics:
  - `num_points=512`
  - `min_points=513`
  - backend: `isaacsim.sensors.experimental.rtx.LidarSensor`
  - `diagnostics.reason=point_count_below_minimum`
  - `diagnostics.fallback_tool_order=[simulation_step,
    sensor_lidar_get_point_cloud, extension_capture_logs]`
  - `diagnostics.readback_paths_attempted=[cached_lidar_sensor]`
  - `diagnostics.cached_lidar_instance=true`
- Redacted Markdown report contained:
  - `Failure Summary`
  - `Data Summary Highlights`
  - `Retry Failures` for attempts 1, 2, and 3
  - `Diagnostic Next Actions` for the final failed step plus each retry attempt
  - flat diagnostic keys `diagnostics.num_points=512` and
    `diagnostics.min_points=513`
- Post-run status: `simulation_get_status` passed with `is_playing=false`,
  `is_stopped=true`, `current_time=0.0`.
- Logs after clear/capture:
  - WARN entries: 8
  - ERROR entries: 0

## Public Safety

This artifact records only relative workspace/scenario paths, aggregate counts,
tool names, error codes, and redacted report facts. It excludes local absolute
paths, process IDs, worker/thread IDs, raw log paths, secrets, generated cache
paths, and unredacted screenshot/capture paths.
