# Robot RTX Golden Close-Gate Live Refresh

Date: 2026-06-26

Scope: workspace-local Isaac Sim MCP live validation of
`smoke/robot_rtx_sensor_golden_workflow.yaml` after `probe_mcp_surface.py`
started hard-gating final log-capture close metadata. This scenario uses the
documented scratch/test-stage boundary and cleanup expectations for bounded
Robot + RTX proof.

## Command

- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --scenario-validate-live --expect-live-status passed --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-live-cleanup-failures 0 --expect-live-evidence-kind rtx_lidar_point_cloud --expect-live-evidence-kind viewport_framing --expect-live-evidence-kind visual_capture --expect-live-evidence-field read_lidar_point_cloud:status=passed --expect-live-evidence-field-min read_lidar_point_cloud:num_points=1 --expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false --expect-live-evidence-field capture_visible_result:passed=true`

## Result

- Exit code: 0.
- A follow-up rerun after
  `docs/artifacts/workspace-live-preflight-current-gate-2026-06-26.md` also
  exited 0 with the same canonical command and live assertion gates.
- Runtime gate was fresh: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan and dry-run both reported `scenario_id=robot_rtx_sensor_golden_workflow`,
  `total_steps=32`, `scratch_stage_required=true`,
  `log_capture_recommended=true`, `requires_play_count=2`,
  `simulation_state_step_count=2`, `timeline_control_step_count=7`, and the
  9-tool live wrapper order.
- The plan preserved `__fallback_cleanup_reset.timeoutSeconds=30`.
- The lidar retry gate preserved `min_points=1`, `max_points=512`,
  `frames_to_wait=180`, and `fail_on_warning=true`.
- Live validation passed with `passed_steps=32`, `failed_steps=0`,
  `continued_steps=0`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- The live status gate was asserted with `--expect-live-status passed`.
- Required evidence assertions passed:
  - `read_lidar_point_cloud:status=passed`
  - `read_lidar_point_cloud:num_points>=1` with observed `num_points=512`
  - `frame_robot_and_sensors:bbox_empty=false`
  - `capture_visible_result:passed=true`
- Evidence kinds were `rtx_lidar_point_cloud`, `viewport_framing`, and
  `visual_capture`.
- Visual capture compact proof preserved `width=1280`, `height=720`,
  `warmup_frames_used=8`, `pixel_mean_average=145.69952510127314`,
  `pixel_variance_average=1101.8297503731858`, and
  `sha256=18b1ba43fc03509e09279209869a8f2e6c294564652790e1cb999e7bbda0f5aa`.
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
while preserving stable SHA256 and pixel statistics.
