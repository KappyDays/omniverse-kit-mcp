# Probe Live Help Report Boundary

Date: 2026-06-26

Scope: static/unit guard that `probe_mcp_surface.py --help` describes the same
report boundary used by live wrapper execution.

## Contract

`--scenario-validate-live` help must name both:

- `scenario_validate(report_format=json, redact_local_paths=true)` for live
  exact-field assertions.
- `scenario_last_report(report_format=markdown, redact_local_paths=true)` for
  compact public-safe Markdown evidence.
- `--expect-live-evidence-field` help must say selectors match either
  `evidence_kind` or `step_id`.
- `--expect-live-diagnostic-field` help must say it reads
  `diagnostic_next_actions` fields formatted as `step_id:key=value`.

## Evidence

- Updated `scripts/probe_mcp_surface.py` earlier; current refresh strengthens
  the help-output test assertions without changing runtime code.
- Guarded by
  `tests/unit/test_standalone_scripts.py::test_mcp_probe_help_names_log_capture_stop_boundary`.
- Current targeted result:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py::test_mcp_probe_help_names_log_capture_stop_boundary tests\unit\test_standalone_scripts.py::test_mcp_probe_parses_expected_live_diagnostic_fields tests\unit\test_standalone_scripts.py::test_mcp_probe_main_wires_live_assertion_options tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: `5 passed in 1.01s`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_standalone_scripts.py tests\unit\test_doc_references.py`
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

- Static/unit validation only.
- No live scenario was run and no stage was mutated.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, Kit
  logs, generated catalog records, or capture paths are included.
