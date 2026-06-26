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
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_standalone_scripts.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `946 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
