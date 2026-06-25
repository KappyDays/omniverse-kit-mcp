# Robot RTX Default Wrapper Refresh - 2026-06-25

## Scope

Re-verified the default `smoke/robot_rtx_sensor_golden_workflow.yaml` through
the workspace-local Isaac Sim MCP live wrapper after adding bounded cleanup and
expected live status checks. This is the default success proof paired with the
controlled `lidar_min_points=513` failure proof.

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
  - retry key args: `read_lidar_point_cloud.min_points=1`,
    `max_points=512`, `frames_to_wait=180`, `fail_on_warning=true`
- Mutating live validation:
  - wrapper exit: success because live status matched expected `passed`
  - status: `passed`
  - duration: about `14.5s`
  - steps: `32 passed`, `0 failed`, `0 skipped`
  - diagnostic next actions: `0`
  - cleanup failures: `0`
  - fallback cleanup reset: `passed`, about `35ms`
- RTX lidar evidence:
  - `num_points=512`
  - `frames_waited=180`
  - `attempts=1/3`
  - backend: `isaacsim.sensors.experimental.rtx.LidarSensor`
  - `diagnostics.readback_paths_attempted=[cached_lidar_sensor]`
  - warning: `null`
  - `truncated=true`
- Viewport evidence:
  - evidence kinds: `rtx_lidar_point_cloud`, `viewport_framing`,
    `visual_capture`
  - capture: `<validation-api-capture>/capture_8fcab41356f3.png`
  - SHA-256: `c6b3859cb85d4f88ba7d8e33a8bb0f3002badab27865826c53cfcb4a8b343eaa`
  - size: `1280x720`
  - `pixel_mean_average=145.70699435763888`
  - `pixel_variance_average=1101.4757245159337`
  - visual inspection: the PNG shows NovaCarter centered on the NVIDIA grid,
    with the top RTX lidar visible and four gray lidar target cubes around the
    robot.
- Post-run log capture:
  `extension_capture_logs(level=WARN, stop_after_capture=true)` passed.

## Public Safety

This artifact records relative scenario/workspace facts, aggregate counts,
tool names, error codes, hashes, pixel statistics, and redacted capture facts
only. It omits host-local absolute paths, process IDs, worker/thread IDs, raw
log paths, secrets, generated cache paths, and unredacted capture paths.
