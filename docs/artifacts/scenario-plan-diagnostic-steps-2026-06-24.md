# Scenario Plan Diagnostic Steps — 2026-06-24

## Objective

Make official asset read-only diagnostics visible before live scenario execution,
so agents can confirm the intended catalog/status/search/resolve/get probes at
`scenario_plan` or `scenario_validate(..., dry_run=true)` time.

## Change

- Added `diagnostic_steps` to scenario plan payloads.
- Added official asset plan rows for:
  - `asset.official_sync_status`
  - `asset.official_search`
  - `asset.official_resolve`
  - `asset.official_get`
- Preserved existing `phase_counts`, `evidence_steps`, `retry_steps`, and full
  `phases` output.

## Evidence

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_official_asset_catalog_diagnostics_smoke_routes_through_runner tests\unit\test_tools_registration.py::test_scenario_validate_dry_run_uses_plan_step_counts tests\unit\test_doc_references.py -q`
  - Result: `18 passed, 1 skipped`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\tools\scenario_tools.py tests\unit\test_scenario_integration.py tests\unit\test_tools_registration.py tests\unit\test_doc_references.py`
  - Result: passed
- `.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run smoke\official_asset_catalog_diagnostics.yaml`
  - Result: exit 0
  - `diagnostic_steps`: 5 rows
  - Kinds: `official_asset_sync_status`, `official_asset_search`,
    `official_asset_resolve`, `official_asset_get`
  - Continued diagnostic gate:
    `get_pallet_wrong_profile.continueOnFailure=true`
- `.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run smoke\official_asset_verify_live.yaml`
  - Result: exit 0
  - `diagnostic_steps`: sync/search/resolve/get rows before verify
  - `evidence_steps`: `verify_pallet_asset` with
    `evidence_kind=official_asset_verify`
