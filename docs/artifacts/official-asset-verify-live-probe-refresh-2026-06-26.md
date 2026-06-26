# Official Asset Verify Live Probe Refresh - 2026-06-26

## Scope

This artifact records a workspace-local Isaac Sim live MCP smoke for
`smoke/official_asset_verify_live.yaml` after probe live evidence field
assertions were tightened and documented. The workflow uses the documented
scratch/test-stage boundary and final log close gate.

## Command

`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_verify_live.yaml --scenario-validate-dry-run --scenario-validate-live --expect-live-status passed --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-live-cleanup-failures 0 --expect-live-evidence-kind official_asset_verify --expect-live-evidence-field official_asset_verify:verification_status=load_verified --expect-live-evidence-field official_asset_verify:kind=asset --expect-live-evidence-field official_asset_verify:app_profile=isaac-sim --expect-live-evidence-field official_asset_verify:load_quality=content_verified_no_bbox`

## Result

- Exit code: `0`.
- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan and dry-run shape: `total_steps=5`, `live_validation_step_count=9`,
  `diagnostic_steps=true`, `evidence_steps=true`,
  `stage_mutation_steps=true`, `scratch_stage_required=true`, and
  `log_capture_recommended=true`.
- Live scenario status: `passed`, with `passed_steps=5`, `failed_steps=0`,
  `skipped_steps=0`, `continued_steps=0`, `fatal_failed_steps=0`, and
  `cleanup_failed_steps=0`.
- Evidence boundary: exactly one compact `official_asset_verify` evidence row
  for `verify_pallet_asset`; it preserved `verification_status=load_verified`,
  `kind=asset`, `app_profile=isaac-sim`,
  `load_quality=content_verified_no_bbox`, `name=aluminumpallet_a01.usd`,
  `attempts=1/1`, `timeout_s=180.0`, `retry_count=1`, and `error=null`.
- Success rows remain `error_code` free; keep `error_code` assertions for
  failed evidence rows selected by concrete `step_id`.
- Final log close gate passed with `data.capture_stop_requested=true`,
  `data.capture_stop_completed=true`, `data.capture_stop_timed_out=false`, and
  `data.capture_running=false`.
- The generated `tmp_mcp_surface.json` snapshot remained ignored and was not
  promoted as public evidence.

## Public Boundary

No raw local absolute paths, process IDs, worker/thread IDs, secrets, raw Kit
logs, local capture paths, generated catalog records, generated verification
JSONL, Python object reprs, or private workspace state are included. The raw
redacted Markdown report included a public official asset URL; it is omitted
here because this artifact only needs stable result-shape and evidence proof.
