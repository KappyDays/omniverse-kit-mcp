# Scenario Official Asset Bounded Highlights — 2026-06-24

## Scope

`scenario_last_report(report_format="markdown")` now surfaces the bounded
official asset diagnostics that the `official_asset_*` tools already return in
JSON:

- catalog availability hints: `available_kinds`, status counts, and sample names
- sync-status profile hints: catalog vs matching status counts
- verify failure checks: asset load-quality checks and material binding checks

## Why

Agents commonly triage scenario failures from Markdown before opening exact
JSON. Without these bounded highlights, official catalog misses and verify
failures had useful machine-readable diagnostics that were easy to overlook.

## Validation

Static/unit validation should cover:

- `tests/unit/test_scenario_integration.py::test_markdown_highlights_official_asset_bounded_diagnostic_details`
- existing official asset scenario report tests
- `scripts/verify_mcp_sync.py`
- public hygiene scan before any push
