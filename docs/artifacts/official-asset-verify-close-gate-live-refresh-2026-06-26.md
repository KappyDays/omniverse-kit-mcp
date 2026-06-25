# Official Asset Verify Close-Gate Live Refresh

Date: 2026-06-26

Scope: workspace-local Isaac Sim MCP live validation of
`smoke/official_asset_verify_live.yaml` after `probe_mcp_surface.py` started
hard-gating final log-capture close metadata. This scenario uses the documented
scratch/test-stage boundary and cleanup expectations for bounded live proof.

## Command

- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_verify_live.yaml --scenario-validate-dry-run --scenario-validate-live --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-live-cleanup-failures 0 --expect-live-evidence-kind official_asset_verify --expect-live-evidence-field official_asset_verify:verification_status=load_verified --expect-live-evidence-field official_asset_verify:kind=asset --expect-live-evidence-field official_asset_verify:app_profile=isaac-sim`

## Result

- Exit code: 0.
- Runtime gate was fresh: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Plan and dry-run both reported `scenario_id=official_asset_verify_live`,
  `total_steps=5`, `diagnostic_steps=true`, `evidence_steps=true`,
  `stage_mutation_steps=true`, `scratch_stage_required=true`,
  `log_capture_recommended=true`, and the 9-tool live wrapper order.
- Live validation passed with `passed_steps=5`, `failed_steps=0`,
  `continued_steps=0`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- Required evidence assertions passed for `official_asset_verify`:
  - `verification_status=load_verified`
  - `kind=asset`
  - `app_profile=isaac-sim`
- The compact evidence row preserved `step_id=verify_pallet_asset`,
  `name=aluminumpallet_a01.usd`, `attempts=1/1`, `timeout_s=180.0`, and
  `retry_count=1`.
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
redacted Markdown report included a public official asset URL; it is omitted
here because this artifact only needs the stable result-shape/evidence proof.
