# Public Hygiene Python History PID Guard - 2026-06-24

## Scope

Public hygiene history scans must treat Python source the same way as Markdown
or JSON evidence when a commit adds a labeled process identifier. A copied
report fixture in a Python file can be just as public as a Markdown artifact.

## Change

- Remove the pending-history Python-source exemption for labeled process ID
  matches in `scripts/review_public_hygiene.py`.
- Add a regression test proving a Python source commit that adds a labeled
  process ID is reported as a redacted `history-added-line` finding.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`
  - `23 passed`
- `.\.venv\Scripts\python.exe -m ruff check scripts\review_public_hygiene.py tests\unit\test_public_repo_hygiene.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `803 passed, 16 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --skip-history --redact-samples`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --redact-samples`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --redact-samples`
  - failed as expected with only historical `already_public` findings:
    `public-ref-current=absent_from_public_ref`

## Public Safety

This artifact uses only placeholder descriptions and command forms. It does not
include raw process IDs, user paths, worker/thread IDs, secrets, or generated
local reference paths.
