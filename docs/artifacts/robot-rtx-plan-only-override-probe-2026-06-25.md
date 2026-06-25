# Robot RTX Plan-Only Override Probe - 2026-06-25

Purpose: prove the parent-side Robot + RTX plan-only probe path without stage
mutation. This is the safe preflight for a controlled lidar threshold failure
before running live `scenario_validate`.

Workspace-local probe:

```powershell
.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --require-plan-fields --input-overrides-json '{"lidar_min_points":513}' --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --expect-retry-key-arg read_lidar_point_cloud:min_points=513 --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true
```

Result:

- Exit status: `0`.
- MCP runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`,
  `restart_required_for_latest_mcp_code=false`.
- Robot probe contract present:
  `robot_probe_result_has_checks=true`,
  `robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE`, and
  `robot_probe_unknown_profile_fallback_tool_order`.
- Probe called `scenario_plan` only for scenario verification; there was no
  `scenario_validate dry-run smoke` section in the output.
- Scenario id: `robot_rtx_sensor_golden_workflow`.
- Total planned steps: `32`.
- Required plan fields present: `simulation_state_summary`,
  `simulation_state_steps`, `timeline_control_steps`,
  `live_validation_checklist`.
- `play_state_missing_count=0`.
- Preflight runtime checks included:
  `robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE` and
  `robot_probe_unknown_profile_fallback_tool_order`.
- Retry step: `read_lidar_point_cloud`, `max_attempts=3`.
- Retry key args included:
  - `sensor_prim=/World/Robot/NovaCarter/TopLidar`
  - `frames_to_wait=180`
  - `min_points=513`
  - `max_points=512`
  - `fail_on_warning=true`
- Live validation checklist order:
  `mcp_runtime_info -> kit_app_start -> simulation_get_status ->
  scenario_plan -> scenario_validate -> extension_clear_logs ->
  scenario_validate -> scenario_last_report -> extension_capture_logs`.
- `scratch_stage_required=true`.
- `log_capture_recommended=true`.
- Snapshot output: `snapshot: tmp_mcp_surface.json`.

Public-safety note: this artifact contains no local absolute workspace paths,
process IDs, worker/thread IDs, secrets, raw Kit logs, or generated catalog
payloads. The `tmp_mcp_surface.json` snapshot is ignored and was not promoted
to public docs.
