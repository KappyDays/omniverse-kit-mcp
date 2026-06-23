# Public Hygiene Date Audit - 2026-06-24

## Scope

`scripts/review_public_hygiene.py --today` intentionally follows the current
local date. After a long session crosses midnight, the same command no longer
audits the previous day's commits. This made the 2026-06-23 public-history
review easy to mis-run after 2026-06-24 began.

## Change

- Add `--date YYYY-MM-DD` as a named-day history range.
- Keep `--today` for the current local day.
- Keep `--since` for free-form git date expressions.
- Document `--date` in the public hygiene invariant and script guide.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`
  - `16 passed`
- `.\.venv\Scripts\python.exe -m ruff check scripts\review_public_hygiene.py tests\unit\test_public_repo_hygiene.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - `19 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-23 --head HEAD --format json --redact-samples`
  - failed as expected with `finding_count=7`, all `already_public`
- `git diff --check`
  - passed
