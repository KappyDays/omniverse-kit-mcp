# Official Asset Verify Stop Guard Refresh - 2026-06-26

Purpose: re-run the bounded official asset live verification workflow after
hardening `extension_capture_logs(..., stop_after_capture=true)`, confirming
that the official proof still passes with exact evidence field assertions and a
clean log-capture close.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/official_asset_verify_live.yaml`
- Required live wrapper tools:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `scenario_plan`, `scenario_validate`, `extension_clear_logs`,
  `scenario_validate`, `scenario_last_report`, `extension_capture_logs`
- Probe assertions:
  - `--expect-live-status passed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind official_asset_verify`
  - `--expect-live-evidence-field official_asset_verify:verification_status=load_verified`
  - `--expect-live-evidence-field official_asset_verify:kind=asset`
  - `--expect-live-evidence-field official_asset_verify:app_profile=isaac-sim`

Result:

- Exit code: `0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- Plan and dry-run:
  - total steps: `5`
  - live validation step count: `9`
  - scratch stage required: `true`
  - log capture recommended: `true`
  - diagnostic/evidence/stage-mutation plan fields present
- Live summary:
  - status: `passed`
  - passed/failed/skipped: `5` / `0` / `0`
  - cleanup failed steps: `0`
  - diagnostic next actions: `0`
- Evidence:
  - `verify_pallet_asset`: evidence kind `official_asset_verify`,
    status `passed`, attempts `1/1`, kind `asset`, name
    `aluminumpallet_a01.usd`, app profile `isaac-sim`, verification status
    `load_verified`, attempt `1`, timeout `180.0`, retry count `1`,
    error `null`
- Final WARN+ log capture: `passed`

Stop guard check:

- Direct post-run log close metadata:
  - `ok=true`
  - `capture_running=false`
  - `capture_stop_requested=true`
  - `capture_stop_completed=true`
  - `capture_stop_timed_out=false`
  - `capture_stop_timeout_s=1.0`

Public hygiene:

- This artifact records public scenario/tool names and compact evidence fields
  only.
- No local absolute paths, process IDs, raw Kit logs, worker/thread IDs, or
  secrets are included.
