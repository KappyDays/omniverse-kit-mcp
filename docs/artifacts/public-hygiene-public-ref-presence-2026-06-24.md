# Public Hygiene Public Ref Presence - 2026-06-24

## Scope

Improve the public history audit so `already_public` findings also explain
whether the same class of finding is still present at the current public ref
tip. This helps separate two cases:

- reachable public history only
- current public ref tree still contains the finding

## Change

- Add `public_presence` to history findings.
- Add text and JSON `public_presence_counts`.
- Report `present_on_public_ref` when the current public ref file still matches
  the same finding label.
- Report `absent_from_public_ref` when the finding remains in reachable history
  but no longer appears at the public ref tip.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`
  - `22 passed`
- `.\.venv\Scripts\python.exe -m ruff check scripts\review_public_hygiene.py tests\unit\test_public_repo_hygiene.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --redact-samples`
  - failed as expected with `reachability: already_public=1`
  - now also reports `public-ref-current: present_on_public_ref=1`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples`
  - failed as expected with `public_presence_counts.present_on_public_ref=1`

## Public Safety

This artifact records only redacted scan output categories, counts, and command
forms. It does not include raw process IDs, user paths, secrets, worker/thread
IDs, or generated local reference paths.
