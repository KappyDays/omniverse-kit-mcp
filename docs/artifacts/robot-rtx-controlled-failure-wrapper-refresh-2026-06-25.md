# Robot RTX Controlled Failure Wrapper Refresh - 2026-06-25

## Scope

Re-verified the workspace-local MCP live wrapper after adding:

- `--expect-automatic-cleanup-timeout __fallback_cleanup_reset=30`
- `--expect-live-status failed`

The run used `smoke/robot_rtx_sensor_golden_workflow.yaml` with
`input_overrides={"lidar_min_points": 513}`. This is an intentional scratch
stage controlled-failure proof, not a default success proof.

## Evidence

- MCP runtime: `tool_profile=full`, `app_profile=isaac-sim`, `tool_count=152`,
  source/import freshness clean.
- Kit/status preflight: `kit_app_start` returned `status=ready`;
  `simulation_get_status` passed with `is_playing=false`, `current_time=0.0`.
- Plan and dry-run:
  - `scenario_id=robot_rtx_sensor_golden_workflow`
  - `total_steps=32`
  - `scratch_stage_required=true`
  - `log_capture_recommended=true`
  - automatic cleanup: `__fallback_cleanup_reset`, `timeoutSeconds=30.0`
  - retry key args reached the override:
    `read_lidar_point_cloud.min_points=513`, `max_points=512`,
    `frames_to_wait=180`, `fail_on_warning=true`
- Mutating live validation:
  - wrapper exit: success because live status matched expected `failed`
  - status: `failed`
  - duration: about `20.2s`
  - steps: `25 passed`, `1 failed`, `5 skipped`
  - failed step: `read_lidar_point_cloud`
  - error code: `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
  - attempts: `3/3`
  - cleanup failures: `0`
  - fallback cleanup reset: `passed`, about `39ms`
- Diagnostics:
  - `num_points=512`
  - `min_points=513`
  - `diagnostics.reason=point_count_below_minimum`
  - `diagnostics.fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud, extension_capture_logs]`
  - `diagnostics.readback_paths_attempted=[cached_lidar_sensor]`
- Post-run log capture:
  `extension_capture_logs(level=WARN, stop_after_capture=true)` passed.

## Public Safety

This artifact records relative scenario/workspace facts, aggregate counts,
tool names, error codes, and redacted report facts only. It omits local absolute
paths, process IDs, worker/thread IDs, raw log paths, secrets, generated cache
paths, and unredacted capture paths.
