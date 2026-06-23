# Official Asset Sync Status Runner Diagnostics

Date: 2026-06-23

## Scope

This batch locks the real scenario runner path for
`asset.official_sync_status(app_profile=...)` diagnostics. A synthetic scenario
runs `official_sync_status` through the runner against an offline generated
catalog that only covers `isaac-sim`, then requests `kit-app`.

The step remains `passed` because sync-status diagnostics are guidance, not a
tool failure, and the diagnostic payload is preserved in both JSON
`data_summary` and Markdown highlights.

## Verification

- Targeted scenario integration test covers:
  - `diagnostics.reason=app_profile_not_covered`
  - `diagnostics.requested_app_profile`
  - `diagnostics.available_profiles`
  - `diagnostics.matching_item_count`
  - Markdown `Data Summary Highlights`

## Live Evidence

No live Kit smoke was required. This is an offline scenario-report contract
update using a synthetic generated official catalog.
