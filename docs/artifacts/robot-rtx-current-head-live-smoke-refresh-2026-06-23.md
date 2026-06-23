# Robot RTX Current-HEAD Live Smoke Refresh - 2026-06-23

## Scope

Workspace-local Isaac Sim MCP smoke from `workspaces/isaac/instance-1` after
local commit `16b7e6d`. The goal was to re-prove the robot + RTX sensor golden
workflow after the scenario report and public-hygiene diagnostics batches.

The smoke used the workspace-local MCP stdio entry only; Kit was not launched
from the repo root.

## Wrapper

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
extension_clear_logs -> scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)
-> scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml) ->
scenario_last_report(report_format="markdown", redact_local_paths=true) ->
extension_capture_logs(level="WARN") -> extension_capture_logs(level="ERROR")`

## Runtime Evidence

- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`.
- Registered tools: `152`.
- `restart_required_for_latest_mcp_code=false`.
- `kit_app_start`: `ok=true`, `status=ready`; instance 1 was already healthy
  on port `8111`.
- Initial simulation status: stopped at time `0.0`.

## Scenario Evidence

- Scenario: `robot_rtx_sensor_golden_workflow`.
- Plan phases: `arrange=11`, `act=9`, `assert=5`, `cleanup=6`.
- Validate status: `passed`.
- Steps: `32 passed`, `0 failed`, `0 skipped`.
- Continued/fatal/cleanup failures: `0`.
- `diagnostic_next_actions=[]`.
- Same-session Markdown report was available and redacted local paths.

## Lidar Evidence

- Step: `read_lidar_point_cloud`.
- Status: `passed`.
- Attempts: `1/3`; retry failures: `0`.
- Lidar points: `512`.
- Backend: `isaacsim.sensors.experimental.rtx.LidarSensor`.
- Annotator: `IsaacCreateRTXLidarScanBuffer`.
- Frames waited: `180`.
- Warning: `null`; empty reason: `null`.
- Truncated: `true`.
- Raw key sample: `coords_type:SPHERICAL`, `data`,
  `generic-model-output`, `num_elements:352383`, `source:top_level`.
- Diagnostics: `cached_lidar_instance=true`,
  `readback_paths_attempted=["cached_lidar_sensor"]`.

## Viewport Evidence

- Step: `capture_visible_result`.
- Status: `passed`.
- Artifact: `<validation-api-capture>/capture_4a04c41846cf.png`.
- SHA256: `d69f2a8c2e696929f8645422d5a288df9c4d9e8a4a8f2bf13d19ededbe031294`.
- Pixel mean average: `145.5982277199074`.
- Pixel variance average: `1108.411076873289`.
- Warmup frames: `8`.
- Failure codes: `[]`.

## Visual Inspection

The captured PNG was inspected locally. It showed the NovaCarter robot on the
Flat Grid, framed between the four lidar target cubes. The frame was not blank,
black, flat, or off-camera.

## Logs

- WARN capture: `ok=true`, `status=passed`, `count=11`, `truncated=false`.
- ERROR capture: `ok=true`, `status=passed`, `count=0`, `truncated=false`.
- WARN sources were routine Carb/USD/Hydra/SyntheticData/Replicator lifecycle
  and render-var messages observed during stage replacement, annotator setup,
  capture, and cleanup. No ERROR log was observed.

## Public Evidence Note

Raw MCP responses contained host-local capture paths, process IDs, and Kit
source filenames. This artifact intentionally keeps only redacted artifact
paths, stable hashes, pixel statistics, status counts, and result-shape fields.
