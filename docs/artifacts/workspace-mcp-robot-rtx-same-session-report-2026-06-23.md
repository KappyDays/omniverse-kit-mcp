# Workspace MCP Robot + RTX Same-Session Report - 2026-06-23

## Scope

Workspace-local Isaac Sim MCP smoke from `workspaces/isaac/instance-1`.
The goal was to prove that the robot + RTX golden scenario can be executed and
then queried through `scenario_last_report` in the same MCP server process.

## Sequence

1. `codex mcp list`
2. MCP stdio client against `isaacsim-mcp-1`
3. `mcp_runtime_info`
4. `official_asset_sync_status(app_profile="isaac-sim")`
5. `kit_app_start`
6. `simulation_get_status`
7. `extension_clear_logs`
8. `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)`
9. `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)`
10. `scenario_last_report`
11. `scenario_last_report(report_format="markdown")`
12. `extension_capture_logs(level="WARN", limit=50)`
13. `extension_capture_logs(level="ERROR", limit=50)`

## Result

- Required tools missing: none.
- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`.
- Official catalog: `ok=true`, `catalog_path=docs/references/official-assets/latest-isaac-sim.json`,
  `profile_count=1`.
- Kit: `ok=true`, `status=started`, `ext_port=8111`.
- Plan: `scenario_id=robot_rtx_sensor_golden_workflow`,
  `read_lidar_point_cloud` was idempotent and had `maxAttempts=3`.
- Validate: `status=passed`, `31 passed / 0 failed / 0 skipped`.
- Same-session JSON report: `status=passed`, `step_count=31`.
- Same-session Markdown report: started with `# Scenario Report`, included
  `Data Summary Highlights`, `read_lidar_point_cloud`, and
  `capture_visible_result`.

## Lidar Evidence

- Step: `read_lidar_point_cloud`
- Status: `passed`
- Attempts: `1/3`
- Retry failures: `0`
- `num_points=512`
- `backend=omni.replicator.core`
- `frames_waited=60`
- `truncated=true`
- `warning=null`
- `empty_reason=null`
- Raw key summary: `count=17`, sample `azimuth`, `channelId`, `data`
- Diagnostics:
  - `cached_lidar_instance=true`
  - `raw_key_count=17`
  - `readback_paths_attempted=["cached_lidar_sensor","replicator_annotator"]`

## Viewport Evidence

- Step: `capture_visible_result`
- Status: `passed`
- Attempts: `1/1`
- Artifact path: `<validation-api-capture>/capture_ffd8e5d5fab8.png`
- SHA256: `f13a3194553606e8a7d64593e45c062e04f781181ad9f67348b8e218a5c5c438`
- Pixel mean average: `145.71649811921296`
- Pixel variance average: `1101.2109916754364`
- `passed=true`
- `failure_codes=[]`

## Logs

- WARN capture: `ok=true`, `count=10`.
- ERROR capture: `ok=true`, `count=0`.
- WARN samples were routine USD/Hydra/Carb lifecycle messages during stage and
  render-product cleanup; no scenario failure or ERROR log was observed.

## Public Evidence Note

The raw MCP report intentionally contains host-local capture paths and Kit log
filenames so an operator can inspect artifacts on the same machine. Public repo
evidence must keep only redacted artifact paths plus stable evidence such as
SHA256, pixel statistics, status counts, and WARN/ERROR counts. Do not commit a
raw `scenario_last_report` dump without redaction.
