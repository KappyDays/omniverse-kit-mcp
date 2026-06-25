# Robot RTX Controlled Failure Diagnostic Field Assertion - 2026-06-25

Purpose: verify that `scripts/probe_mcp_surface.py` can assert the exact
diagnostic reason, minimum-point override, and fallback route for the Robot +
RTX controlled lidar failure, not only the failure step, error code, and
diagnostic next-action count.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`
- Input override: `lidar_min_points=513`
- Full live diagnostic probe command:
  `scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --scenario-validate-live --input-overrides-json '{"lidar_min_points":513}' --expect-live-status failed --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-retry-key-arg read_lidar_point_cloud:min_points=513 --expect-live-cleanup-failures 0 --expect-live-evidence-kind rtx_lidar_point_cloud --expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS --expect-live-diagnostic-next-actions-min 1 --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513 --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.fallback_tool_order='["simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]'`
- Live assertions:
  - `--expect-live-status failed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind rtx_lidar_point_cloud`
  - `--expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
  - `--expect-live-diagnostic-next-actions-min 1`
  - `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`
  - `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513`
  - `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.fallback_tool_order='["simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]'`

Result:

- Exit code: `0`
- MCP server: `isaacsim-validation-mcp v1.27.0`
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
- WARN+ log capture (stop_after_capture=true): `passed`

Refresh run after full command pin:

- Exit code: `0`
- Live summary: `failed` as expected
- Steps: `25` passed, `1` failed, `5` skipped
- Failed step: `read_lidar_point_cloud`
- Error code: `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
- Evidence kind asserted: `rtx_lidar_point_cloud`
- Diagnostic field asserted:
  `read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`
- Diagnostic field asserted:
  `read_lidar_point_cloud:diagnostics.min_points=513`
- Diagnostic field asserted:
  `read_lidar_point_cloud:diagnostics.fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud, extension_capture_logs]`
- Retry key arg asserted: `read_lidar_point_cloud:min_points=513`
- Cleanup failed steps: `0`
- WARN+ log capture (stop_after_capture=true): `passed`
- Snapshot path printed by the probe: `tmp_mcp_surface.json`

Diagnostic fields asserted:

- `diagnostics.reason=point_count_below_minimum`
- `diagnostics.num_points=512`
- `diagnostics.min_points=513`
- `diagnostics.fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud, extension_capture_logs]`
- `diagnostics.readback_paths_attempted=[cached_lidar_sensor]`
- `diagnostics.cached_lidar_instance=true`

2026-06-26 fallback-route unit refresh:

- `tests/unit/test_sensor_ext_tools.py::test_lidar_empty_fallback_tool_order_matches_empty_readback_triage_route`
  directly guards the validation-api empty-readback fallback helper route:
  `simulation_get_status -> simulation_step -> sensor_lidar_get_point_cloud -> extension_capture_logs`.
- `tests/unit/test_sensor_ext_tools.py::test_lidar_readback_diagnostics_suggests_retry_for_empty_scan_buffer`
  confirms empty-readback diagnostics use that helper. The controlled
  `point_count_below_minimum` probe assertion above remains the MCP/module-level
  route: `simulation_step -> sensor_lidar_get_point_cloud -> extension_capture_logs`.
- Targeted run: `2 passed`.

2026-06-26 post-stop-guard refresh:

- Exit code: `0`
- Live summary: `failed` as expected
- Steps: `25` passed, `1` failed, `5` skipped
- Failed step: `read_lidar_point_cloud`
- Error code: `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
- Retry key arg asserted: `read_lidar_point_cloud:min_points=513`
- Evidence kind asserted: `rtx_lidar_point_cloud`
- Diagnostic next action count: `4`
- Diagnostic field asserted:
  `read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`
- Diagnostic field asserted:
  `read_lidar_point_cloud:diagnostics.min_points=513`
- Diagnostic field asserted:
  `read_lidar_point_cloud:diagnostics.fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud, extension_capture_logs]`
- Diagnostic values observed:
  - `diagnostics.num_points=512`
  - `diagnostics.min_points=513`
  - `diagnostics.fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud, extension_capture_logs]`
  - `diagnostics.readback_paths_attempted=[cached_lidar_sensor]`
  - `diagnostics.cached_lidar_instance=true`
- Cleanup failed steps: `0`
- Probe `extension_capture_logs WARN+` summary:
  - `data.capture_running=false`
  - `data.capture_stop_requested=true`
  - `data.capture_stop_completed=true`
  - `data.capture_stop_timed_out=false`
  - `data.capture_stop_timeout_s=1.0`
- Snapshot path printed by the probe: `tmp_mcp_surface.json`

Public hygiene:

- This artifact records relative scenario/workspace facts, aggregate counts,
  tool names, error codes, and redacted report facts only.
- No local absolute paths, process IDs, worker/thread IDs, raw log paths,
  secrets, generated cache paths, or unredacted capture paths are included.
