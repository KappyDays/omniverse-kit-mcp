# Scenario Plan Timeout Metadata

Date: 2026-06-24
Batch: scenario plan timeout visibility

## Change

`scenario_plan` now includes a step-level `timeoutSeconds` field when a step overrides the scenario default timeout. The scenario-level default remains in `defaults.step_timeout_s`.

## Why

Robot and RTX sensor workflows often contain long-running or timing-sensitive steps. Agents need to see timeout overrides before executing a live scenario so they can catch suspicious values during plan review instead of discovering them during `scenario_validate`.

## Verification

- `python -m pytest tests/unit/test_scenario_runner.py -q`: 9 passed.
- `python -m pytest tests/unit/test_doc_integrity.py tests/unit/test_scenario_runner.py -q`: 16 passed, 1 skipped.
- `python -m ruff check src/omniverse_kit_mcp/tools/scenario_tools.py tests/unit/test_scenario_runner.py`: passed.
- `python scripts/verify_mcp_sync.py`: passed, 34 sync tests.
- `python scripts/review_public_hygiene.py --format json --redact-samples`: finding_count 0.
- `python -m pytest tests/unit/ -q`: 760 passed, 16 skipped.
- `git diff --check`: passed with Windows line-ending warnings only.

## Public Hygiene

This artifact contains no live worker IDs, account data, local absolute paths, process IDs, or generated Kit log snippets.
