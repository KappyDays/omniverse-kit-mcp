# Official Asset Read-Only Diagnostic Live Probe Refresh - 2026-06-26

## Scope

This artifact records a workspace-local live MCP smoke for
`smoke/official_asset_catalog_diagnostics.yaml` after the probe assertion path
was tightened for dotted evidence and diagnostic fields. The scenario is
read-only and did not mutate a stage.

## Command

`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --scenario-validate-dry-run --scenario-validate-live --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true --expect-live-status passed --expect-live-cleanup-failures 0 --expect-live-failure-step-error get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND --expect-live-diagnostic-next-actions-min 2 --expect-live-diagnostic-field search_known_miss:diagnostics.reason=query_no_match --expect-live-diagnostic-field get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered --expect-live-diagnostic-field search_known_miss:diagnostics.fallback_tool_order='["official_asset_sync_status","official_asset_search","official_asset_resolve","official_asset_verify","asset_search"]' --expect-live-diagnostic-field get_pallet_wrong_profile:diagnostics.fallback_tool_order='["official_asset_sync_status","official_asset_search","official_asset_resolve","official_asset_verify","asset_search"]'`

## Result

- Exit code: `0`.
- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan and dry-run shape: `total_steps=5`, `live_validation_step_count=8`,
  `scratch_stage_required=false`, `log_capture_recommended=true`, and required
  `diagnostic_steps` / `stage_mutation_steps` fields present.
- Live scenario status: `passed` with `passed_steps=4`, `failed_steps=1`,
  `continued_steps=1`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- Expected continued failure: `get_pallet_wrong_profile` reported
  `OFFICIAL_ASSET_NOT_FOUND` and remained non-terminal.
- Diagnostic assertions passed for:
  `search_known_miss:diagnostics.reason=query_no_match`,
  `get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`, and
  both exact fallback orders:
  `official_asset_sync_status -> official_asset_search -> official_asset_resolve -> official_asset_verify -> asset_search`.
- Evidence boundary: `evidence_kinds=[]` and `evidence=[]`, as expected for the
  read-only catalog diagnostic scenario.
- Final log close gate passed with `data.capture_stop_requested=true`,
  `data.capture_stop_completed=true`, `data.capture_stop_timed_out=false`, and
  `data.capture_running=false`.
- The generated `tmp_mcp_surface.json` snapshot remained ignored and was not
  promoted as public evidence.

## Public Boundary

No raw local absolute paths, local capture paths, worker/thread IDs, process
IDs, secrets, raw Kit logs, generated catalog records, generated verification
JSONL, or private workspace state are included.
