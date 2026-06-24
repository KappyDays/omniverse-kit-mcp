# Workspace MCP Plan Checklist Summary - 2026-06-24

## Scope

Make the workspace-local MCP stdio probe show the actual
`scenario_plan.live_validation_checklist` wrapper order, not only whether the
field exists. This gives parent/root sessions a compact read-only way to verify
the live Robot + RTX or official asset run order before mutating a stage.

## Change

- Add `live_validation_tools`, `scratch_stage_required`, and
  `log_capture_recommended` to `scripts/probe_mcp_surface.py` scenario plan
  summaries.
- Guard the summary against missing or malformed checklist payloads.
- Extend unit coverage for the new summary fields.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py -q`
  - passed as part of `tests\unit\test_standalone_scripts.py tests\unit\test_doc_references.py`
  - combined result: `30 passed, 1 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; catalog already up to date
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `803 passed, 16 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --skip-history --redact-samples`
  - passed
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\robot_rtx_sensor_golden_workflow.yaml --require-plan-fields`
  - passed
  - `live_validation_tools`: `mcp_runtime_info`, `kit_app_start`,
    `simulation_get_status`, `scenario_plan`, `scenario_validate`,
    `extension_clear_logs`, `scenario_validate`, `scenario_last_report`,
    `extension_capture_logs`
  - `scratch_stage_required`: `true`
  - `log_capture_recommended`: `true`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\official_asset_verify_live.yaml --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-plan-field live_validation_checklist`
  - passed
  - `live_validation_step_count`: `9`
  - `scratch_stage_required`: `true`
  - `log_capture_recommended`: `true`

## Public Safety

This artifact records only relative commands, field names, and aggregate
checklist shape. It does not include local paths, process IDs,
worker/thread IDs, secrets, or generated local reference paths.
