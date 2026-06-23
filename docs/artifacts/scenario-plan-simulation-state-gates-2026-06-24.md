# Scenario Plan Simulation State Gates - 2026-06-24

## Scope

Robot and RTX lidar steps depend on the simulation timeline being in the right
state. Before this batch, `scenario_plan` exposed stage mutation, evidence,
retry, and diagnostic rows, but did not summarize whether play-state-dependent
robot/sensor steps were actually preceded by `simulation.play`.

## Change

- Add `simulation_state_summary` to `scenario_plan` and dry-run payloads.
- Add `simulation_state_steps` for robot, character, RTX lidar, and simulation
  wait steps that require an active `simulation.play` state.
- Add `timeline_control_steps` for `simulation.play`, `pause`, `stop`, `step`,
  `set_time`, and `wait_until` ordering review.
- Document that `simulation_state_summary.play_state_missing_count` should be
  zero before live robot/RTX proof runs.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `65 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py -q`
  - `16 passed, 1 skipped`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\tools\scenario_tools.py tests\unit\test_scenario_integration.py tests\unit\test_doc_references.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run scenarios\smoke\robot_rtx_sensor_golden_workflow.yaml`
  - includes `simulation_state_summary.play_state_missing_count=0`,
    `simulation_state_steps`, and `timeline_control_steps`.

## Public Safety

This artifact records plan field names and aggregate test results only. It
contains no local absolute paths, raw process IDs, worker/thread IDs, account
data, secrets, raw Kit logs, or generated catalog cache paths.
