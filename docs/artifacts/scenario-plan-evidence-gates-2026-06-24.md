# Scenario Plan Evidence Gates - 2026-06-24

## Scope

`scenario_plan` now exposes top-level `evidence_steps` and `retry_steps` so an
agent can inspect the robot + RTX sensor golden workflow before mutating a live
stage. This complements the existing per-phase plan, which already contains the
full step args.

No live Kit app was launched for this batch. The change is a static plan-shape
improvement over the already live-smoked golden workflow.

## Robot + RTX Plan Evidence

Static compile of `scenarios/smoke/robot_rtx_sensor_golden_workflow.yaml`
reported:

- `total_steps=32`
- `phase_counts`: `arrange=11`, `act=9`, `assert=5`, `cleanup=7`
- `evidence_steps`:
  - `read_lidar_point_cloud`: `evidence_kind=rtx_lidar_point_cloud`,
    `frames_to_wait=180`, `min_points=1`, `max_points=512`,
    `fail_on_warning=true`, `idempotent=true`, `retries.maxAttempts=3`
  - `frame_robot_and_sensors`: `evidence_kind=viewport_framing`,
    frames robot, RTX camera, RTX lidar, and lidar targets
  - `capture_visible_result`: `evidence_kind=viewport_capture_assert`,
    `1280x720`, `warmup_frames=8`, `min_mean=8.0`, `min_variance=1.0`
- `retry_steps`:
  - `read_lidar_point_cloud`: idempotent retry gate with `maxAttempts=3`

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_routes_through_runner tests\unit\test_tools_registration.py::test_scenario_validate_dry_run_uses_plan_step_counts tests\unit\test_tools_registration.py::test_scenario_plan_accepts_input_overrides -q`
  - `3 passed`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\tools\scenario_tools.py tests\unit\test_scenario_integration.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; generated catalog stayed up to date and 36 sync tests passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py tests\unit\test_tools_registration.py -q`
  - `80 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py tests\unit\test_doc_integrity.py -q`
  - `19 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  - `finding_count=0`

## Public Hygiene

This artifact contains no live worker IDs, account data, local absolute paths,
process IDs, raw Kit logs, or unredacted generated catalog paths.
