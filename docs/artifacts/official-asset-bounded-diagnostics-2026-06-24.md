# Official Asset Bounded Diagnostics - 2026-06-24

## Change

`official_asset_search` no-result diagnostics now include bounded recovery
context:

- `available_kinds`
- `status_counts`
- `sample_names`

The fields are intended to guide the next retry without exposing local catalog
paths or dumping full generated catalog entries.

## Covered Cases

- Query miss under a covered app profile.
- `min_status` too strict for otherwise matching candidates.
- Missing app profile.
- Missing provider.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py -q`
  - `47 passed`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\modules\asset_module.py tests\unit\test_asset_module.py`
  - passed

## Public Boundary

No raw catalog path, local install root, worker id, process id, or generated
official catalog snapshot is recorded in this artifact.
