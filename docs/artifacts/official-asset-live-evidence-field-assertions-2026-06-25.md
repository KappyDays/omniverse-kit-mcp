# Official Asset Live Evidence Field Assertions - 2026-06-25

Purpose: verify that `scripts/probe_mcp_surface.py` can guard the official
asset live workflow with exact evidence row field assertions, not only the
presence of an `official_asset_verify` evidence kind.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/official_asset_verify_live.yaml`
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
