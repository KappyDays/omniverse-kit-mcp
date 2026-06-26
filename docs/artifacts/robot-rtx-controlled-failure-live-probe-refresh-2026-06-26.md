# Robot RTX Controlled Failure Live Probe Refresh - 2026-06-26

## Scope

This artifact records a workspace-local Isaac Sim live MCP smoke for the
controlled-failure branch of `smoke/robot_rtx_sensor_golden_workflow.yaml`
after the probe assertion path was tightened for dotted evidence and diagnostic
fields. The workflow uses the scenario scratch/test-stage route and cleanup
gates. The expected outcome is scenario status `failed`.

## Command

`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --scenario-validate-live --input-overrides-json '{"lidar_min_points":513}' --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --expect-retry-key-arg read_lidar_point_cloud:min_points=513 --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-live-status failed --expect-live-cleanup-failures 0 --expect-live-evidence-kind rtx_lidar_point_cloud --expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS --expect-live-diagnostic-next-actions-min 1 --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513 --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.fallback_tool_order='["simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]'`

## Result

- Exit code: `0`.
- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan and dry-run shape: `total_steps=32`, `live_validation_step_count=9`,
  `scratch_stage_required=true`, `log_capture_recommended=true`,
  `play_state_missing_count=0`, `requires_play_count=2`,
  `simulation_state_step_count=2`, `timeline_control_step_count=7`, and
  fallback cleanup `__fallback_cleanup_reset.timeoutSeconds=30`.
- Override gate: `read_lidar_point_cloud` kept `min_points=513`,
  `max_points=512`, `max_attempts=3`, `frames_to_wait=180`, and
  `fail_on_warning=true`.
- Live scenario status: `failed` as expected, with `passed_steps=25`,
  `failed_steps=1`, `skipped_steps=5`, `continued_steps=0`,
  `fatal_failed_steps=1`, and `cleanup_failed_steps=0`.
- Expected failure step: `read_lidar_point_cloud` reported
  `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`.
- Diagnostic next-action count was `4`: the final failed step plus three retry
  failure rows all kept `diagnostics.reason=point_count_below_minimum`,
  `diagnostics.num_points=512`, `diagnostics.min_points=513`, and fallback
  order `simulation_step -> sensor_lidar_get_point_cloud -> extension_capture_logs`.
- Evidence boundary: evidence kind `rtx_lidar_point_cloud`, status `failed`,
  attempts `3/3`, `retry_failure_count=3`, `error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`,
  `num_points=512`, `frames_waited=180`, `truncated=true`, cached-lidar
  readback diagnostics, and no visual-capture evidence because assert steps
  were skipped after the controlled act-phase failure.
- Final log close gate passed with `data.capture_stop_requested=true`,
  `data.capture_stop_completed=true`, `data.capture_stop_timed_out=false`, and
  `data.capture_running=false`.
- The generated `tmp_mcp_surface.json` snapshot remained ignored and was not
  promoted as public evidence.

## Public Boundary

No raw local absolute paths, local capture paths, worker/thread IDs, process
IDs, secrets, raw Kit logs, generated catalog records, generated verification
JSONL, Python object reprs, or private workspace state are included.
