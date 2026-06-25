# Probe Assertion Durable Docs E2E

Date: 2026-06-25

Scope: parent-side, workspace-local stdio validation that the durable docs and
scenario authoring guide describe runnable Robot + RTX and official asset proof
orders without requiring first-class live tools in the parent host.

## Commands

- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_verify_live.yaml --scenario-validate-dry-run --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true`

## Results

- Robot + RTX dry-run: passed. `scenario_id=robot_rtx_sensor_golden_workflow`,
  `total_steps=32`, `scratch_stage_required=true`,
  `log_capture_recommended=true`, fallback cleanup
  `__fallback_cleanup_reset.timeoutSeconds=30`, and lidar retry key args
  included `min_points=1`, `max_points=512`, `frames_to_wait=180`, and
  `fail_on_warning=true`.
- Official asset verify-live dry-run: passed.
  `scenario_id=official_asset_verify_live`, `total_steps=5`,
  `diagnostic_steps`, `evidence_steps`, and `stage_mutation_steps` were present,
  with `scratch_stage_required=true` and the 9-tool live wrapper order.
- Official asset read-only catalog diagnostics plan: passed.
  `scenario_id=official_asset_catalog_diagnostics`, `total_steps=5`,
  `diagnostic_steps` and `stage_mutation_steps` were present, with
  `scratch_stage_required=false` and the 8-tool read-only wrapper order.

## Public Boundary

- No mutating live scenario was run for this artifact.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, raw Kit
  logs, or capture paths are included.
- The ignored `tmp_mcp_surface.json` snapshot was produced locally and is not a
  public artifact.
