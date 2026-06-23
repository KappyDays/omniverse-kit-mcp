# Scenario continued hard failures - 2026-06-23

## Change

- Added regression coverage for `continueOnFailure: true` when the runner hits
  hard timeout and hard exception paths before a module result exists.

## Evidence target

- The scenario terminal status remains `PASSED`.
- JSON step results preserve `continue_on_failure=true`.
- Markdown reports hard timeout/error rows as `timeout (continued)` and
  `error (continued)`.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q -k "continued_hard_timeout_and_exception"`
  - 1 passed, 47 deselected.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_scenario_integration.py`
  - All checks passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - 48 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - 19 passed, 2 skipped.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - OK, 34 passed.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py`
  - OK for the pending branch range.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - 747 passed, 16 skipped.

## Push blocker

The day/session public-history audit still reports the pre-existing 7 findings
from already-pushed commits. This batch adds no new pending public-hygiene
findings, but push remains blocked until an approved history rewrite resolves
the existing public ref.
