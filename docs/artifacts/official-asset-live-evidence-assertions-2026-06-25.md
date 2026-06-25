# Official Asset Live Evidence Assertions — 2026-06-25

Purpose: verify that `scripts/probe_mcp_surface.py` live assertions can guard
the official asset scenario workflow by requiring the expected
`official_asset_verify` evidence row and preserved cleanup.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/official_asset_verify_live.yaml`
- Added live expectations:
  - `--expect-live-status passed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind official_asset_verify`

Result:

- Exit code: `0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- Plan/dry-run: `diagnostic_steps`, `evidence_steps`, and
  `stage_mutation_steps` present
- Scratch stage required: `true`
- Log capture recommended: `true`
- Live summary: `passed`
- Steps: `5` passed, `0` failed, `0` skipped
- Cleanup failed steps: `0`
- Evidence kinds:
  - `official_asset_verify`
- WARN+ log capture: `passed`

Evidence row:

- Step: `verify_pallet_asset`
- Asset id:
  `url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/common_assets/props/aluminumpallet_a01/aluminumpallet_a01.usd`
- Kind: `asset`
- Name: `aluminumpallet_a01.usd`
- App profile: `isaac-sim`
- Verification status: `load_verified`
- Timeout: `180.0`
- Error: `null`

Public hygiene:

- The artifact records only public S3 asset URLs and redacted operational
  evidence.
- No local absolute paths, process IDs, worker/thread IDs, or secrets are
  included in this artifact.
