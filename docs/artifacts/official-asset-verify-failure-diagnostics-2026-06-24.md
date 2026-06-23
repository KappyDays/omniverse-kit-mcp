# Official Asset Verify Failure Diagnostics - 2026-06-24

## Change

`official_asset_verify` failed records now include a bounded `diagnostics`
object. The diagnostics classify the failure and expose the relevant readback
summary without requiring agents to infer the next action from raw stage or
material payloads.

Failure reasons currently covered:

- `verify_timeout`
- `asset_load_quality_failed`
- `material_assign_or_binding_failed`
- `verify_failed`

## Contract

- Asset failures include `diagnostics.asset_checks`.
- Material failures include `diagnostics.material_checks`.
- Timeout/exception failures preserve `diagnostics.error_type` when available.
- `diagnostics.suggested_next` and `diagnostics.fallback_tool_order` are present
  for failed verify records.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py -q`
  - `48 passed`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\modules\asset_module.py tests\unit\test_asset_module.py`
  - passed

## Public Boundary

No local install root, raw generated official catalog path, worker id, process
id, or live capture path is recorded here.
