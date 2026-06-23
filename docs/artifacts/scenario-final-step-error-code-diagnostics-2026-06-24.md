# Scenario Final Step Error-Code Diagnostics - 2026-06-24

## Purpose

Lock the scenario report contract so final failed steps preserve their
`ModuleResult.error_code` in `step_results[]` and root
`diagnostic_next_actions[]`.

## Change

- `StepResult` now carries an optional `error_code`.
- `ScenarioRunner` copies `ModuleResult.error_code` into each executed step
  result and labels hard timeout/exception cleanup failures.
- JSON reports omit `error_code` when it is absent, preserving the existing
  passed-step shape.

## Evidence

- `tests/unit/test_scenario_integration.py::test_report_preserves_failed_step_next_action_error_code`
  verifies a final failed lidar step exposes
  `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS` in both the step result and the
  root diagnostic queue.
- `tests/unit/test_scenario_integration.py::test_scenario_runner_rejects_retries_without_idempotent_flag`
  verifies runner-created module errors are propagated into `StepResult`.

## Public Hygiene

No live worker IDs, local absolute paths, process IDs, secrets, raw Kit logs, or
unredacted generated catalog paths are recorded here.
