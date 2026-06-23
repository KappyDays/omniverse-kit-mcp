# Official Asset Profile-Strict Lookup - 2026-06-23

## Scope

The official asset workflow now treats `app_profile` as a strict lookup
boundary for exact id/URL calls as well as search filters.

Before this fix, `_find_official_entry` could accept an exact asset id from a
different profile after profile filtering found no match. That made
`official_asset_get`, `official_asset_resolve`, and `official_asset_verify`
able to proceed with a catalog item that was only provided by another app
profile.

## Fixed Behavior

- `official_asset_get(asset_id, app_profile=...)` returns
  `OFFICIAL_ASSET_NOT_FOUND` when the exact item is not provided by the requested
  profile.
- `official_asset_resolve(name_or_id, app_profile=...)` follows the same strict
  boundary.
- `official_asset_verify(asset_id, app_profile=...)` also stops before live REST
  verification and reports catalog diagnostics.
- Diagnostics include `reason=app_profile_not_covered`,
  `candidate_counts.total_entries`, and `candidate_counts.after_app_profile`.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py::test_official_asset_exact_lookup_respects_requested_app_profile -q`

No live Isaac Sim stage mutation was needed for this batch; the corrected
contract is an offline catalog selection guard.
