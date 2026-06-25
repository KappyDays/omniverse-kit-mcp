# Official Asset Live Evidence Field Assertions - 2026-06-25

Purpose: verify that `scripts/probe_mcp_surface.py` can guard the official
asset live workflow with exact evidence row field assertions, not only the
presence of an `official_asset_verify` evidence kind.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/official_asset_verify_live.yaml`
- Full live probe command:
  `scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_verify_live.yaml --scenario-validate-dry-run --scenario-validate-live --expect-live-status passed --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-live-cleanup-failures 0 --expect-live-evidence-kind official_asset_verify --expect-live-evidence-field official_asset_verify:verification_status=load_verified --expect-live-evidence-field official_asset_verify:kind=asset --expect-live-evidence-field official_asset_verify:app_profile=isaac-sim`
- Live assertions:
  - `--expect-live-status passed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind official_asset_verify`
  - `--expect-live-evidence-field official_asset_verify:verification_status=load_verified`
  - `--expect-live-evidence-field official_asset_verify:kind=asset`
  - `--expect-live-evidence-field official_asset_verify:app_profile=isaac-sim`

Result:

- Exit code: `0`
- MCP server: `isaacsim-validation-mcp v1.27.0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- `kit_app_start`: `ready`
- `simulation_get_status`: `passed`, `is_playing=false`, `current_time=0.0`
- Plan/dry-run: `diagnostic_steps`, `evidence_steps`, and
  `stage_mutation_steps` present
- Scratch stage required: `true`
- Log capture recommended: `true`
- Live summary: `passed`
- Steps: `5` passed, `0` failed, `0` skipped
- Cleanup failed steps: `0`
- Failure summary count: `0`
- Diagnostic next-action count: `0`
- WARN+ log capture: `passed`

Refresh run after durable-doc bridge:

- Exit code: `0`
- Scenario id: `official_asset_verify_live`
- Live validation tools:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `scenario_plan`, `scenario_validate`, `extension_clear_logs`,
  `scenario_validate`, `scenario_last_report`, `extension_capture_logs`
- Live summary: `passed`
- Total steps: `5`
- Passed/failed/skipped steps: `5` / `0` / `0`
- Cleanup failed steps: `0`
- Evidence kinds: `official_asset_verify`
- Asserted evidence fields:
  - `official_asset_verify:verification_status=load_verified`
  - `official_asset_verify:kind=asset`
  - `official_asset_verify:app_profile=isaac-sim`
- WARN+ log capture: `passed`
- Snapshot path printed by the probe: `tmp_mcp_surface.json`

Evidence row asserted:

- Step: `verify_pallet_asset`
- Evidence kind: `official_asset_verify`
- Status: `passed`
- Attempts: `1/1`
- Kind: `asset`
- Name: `aluminumpallet_a01.usd`
- App profile: `isaac-sim`
- Verification status: `load_verified`
- Attempt: `1`
- Timeout: `180.0`
- Retry count: `1`
- Error: `null`

Public hygiene:

- The artifact records only public scenario/tool names and compact redacted
  evidence fields.
- No local absolute paths, process IDs, worker/thread IDs, or secrets are
  included in this artifact.
