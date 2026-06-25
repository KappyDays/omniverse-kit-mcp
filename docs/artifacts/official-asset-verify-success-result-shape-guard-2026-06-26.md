# Official Asset Verify Success Result-Shape Guard

Date: 2026-06-26

Scope: unit guard for the current public official asset verify close-gate
success proof after the live workflow had already passed in
`docs/artifacts/official-asset-verify-close-gate-live-refresh-2026-06-26.md`.

## Guarded Contract

- `tests/unit/test_doc_references.py` now asserts that the current official
  verify success artifact keeps the live result shape as `passed_steps=5`,
  `failed_steps=0`, `continued_steps=0`, `fatal_failed_steps=0`, and
  `cleanup_failed_steps=0`.
- The same guard keeps the evidence row anchored to
  `official_asset_verify` with `verification_status=load_verified`,
  `kind=asset`, `app_profile=isaac-sim`, and
  `load_quality=content_verified_no_bbox`.
- The guard preserves compact row details used by doc-only replay:
  `step_id=verify_pallet_asset`, `attempts=1/1`, and `retry_count=1`.
- The guard also keeps the final log-capture close metadata explicit:
  `data.capture_stop_completed=true` and
  `data.capture_stop_timed_out=false`.

## Public Boundary

This guard artifact records only relative paths, public evidence-field names,
aggregate counts, and public-safe status values. It excludes local absolute paths,
process IDs, worker/thread IDs, raw logs, local capture paths, secrets, and
generated catalog records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_official_asset_field_artifact_live_probe_command_parse -q`
  passed: `2 passed in 0.04s`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `936 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
