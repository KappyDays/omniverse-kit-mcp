# Official Asset Evidence Error Code Guard - 2026-06-26

## Scope

This artifact records a static reporter/result-shape guard for official asset
verification evidence rows. The goal is to keep `error_code` available in
`scenario_last_report(redact_local_paths=true)` JSON `evidence_summary[]` and
Markdown `Evidence Summary` whenever the underlying `StepResult` has an error
code, while keeping successful `load_verified` rows error-code-free.

## Evidence

- `src/omniverse_kit_mcp/scenario/reporters.py` now carries
  `StepResult.error_code` into evidence rows before formatting.
- `tests/unit/test_scenario_integration.py::test_official_asset_verify_evidence_summary_preserves_error_type`
  now asserts both JSON `evidence_summary[].error_code` and Markdown
  `error_code=...` output for an official asset verify timeout-shaped record.
- `tests/unit/test_standalone_scripts.py::test_mcp_probe_live_summary_keeps_public_official_asset_evidence_fields`
  now separates the successful `verify_pallet_asset` row from a failed
  `verify_timeout_asset` row so public summaries preserve `error_code` only for
  timeout/failure-shaped evidence.
- `tests/unit/test_scenario_integration.py::test_official_asset_verify_live_smoke_routes_through_runner`
  now asserts the successful `load_verified` evidence row does not include
  `error_code`.
- `docs/mcp-usage-guide.md`, `docs/invariants/scenario-validation.md`, and
  `docs/tool-diagnostic-map.md` now tell operators to inspect
  `evidence_summary[].error_code` when present.

## Public Boundary

This was a static/unit reporter guard, not a live Kit run. It records no local absolute paths,
worker/thread IDs, process IDs, secrets, temp log paths,
generated catalog JSON, generated verification JSONL, or raw Kit logs.
