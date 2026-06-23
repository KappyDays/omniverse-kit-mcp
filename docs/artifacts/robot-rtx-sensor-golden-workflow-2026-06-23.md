# Robot RTX Sensor Golden Workflow Live Proof - 2026-06-23

## Summary

- Scenario: `scenarios/smoke/robot_rtx_sensor_golden_workflow.yaml`
- Final validation workspace: `workspaces/isaac/instance-1`
- Validation route: `.venv\Scripts\python.exe scripts\run_scenario_standalone.py smoke\robot_rtx_sensor_golden_workflow.yaml`
- Reason for standalone route: bounded import-cache bypass for live validation,
  while still using the workspace-local Isaac REST profile.
- Scenario result: `31 passed / 0 failed / 0 skipped`
- WARN log capture after validation: `count=0`, `log_truncated=false`

## Evidence

- Unit/static gates:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_routes_through_runner tests\\unit\\test_scenario_integration.py::test_scenario_runner_retries_transient_lidar_read_failure tests\\unit\\test_scenario_runner.py::test_plan_step_includes_idempotent_retry_metadata -q`: `3 passed`.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_scenario_integration.py tests\\unit\\test_scenario_runner.py tests\\unit\\test_doc_integrity.py tests\\unit\\test_doc_references.py -q`: `50 passed, 1 skipped`.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_sensor_tools.py tests\\unit\\test_sensor_ext_tools.py -q`: `22 passed`.
  - `.\\.venv\\Scripts\\python.exe scripts\\verify_mcp_sync.py`: OK, `25 passed`.
  - `git diff --check`: OK.
- A live diagnostic pass isolated the failure:
  - cold `TopLidar` before camera annotators: `0` points, warning `polar arrays contained 0 elements`;
  - same `TopLidar` after camera annotators: `0` points, same warning;
  - fresh `PostCameraLidar` attached while timeline was playing in the same scene: `64` points, warning `null`.
- The golden workflow now plays the timeline before `attach_top_lidar`.
- `read_lidar_point_cloud` live data summary:
  - `num_points=512`
  - `backend=omni.replicator.core`
  - `frames_waited=60`
  - `raw_keys.count=17`, sample `azimuth`, `channelId`, `data`
  - `warning=null`
  - `lidar_data_truncated=true`
- `capture_visible_result` passed with:
  - artifact path: local validation capture path redacted
  - SHA256: `072ba6ed768621c11506f9875131c68943aca1949282b3e3171629f52614d34e`
  - average pixel mean: `145.58`
  - average pixel variance: `1107.94`
- Visual inspection confirmed NovaCarter on the grid with four target cubes visible.

## Boundary

This proof covers the NovaCarter robot + RTX camera/lidar golden smoke path in
Isaac Sim. It does not prove all robot profiles, all RTX lidar presets, or
official asset workflows beyond this scenario.
