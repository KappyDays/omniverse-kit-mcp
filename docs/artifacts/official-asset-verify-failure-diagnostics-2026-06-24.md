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
- `tests/unit/test_scenario_integration.py::test_official_asset_verify_failure_diagnostics_survive_runner_report`
  locks the scenario-report path: a failed `official_asset_verify` record still
  leaves the scenario step `passed`, but JSON `diagnostic_next_actions` and
  Markdown `Diagnostic Next Actions` preserve `asset_checks`, `suggested_next`,
  and the official-asset fallback order for agent triage.
- `tests/unit/test_scenario_integration.py::test_official_asset_verify_material_failure_diagnostics_survive_runner_report`
  locks the material-report path: a failed material verify record preserves
  `material_checks.create_prim_ok`, `material_checks.assign_ok`,
  `material_checks.bound_ok`, `suggested_next`, and the official fallback order
  in JSON and Markdown reports.
- The scenario reporter now also preserves official verify failure diagnostics
  in `evidence_summary`, including `asset_checks`, `material_checks`, and
  timeout `error_type` when present.

## Public Boundary

No local install root, raw generated official catalog path, worker id, process
id, live capture path, or generated material catalog snapshot is recorded here.
