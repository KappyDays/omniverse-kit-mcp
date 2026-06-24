# Public Hygiene Push Decision - 2026-06-24

## Scope

Make `scripts/review_public_hygiene.py` harder to misread when a session/day
audit finds history issues after commits have already reached `origin/main`.

## Change

- Add a text `push-decision` summary and JSON `push_decision` object.
- Include `normal_push_allowed` and `requires_user_approval` booleans for
  automation or agent handoff.
- Distinguish pending-push findings from already-public history findings:
  - `blocked_pending_push`
  - `blocked_current_tree`
  - `blocked_already_public_history`
  - `clean`

## Public Safety Note

This scanner change was developed while the branch still had already-public
history findings. After the user approved public-history remediation, the
rewritten branch now reports clean named-day audits; the scanner still exposes
`blocked_already_public_history` for future branches that hit the same state.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`
  - `23 passed`
- `.\.venv\Scripts\python.exe -m ruff check scripts\review_public_hygiene.py tests\unit\test_public_repo_hygiene.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --skip-history --redact-samples`
  - passed with `push-decision: clean` and `normal-push-allowed: true`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --redact-samples`
  - after approved history rewrite: passed with `push-decision: clean`
    and `normal-push-allowed: true`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --redact-samples`
  - before history rewrite: failed as expected with
    `push-decision: blocked_already_public_history` and
    `normal-push-allowed: false`
  - after approved history rewrite: passed with `push-decision: clean`
    and `normal-push-allowed: true`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-23 --head HEAD --redact-samples`
  - after approved history rewrite: passed with `push-decision: clean`
    and `normal-push-allowed: true`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py tests\unit\test_doc_integrity.py -q`
  - `23 passed, 2 skipped`
- `git diff --check`
  - passed
