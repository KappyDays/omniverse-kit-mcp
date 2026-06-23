# Official Asset Scenario Diagnostics Smoke - 2026-06-23

## Summary

- Scenario: `scenarios/smoke/official_asset_catalog_diagnostics.yaml`
- Route: workspace-local Isaac MCP stdio from `workspaces/isaac/instance-1`
- Tools: `mcp_runtime_info`, `scenario_plan`, `scenario_validate`, `scenario_last_report`
- Result after fix: `PASSED`, `3 passed / 0 failed / 0 skipped`

## Evidence

- `mcp_runtime_info`:
  - `ok=true`
  - `tool_profile=full`
  - `app_profile=isaac-sim`
  - `tool_count=152`
- `scenario_plan` confirmed the read-only assert steps:
  - `asset.official_sync_status(app_profile=isaac-sim)`
  - `asset.official_search(query=definitely-not-a-real-official-asset-name-zzzz, min_status=discovered)`
  - `asset.official_search(query=pallet, min_status=url_validated)`
- First live run exposed a cleanup-result shape issue: the read-only catalog
  scenario passed its three official asset steps but still reported
  `__fallback_cleanup_reset` as an error when Kit REST was not running.
- Fix: scenario runner now skips fallback extension reset when every step is a
  read-only official asset catalog action:
  `official_sync_status`, `official_search`, `official_resolve`, or
  `official_get`. `official_verify` and live app/stage actions still keep the
  fallback cleanup.
- Re-run `scenario_validate(report_format=markdown)`:
  - `Status=PASSED`
  - `Steps=3 passed, 0 failed, 0 skipped`
  - `search_known_miss` data summary preserved
    `diagnostics.reason=query_no_match` and
    `diagnostics.fallback_tool_order=[official_asset_sync_status, official_asset_search, official_asset_resolve, official_asset_verify, asset_search]`.

## Static Gates

- `tests/unit/test_scenario_integration.py::test_official_asset_catalog_diagnostics_smoke_routes_through_runner`
- `tests/unit/test_scenario_integration.py tests/unit/test_scenario_runner.py`
- `tests/unit/test_doc_integrity.py tests/unit/test_doc_references.py`
- `scripts/verify_mcp_sync.py`

## Boundary

This smoke proves the official asset catalog diagnostics route and report shape.
It does not verify loading assets into a live stage; use `official_asset_verify`
for that stronger workflow.
