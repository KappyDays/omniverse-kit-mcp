# Official Asset Read-Only Result-Shape Guard

Date: 2026-06-26

Scope: unit guard for the current public official asset read-only catalog
diagnostic close-gate proof after the live workflow had already passed in
`docs/artifacts/official-asset-readonly-close-gate-live-refresh-2026-06-26.md`.

## Guarded Contract

- `tests/unit/test_doc_references.py` now asserts that the current read-only
  diagnostics artifact keeps the live result shape as `passed_steps=4`,
  `failed_steps=1`, `continued_steps=1`, `fatal_failed_steps=0`, and
  `cleanup_failed_steps=0`.
- The guard keeps the expected continued failure explicit:
  `get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND` is non-terminal only when
  paired with `--expect-live-status passed` and `fatal_failed_steps=0`.
- The guard preserves both diagnostic reason rows and the fallback order through
  `official_asset_sync_status`, `official_asset_search`,
  `official_asset_resolve`, `official_asset_verify`, and `asset_search`.
- The guard also keeps the final log-capture close metadata explicit:
  `data.capture_stop_completed=true` and
  `data.capture_stop_timed_out=false`.

## Public Boundary

This guard artifact records only relative paths, public option names,
aggregate counts, and public-safe diagnostic values. It excludes local absolute paths,
process IDs, worker/thread IDs, secrets, raw logs, local capture paths, and
generated catalog records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_official_asset_readonly_diagnostic_artifact_command_parse -q`
  passed: `2 passed in 0.04s`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `944 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
