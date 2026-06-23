# Scenario Retry Failure Data Summary - 2026-06-23

## Scope

Scenario retry failures now retain a bounded structured `data_summary` when a
failed attempt returns module data. This complements the existing retry failure
message and prevents diagnostics such as RTX lidar readback state from depending
only on a truncated string.

The first target is `sensor.lidar_get_point_cloud` retry evidence:

- `retry_failures[].data_summary.num_points`
- `retry_failures[].data_summary.empty_reason`
- `retry_failures[].data_summary.diagnostics.cached_lidar_instance`
- `retry_failures[].data_summary.diagnostics.readback_paths_attempted`

Markdown retry failure lines also append the same compact diagnostic highlight
when the summary contains known diagnostic fields.

## Public Hygiene

- No host-local paths, worker IDs, process IDs, or temporary capture paths are
  recorded here.
- Public hygiene gates were run before commit.

## Validation

- Targeted retry tests: `2 passed`.
- Scenario integration file: `48 passed`.
- `ruff check` on touched Python files: passed.
- `git diff --check`: passed.
- `scripts/verify_mcp_sync.py`: passed, including `34 passed` catalog tests.
- Public hygiene current/pending gates: passed.
- Full unit suite: `750 passed, 16 skipped`.

## Known Public-History Gate

The current tree and pending commit range are public-safe. The day-wide public
history audit still reports the previously identified seven findings already
reachable from `origin/main`; no new finding was introduced by this batch.
