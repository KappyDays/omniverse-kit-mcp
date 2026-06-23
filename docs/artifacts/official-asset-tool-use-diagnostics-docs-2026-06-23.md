# Official Asset Tool-Use Diagnostics Docs

Date: 2026-06-23

## Scope

This batch aligns the official asset reference docs with the diagnostics result
shape added for `official_asset_*` recovery:

- `data.diagnostics.reason`
- `candidate_counts`
- `suggested_next`
- `fallback_tool_order`

It also points scenario users to Markdown report highlights for the same fields.

## Verification

- `tests/unit/test_doc_integrity.py tests/unit/test_doc_references.py`: 17 passed, 1 skipped.
- `scripts/verify_mcp_sync.py`: OK.
- `tests/unit/ -q`: 705 passed, 15 skipped.
- `git diff --check`: passed.

## Live Evidence

No live Kit smoke was required. This is documentation-only guidance for an
already unit-covered offline result-shape workflow.
