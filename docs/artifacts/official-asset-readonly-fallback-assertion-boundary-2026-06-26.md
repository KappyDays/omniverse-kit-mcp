# Official Asset Read-Only Fallback Assertion Boundary

Date: 2026-06-26

Scope: docs/test guard that official asset read-only diagnostic proof guidance
uses exact `probe_mcp_surface.py --expect-live-diagnostic-field` assertions for
both diagnostic rows' `diagnostics.fallback_tool_order` values.

## Guarded Contract

- `scenarios/CLAUDE.md` must name the exact fallback assertion for
  `search_known_miss`.
- `scenarios/CLAUDE.md` must name the exact fallback assertion for
  `get_pallet_wrong_profile`.
- `docs/invariants/scenario-validation.md` must keep the same exact assertions
  in the durable scenario validation rule.
- `docs/tool-diagnostic-map.md` must keep the same exact assertions in the
  failure triage route, not a prose-only list.
- `docs/references/official-asset-catalog.md` and
  `docs/invariants/asset-discovery.md` must keep the same exact assertions so
  official asset pull-doc readers see the same proof criteria before reaching
  the usage guide.
- `docs/mcp-usage-guide.md` remains the canonical command source for the full
  read-only wrapper.

## Public Boundary

This artifact records only relative documentation paths, public scenario step
IDs, public diagnostic field names, and public tool names. It excludes local
absolute paths, process IDs, worker/thread IDs, secrets, raw logs, local capture
paths, and generated catalog records; no local absolute paths are included.

## Verification

- `python -m pytest tests/unit/test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order tests/unit/test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests/unit/test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: 3 tests.
- `python -m ruff check tests/unit/test_doc_references.py` passed.
- `rg "...:diagnostics.fallback_tool_order|diagnostics.fallback_tool_order=[official_asset_sync_status" docs/references/official-asset-catalog.md docs/invariants/asset-discovery.md docs/invariants/scenario-validation.md docs/tool-diagnostic-map.md scenarios/CLAUDE.md`
  returned no matches.
- `python scripts/verify_mcp_sync.py` passed: registration/catalog sync green,
  37 tests.
- `python -m pytest tests/unit/ -q` passed: 945 tests, 16 skipped.
- `git diff --check` passed.
- `python scripts/review_public_hygiene.py --redact-samples` passed.
