# Scenario Public Redacts Process IDs - 2026-06-24

## Scope

`scenario_last_report(..., redact_local_paths=true)` is the documented path for
copying live scenario reports into public evidence. The public hygiene invariant
also requires process IDs to be redacted, but the reporter redaction path was
limited to host-local path strings.

## Change

- Redact structured keys such as `pid`, `process_id`, and `*_pid` only when
  `redact_local_paths=true`.
- Redact inline text patterns such as `pid=<process-id>`.
- Preserve exact JSON report data when redaction is not requested.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `50 passed`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\scenario\reporters.py tests\unit\test_scenario_integration.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - passed with `finding_count=0`
- `git diff --check`
  - passed
