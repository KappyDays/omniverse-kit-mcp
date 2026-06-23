# Official Asset Scenario Runner Diagnostics

Date: 2026-06-23

## Scope

This batch locks the real scenario runner path for official asset diagnostics.
A synthetic scenario runs `asset.official_resolve` through the runner with an
offline generated catalog, receives `OFFICIAL_ASSET_NOT_FOUND`, and preserves
the diagnostic payload in both JSON data summary and Markdown highlights.

## Verification

- `tests/unit/test_scenario_integration.py`: 39 passed.
- Focused `ruff check` for the scenario integration test: passed.
- `scripts/verify_mcp_sync.py`: OK.
- `tests/unit/test_doc_integrity.py tests/unit/test_doc_references.py`: 17 passed, 1 skipped.
- `tests/unit/ -q`: 705 passed, 15 skipped.
- `git diff --check`: passed.

## Live Evidence

No live Kit smoke was required. The evidence is runner-level unit coverage of
the offline official asset workflow using a synthetic catalog.
