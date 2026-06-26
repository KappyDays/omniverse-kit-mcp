# Robot RTX Success Live Probe Refresh - 2026-06-26

## Scope

This artifact records a workspace-local Isaac Sim live MCP smoke for
`smoke/robot_rtx_sensor_golden_workflow.yaml` after the probe assertion path was
tightened for dotted evidence and diagnostic fields. The workflow uses the
scenario scratch/test-stage route and cleanup gates.

## Command

`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --scenario-validate-live --expect-live-status passed --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-live-cleanup-failures 0 --expect-live-evidence-kind rtx_lidar_point_cloud --expect-live-evidence-kind viewport_framing --expect-live-evidence-kind visual_capture --expect-live-evidence-field read_lidar_point_cloud:status=passed --expect-live-evidence-field-min read_lidar_point_cloud:num_points=1 --expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false --expect-live-evidence-field capture_visible_result:passed=true`

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
- Retry gate: `read_lidar_point_cloud` kept `max_attempts=3`,
  `frames_to_wait=180`, `min_points=1`, `max_points=512`, and
  `fail_on_warning=true`.
- Live scenario status: `passed` with `passed_steps=32`, `failed_steps=0`,
  `continued_steps=0`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- Evidence kinds were `rtx_lidar_point_cloud`, `viewport_framing`, and
  `visual_capture`.
- `read_lidar_point_cloud` passed on attempt `1/3` with `num_points=512`,
  `frames_waited=180`, `truncated=true`, and cached-lidar readback diagnostics.
- `frame_robot_and_sensors` passed with `bbox_empty=false`, `prim_count=4`,
  and viewport distance around `12.50`.
- `capture_visible_result` passed with `width=1280`, `height=720`,
  `warmup_frames_used=8`, `pixel_mean_average=145.69`,
  `pixel_variance_average=1102.24`, and SHA256
  `86f3ee956c5d89f82f467fe7a0d1584285976ef2eededbbdd2c7f2ece4013b80`.
- Final log close gate passed with `data.capture_stop_requested=true`,
  `data.capture_stop_completed=true`, `data.capture_stop_timed_out=false`, and
  `data.capture_running=false`.
- The generated `tmp_mcp_surface.json` snapshot remained ignored and was not
  promoted as public evidence.

## Public Boundary

No raw local absolute paths, local capture paths, worker/thread IDs, process
IDs, secrets, raw Kit logs, generated catalog records, generated verification
JSONL, Python object reprs, or private workspace state are included. The live
report was requested with `redact_local_paths=true`; only the public-safe
`<validation-api-capture>` placeholder and compact numeric evidence are
recorded.
