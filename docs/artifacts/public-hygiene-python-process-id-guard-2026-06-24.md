# Public Hygiene Python Process ID Guard - 2026-06-24

## Scope

Public hygiene review treats labeled process IDs as blocking evidence leaks.
The current-tree guard previously skipped `process_id_number` matches in Python
source, which left room for public report fixtures or copied evidence snippets
in tests to carry raw `pid=<number>` style text.

## Change

- Remove the Python-source exemption from current-tree scans in
  `scripts/review_public_hygiene.py`.
- Keep the existing pending-history compatibility for Python fixture commits so
  this non-destructive batch does not require rewriting local-only history.
- Keep mock process semantics by constructing synthetic PID values in tests
  instead of committing raw labeled PID literals.
- Add a regression case proving a tracked Python source file containing a
  labeled process ID is flagged and redacted in public-safe output.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py tests\unit\test_scenario_integration.py tests\unit\test_process_module_multi_app.py -q`
  - `98 passed`
- `.\.venv\Scripts\python.exe -m ruff check scripts\review_public_hygiene.py tests\unit\test_public_repo_hygiene.py tests\unit\test_scenario_integration.py tests\unit\test_process_module_multi_app.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --skip-history --redact-samples`
  - passed

## Public Safety

This artifact records only synthetic placeholder values. It contains no local
absolute paths, raw process IDs, worker/thread IDs, account data, secrets, or
raw Kit log snippets.
