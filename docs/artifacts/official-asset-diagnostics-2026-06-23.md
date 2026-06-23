# Official Asset Diagnostics Contract

Date: 2026-06-23

## Scope

This batch hardens `official_asset_*` recovery paths without launching Kit or
mutating a stage. The change adds machine-readable diagnostics for these cases:

- `official_asset_search` returns zero candidates.
- `official_asset_resolve`, `official_asset_get`, or `official_asset_verify`
  cannot find the requested catalog entry.
- `official_asset_*` cannot load the ignored generated catalog.

## Result Shape

Diagnostics are exposed under `data.diagnostics` and include:

- `reason`: one of `catalog_unavailable`, `empty_catalog`, `kind_not_found`,
  `app_profile_not_covered`, `provider_not_covered`, `min_status_too_strict`,
  `only_stale_matches`, `query_no_match`, `limit_zero`, or `no_results`.
- `candidate_counts`: filter-stage counts for zero-result and not-found cases.
- `suggested_next`: bounded recovery guidance.
- `fallback_tool_order`: the preferred recovery sequence, ending with
  `asset_search` only after official catalog recovery attempts.

Existing `ok`, `status`, and `error_code` semantics are preserved.

## Verification

- `tests/unit/test_asset_module.py -q`: 40 passed.
- Focused `ruff check` for touched source/tests: passed.
- `scripts/verify_mcp_sync.py`: passed after regenerating `docs/tool-catalog.md`.
- `tests/unit/ -q`: 703 passed, 15 skipped.

## Live Evidence

No live Kit smoke was required. The change is offline catalog result-shape
hardening, and unit coverage exercises the missing/empty result paths with a
synthetic catalog.
