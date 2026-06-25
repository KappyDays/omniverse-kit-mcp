# Workspace MCP Plan Checklist Summary - 2026-06-24

## Scope

Make the workspace-local MCP stdio probe show the actual
`scenario_plan.live_validation_checklist` wrapper order and optionally execute
`scenario_validate(dry_run=true)`, not only check whether those fields exist.
This gives parent/root sessions a compact read-only way to verify the live
Robot + RTX or official asset run order and scratch/read-only routing before
mutating a stage.

## Change

- Add `live_validation_tools`, `scratch_stage_required`, and
  `log_capture_recommended` to `scripts/probe_mcp_surface.py` scenario plan
  summaries.
- Guard the summary against missing or malformed checklist payloads.
- Extend unit coverage for the new summary fields.
- Add `--require-live-validation-tools` so workspace-local stdio smoke can fail
  when the live wrapper order drifts.
- Add `--expect-scratch-stage-required` and
  `--expect-log-capture-recommended` so the same read-only smoke can fail when a
  live-load scenario is no longer marked scratch-bound, or when a read-only
  diagnostics scenario accidentally gains stage-mutation routing.
- Add `--scenario-validate-dry-run` so the workspace-local stdio smoke can also
  call `scenario_validate(dry_run=true)` and gate the same plan fields before
  stage mutation.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py -q`
  - `19 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py tests\unit\test_doc_integrity.py -q`
  - `23 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; catalog already up to date
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `808 passed, 16 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  - passed
- `git diff --check`
  - passed
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\robot_rtx_sensor_golden_workflow.yaml --require-plan-fields --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true`
  - passed
  - `live_validation_tools`: `mcp_runtime_info`, `kit_app_start`,
    `simulation_get_status`, `scenario_plan`, `scenario_validate`,
    `extension_clear_logs`, `scenario_validate`, `scenario_last_report`,
    `extension_capture_logs`
  - `scratch_stage_required`: `true`
  - `log_capture_recommended`: `true`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --input-overrides-json '{"lidar_min_points":513}' --require-plan-fields --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true --expect-retry-key-arg read_lidar_point_cloud:min_points=513`
  - passed
  - `scenario_plan` and `scenario_validate(dry_run=true)` target:
    `robot_rtx_sensor_golden_workflow`
  - `total_steps`: `32`
  - `play_state_missing_count`: `0`
  - `requires_play_count`: `2`
  - `live_validation_step_count`: `9`
  - `retry_step_count`: `1`
  - `read_lidar_point_cloud` retry `key_args.min_points`: `513`
  - `scratch_stage_required`: `true`
  - `log_capture_recommended`: `true`
  - This confirms the parent-side controlled lidar failure plan uses the same
    live checklist and scratch/log flags, and that the threshold override reached
    the retry key args in both plan and dry-run validate paths before any stage
    mutation.
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\official_asset_verify_live.yaml --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true`
  - passed
  - `live_validation_step_count`: `9`
  - `scratch_stage_required`: `true`
  - `log_capture_recommended`: `true`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\official_asset_catalog_diagnostics.yaml --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true`
  - passed
  - `live_validation_step_count`: `8`
  - `scratch_stage_required`: `false`
  - `log_capture_recommended`: `true`

The controlled lidar smoke above executes `scenario_validate(dry_run=true)`;
the remaining workspace-local stdio probes listed here are `scenario_plan`
smokes. None of them execute a mutating `scenario_validate` or mutate a live
stage.

## Public Safety

This artifact records only relative commands, field names, and aggregate
checklist shape. It does not include local paths, process IDs,
worker/thread IDs, secrets, or generated local reference paths.
