# Scenario Sync Status Profile Highlights

Date: 2026-06-23

## Scope

This batch extends scenario Markdown diagnostics for
`official_asset_sync_status(app_profile=...)` recovery. When sync-status
diagnostics are present, `Data Summary Highlights` now include:

- `diagnostics.requested_app_profile`
- `diagnostics.available_profiles`
- `diagnostics.matching_item_count`

The existing `diagnostics.reason`, `suggested_next`, and
`diagnostics.fallback_tool_order` highlights remain unchanged.

## Verification

- `tests/unit/test_scenario_integration.py`: 40 passed.
- Focused `ruff check` for reporter/tests: passed.
- `scripts/verify_mcp_sync.py`: OK.
- `tests/unit/test_doc_integrity.py tests/unit/test_doc_references.py`: 17 passed, 1 skipped.
- `tests/unit/ -q`: 707 passed, 15 skipped.
- `git diff --check`: passed.

## Live Evidence

No live Kit smoke was required. This is an offline scenario-report formatting
contract update covered by synthetic summary tests.
