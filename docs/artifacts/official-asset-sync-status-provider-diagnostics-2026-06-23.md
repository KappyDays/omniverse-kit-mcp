# Official Asset Sync Status Provider Diagnostics - 2026-06-23

## Change

`official_asset_sync_status(app_profile=...)` profile-miss diagnostics now
include `available_providers` alongside `available_profiles`. Scenario Markdown
highlights the same field, so a profile status probe and a search miss expose
the same recovery filters.

## Evidence Plan

- Unit: `tests/unit/test_asset_module.py` covers the missing-profile sync
  status diagnostics shape.
- Scenario: `tests/unit/test_scenario_integration.py` covers Markdown
  propagation for synthetic summaries and runner-produced sync status reports.
- Static/public gates: `ruff`, `scripts/verify_mcp_sync.py`,
  `scripts/review_public_hygiene.py`, and `git diff --check`.

## Live Scope

No live Isaac Sim stage mutation is needed. This is an offline catalog
diagnostics result-shape change.

## Validation Results

- Targeted diagnostics pytest: 3 passed, 92 deselected.
- Asset + scenario integration unit files: 95 passed.
- Doc integrity/reference checks: 19 passed, 2 skipped.
- `scripts/verify_mcp_sync.py`: OK, 34 sync tests passed.
- `ruff check` on touched Python files: passed.
- `scripts/review_public_hygiene.py`: passed for current tree and pending
  history.
- `scripts/review_public_hygiene.py --base origin/main --head HEAD`: passed
  for the pending push range.
- Full unit suite: 750 passed, 16 skipped.
