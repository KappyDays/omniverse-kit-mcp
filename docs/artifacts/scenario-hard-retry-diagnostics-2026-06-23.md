# Scenario Hard Retry Diagnostics (2026-06-23)

## Change

- Idempotent scenario steps with `retries.maxAttempts > 1` now retry:
  - returned non-pass `ModuleResult` statuses
  - hard per-attempt step timeouts
  - hard exceptions raised while executing the step
- Hard timeout retries record `SCENARIO_STEP_TIMEOUT` in `retry_failures`.
- Hard exception retries record `SCENARIO_STEP_EXCEPTION` in `retry_failures`.
- Final timeout after all attempts returns a `StepResult` with
  `status=timeout`, `attempts=maxAttempts`, and bounded retry diagnostics.

## Why

Robot + RTX sensor live workflows can hit transient bridge-level failures that
do not return a normal module failure payload. Retrying only returned failures
left idempotent sensor reads vulnerable to one-off timeout/exception exits.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `33 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `684 passed, 15 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - `25 passed`
- `git diff --check`
  - passed with LF-to-CRLF working-copy warnings only
- Targeted assertions cover:
  - hard timeout on attempt 1 passing on attempt 2
  - hard exception on attempt 1 passing on attempt 2
  - hard timeout exhausting all attempts
  - hard exception exhausting all attempts
  - retry failure diagnostics preserving `SCENARIO_STEP_TIMEOUT`
  - retry failure diagnostics preserving `SCENARIO_STEP_EXCEPTION`
  - bounded hard-error retry messages
