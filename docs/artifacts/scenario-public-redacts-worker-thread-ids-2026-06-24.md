# Scenario Public Redacts Worker Thread IDs - 2026-06-24

## Scope

`scenario_last_report(..., redact_local_paths=true)` is the public evidence path
for live scenario reports. The public hygiene invariant requires worker and
thread identifiers to be removed from public artifacts.

## Change

- Redact structured keys such as `thread_id`, `worker_id`,
  `pendingWorktreeId`, and `*_thread_id` only when redaction is requested.
- Redact inline text patterns such as `thread_id=...` and `worker_id=...`.
- Avoid blanket UUID redaction so official asset IDs and scenario data remain
  available unless the key name marks them as worker/thread identifiers.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `50 passed`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\scenario\reporters.py tests\unit\test_scenario_integration.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - passed with `finding_count=0`
- `git diff --check`
  - passed
