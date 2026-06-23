# Official asset profile mismatch scenario coverage - 2026-06-23

## Change

- Added `get_pallet_wrong_profile` to
  `scenarios/smoke/official_asset_catalog_diagnostics.yaml`.
- The step calls `asset.official_get` with a known official asset URL and an
  intentionally unsupported `app_profile`.
- The step is `continueOnFailure: true`, so the smoke remains a passing
  diagnostics workflow while preserving the `OFFICIAL_ASSET_NOT_FOUND` report.

## Evidence target

- Scenario runner keeps the profile-mismatch diagnostics in `data_summary`.
- Markdown reports highlight:
  - `diagnostics.reason=app_profile_not_covered`
  - `diagnostics.candidate_counts.total_entries`
  - `diagnostics.candidate_counts.after_app_profile`

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q -k "official_asset_catalog_diagnostics_smoke_routes_through_runner or official_asset_diagnostics_survive_runner_failure"`
  - 2 passed, 45 deselected.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - 47 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - 19 passed, 2 skipped.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - OK, 34 passed.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py`
  - OK for the pending branch range.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - 746 passed, 16 skipped.

## Push blocker

The day/session public-history audit still reports the pre-existing 7 findings
from already-pushed commits. This batch adds no new pending public-hygiene
findings, but push remains blocked until an approved history rewrite resolves
the existing public ref.
