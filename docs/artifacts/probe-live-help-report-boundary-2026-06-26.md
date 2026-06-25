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

## Evidence

- Updated `scripts/probe_mcp_surface.py`.
- Guarded by
  `tests/unit/test_standalone_scripts.py::test_mcp_probe_help_names_log_capture_stop_boundary`.
- Targeted result: `2 passed` for the help-boundary and official asset wrapper
  doc-reference tests.

## Public Boundary

- Static/unit validation only.
- No live scenario was run and no stage was mutated.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, Kit
  logs, generated catalog records, or capture paths are included.
