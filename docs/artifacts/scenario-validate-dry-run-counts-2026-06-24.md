# Scenario Validate Dry-Run Counts - 2026-06-24

## Scope

`scenario_validate(..., dry_run=true)` is a compile-only path that agents may use
before live stage mutation. After `scenario_plan` began exposing executable
`total_steps`, `phase_counts`, and automatic fallback cleanup, dry-run still
reported only arrange, act, and assert steps through its legacy `steps` field.

## Change

- Reuse the same executable plan payload for dry-run counts.
- Preserve the legacy `steps` field, but make it equal to `total_steps`.
- Add `total_steps` and `phase_counts` to dry-run output.
- Document that dry-run counts match `scenario_plan`.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py::test_scenario_validate_dry_run_uses_plan_step_counts tests\unit\test_scenario_runner.py::test_scenario_plan_payload_includes_phase_counts -q`
  - `2 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py tests\unit\test_tools_registration.py -q`
  - `47 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; generated tool catalog stayed up to date and 35 sync tests passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `762 passed, 16 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - `finding_count=0`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples`
  - `finding_count=0`
- `git diff --check`
  - passed; Git reported only LF-to-CRLF working-copy warnings for edited text files

## Live Evidence

Not required. This batch changes compile-only result shape and documentation; it
does not execute a live scenario or mutate a Kit stage.

## Public Hygiene

This artifact contains no local absolute paths, process IDs, worker/thread IDs,
account data, secrets, or raw Kit log snippets.
