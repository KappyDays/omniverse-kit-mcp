# Canonical Probe Dry-Run E2E - 2026-06-26

## Scope

This checked whether a fresh agent can follow the canonical probe commands in
`docs/mcp-usage-guide.md` up to the dry-run boundary without live stage
mutation.

The commands used the workspace-local MCP entry under
`workspaces/isaac/instance-1` and did not pass `--scenario-validate-live`.
They called `tools/list`, `resources/list`, `mcp_runtime_info`,
`scenario_plan`, and `scenario_validate(dry_run=true)` only.

## Shared Runtime Result

- MCP server: `isaacsim-validation-mcp v1.27.0`
- Tool profile: `full`
- App profile: `isaac-sim`
- Tool count: 152
- Resource count: 5
- `source_newer_than_import=false`
- `restart_required_for_latest_mcp_code=false`
- Robot probe unknown-profile contract present:
  `ROBOT_PROBE_UNKNOWN_PROFILE`,
  `data.checks.probe.evidence`, and fallback order
  `robot_list_arm_profiles`, `robot_probe_arm_profiles`,
  `official_asset_search`, `asset_search`, `robot_load`.

## Robot + RTX Golden Workflow Dry-Run

- Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`
- `total_steps=32`
- Required fields present:
  `preflight_requirements`, `simulation_state_summary`,
  `simulation_state_steps`, `timeline_control_steps`,
  `live_validation_checklist`.
- `play_state_missing_count=0`
- `requires_play_count=2`
- `simulation_state_step_count=2`
- `timeline_control_step_count=7`
- Automatic cleanup includes `__fallback_cleanup_reset` with
  `timeoutSeconds=30.0`.
- Retry gate includes `read_lidar_point_cloud` with
  `max_attempts=3`, `min_points=1`, `max_points=512`,
  and `fail_on_warning=true`.
- Planned live proof order has 9 tools:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `scenario_plan`, `scenario_validate`, `extension_clear_logs`,
  `scenario_validate`, `scenario_last_report`, `extension_capture_logs`.
- `scratch_stage_required=true`
- `log_capture_recommended=true`

## Official Asset Verify Dry-Run

- Scenario: `smoke/official_asset_verify_live.yaml`
- `total_steps=5`
- Required fields present:
  `diagnostic_steps`, `evidence_steps`, `stage_mutation_steps`.
- Planned live proof order has 9 tools:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `scenario_plan`, `scenario_validate`, `extension_clear_logs`,
  `scenario_validate`, `scenario_last_report`, `extension_capture_logs`.
- `scratch_stage_required=true`
- `log_capture_recommended=true`

## Official Asset Read-Only Diagnostics Dry-Run

- Scenario: `smoke/official_asset_catalog_diagnostics.yaml`
- `total_steps=5`
- Required fields present: `diagnostic_steps`, `stage_mutation_steps`.
- Planned live proof order has 8 tools:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `scenario_plan`, `extension_clear_logs`, `scenario_validate`,
  `scenario_last_report`, `extension_capture_logs`.
- `scratch_stage_required=false`
- `log_capture_recommended=true`

## Boundary

No live MCP smoke was run and no stage was mutated. The generated
`tmp_mcp_surface.json` snapshot is ignored by `.gitignore` as `tmp_*.json`.
