# Scenario Official Asset Next Actions — 2026-06-24

## Scope

`diagnostic_next_actions` now preserves bounded official verify failure context:

- `diagnostics.target_status`
- `diagnostics.current_catalog_status`
- `diagnostics.error_type`
- `diagnostics.asset_checks`
- `diagnostics.material_checks`

## Why

Agents often read the top-level JSON `diagnostic_next_actions` queue before
opening each step's full `data_summary`. Official verify failures already
reported detailed checks, but those checks were not carried into the next-action
queue.

## Validation

Static/unit validation should cover:

- `tests/unit/test_scenario_integration.py::test_markdown_highlights_official_asset_bounded_diagnostic_details`
- existing diagnostic next-action tests
- public hygiene scan before push
