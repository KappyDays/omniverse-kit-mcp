# Probe Evidence Error Code Assertion Guard - 2026-06-26

## Scope

This artifact records a static probe contract guard for asserting
`evidence_summary[].error_code` through `--expect-live-evidence-field`.

## Evidence

- `scripts/probe_mcp_surface.py` already lists `error_code` in
  `LIVE_EVIDENCE_SUMMARY_FIELDS`.
- `tests/unit/test_standalone_scripts.py::test_mcp_probe_parses_expected_live_evidence_fields`
  now parses `capture_visible_result:error_code=VIEWPORT_CAPTURE_ASSERT_FAILED`.
- `tests/unit/test_standalone_scripts.py::test_mcp_probe_live_summary_keeps_public_official_asset_evidence_fields`
  now keeps `error_code` in the public live evidence summary.
- `tests/unit/test_standalone_scripts.py::test_mcp_probe_live_evidence_field_mismatches_are_empty_for_expected_value`
  now proves a `step_id:error_code=...` expectation succeeds.

## Public Boundary

This was a static/unit probe guard, not a live Kit run. It records no local absolute paths,
worker/thread IDs, process IDs, secrets, temp log paths, generated catalog JSON,
generated verification JSONL, or raw Kit logs.
