# Robot RTX Lidar Raw-Key Normalization - 2026-06-23

Purpose: live evidence that successful RTX lidar readback no longer exposes the
early empty-frame `num_elements:0` sentinel when the same read returns a positive
GenericModelOutput element count.

## Route

- Worker: `workspaces/isaac/instance-1`
- MCP profile: `full`
- App profile: `isaac-sim`
- Registered tools: `152`
- Wrapper:
  `mcp_runtime_info -> process_list_kit_instances -> kit_app_restart ->
  simulation_get_status -> extension_clear_logs ->
  scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml) ->
  scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml) ->
  scenario_last_report(redact_local_paths=true) -> extension_capture_logs`
- Public redaction check: `0` local-path hits across redacted JSON and Markdown.

## Result

- Scenario status: `passed`
- Steps: `32 passed`, `0 failed`, `0 skipped`
- Lidar status: `passed`
- Lidar attempts: `1`
- Lidar backend: `isaacsim.sensors.experimental.rtx.LidarSensor`
- Lidar points: `512`
- Lidar frames waited: `180`
- Lidar raw keys:
  `[coords_type:SPHERICAL, data, generic-model-output, num_elements:352385, source:top_level]`
- Lidar warning: `null`
- Lidar empty reason: `null`
- Capture artifact: `<validation-api-capture>/capture_aeba0cc59b20.png`
- Capture SHA256:
  `a653137dc6d59e311c8d858ba93203b145014fbf694451eef4aa1e1c0edb83f9`
- Pixel mean average: `145.72477828414353`
- Pixel variance average: `1100.5223209082567`
- WARN/ERROR log entries captured: `11`

## Visual Check

The capture was inspected locally. It showed the Nova Carter robot framed
between the lidar target cubes on the grid, with nonblank RTX output.
