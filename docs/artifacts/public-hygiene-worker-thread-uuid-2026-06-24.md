# Public Hygiene Worker Thread UUID Guard - 2026-06-24

## Scope

Strengthen the public repository hygiene gate after manual review found that a
labeled worker/thread UUID fixture could pass the existing path/secret checks.

## Change

- Add a `worker_thread_uuid` detector for values labeled as `thread_id`,
  `worker_id`, `worker_thread_id`, `pendingWorktreeId`, or
  `pending_worktree_id`.
- Limit the detector to UUID-shaped values so ordinary asset IDs and synthetic
  example labels do not become broad false positives.
- Redact matched samples as `<sensitive-id:worker_thread_uuid>` in public-safe
  review output.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`
  - 18 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_public_repo_hygiene.py -q`
  - 25 passed, 1 skipped.
- `.\.venv\Scripts\python.exe -m ruff check scripts\review_public_hygiene.py tests\unit\test_public_repo_hygiene.py`
  - Passed.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --format json --redact-samples`
  - `finding_count=0` for current tree and pending history.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - `finding_count=0` for the pending push range.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples`
  - `finding_count=0` for the current-day commit audit.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - Passed; generated tool catalog remained up to date and 34 sync tests passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - 759 passed, 16 skipped.
- `git diff --check`
  - Passed; Git reported only LF-to-CRLF working-copy warnings for edited text files.

## Live Evidence

Not required. This batch only changes repository hygiene scanning and unit tests;
it does not touch live Kit, scenario execution, or stage state.
