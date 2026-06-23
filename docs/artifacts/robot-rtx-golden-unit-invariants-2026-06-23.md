# Robot RTX Golden Unit Invariants

Date: 2026-06-23

## Change

The unit regression for `robot_rtx_sensor_golden_workflow.yaml` now pins the
parts of the live-proven sequence that are easiest to accidentally weaken:

- The viewport framing step must include the robot, RTX camera, RTX lidar, and
  lidar target root before capture.
- `capture_visible_result` must keep the nonblank capture assertion thresholds
  and warmup frame count.
- The lidar point-cloud read must happen before `simulation_pause`.
- Viewport framing and capture must happen after the pause.
- The final cleanup `simulation_stop` must run after capture and before stage
  deletions.

## Evidence

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_routes_through_runner -q`:
  `1 passed`
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_scenario_integration.py`:
  passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`:
  `48 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`:
  `19 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py`: passed
- `git diff --check`: passed
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`: passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD --format json`:
  failed as expected with the pre-existing public-history findings.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`:
  `748 passed, 16 skipped`

## Public Hygiene Note

This artifact records only scenario ids, command names, counts, and public-safe
workflow assertions. It does not include live capture paths, worker ids, process
ids, or local install paths.
