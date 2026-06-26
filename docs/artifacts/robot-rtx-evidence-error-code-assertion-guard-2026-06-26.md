# Robot RTX Evidence Error Code Assertion Guard - 2026-06-26

## Scope

This artifact records a static probe summary guard for Robot + RTX failed
evidence rows that expose `error_code`.

## Evidence

- `tests/unit/test_standalone_scripts.py::test_mcp_probe_live_summary_keeps_public_robot_rtx_evidence_fields`
  now proves Robot + RTX public evidence summaries preserve
  `read_lidar_point_cloud:error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
  and `capture_visible_result:error_code=VIEWPORT_CAPTURE_ASSERT_FAILED`.
- `docs/mcp-usage-guide.md`, `docs/invariants/scenario-validation.md`, and
  `scenarios/CLAUDE.md` keep `--expect-live-failure-step-error` as the primary
  terminal failure contract; `--expect-live-evidence-field <step>:error_code=...`
  is documented only as an optional additional assertion when present.

## Public Boundary

This was a static/unit probe guard, not a live Kit run. It records no local absolute paths,
worker/thread IDs, process IDs, secrets, temp log paths, generated catalog JSON,
generated verification JSONL, or raw Kit logs.
