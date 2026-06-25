# Probe Assertion Durable Docs E2E Refresh

Date: 2026-06-26

Scope: parent-side, workspace-local stdio validation that the durable docs and
scenario authoring guide still describe runnable Robot + RTX and official asset
proof orders after the probe assertion and log-capture close guard updates. This
artifact is dry-run only; it did not mutate a stage.

## Commands

- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_verify_live.yaml --scenario-validate-dry-run --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --scenario-validate-dry-run --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true`

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
- Official asset read-only catalog diagnostics plan + dry-run: passed.
  `scenario_id=official_asset_catalog_diagnostics`, `total_steps=5`,
  `diagnostic_steps` and `stage_mutation_steps` were present, with
  `scratch_stage_required=false` and the 8-tool read-only wrapper order.
- Runtime gate fields were fresh: `tool_profile=full`,
  `app_profile=isaac-sim`, `tool_count=152`,
  `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- The generated `tmp_mcp_surface.json` snapshot is ignored and was not promoted
  as public evidence.

## Follow-up live assertion artifacts

- Robot + RTX success exact fields:
  `docs/artifacts/robot-rtx-live-evidence-field-assertions-2026-06-25.md`
- Robot + RTX success numeric threshold:
  `docs/artifacts/robot-rtx-live-evidence-threshold-assertions-2026-06-25.md`
- Robot + RTX controlled failure diagnostics:
  `docs/artifacts/robot-rtx-controlled-failure-diagnostic-field-assertion-2026-06-25.md`
- Official asset verify fields:
  `docs/artifacts/official-asset-live-evidence-field-assertions-2026-06-25.md`
- Official asset read-only diagnostic fields:
  `docs/artifacts/official-asset-readonly-diagnostic-field-assertions-2026-06-25.md`
- Robot + RTX success final-log close gate:
  `docs/artifacts/robot-rtx-golden-close-gate-live-refresh-2026-06-26.md`
- Robot + RTX controlled-failure final-log close gate:
  `docs/artifacts/robot-rtx-controlled-failure-close-gate-live-refresh-2026-06-26.md`
- Official asset verify final-log close gate:
  `docs/artifacts/official-asset-verify-close-gate-live-refresh-2026-06-26.md`
- Official asset read-only diagnostics final-log close gate:
  `docs/artifacts/official-asset-readonly-close-gate-live-refresh-2026-06-26.md`

## Public Boundary

- No mutating live scenario was run for this artifact.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, raw Kit
  logs, generated catalog records, or capture paths are included.
- This artifact records only stable command lines and compact plan/dry-run
  summaries from the workspace-local MCP entry.
