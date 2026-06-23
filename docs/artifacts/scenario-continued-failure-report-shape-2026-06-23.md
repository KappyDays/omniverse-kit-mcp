# Scenario continued failure report shape - 2026-06-23

## Change

- `StepResult` now carries `continue_on_failure`.
- Markdown scenario reports render non-passed continued steps as
  `error (continued)`, `failed (continued)`, or `timeout (continued)`.
- Step summary counts non-cleanup continued failures separately from fatal
  failures.

## Evidence target

- A diagnostics scenario can finish with `Status: PASSED` while clearly showing
  that an intended not-found probe was continued, not accidentally ignored.
- JSON reports preserve `continue_on_failure=true` for exact result-shape
  inspection.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q -k "official_asset_catalog_diagnostics_smoke_routes_through_runner"`
  - 1 passed, 46 deselected.
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\types\scenario.py src\omniverse_kit_mcp\scenario\runner.py src\omniverse_kit_mcp\scenario\reporters.py tests\unit\test_scenario_integration.py`
  - All checks passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - 47 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - 19 passed, 2 skipped after compressing the `scenarios/CLAUDE.md`
    note back under the 150-line hardcap.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - OK, 34 passed.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py`
  - OK for the pending branch range.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - 746 passed, 16 skipped.

## Push blocker

The day/session public-history audit still reports the pre-existing 7 findings
from already-pushed commits. This batch adds no new pending public-hygiene
findings, but push remains blocked until an approved history rewrite resolves
the existing public ref.
