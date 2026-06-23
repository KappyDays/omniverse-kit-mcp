# Official Asset Diagnostics Filter Options - 2026-06-23

## Change

`official_asset_search` no-result diagnostics now report the catalog-covered
`available_profiles` and `available_providers`. Scenario Markdown highlights
the same fields so an agent can recover from an `app_profile` or `provider`
miss without first running a separate status probe.

## Evidence Plan

- Unit: `tests/unit/test_asset_module.py` covers query miss, app-profile miss,
  and provider miss diagnostics.
- Scenario: `tests/unit/test_scenario_integration.py` covers JSON and Markdown
  propagation through the official asset diagnostics smoke path.
- Static/public gates: `ruff`, `scripts/verify_mcp_sync.py`,
  `scripts/review_public_hygiene.py`, and `git diff --check`.

## Live Scope

No live Isaac Sim stage mutation was needed for this result-shape batch. The
change is catalog diagnostics and scenario report formatting only.

## Validation Results

- Targeted diagnostics pytest: 5 passed, 90 deselected.
- Asset + scenario integration unit files: 95 passed.
- Doc integrity/reference checks: 19 passed, 2 skipped.
- `scripts/verify_mcp_sync.py`: OK, 34 sync tests passed.
- `ruff check` on touched Python files: passed.
- `scripts/review_public_hygiene.py`: passed for current tree and pending
  history.
- `scripts/review_public_hygiene.py --base origin/main --head HEAD`: passed
  for the pending push range.
- Full unit suite: 750 passed, 16 skipped.
- `scripts/review_public_hygiene.py --today --head HEAD`: still reports the
  pre-existing public-history findings documented in the remediation plan; no
  new finding was introduced by this batch.
