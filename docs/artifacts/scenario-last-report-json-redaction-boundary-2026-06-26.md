# Scenario Last Report JSON Redaction Boundary

Date: 2026-06-26

Scope: documentation and tool-level guard for the exact-field report boundary
used by Robot + RTX and official asset proof workflows.

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
- Strengthened `tests/unit/test_tools_registration.py::test_scenario_last_report_can_redact_local_paths`
  so `scenario_last_report(redact_local_paths=true)` uses the same redacted
  default JSON path as `scenario_last_report(report_format="json",
  redact_local_paths=true)`: `safe_default_json == safe_json`.
- Targeted result:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py::test_scenario_last_report_can_redact_local_paths tests\unit\test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_robot_rtx_public_evidence_redaction_guidance -q`
  passed: `3 passed in 1.15s`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_tools_registration.py tests\unit\test_doc_references.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `944 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.

## Public Boundary

- Static documentation/test validation only.
- No live scenario was run and no stage was mutated.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, Kit
  logs, generated catalog records, or capture paths are included.
