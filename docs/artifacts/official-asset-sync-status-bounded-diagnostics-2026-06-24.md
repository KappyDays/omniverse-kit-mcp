# Official Asset Sync Status Bounded Diagnostics - 2026-06-24

## Change

`official_asset_sync_status(app_profile=...)` diagnostics now include bounded
catalog recovery context when the requested profile is missing or empty:

- `available_kinds`
- `catalog_status_counts`
- `matching_status_counts`
- `sample_names`

This separates "the catalog has entries" from "the requested profile matched
entries" without exposing local generated catalog paths.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py -q`
  - `47 passed`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\modules\asset_module.py tests\unit\test_asset_module.py`
  - passed

## Public Boundary

No local install root, raw generated official catalog path, worker id, or
process id is recorded here.
