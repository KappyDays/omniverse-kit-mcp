# Public Hygiene Reachability Classification

Date: 2026-06-23

## Change

`scripts/review_public_hygiene.py` now annotates history-added findings with
the commit SHA and `reachability`:

- `already_public`: the offending commit is reachable from the current upstream
  or `origin/main`.
- `pending_push`: the offending commit is in the scanned local range but is not
  reachable from the public ref.
- `unknown`: no public ref is available for the scanned repository.

JSON output also includes `public_ref` and `reachability_counts`, so pre-push
reviews can distinguish "do not push this local range" from "already public,
prepare a non-destructive rewrite plan".

## Validation Plan

- `tests/unit/test_public_repo_hygiene.py` adds a temporary repository case that
  creates one public-ref-reachable leak and one local-only leak, then verifies
  the JSON reachability counts.
- Current repo gates should continue to report zero findings for
  `origin/main..HEAD`, while `--today` should still report the known already
  public findings until an approved history rewrite occurs.

## Public Hygiene Note

This artifact uses only generic placeholders and does not record local install
roots, user temp paths, process IDs, worker IDs, or raw generated cache paths.
