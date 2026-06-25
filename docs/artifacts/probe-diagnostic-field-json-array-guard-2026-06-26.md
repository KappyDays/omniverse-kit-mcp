# Probe Diagnostic Field JSON Array Guard

Date: 2026-06-26

Scope: unit guard for `scripts/probe_mcp_surface.py` diagnostic field assertions
that compare JSON-array values such as `diagnostics.fallback_tool_order`.

## Guarded Contract

- `--expect-live-diagnostic-field step_id:key=value` JSON-decodes `value` when
  possible, including array values used by Robot + RTX and official asset
  fallback-order assertions.
- `_live_diagnostic_field_mismatches` compares decoded array values directly
  against `diagnostic_next_actions[]` rows instead of stringifying them.
- `main()` passes repeated `--expect-live-diagnostic-field` CLI values through to
  `probe(...)` with decoded values intact.
- `docs/mcp-usage-guide.md` links this guard beside the Robot + RTX diagnostic
  assertion artifacts so new agents can rely on JSON-array fallback-order
  assertions.

## Public Boundary

This artifact records only relative documentation paths, public option names,
and rule text. It excludes local absolute paths, process IDs, worker/thread IDs,
secrets, raw logs, local capture paths, and generated catalog records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py::test_mcp_probe_parses_expected_live_diagnostic_fields tests\unit\test_standalone_scripts.py::test_mcp_probe_live_diagnostic_field_mismatches_are_empty_for_expected_value tests\unit\test_standalone_scripts.py::test_mcp_probe_main_wires_live_assertion_options tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: `5 passed in 0.99s`.
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
