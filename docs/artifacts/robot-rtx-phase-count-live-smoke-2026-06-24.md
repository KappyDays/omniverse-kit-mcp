# Robot RTX Phase Count Live Smoke

Date: 2026-06-24
Workspace: `workspaces/isaac/instance-1`
Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`

## Scope

Workspace-local Isaac Sim MCP smoke after `scenario_plan` began exposing
`total_steps`, `phase_counts`, and automatic fallback cleanup steps. The goal was
to prove the plan shape matches the live runner summary for the robot + RTX
sensor golden workflow.

## Wrapper

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
extension_clear_logs -> scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)
-> scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml) ->
scenario_last_report(report_format="json", redact_local_paths=true) ->
scenario_last_report(report_format="markdown", redact_local_paths=true) ->
extension_capture_logs(level="WARN") -> extension_capture_logs(level="ERROR")`

The MCP server was started from the workspace-local stdio entry, not from the
repo root.

## Runtime Evidence

- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`.
- Registered tools: `152`.
- `restart_required_for_latest_mcp_code=false`.
- `source_newer_than_import=false`.
- `kit_app_start`: `ok=true`, `status=ready` on port `8111`.
- Initial simulation status: stopped at time `0.0`.

## Plan And Summary Evidence

- `scenario_plan.total_steps=32`.
- `scenario_plan.phase_counts`: `arrange=11`, `act=9`, `assert=5`, `cleanup=7`.
- Cleanup plan ends with automatic `__fallback_cleanup_reset`:
  `module=extension`, `action=reset`, `automatic=true`.
- `scenario_validate`: `status=passed`.
- Summary counts: `32 passed`, `0 failed`, `0 skipped`.
- `scenario_last_report` Markdown also reported `32 passed`, `0 failed`,
  `0 skipped`.

## Lidar Evidence

- Step: `read_lidar_point_cloud`.
- Status: `passed`.
- Attempts: `1/3`; retry failures: `0`.
- Lidar points: `512`.
- Backend: `isaacsim.sensors.experimental.rtx.LidarSensor`.
- Frames waited: `180`.
- Warning: `null`; empty reason: `null`.
- Diagnostics: `cached_lidar_instance=true`,
  `readback_paths_attempted=["cached_lidar_sensor"]`.

## Viewport Evidence

- Step: `capture_visible_result`.
- Status: `passed`.
- Artifact: `<validation-api-capture>/capture_1f6bda31b6e8.png`.
- SHA256: `aafbafb2ddbb995593c1837262f26251758ea1dfc4aa2ed9166199a07691bc99`.
- Pixel mean average: `145.70992332175925`.
- Pixel variance average: `1101.0224151017462`.
- Warmup frames: `8`.
- Failure codes: `[]`.

## Visual Inspection

The captured PNG was inspected locally. It showed the NovaCarter robot on the
Flat Grid, framed between the four lidar target cubes. The frame was not blank,
black, flat, or off-camera.

## Logs

- WARN capture: `ok=true`, `status=passed`, `count=7`.
- ERROR capture: `ok=true`, `status=passed`, `count=0`.
- WARN sources were routine Carb/USD/Hydra lifecycle messages observed during
  stage replacement, render-product setup, and cleanup. No ERROR log was
  observed.

## Public Hygiene

Raw MCP responses contained host-local capture paths, process IDs, and Kit
source filenames. This artifact intentionally keeps only redacted artifact
paths, stable hashes, pixel statistics, status counts, and result-shape fields.
