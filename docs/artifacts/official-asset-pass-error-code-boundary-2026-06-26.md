# Official Asset Pass Error Code Boundary - 2026-06-26

## Scope

This artifact records the official asset live proof boundary for
`evidence_summary[].error_code`: successful `load_verified` proof rows should be
error-code-free, while failed or timeout-shaped evidence rows may preserve and
assert `error_code` and nested diagnostics with a concrete `step_id` selector.

## Evidence

- `docs/mcp-usage-guide.md`, `docs/invariants/scenario-validation.md`,
  `docs/invariants/asset-discovery.md`,
  `docs/references/official-asset-catalog.md`, `scenarios/CLAUDE.md`, and
  `src/omniverse_kit_mcp/modules/integration-facts.md` now state that the
  canonical successful official asset pass command must not add
  `official_asset_verify:error_code=...`.
- `tests/unit/test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order`
  guards that the canonical successful official asset live probe command stays
  free of `official_asset_verify:error_code` while the surrounding docs and
  module integration facts explain that failed rows can assert `error_code` by
  `step_id`.
- `tests/unit/test_standalone_scripts.py::test_mcp_probe_live_summary_keeps_public_official_asset_evidence_fields`
  separates the successful `verify_pallet_asset` row from a failed
  `verify_timeout_asset` row and keeps public-safe nested diagnostics such as
  `diagnostics.error_type` on the failed evidence row.
- `tests/unit/test_scenario_integration.py::test_official_asset_verify_live_smoke_routes_through_runner`
  asserts the successful `load_verified` evidence row does not include
  `error_code`.

## Public Boundary

This is a docs/static result-shape guard, not a live Kit run. It records no raw
Kit logs, worker/thread IDs, process IDs, local absolute paths, secrets,
generated catalog JSON, or generated verification JSONL.
