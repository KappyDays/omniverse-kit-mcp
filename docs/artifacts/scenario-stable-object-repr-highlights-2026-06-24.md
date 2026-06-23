# Scenario Stable Object Repr Highlights - 2026-06-24

## Scope

Harden Markdown scenario reports after the Robot + RTX current-head live smoke
showed a runtime object representation in `Data Summary Highlights`.

The raw JSON report should keep exact result data for debugging. The Markdown
triage report should avoid unstable Python memory addresses such as
`<some.module.Type object at 0x...>`, because those addresses change every run
and are not useful public evidence.

## Change

- Normalize Python object repr scalars only in Markdown summary formatting.
- Preserve JSON `scenario_last_report` output exactly.
- Cover the behavior with a unit test that uses a representative Hydra texture
  object repr from live RTX/viewport capture metadata.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `50 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - `33 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; tool catalog stayed up to date
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `755 passed, 16 skipped`
- `git diff --check`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - passed with `finding_count=0`
