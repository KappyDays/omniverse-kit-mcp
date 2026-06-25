# Robot RTX Controlled Failure Step/Error Assertion — 2026-06-25

Purpose: verify that `scripts/probe_mcp_surface.py` can assert the exact
controlled-failure step and error code for the Robot + RTX lidar workflow.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`
- Input override: `lidar_min_points=513`
- Added live expectations:
  - `--expect-live-status failed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind rtx_lidar_point_cloud`
  - `--expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`

Result:

- Exit code: `0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- Plan/dry-run: required Robot + RTX plan fields present
- Retry key args: `read_lidar_point_cloud.min_points=513`,
  `max_points=512`, `frames_to_wait=180`, `fail_on_warning=true`
- Live summary: `failed` as expected
- Steps: `25` passed, `1` failed, `5` skipped
- Failed step: `read_lidar_point_cloud`
- Error code: `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
- Attempts: `3/3`
- Cleanup failed steps: `0`
- Evidence kinds:
  - `rtx_lidar_point_cloud`
- Diagnostic next action count: `4`
- WARN+ log capture: `passed`

Diagnostic shape:

- `diagnostics.reason=point_count_below_minimum`
- `diagnostics.num_points=512`
- `diagnostics.min_points=513`
- `diagnostics.fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud, extension_capture_logs]`
- `diagnostics.cached_lidar_instance=True`
- `diagnostics.readback_paths_attempted=[cached_lidar_sensor]`

Public hygiene:

- This artifact records relative scenario/workspace facts, aggregate counts,
  tool names, error codes, and redacted report facts only.
- No local absolute paths, process IDs, worker/thread IDs, raw log paths,
  secrets, generated cache paths, or unredacted capture paths are included.
