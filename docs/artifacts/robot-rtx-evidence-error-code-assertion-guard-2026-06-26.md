# Robot RTX Evidence Error Code Assertion Guard - 2026-06-26

## Scope

This artifact records the Robot + RTX failed evidence-row `error_code` guard.
It started as a static probe summary guard and was refreshed with a
workspace-local live controlled-failure probe.

## Evidence

- `tests/unit/test_standalone_scripts.py::test_mcp_probe_live_summary_keeps_public_robot_rtx_evidence_fields`
  now proves Robot + RTX public evidence summaries preserve
  `read_lidar_point_cloud:error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
  and `capture_visible_result:error_code=VIEWPORT_CAPTURE_ASSERT_FAILED`.
- `docs/mcp-usage-guide.md`, `docs/invariants/scenario-validation.md`, and
  `scenarios/CLAUDE.md` keep `--expect-live-failure-step-error` as the primary
  terminal failure contract; `--expect-live-evidence-field <step>:error_code=...`
  is documented only as an optional additional assertion when present.
- Workspace-local live refresh command shape:
  `scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1
  --runtime-info --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml
  --scenario-validate-dry-run --scenario-validate-live
  --input-overrides-json {"lidar_min_points":513}
  --expect-live-status failed
  --expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS
  --expect-live-evidence-field read_lidar_point_cloud:error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS
  --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum
  --expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513`.
- Live refresh exit code: `0`.
- Runtime/profile checks passed: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan/dry-run gate passed with `total_steps=32`,
  `scratch_stage_required=true`, `log_capture_recommended=true`, and the
  expected nine live-validation tools.
- Live result matched the controlled failure contract:
  `status=failed`, `passed_steps=25`, `failed_steps=1`, `skipped_steps=5`,
  `cleanup_failed_steps=0`, and failure step
  `read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`.
- Live evidence row contained `evidence_kind=rtx_lidar_point_cloud`,
  `status=failed`, `error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`,
  `num_points=512`, `frames_waited=180`, and `truncated=true`.
- Diagnostic next actions kept `diagnostics.reason=point_count_below_minimum`,
  `diagnostics.min_points=513`, and fallback order
  `simulation_step -> sensor_lidar_get_point_cloud -> extension_capture_logs`.
- Final log close metadata passed:
  `capture_stop_requested=true`, `capture_stop_completed=true`,
  `capture_stop_timed_out=false`, and `capture_running=false`.

## Public Boundary

This artifact records only stable public-safe fields. It omits raw local absolute paths,
worker/thread IDs, process IDs, secrets, temp log paths, generated catalog JSON,
generated verification JSONL, raw Kit logs, and raw Markdown report content.
