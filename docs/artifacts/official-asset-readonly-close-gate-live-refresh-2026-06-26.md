# Official Asset Read-Only Close-Gate Live Refresh

Date: 2026-06-26

Scope: workspace-local Isaac Sim MCP live validation of
`smoke/official_asset_catalog_diagnostics.yaml` after `probe_mcp_surface.py`
started hard-gating final log-capture close metadata. This scenario is read-only
and did not mutate a stage.

## Command

- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --scenario-validate-dry-run --scenario-validate-live --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true --expect-live-status passed --expect-live-cleanup-failures 0 --expect-live-failure-step-error get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND --expect-live-diagnostic-next-actions-min 2 --expect-live-diagnostic-field search_known_miss:diagnostics.reason=query_no_match --expect-live-diagnostic-field get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`

## Result

- Exit code: 0.
- Runtime gate was fresh: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan and dry-run both reported `scenario_id=official_asset_catalog_diagnostics`,
  `total_steps=5`, `diagnostic_steps=true`, `stage_mutation_steps=true`,
  `scratch_stage_required=false`, `log_capture_recommended=true`, and the
  8-tool read-only wrapper order.
- Live validation passed with `passed_steps=4`, `failed_steps=1`,
  `continued_steps=1`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- Required diagnostic assertions passed:
  - `search_known_miss:diagnostics.reason=query_no_match`
  - `get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`
  - `get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND`
- Both diagnostic next-action rows preserved the fallback route:
  `official_asset_sync_status -> official_asset_search ->
  official_asset_resolve -> official_asset_verify -> asset_search`.
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
redacted Markdown report included public official asset URLs; they are omitted
here because this artifact only needs the stable diagnostic/result-shape proof.
