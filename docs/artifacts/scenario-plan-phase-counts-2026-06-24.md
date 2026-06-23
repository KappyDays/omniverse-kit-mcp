# Scenario Plan Phase Counts

Date: 2026-06-24
Batch: scenario plan phase count visibility

## Change

`scenario_plan` now includes `total_steps` and per-phase `phase_counts` before the expanded `phases` payload.

## Why

Robot and RTX sensor workflows are long enough that agents should confirm the expected arrange, act, assert, and cleanup shape before mutating a live stage. Exposing counts directly in the tool result makes this check less fragile than manually counting expanded plan arrays.

## Verification

- Unit coverage pins phase counts for a small fixture scenario.
- The robot + RTX golden workflow unit path pins the current compiled `31` total steps and `11/9/5/6` phase split.
- `python -m pytest tests/unit/test_scenario_runner.py tests/unit/test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_routes_through_runner -q`: 11 passed.
- `python -m ruff check src/omniverse_kit_mcp/tools/scenario_tools.py tests/unit/test_scenario_runner.py tests/unit/test_scenario_integration.py`: passed.
- `python -m pytest tests/unit/test_doc_integrity.py tests/unit/test_doc_references.py tests/unit/test_scenario_runner.py tests/unit/test_scenario_integration.py -q`: 79 passed, 2 skipped.
- `python scripts/verify_mcp_sync.py`: passed, 34 sync tests.
- `python scripts/review_public_hygiene.py --format json --redact-samples`: finding_count 0.
- `python -m pytest tests/unit/ -q`: 761 passed, 16 skipped.
- `git diff --check`: passed with Windows line-ending warnings only.

## Public Hygiene

This artifact contains no live worker IDs, account data, local absolute paths, process IDs, or generated Kit log snippets.
