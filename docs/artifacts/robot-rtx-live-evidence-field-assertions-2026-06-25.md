# Robot + RTX Live Evidence Field Assertions - 2026-06-25

Purpose: verify that `scripts/probe_mcp_surface.py` can guard the Robot + RTX
golden workflow with exact live evidence field assertions for lidar, viewport
framing, visual capture, and cleanup preservation.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`
- Full live field probe command:
  `scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --scenario-validate-live --expect-live-status passed --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-live-cleanup-failures 0 --expect-live-evidence-kind rtx_lidar_point_cloud --expect-live-evidence-kind viewport_framing --expect-live-evidence-kind visual_capture --expect-live-evidence-field read_lidar_point_cloud:status=passed --expect-live-evidence-field read_lidar_point_cloud:num_points=512 --expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false --expect-live-evidence-field capture_visible_result:passed=true`
- Live assertions:
  - `--expect-live-status passed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind rtx_lidar_point_cloud`
  - `--expect-live-evidence-kind viewport_framing`
  - `--expect-live-evidence-kind visual_capture`
  - `--expect-live-evidence-field read_lidar_point_cloud:status=passed`
  - `--expect-live-evidence-field read_lidar_point_cloud:num_points=512`
  - `--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false`
  - `--expect-live-evidence-field capture_visible_result:passed=true`

Result:

- Exit code: `0`
- MCP server: `isaacsim-validation-mcp v1.27.0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- Robot probe contract: `ROBOT_PROBE_UNKNOWN_PROFILE` with fallback order present
- `kit_app_start`: `ready`
- `simulation_get_status`: `passed`, `is_playing=false`, `current_time=0.0`
- Plan/dry-run: default required fields present; scratch stage required; log
  capture recommended
- Automatic cleanup: `__fallback_cleanup_reset`, `timeoutSeconds=30.0`
- Live summary: `passed`
- Steps: `32` passed, `0` failed, `0` skipped
- Cleanup failed steps: `0`
- Failure summary count: `0`
- Diagnostic next-action count: `0`
- WARN+ log capture (stop_after_capture=true): `passed`

Evidence rows asserted:

- `read_lidar_point_cloud`: `status=passed`, attempts `1/3`,
  `num_points=512`, backend `isaacsim.sensors.experimental.rtx.LidarSensor`,
  `frames_waited=180`, `warning=null`, `truncated=true`
- `frame_robot_and_sensors`: `status=passed`, attempts `1/1`,
  viewport `Viewport`, `prim_count=4`, `bbox_empty=false`
- `capture_visible_result`: `status=passed`, attempts `1/1`,
  `sha256=4efcb29a45dbb71d6050d7b12e17580fadd58e9f3a2876a48ed5b371707649fa`,
  `width=1280`, `height=720`, `warmup_frames_used=8`, `passed=true`,
  `pixel_mean_average=145.60244285300928`,
  `pixel_variance_average=1107.7352252791916`, `failure_codes=[]`

Public hygiene:

- The artifact records only public scenario/tool names and compact redacted
  evidence fields.
- The capture path was redacted in the live Markdown report as
  `<validation-api-capture>/capture_23afbbb75a31.png`.
- No local absolute paths, process IDs, worker/thread IDs, or secrets are
  included in this artifact.

Refresh run after full command pin:

- Command: the full live field probe command above.
- Exit code: `0`
- Live summary: `passed`
- Steps: `32` passed, `0` failed, `0` skipped
- Cleanup failed steps: `0`
- Evidence kinds asserted: `rtx_lidar_point_cloud`, `viewport_framing`,
  `visual_capture`
- `read_lidar_point_cloud`: `status=passed`, attempts `1/3`,
  `num_points=512`, backend `isaacsim.sensors.experimental.rtx.LidarSensor`,
  `frames_waited=180`, `warning=null`, `truncated=true`
- `frame_robot_and_sensors`: `bbox_empty=false`, viewport `Viewport`,
  `prim_count=4`
- `capture_visible_result`: `passed=true`,
  `sha256=e8e18c92b52ba8a19b4cc4d2df0f974b7fdf63f797423f2adbeec20e658a13c4`,
  `width=1280`, `height=720`, `warmup_frames_used=8`,
  `pixel_mean_average=145.59828956886574`,
  `pixel_variance_average=1109.1388791795941`, `failure_codes=[]`
- WARN+ log capture (stop_after_capture=true): `passed`
- Snapshot: `tmp_mcp_surface.json`
