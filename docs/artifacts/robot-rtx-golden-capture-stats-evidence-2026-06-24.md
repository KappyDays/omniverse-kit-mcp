# Robot RTX Golden Capture Stats Evidence - 2026-06-24

## Scope

Verified that `scenario_last_report` evidence summaries now expose useful
`viewport_capture_assert` pixel-stat evidence for the robot RTX golden workflow.
The run used the Isaac Sim workspace-local MCP entry from
`workspaces/isaac/instance-1`.

## Command Sequence

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
extension_clear_logs -> scenario_plan -> scenario_validate ->
scenario_last_report(report_format="markdown", redact_local_paths=true) ->
extension_capture_logs(WARN) -> extension_capture_logs(ERROR) ->
simulation_get_status`

## Result

- Scenario status: `passed`
- Step counts: `32` passed, `0` failed, `0` skipped
- Runtime: `tool_profile=full`, `app_profile=isaac-sim`, registered tools `152`
- `source_newer_than_import`: `false`
- Final simulation status: stopped at time `0.0`

## Visual Capture Evidence Summary

- Step: `capture_visible_result`
- Status: `passed`
- Capture artifact: `<validation-api-capture>/capture_a3df01086f3f.png`
- Capture SHA-256:
  `2e64dc03bc48fe27f4426d49e6f22a6fc20a3b771a31df86044da9b821e44c85`
- Resolution: `1280x720`
- `passed`: `true`
- `pixel_mean_average`: `145.58547128182872`
- `pixel_variance_average`: `1108.1396967975027`
- `pixel_mean`: `[128.813779296875, 147.59493706597223, 160.3476974826389]`
- `pixel_variance`: `[1400.5070004507638, 937.214895374802, 986.6971945669419]`
- `warmup_frames_used`: `8`
- `failure_codes`: `[]`

Visual inspection confirmed NovaCarter on the NVIDIA grid, the top RTX lidar,
and four surrounding lidar target cubes are visible.

## Logs

- WARN count: `6`
- ERROR count: `0`
- Raw WARN payload was not copied into this public artifact.

## Public Hygiene

No raw local capture path, local install root, process ID, worker/thread ID,
secret, or raw Kit log snippet is recorded here.
