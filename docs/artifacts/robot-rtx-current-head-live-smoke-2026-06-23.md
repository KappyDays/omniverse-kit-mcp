# Robot RTX Current-HEAD Live Smoke - 2026-06-23

## Scope

Workspace-local Isaac Sim MCP smoke from `workspaces/isaac/instance-1` after
local commit `d3076e2`. The goal was to prove that the current robot + RTX
sensor golden workflow still passes after the latest public-history remediation
checkpoint and validation API cleanup.

The smoke used the workspace-local MCP entry only; Kit was not launched from the
repo root.

## Sequence

1. MCP stdio client from `workspaces/isaac/instance-1`
2. `mcp_runtime_info`
3. `process_list_kit_instances`
4. `kit_app_restart`
5. `simulation_get_status`
6. `extension_clear_logs`
7. `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)`
8. `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)`
9. `scenario_last_report(report_format="markdown")`
10. `scenario_last_report(report_format="json")`
11. `extension_capture_logs(level="WARN")`
12. `extension_capture_logs(level="ERROR")`

`kit_app_restart` was used because this batch touched
`omni.mycompany.validation_api` Python source; there were no external Kit
instances reported by `process_list_kit_instances`.

## Runtime Evidence

- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `registered_tool_count=152`.
- Kit preparation: `kit_app_restart` returned `status=started`.
- External Kit instances: `0`.
- MCP-owned Kit instances before restart: `1`.

## Scenario Evidence

- Scenario: `robot_rtx_sensor_golden_workflow`.
- Validate: `status=passed`, `31 passed / 0 failed / 0 skipped`.
- Artifact count: `1`.
- Same-session Markdown report included `# Scenario Report`,
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
- Artifact path: `<validation-api-capture>/capture_dce22b19cd57.png`
- SHA256: `117564a9a0416d5f362bcc7a93a01bd04c2e14e1f50af86d607b75df65621f2b`
- Pixel mean average: `145.58317563657408`
- Pixel variance average: `1107.4312033295819`
- `failure_codes=[]`
- Visual inspection: NovaCarter and four lidar target cubes were visible on
  the Flat Grid; the frame was not blank, black, or flat.

## Logs

- WARN capture: `ok=true`, `status=passed`, `count=11`.
- ERROR capture: `ok=true`, `status=passed`, `count=0`.
- WARN samples were routine USD/Hydra/Carb/RTX sensor lifecycle or deprecation
  messages during stage replacement, render-product setup, lidar readback, and
  cleanup. No scenario failure or ERROR log was observed.

## Public Evidence Note

Raw MCP responses contained host-local capture paths and Kit source filenames.
This committed artifact intentionally keeps only redacted artifact paths,
stable hashes, pixel statistics, status counts, and result-shape fields.
