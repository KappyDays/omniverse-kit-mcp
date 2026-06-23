# Robot RTX Current-HEAD Live Smoke - 2026-06-23

## Scope

Workspace-local Isaac Sim MCP smoke from `workspaces/isaac/instance-1` at
`HEAD=bd21fe6`. The goal was to prove that the current robot + RTX sensor
golden workflow still passes after the latest lidar diagnostic result-shape
changes, and that the latest `validation_api` code exposes the empty-lidar
diagnostic recovery fields.

## Sequence

1. `codex mcp list`
2. MCP stdio client against `isaacsim-mcp-1`
3. `mcp_runtime_info`
4. `kit_app_start`
5. `simulation_get_status`
6. `extension_clear_logs`
7. `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)`
8. `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)`
9. `scenario_last_report`
10. `scenario_last_report(report_format="markdown")`
11. `kit_python_run(code=<diagnostic-helper-read-only-marker>)`
12. `extension_capture_logs(level="WARN", limit=50)`
13. `extension_capture_logs(level="ERROR", limit=50)`

## Runtime Evidence

- Required tools missing: none.
- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`.
- Kit: `ok=true`, `status=started`, `app_profile=isaac-sim`,
  `instance_id=1`, `ext_port=8111`.
- Initial simulation status: `is_playing=false`, `is_stopped=true`,
  `time_codes_per_second=60.0`.

## Scenario Evidence

- Plan: `scenario_id=robot_rtx_sensor_golden_workflow`.
- Plan confirmed `read_lidar_point_cloud` is idempotent and has
  `retries.maxAttempts=3`.
- Validate: `status=passed`, `31 passed / 0 failed / 0 skipped`.
- Same-session JSON report: `status=passed`, `step_count=31`.
- Same-session Markdown report included:
  - `# Scenario Report`
  - `## Data Summary Highlights`
  - `read_lidar_point_cloud`
  - `capture_visible_result`
  - `num_points=`
  - `frames_waited=`
  - `sha256=`

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
- Artifact path: `<validation-api-capture>/capture_80d99b4b4d6b.png`
- SHA256: `90e14c68d8ead4386d29dfe87249aa2128c4c8dffb4266e13b4096a36507bb23`
- Pixel mean average: `145.59828414351853`
- Pixel variance average: `1108.4088804722876`
- `failure_codes=[]`
- Visual inspection: NovaCarter and four lidar target cubes were visible on
  the Flat Grid; the frame was not blank, black, or flat.

## Diagnostic Marker Evidence

The live Kit process was queried with a read-only `kit_python_run` marker that
called the current `validation_api` lidar diagnostic helper with
`empty_reason="not_spun_up"`. It returned:

- `reason=not_spun_up`
- `empty_reason=not_spun_up`
- `suggested_next=ensure simulation_play is active, step more frames, keep scan targets near the lidar plane, then retry an idempotent read`
- `fallback_tool_order=["simulation_get_status","simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]`

This marker does not mutate the stage; it only proves that the latest
validation-api diagnostic helper loaded in the live Kit process exposes the
expected recovery fields.

## Logs

- WARN capture: `ok=true`, `status=passed`, `count=10`.
- ERROR capture: `ok=true`, `status=passed`, `count=0`.

## Public Evidence Note

The raw MCP responses contained host-local process IDs and capture/log paths.
This committed artifact intentionally keeps only redacted artifact paths,
stable hashes, pixel statistics, status counts, and result-shape fields.
