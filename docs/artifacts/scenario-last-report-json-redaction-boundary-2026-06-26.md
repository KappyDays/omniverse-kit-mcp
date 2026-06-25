# Scenario Last Report JSON Redaction Boundary

Date: 2026-06-26

Scope: documentation/static guard for the exact-field report boundary used by
Robot + RTX and official asset proof workflows.

## Contract

- `scenario_last_report` defaults to JSON because its tool signature uses
  `report_format="json"`.
- Public exact-field copies should call
  `scenario_last_report(redact_local_paths=true)` so JSON fields remain
  machine-checkable while local paths, process IDs, and worker/thread IDs are
  redacted.
- Redacted Markdown remains the compact public triage/report form:
  `scenario_last_report(report_format="markdown", redact_local_paths=true)`.

## Evidence

- Updated `docs/mcp-usage-guide.md`, `docs/invariants/scenario-validation.md`,
  `docs/references/official-asset-catalog.md`, `docs/tool-diagnostic-map.md`,
  and `scenarios/CLAUDE.md`.
- Added unit assertions in `tests/unit/test_doc_references.py`.
- Targeted result:
  `tests\unit\test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order`
  passed.

## Public Boundary

- Static documentation/test validation only.
- No live scenario was run and no stage was mutated.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, Kit
  logs, generated catalog records, or capture paths are included.
