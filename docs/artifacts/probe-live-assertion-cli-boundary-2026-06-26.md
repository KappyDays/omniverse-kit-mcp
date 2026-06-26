# Probe Live Assertion CLI Boundary

Date: 2026-06-26

Scope: unit guard for `scripts/probe_mcp_surface.py` live assertion options
after Robot/RTX and official asset workflows started relying on
`--expect-live-evidence-field`, `--expect-live-evidence-field-min`, and
`--expect-live-diagnostic-field`.

## Guarded Contract

- `tests/unit/test_standalone_scripts.py` now asserts that live assertion
  options exit with code `2` before calling `probe()` unless
  `--scenario-validate-live` is present.
- The guarded options are `--expect-live-status`,
  `--expect-live-evidence-kind`, `--expect-live-evidence-field`,
  `--expect-live-evidence-field-min`, `--expect-live-cleanup-failures`,
  `--expect-live-failure-step-error`,
  `--expect-live-diagnostic-next-actions-min`, and
  `--expect-live-diagnostic-field`.
- This keeps dry-run-only probe commands from accidentally claiming live
  evidence, diagnostics, cleanup, or failure-step proof.
- `--expect-live-evidence-field` can assert public-safe dotted evidence fields
  preserved in the compact live summary, such as
  `<step_id>:diagnostics.error_type=TimeoutError`; row-specific failure fields
  should use the concrete `step_id` selector when multiple evidence rows share
  an `evidence_kind`.
- The compact live summary preserves the same bounded nested evidence
  diagnostics exposed by `scenario_last_report` for official asset verify and
  RTX lidar evidence rows, including target/current status, `error_type`,
  `suggested_next`, fallback order, asset/material checks, lidar `min_points`,
  cached-lidar state, and readback paths.
- Evidence field assertions resolve dotted keys through the same
  `_summary_field_value` helper used by compact summaries, so
  `--expect-live-evidence-field <step_id>:diagnostics.error_type=TimeoutError`
  matches both flat `diagnostics.error_type` rows and nested
  `{"diagnostics": {"error_type": "TimeoutError"}}` rows.
- Diagnostic field assertions use the same dotted-key resolution, so
  `--expect-live-diagnostic-field <step_id>:diagnostics.fallback_tool_order=...`
  matches either flat summary rows or nested `diagnostics` objects.
- Minimum evidence field assertions use the same dotted-key resolution for
  numeric thresholds, so
  `--expect-live-evidence-field-min <step_id>:diagnostics.min_points=512`
  can validate nested numeric diagnostic values when a workflow chooses to
  threshold one.
- `--scenario-validate-live` itself exits with code `2` unless
  `--scenario-validate-dry-run` is present, even when `--workspace` and
  `--scenario-plan` are already provided.

## Public Boundary

This artifact records only relative paths, option names, exit codes, and
public-safe test behavior. It excludes local absolute paths, process IDs,
worker/thread IDs, secrets, raw logs, local capture paths, and generated
catalog records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py::test_mcp_probe_main_rejects_live_mode_without_dry_run tests\unit\test_standalone_scripts.py::test_mcp_probe_main_rejects_live_assertions_without_live_mode tests\unit\test_standalone_scripts.py::test_mcp_probe_main_wires_live_assertion_options -q`
  passed: `10 passed in 0.71s`.
- Current dotted evidence refresh:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py::test_mcp_probe_parses_expected_live_evidence_fields tests\unit\test_standalone_scripts.py::test_mcp_probe_live_evidence_field_mismatches_are_empty_for_expected_value tests\unit\test_standalone_scripts.py::test_mcp_probe_live_evidence_field_minimum_mismatches_are_empty tests\unit\test_standalone_scripts.py::test_mcp_probe_main_wires_live_assertion_options tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact -q`
  passed: `5 passed in 0.95s`.
- Current minimum dotted evidence refresh:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py::test_mcp_probe_live_evidence_field_minimum_mismatches_are_empty tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact -q`
  passed: `2 passed`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_standalone_scripts.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `948 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
