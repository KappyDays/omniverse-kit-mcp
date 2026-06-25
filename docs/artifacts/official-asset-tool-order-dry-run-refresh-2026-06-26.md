# Official Asset Tool-Order Dry-Run Refresh - 2026-06-26

Purpose: refresh the docs-only agent check that the official asset wrappers in
`docs/mcp-usage-guide.md` still match the workspace MCP plan/dry-run shape
without mutating a stage.

## Commands

- Verify the read-only catalog diagnostics wrapper:
  `scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --scenario-validate-dry-run --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true`
- Verify the mutating official asset live-verify wrapper plan gate:
  `scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_verify_live.yaml --scenario-validate-dry-run --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true`

## Result

- Both commands exited 0 against the workspace-local Isaac Sim MCP entry.
- `official_asset_catalog_diagnostics` plan and dry-run reported
  `live_validation_step_count=8`, `scratch_stage_required=false`, and
  `log_capture_recommended=true`.
- `official_asset_verify_live` plan and dry-run reported
  `live_validation_step_count=9`, `scratch_stage_required=true`, and
  `log_capture_recommended=true`.
- Runtime gate fields were fresh:
  `tool_profile=full`, `app_profile=isaac-sim`, `tool_count=152`,
  `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- The generated `tmp_mcp_surface.json` snapshot is ignored and was not promoted
  as public evidence.

## Public Boundary

Only stable command lines and compact plan/dry-run summaries are recorded here.
No local absolute paths, local capture paths, private filesystem roots,
worker/thread IDs, secrets, or generated catalog records are included.
