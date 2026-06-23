# Scenario Summary Failure Class Counts

Date: 2026-06-23

## Change

`ScenarioRunSummary` JSON now carries failure-class counters in addition to the
legacy aggregate `failed_steps` value:

- `continued_steps`: failed non-cleanup steps that were allowed to continue.
- `fatal_failed_steps`: failed non-cleanup steps that make the scenario fail.
- `cleanup_failed_steps`: failed cleanup steps.

This keeps machine-readable reports aligned with the Markdown step summary,
where continued diagnostic failures are shown separately from fatal failures.

## Evidence

- Continued hard timeout and exception steps report `failed_steps=2`,
  `continued_steps=2`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- Official asset profile-mismatch diagnostics smoke reports `failed_steps=1`,
  `continued_steps=1`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- Fatal retry exhaustion paths report `failed_steps=1`,
  `continued_steps=0`, `fatal_failed_steps=1`, and `cleanup_failed_steps=0`.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q -k "continued_hard_timeout_and_exception or official_asset_catalog_diagnostics_smoke_routes_through_runner or exhausted_hard_timeout_retries or bounds_hard_error_retry_messages"`:
  `4 passed, 44 deselected`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\types\scenario.py src\omniverse_kit_mcp\scenario\runner.py src\omniverse_kit_mcp\scenario\reporters.py tests\unit\test_scenario_integration.py`:
  passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`:
  `48 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`:
  `19 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`: passed
- `git diff --check`: passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py`: passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`:
  `747 passed, 16 skipped`

## Public Hygiene Note

The pending-tree public hygiene gate passed for this batch. The separate
2026-06-23 history audit still reports pre-existing pushed findings in earlier
commits, so no push should proceed until the public-history rewrite plan is
explicitly approved.
