# Official Asset Sync Status Diagnostics

Date: 2026-06-23

## Scope

This batch adds diagnostics to `official_asset_sync_status(app_profile=...)`
when the generated catalog is present but the requested app profile is not
covered, or the covered profile has no matching entries.

The response remains `ok=true` and keeps the existing counts/profile fields. It
adds `data.diagnostics` with:

- `reason`
- `requested_app_profile`
- `available_profiles`
- `matching_item_count`
- `suggested_next`
- `fallback_tool_order`

## Verification

- `tests/unit/test_asset_module.py`: 41 passed.
- Focused `ruff check` for touched source/tests: passed.
- `scripts/verify_mcp_sync.py`: OK.
- `tests/unit/test_doc_integrity.py tests/unit/test_doc_references.py`: 17 passed, 1 skipped.
- `tests/unit/ -q`: 706 passed, 15 skipped.
- `git diff --check`: passed.

## Live Evidence

No live Kit smoke was required. This is an offline result-shape contract update
covered by synthetic generated-catalog tests.
