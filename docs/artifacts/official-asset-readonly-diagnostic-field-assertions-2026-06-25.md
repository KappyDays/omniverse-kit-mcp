# Official Asset Read-Only Diagnostic Field Assertions - 2026-06-25

Purpose: verify that the read-only official asset catalog diagnostics scenario
can be promoted from documented plan/dry-run guidance to a live diagnostic proof
with exact `diagnostic_next_actions` field assertions.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/official_asset_catalog_diagnostics.yaml`
- Full live diagnostic probe command:
  `scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --scenario-validate-dry-run --scenario-validate-live --expect-live-status passed --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true --expect-live-cleanup-failures 0 --expect-live-failure-step-error get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND --expect-live-diagnostic-next-actions-min 2 --expect-live-diagnostic-field search_known_miss:diagnostics.reason=query_no_match --expect-live-diagnostic-field get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`

Result:

- Exit code: `0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- Plan and dry-run: `diagnostic_steps` and `stage_mutation_steps` present
- Scratch stage required: `false`
- Log capture recommended: `true`
- Live validation tool order:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `scenario_plan`, `extension_clear_logs`, `scenario_validate`,
  `scenario_last_report`, `extension_capture_logs`
- Live summary: `passed`
- Steps: `4` passed, `1` continued failure, `0` fatal failures, `0` skipped
- Cleanup failed steps: `0`
- Failure step asserted:
  `get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND`
- Diagnostic next-action count: `2`
- Diagnostic fields asserted:
  - `search_known_miss:diagnostics.reason=query_no_match`
  - `get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`
- WARN+ log capture (stop_after_capture=true): `passed`
- Snapshot path printed by the probe: `tmp_mcp_surface.json`

Recovery note:

- A prior attempt proved the scenario diagnostic assertions but failed at the
  final log-capture step with `EXTENSION_LOGS_ERROR`.
- The workspace-local log endpoint was recovered with a lifecycle-allowed
  `kit_app_restart` after confirming the log endpoint hang; no root Kit launch
  was used.
- The code now preserves log-capture failure diagnostics in the MCP result and
  probe summary so a future timeout exposes `data.diagnostics.reason`,
  `data.diagnostics.error_type`, `data.diagnostics.retryable`, and
  `data.diagnostics.fallback_tool_order`.

2026-06-26 recovery refresh:

- Symptom: the final `extension_capture_logs` step had timed out after the
  scenario assertions passed; direct health/log endpoint checks also timed out.
- Lifecycle route used:
  `extension_clear_logs`/`extension_capture_logs` retry evidence ->
  process inspection -> `scripts/run_process_module_standalone.py restart
  --profile isaac-sim --instance 1`.
- Restart result: `ok=true`, `status=started`, `caches_cleared=4`.
- Post-restart health: `ok=true`, `extension_enabled=true`, `busy=false`.
- Post-restart preflight:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `extension_clear_logs`, and `extension_capture_logs` all passed.
- Re-run command: same full live diagnostic probe command above.
- Re-run result: exit code `0`, live summary `passed`, `4` passed steps,
  `1` continued expected failure, `0` cleanup failures, `2`
  diagnostic next actions, and final WARN+ log capture passed.
- Field assertions reconfirmed:
  - `search_known_miss:diagnostics.reason=query_no_match`
  - `get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`

Public hygiene:

- The artifact records only public scenario/tool names, public S3 asset URL
  fragments already present in existing docs, and compact redacted result
  fields.
- No local absolute paths, process IDs, worker/thread IDs, ports, raw Kit logs,
  or secrets are included in this artifact.
