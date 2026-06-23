# Public Hygiene Today Audit Shortcut

Date: 2026-06-23

## Change

`scripts/review_public_hygiene.py` now supports `--today` as a shortcut for
the current local day audit. It expands to local midnight and uses the same
history scanning path as `--since`.

This keeps the default pre-push gate focused on pending local commits while
making the "review everything committed or pushed today" check easier to run
without hand-entering a date.

## Evidence

- A temporary repository test creates a redacted current tree with an earlier
  current-day history leak and verifies that `--today --head HEAD` still reports
  the history-added line.
- The existing `--since` tests remain unchanged and continue to cover explicit
  session/day audit ranges.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`:
  `11 passed`
- `.\.venv\Scripts\python.exe -m ruff check scripts\review_public_hygiene.py tests\unit\test_public_repo_hygiene.py`:
  passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD`:
  failed as expected with the existing 2026-06-23 public-history findings.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD --format json`:
  failed as expected with `finding_count=7`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`:
  `19 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`: passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py`: passed
- `git diff --check`: passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`:
  `748 passed, 16 skipped`

## Public Hygiene Note

This artifact intentionally uses only generic placeholders and command names.
It does not record local install roots, capture paths, process IDs, worker IDs,
or user-specific filesystem paths.
