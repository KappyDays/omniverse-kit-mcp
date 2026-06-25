# Robot RTX Controlled-Failure Close-Gate Live Refresh

Date: 2026-06-26

Scope: workspace-local Isaac Sim MCP live validation of the controlled-failure
path for `smoke/robot_rtx_sensor_golden_workflow.yaml` after
`probe_mcp_surface.py` started hard-gating final log-capture close metadata.
The run intentionally overrides `lidar_min_points=513` on the documented
scratch/test-stage workflow so the RTX lidar proof fails at the expected
diagnostic boundary while cleanup and log close behavior remain verified.

## Command

- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --scenario-validate-live --input-overrides-json '{"lidar_min_points":513}' --expect-live-status failed --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-retry-key-arg read_lidar_point_cloud:min_points=513 --expect-live-cleanup-failures 0 --expect-live-evidence-kind rtx_lidar_point_cloud --expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS --expect-live-diagnostic-next-actions-min 1 --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513`

## Result

- Exit code: 0.
- Runtime gate was fresh: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan and dry-run both reported `scenario_id=robot_rtx_sensor_golden_workflow`,
  `total_steps=32`, `scratch_stage_required=true`,
  `log_capture_recommended=true`, `requires_play_count=2`,
  `simulation_state_step_count=2`, `timeline_control_step_count=7`, and the
  9-tool live wrapper order.
- The plan preserved `__fallback_cleanup_reset.timeoutSeconds=30`.
- The lidar retry gate preserved `min_points=513`, `max_points=512`,
  `frames_to_wait=180`, and `fail_on_warning=true`.
- Live validation reported `status=failed` as expected with `passed_steps=25`,
  `failed_steps=1`, `skipped_steps=5`, `continued_steps=0`,
  `fatal_failed_steps=1`, and `cleanup_failed_steps=0`.
- The expected failure was asserted on `read_lidar_point_cloud` with
  `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`.
- Required diagnostic assertions passed:
  - `diagnostic_next_action_count>=1` with observed count `4`
  - `read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`
  - `read_lidar_point_cloud:diagnostics.min_points=513`
- Required evidence assertions passed:
  - Evidence kind `rtx_lidar_point_cloud`
  - Observed `read_lidar_point_cloud.num_points=512`
  - Observed `read_lidar_point_cloud.diagnostics.min_points=513`
  - Observed `read_lidar_point_cloud.diagnostics.fallback_tool_order=[simulation_step, sensor_lidar_get_point_cloud, extension_capture_logs]`
  - Observed `read_lidar_point_cloud.diagnostics.readback_paths_attempted=[cached_lidar_sensor]`
  - Observed `read_lidar_point_cloud.diagnostics.cached_lidar_instance=true`
- Final `extension_capture_logs(level=WARN, stop_after_capture=true)` passed the
  close gate with:
  - `data.capture_running=false`
  - `data.capture_stop_requested=true`
  - `data.capture_stop_completed=true`
  - `data.capture_stop_timed_out=false`
  - `data.capture_stop_timeout_s=1.0`
- The generated `tmp_mcp_surface.json` snapshot is ignored and was not promoted
  as public evidence.

## Public Boundary

No raw local absolute paths, process IDs, worker/thread IDs, secrets, raw Kit
logs, local capture paths, or generated catalog records are included. The raw
redacted Markdown report included a validation capture token; it is omitted here
while preserving stable error-code, diagnostic, evidence, cleanup, and close-gate
facts.
