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
  `evidence_kind` or `step_id`, and must tell operators to use `step_id` for
  row-specific failure fields such as `error_code` when multiple rows share an
  `evidence_kind`.
- `--expect-live-diagnostic-field` help must say it reads
  `diagnostic_next_actions` fields formatted as `step_id:key=value`.
- `scripts/CLAUDE.md` must mirror help grammar for step-scoped assertions:
  `--expect-live-failure-step-error step_id=ERROR_CODE`,
  `--expect-live-diagnostic-field step_id:key=value`,
  `--expect-retry-key-arg step_id:key=value`, and
  `--expect-automatic-cleanup-timeout step_id=seconds`.

## Evidence

- Updated `scripts/probe_mcp_surface.py` help so failed-row `error_code`
  assertions are visibly step-scoped when evidence kinds are shared.
- Updated `scripts/CLAUDE.md` so the script table uses the same `step_id`
  grammar as `probe_mcp_surface.py --help` for failure, diagnostic, retry, and
  cleanup expectations while keeping evidence `selector` grammar distinct.
- Guarded by
  `tests/unit/test_standalone_scripts.py::test_mcp_probe_help_names_log_capture_stop_boundary`.
- Current targeted result:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py::test_mcp_probe_help_names_log_capture_stop_boundary -q`
  passed.
- The `probe_mcp_surface.py --help` output confirmed the CLI help uses
  `step_id=ERROR_CODE`, `step_id:key=value`, and `step_id=seconds` for
  step-scoped assertions, plus `Use step_id for row-specific failure fields
  such as error_code` for evidence-field assertions.
- `rg -n -- "--expect-(retry-key-arg|live-diagnostic-field|live-failure-step-error|automatic-cleanup-timeout) step(:|=)" scripts docs tests`
  returned no matches.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `948 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.

## Public Boundary

- Static/unit validation only.
- No live scenario was run and no stage was mutated.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, Kit
  logs, generated catalog records, or capture paths are included.
