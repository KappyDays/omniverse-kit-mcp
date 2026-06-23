# Scenario Cleanup Report Shape - 2026-06-23

## Summary

Scenario cleanup steps are intentionally non-fatal, but the Markdown report
previously used the raw `failed_steps` count in the top `Steps` line. That made
cleanup-only errors look like primary scenario failures.

## Change

- Markdown reports now subtract cleanup-phase failures from the primary
  `failed` count.
- Cleanup-phase failures are shown separately as:
  `Cleanup: N non-fatal failure(s)`.
- The detailed step table still includes the cleanup row and message.
- JSON output is unchanged; it still exposes the raw `failed_steps` and
  `step_results` data for exact machine inspection.

## Validation

- Added `test_markdown_reports_cleanup_failures_as_non_fatal`.
- Targeted check:
  `.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_markdown_reports_cleanup_failures_as_non_fatal tests\unit\test_scenario_integration.py::test_scenario_runner_reports_retry_context_on_hard_timeout tests\unit\test_scenario_integration.py::test_scenario_runner_bounds_hard_error_retry_messages -q`
  -> `3 passed`.

## Boundary

This is a report-shape fix only. It does not change scenario execution,
cleanup execution, terminal status, JSON serialization, or retry behavior.
