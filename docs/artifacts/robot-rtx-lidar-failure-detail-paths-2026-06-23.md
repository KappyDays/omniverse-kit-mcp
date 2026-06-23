# Robot RTX Lidar Failure Detail Paths - 2026-06-23

## Scope

Small result-shape hardening batch for RTX lidar read failures.

When `sensor_lidar_get_point_cloud` fails because `min_points` is not met, the
failure message now preserves the readback diagnostics already returned by the
extension:

- `cached_lidar_instance`
- `readback_paths_attempted`

This makes scenario retry failures more actionable without opening Kit logs
first. The fields are especially useful when distinguishing a cached
`LidarSensor` readback path from the replicator annotator fallback.

## Public Hygiene

- No local install roots, temp capture paths, process IDs, or worker IDs are
  recorded here.
- Public hygiene gates were run before commit.

## Validation

- Targeted retry/message tests: `3 passed`.
- Sensor + scenario integration files: `60 passed`.
- `ruff check` on touched Python files: passed.
- `git diff --check`: passed.
- `scripts/verify_mcp_sync.py`: passed, including `34 passed` catalog tests.
- Public hygiene current/pending gates: passed.
- Full unit suite: `750 passed, 16 skipped`.

## Known Public-History Gate

The current tree and pending commit range are public-safe. The day-wide public
history audit still reports the previously identified seven findings already
reachable from `origin/main`; no new finding was introduced by this batch.
