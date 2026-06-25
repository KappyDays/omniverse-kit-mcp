# Robot RTX Golden Default Live Pass - 2026-06-25

## Scope

Re-verified the default `smoke/robot_rtx_sensor_golden_workflow.yaml` as the
baseline Robot + RTX sensor golden pass proof. The post-stop-guard refresh in
`docs/artifacts/robot-rtx-golden-stop-guard-refresh-2026-06-26.md` supersedes
this file for log-capture close metadata. This run used the Isaac Sim
workspace-local MCP entry from `workspaces/isaac/instance-1`; Kit was not
started from the repo root.

Historical note: this baseline used a same-host JSON validation call with
`redact_local_paths=false`, but only redacted/stable summary fields were copied
into this public artifact. It is not the current public report contract. Current
repeatable proof must use
`scenario_last_report(report_format="markdown", redact_local_paths=true)` and
the canonical probe assertion command in `docs/mcp-usage-guide.md`.

This pass pairs with the 2026-06-25 controlled-failure artifact for
`lidar_min_points=513`: the default workflow passes at `lidar_min_points=1`,
while the controlled threshold proves the retry/failure diagnostics path.

## Command Sequence

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
scenario_plan -> scenario_validate(dry_run=true) -> extension_clear_logs ->
scenario_validate(report_format="json", redact_local_paths=false) ->
scenario_last_report(report_format="markdown", redact_local_paths=true) ->
extension_capture_logs(level="WARN", stop_after_capture=true) ->
extension_capture_logs(level="ERROR", stop_after_capture=true) ->
simulation_get_status`

## Runtime

- MCP server: `isaacsim-validation-mcp` `1.27.0`
- App profile: `isaac-sim`
- Tool profile: `full`
- Registered tools: `152`
- `source_newer_than_import`: `false`
- Kit start/attach status: `ready`
- Initial simulation status: stopped at time `0.0`

## Plan And Dry Run

- Scenario plan: `32` total steps
- Phase counts: arrange `11`, act `9`, assert `5`, cleanup `7`
- Stage mutation summary: `read_only=false`, `requires_scratch_stage=true`
- Mutation count: `18`
- Retry step: `read_lidar_point_cloud`
- Retry key args: `sensor_prim=/World/Robot/NovaCarter/TopLidar`,
  `frames_to_wait=180`, `min_points=1`, `max_points=512`,
  `fail_on_warning=true`
- Retry policy: `maxAttempts=3`, `initialBackoffSeconds=0.25`,
  `maxBackoffSeconds=1.0`

## Live Result

- Scenario status: `passed`
- Step counts: `32` passed, `0` failed, `0` skipped
- Cleanup failures: `0`
- Diagnostic next actions: `0`
- Final simulation status: stopped at time `0.0`

## RTX Lidar Evidence

- Lidar read step: `passed`, attempts `1/3`
- Lidar points: `512`
- Lidar backend: `isaacsim.sensors.experimental.rtx.LidarSensor`
- Lidar `frames_waited`: `180`
- Lidar `truncated`: `true`
- Lidar warning: `null`
- Lidar empty reason: `null`
- Readback path attempted: `cached_lidar_sensor`
- Raw point-cloud keys included: `coords_type:SPHERICAL`, `data`,
  `generic-model-output`, `num_elements:352389`, `source:top_level`

## Viewport Evidence

- Viewport framing step: `passed`
- Camera: `/OmniverseKit_Persp`
- Viewport: `Viewport`
- Framed prim count: `4`
- Bounding box empty: `false`
- Capture assert step: `passed`
- Capture artifact: `<validation-api-capture>/capture_4c560e605c3d.png`
- Capture size: `1280x720`
- Capture SHA-256:
  `677ac38216e0307a7d6a6360c5be9432c3b85cd76704116b825ea9e2bc8d3ebf`
- Pixel mean: `[128.93074327256946, 147.73080078125, 160.50767469618054]`
- Pixel variance: `[1395.3320904455218, 928.6742071282262, 975.4026667951049]`
- Pixel mean average: `145.72307291666667`
- Pixel variance average: `1099.802988122951`
- Warmup frames used: `8`
- Capture failure codes: `[]`
- Visual inspection: the PNG shows NovaCarter centered on the NVIDIA grid, the
  top RTX lidar visible on the robot, and four gray lidar target cubes around
  the robot.

## Logs

- WARN count after request-scoped `extension_clear_logs`: `8`
- ERROR count after request-scoped `extension_clear_logs`: `0`
- WARN payload was not copied into this public artifact.

## Public Hygiene

No raw local capture path, local install root, process ID, worker/thread ID,
secret, raw Kit log snippet, or raw generated local reference is recorded here.
