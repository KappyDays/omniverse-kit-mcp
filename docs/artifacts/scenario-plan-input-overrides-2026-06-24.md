# Scenario Plan Input Overrides - 2026-06-24

## Scope

`scenario_validate` already accepted `input_overrides`, but
`scenario_plan` could only preview the scenario's default variables. That made a
pre-live plan review less reliable whenever an agent intended to validate a
robot, sensor, asset, or prim path supplied through overrides.

## Change

- Add `input_overrides` to `scenario_plan`.
- Reuse the same override application helper for `scenario_plan` and
  `scenario_validate`.
- Keep the existing plan shape while letting `variables` and expanded step
  `args` reflect the override values.
- Document that agents should pass the same override dict to plan and validate.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py::test_scenario_plan_accepts_input_overrides tests\unit\test_tools_registration.py::test_scenario_validate_dry_run_uses_plan_step_counts -q`
  - `2 passed`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; generated tool catalog stayed up to date after regeneration and 36
    sync tests passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py tests\unit\test_tools_registration.py tests\unit\test_tool_catalog_sync.py -q`
  - `55 passed, 2 skipped`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\tools\scenario_tools.py tests\unit\test_tools_registration.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `763 passed, 16 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --format json --redact-samples`
  - `finding_count=0`
- `git diff --check`
  - passed; Git reported only LF-to-CRLF working-copy warnings for edited text files

## Live Evidence

Not required. This is a compile-only scenario planning change and does not run a
live Kit scenario or mutate stage state.

## Public Hygiene

This artifact contains no local absolute paths, process IDs, worker/thread IDs,
account data, secrets, or raw Kit log snippets.
