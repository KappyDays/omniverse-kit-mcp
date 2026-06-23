# Scenario Diagnostic Reason Highlights

Date: 2026-06-23

## Scope

This batch carries nested MCP diagnostics into scenario Markdown triage. When a
step data summary contains nested diagnostics, Markdown reports now highlight:

- `diagnostics.reason`
- `suggested_next`
- `diagnostics.fallback_tool_order`

This is intended for `official_asset_*` zero-result/not-found recovery and keeps
the existing RTX lidar `suggested_next` path intact.

## Verification

- `tests/unit/test_scenario_integration.py`: 38 passed.
- `tests/unit/test_scenario_integration.py tests/unit/test_doc_integrity.py tests/unit/test_doc_references.py`: 55 passed, 1 skipped.
- `scripts/verify_mcp_sync.py`: OK.
- `tests/unit/ -q`: 704 passed, 15 skipped.
- `git diff --check`: passed.

## Live Evidence

No live Kit smoke was required. This is an offline reporter/documentation
contract update covered by synthetic scenario summary tests.
