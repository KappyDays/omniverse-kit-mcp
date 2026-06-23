# Robot + RTX Sensor Repeat Live Smoke - 2026-06-23

Purpose: public-safe evidence for the golden robot + RTX sensor workflow after
the RTX lidar readback stabilization patch.

## Route

- Worker: `workspaces/isaac/instance-1`
- MCP profile: `full`
- App profile: `isaac-sim`
- Registered tools: `152`
- Wrapper:
  `mcp_runtime_info -> process_list_kit_instances -> kit_app_restart ->
  simulation_get_status -> scenario_validate x2 -> scenario_last_report(redacted)
  -> extension_capture_logs`
- Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`
- Public redaction check: `0` local-path hits across redacted JSON and Markdown.

## Run 1

- Scenario status: `passed`
- Steps: `32 passed`, `0 failed`, `0 skipped`
- Lidar step: `read_lidar_point_cloud`
- Lidar backend: `isaacsim.sensors.experimental.rtx.LidarSensor`
- Lidar points: `512`
- Lidar source elements: `352387`
- Lidar frames waited: `180`
- Lidar warning: `null`
- Lidar empty reason: `null`
- Capture artifact: `<validation-api-capture>/capture_f1307b892f05.png`
- Capture SHA256:
  `451232ab30de686489b8273b051136b071952c68d213640cf42c83e3f4bc7098`
- Pixel mean average: `145.7093117042824`
- Pixel variance average: `1101.395410406515`
- WARN/ERROR log entries captured: `11`

## Run 2

- Scenario status: `passed`
- Steps: `32 passed`, `0 failed`, `0 skipped`
- Lidar step: `read_lidar_point_cloud`
- Lidar backend: `isaacsim.sensors.experimental.rtx.LidarSensor`
- Lidar points: `512`
- Lidar source elements: `352386`
- Lidar frames waited: `180`
- Lidar warning: `null`
- Lidar empty reason: `null`
- Capture artifact: `<validation-api-capture>/capture_d202acba3ae9.png`
- Capture SHA256:
  `1f80f9b239c2c7cc8a14df5363aa99d768a72d50323e673f9851b414d2ebdd31`
- Pixel mean average: `145.59465494791667`
- Pixel variance average: `1109.1542230649195`
- WARN/ERROR log entries captured: `11`

## Visual Check

The second capture was inspected locally. It showed the Nova Carter robot framed
between the lidar target cubes on the grid, with nonblank RTX output.
