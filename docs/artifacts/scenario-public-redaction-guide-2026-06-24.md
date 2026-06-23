# Scenario Public Redaction Guide - 2026-06-24

## Scope

Update the task-first MCP usage guide after the scenario reporter redaction path
was hardened for public live evidence.

## Change

- Document that `redact_local_paths=true` redacts host-local paths, Kit log
  filenames, process IDs, worker/thread IDs, and unstable Python object repr
  addresses.
- Keep the Robot + RTX live proof wrapper order unchanged.
- Add a doc guard so future edits keep this public-evidence guidance visible.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py -q`
  - 12 passed, 1 skipped.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - 19 passed, 2 skipped.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --format json --redact-samples`
  - `finding_count=0` for current tree and pending history.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - `finding_count=0` for the pending push range.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples`
  - `finding_count=0` for the current-day commit audit.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - Passed; generated tool catalog remained up to date and 34 sync tests passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - 757 passed, 16 skipped.
- `git diff --check`
  - Passed; Git reported only LF-to-CRLF working-copy warnings for edited docs.

## Live Evidence

Not rerun. This batch only aligns documentation with the already-tested
scenario report redaction behavior; it does not change live scenario execution,
sensor calls, or stage state.
