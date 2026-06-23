# Robot RTX Sensor Golden Workflow Live Proof - 2026-06-23

## Summary

- Scenario: `scenarios/smoke/robot_rtx_sensor_golden_workflow.yaml`
- Workspace: `workspaces/isaac/instance-2`
- Kit REST port: `8112`
- Worker thread: `019ef205-6865-76f3-8713-efc28835ff4d`
- Scenario result: `31 passed / 0 failed / 0 skipped`
- WARN count after validation: `0`

## Evidence

- Unit/static gates:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\ -q`:
    `671 passed, 15 skipped`.
  - `.\\.venv\\Scripts\\python.exe scripts\\verify_mcp_sync.py`: OK, safe
    to commit.
  - `git diff --check`: OK.
- `kit_app_restart` was used because `omni.mycompany.validation_api` sensor service code changed.
- `mcp_runtime_info` reported `source_newer_than_import=false`,
  `stale_source_modules=[]`, and `restart_required_for_latest_mcp_code=false`.
- `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)` confirmed
  `/World/LidarTargets` and all four target cube setup steps:
  `create_lidar_target_front`, `create_lidar_target_back`,
  `create_lidar_target_left`, and `create_lidar_target_right`.
- `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)` passed in
  a bounded live run after cached RTX lidar GMO/polar dict readback support was added.
- `read_lidar_point_cloud` passed. The scenario report did not expose passing
  step telemetry fields such as `num_points`, `backend`, `frames`,
  `raw_keys`, or `warning`.
- `capture_visible_result` passed.
- Viewport artifact: local temp capture
  `<validation-api-capture>/capture_197e66404343.png`.

## Boundary

This proof covers the NovaCarter robot + RTX camera/lidar golden smoke path in
Isaac Sim instance 2. It does not prove all robot profiles, all RTX lidar
presets, or official asset workflows beyond this scenario.
