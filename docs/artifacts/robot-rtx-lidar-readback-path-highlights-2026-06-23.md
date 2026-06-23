# Robot RTX Lidar Readback Path Highlights - 2026-06-23

## Change

Scenario Markdown `Data Summary Highlights` now includes
`diagnostics.cached_lidar_instance` and
`diagnostics.readback_paths_attempted` when RTX lidar readback diagnostics
provide them.

## Why

Live RTX lidar failures depend heavily on whether the cached `LidarSensor`
readback path was available and whether the fallback replicator annotator path
was attempted. Surfacing those fields in the report lets agents triage empty
scan buffers before opening logs.

## Evidence Plan

- `tests/unit/test_scenario_integration.py` covers the retry path and asserts
  the Markdown highlight includes the readback diagnostics.
- `docs/invariants/scenario-validation.md` lists the fields to inspect before
  logs.
- Static/public gates guard against doc drift and path leakage.

## Live Scope

No live Isaac Sim stage mutation is needed. This batch improves scenario
reporting for diagnostics already returned by the RTX lidar service.

## Validation Results

- Targeted retry scenario test: 1 passed.
- Scenario integration tests: 48 passed.
- Doc integrity/reference checks: 19 passed, 2 skipped.
- `ruff check` on touched Python files: passed.
- `scripts/verify_mcp_sync.py`: OK, 34 sync tests passed.
- `scripts/review_public_hygiene.py`: passed for current tree and pending
  history.
- `scripts/review_public_hygiene.py --base origin/main --head HEAD`: passed
  for the pending push range.
- Full unit suite: 750 passed, 16 skipped.
- `scripts/review_public_hygiene.py --today --head HEAD`: still reports the
  pre-existing public-history findings; this batch introduced no new finding.
