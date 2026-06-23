# Scenario Plan continueOnFailure Metadata - 2026-06-24

## Scope

Expose execution-critical `continueOnFailure` metadata in `scenario_plan` output.
Before this batch, the plan showed `idempotent` and `retries` but hid whether a
step could fail without poisoning the scenario terminal status.

## Change

- Add `continueOnFailure: true` to `_plan_step(...)` output when a compiled step
  has `continue_on_failure`.
- Extend the existing plan metadata unit test so retry/idempotent and
  continue-on-failure behavior stay visible together.
- Document the plan-field expectation in `scenarios/CLAUDE.md`.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_runner.py -q`
  - 8 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_scenario_runner.py -q`
  - 15 passed, 1 skipped.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - Passed; generated tool catalog remained up to date and 34 sync tests passed.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --format json --redact-samples`
  - `finding_count=0` for current tree and pending history.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - `finding_count=0` for the pending push range.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples`
  - `finding_count=0` for the current-day commit audit.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - 759 passed, 16 skipped.
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\tools\scenario_tools.py tests\unit\test_scenario_runner.py`
  - Passed.
- `git diff --check`
  - Passed; Git reported only LF-to-CRLF working-copy warnings for edited text files.

## Live Evidence

Not rerun. This batch changes `scenario_plan` result shape and static
documentation only; live scenario execution and Kit stage state are unchanged.
