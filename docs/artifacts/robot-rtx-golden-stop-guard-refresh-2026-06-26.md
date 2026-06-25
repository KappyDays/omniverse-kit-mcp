# Robot RTX Golden Stop Guard Refresh - 2026-06-26

Purpose: re-run the Robot/RTX Golden Workflow after hardening
`extension_capture_logs(..., stop_after_capture=true)` so the highest-priority
live proof still passes with the documented evidence assertions and bounded log
capture close path.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`
- Required live wrapper tools:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `scenario_plan`, `scenario_validate`, `extension_clear_logs`,
  `scenario_validate`, `scenario_last_report`, `extension_capture_logs`
- Probe assertions:
  - `--expect-live-status passed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind rtx_lidar_point_cloud`
  - `--expect-live-evidence-kind viewport_framing`
  - `--expect-live-evidence-kind visual_capture`
  - `--expect-live-evidence-field read_lidar_point_cloud:status=passed`
  - `--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1`
  - `--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false`
  - `--expect-live-evidence-field capture_visible_result:passed=true`

Result:

- Exit code: `0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- Plan and dry-run:
  - total steps: `32`
  - live validation step count: `9`
  - scratch stage required: `true`
  - log capture recommended: `true`
  - automatic cleanup: `__fallback_cleanup_reset`, timeout `30`
  - retry step: `read_lidar_point_cloud`, `min_points=1`,
    `max_points=512`, `frames_to_wait=180`, `fail_on_warning=true`
- Live summary:
  - status: `passed`
  - passed/failed/skipped: `32` / `0` / `0`
  - cleanup failed steps: `0`
  - diagnostic next actions: `0`
- Evidence:
  - `read_lidar_point_cloud`: status `passed`, attempts `1/3`,
    `num_points=512`, backend
    `isaacsim.sensors.experimental.rtx.LidarSensor`, `frames_waited=180`,
    warning `null`, `truncated=true`
  - `frame_robot_and_sensors`: status `passed`, `prim_count=4`,
    `bbox_empty=false`
  - `capture_visible_result`: status `passed`, image `1280x720`,
    `warmup_frames_used=8`, `pixel_mean_average=145.60176866319446`,
    `pixel_variance_average=1107.9427648625533`,
    `failure_codes=[]`
- Redacted artifact path in markdown report:
  `<validation-api-capture>/capture_4bb648ce6e1f.png`
- Final WARN+ log capture: `passed`

Stop guard check:

- Direct post-run log close metadata:
  - `ok=true`
  - `capture_running=false`
  - `capture_stop_requested=true`
  - `capture_stop_completed=true`
  - `capture_stop_timed_out=false`
  - `capture_stop_timeout_s=1.0`

Public hygiene:

- This artifact records public scenario/tool names and redacted evidence fields
  only.
- No local absolute paths, process IDs, raw Kit logs, worker/thread IDs, or
  secrets are included.
