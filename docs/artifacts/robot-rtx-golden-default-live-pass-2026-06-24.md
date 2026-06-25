# Robot RTX Golden Default Live Pass - 2026-06-24

## Scope

Re-verified the default `smoke/robot_rtx_sensor_golden_workflow.yaml` after the
lidar point-count thresholds were variableized. This run used the Isaac Sim
workspace-local MCP entry from `workspaces/isaac/instance-1`; Kit was not
started from the repo root.

## Command Sequence

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
extension_clear_logs -> scenario_plan -> scenario_validate ->
scenario_last_report(report_format="markdown", redact_local_paths=true) ->
extension_capture_logs(level="WARN", stop_after_capture=true) ->
extension_capture_logs(level="ERROR", stop_after_capture=true) ->
simulation_get_status`

## Runtime

- App profile: `isaac-sim`
- Tool profile: `full`
- Registered tools: `152`
- `source_newer_than_import`: `false`
- Scenario plan: `32` total steps
- Phase counts: arrange `11`, act `9`, assert `5`, cleanup `7`
- Lidar defaults: `lidar_max_points=512`, `lidar_min_points=1`

## Live Result

- Scenario status: `passed`
- Step counts: `32` passed, `0` failed, `0` skipped
- Cleanup failures: `0`
- Diagnostic next actions: `0`
- Final simulation status: stopped at time `0.0`

## Evidence

- Lidar read step: `passed`, attempts `1/3`
- Lidar points: `512`
- Lidar backend: `isaacsim.sensors.experimental.rtx.LidarSensor`
- Lidar `frames_waited`: `180`
- Lidar `truncated`: `true`
- Lidar warning: `null`
- Viewport framing step: `passed`, camera `/OmniverseKit_Persp`, bbox empty `false`
- Capture assert step: `passed`
- Capture artifact: `<validation-api-capture>/capture_b43424b7dcd8.png`
- Capture SHA-256:
  `babc748d9d205e3f698e1bc3ec27c3c228f63c3ed2aeec64dc125a8f096c893b`
- Visual inspection: the PNG shows NovaCarter centered on the NVIDIA grid with
  the RTX lidar visible on top and four gray lidar target cubes around the robot.
- Redacted Markdown report contained `Evidence Summary` and no local user path.

## Logs

- WARN count: `8`
- ERROR count: `0`
- WARN payload was not copied into this public artifact.

## Public Hygiene

No raw local capture path, local install root, process ID, worker/thread ID,
secret, or raw Kit log snippet is recorded here.
