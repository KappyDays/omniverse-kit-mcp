# Scenario Plan Live Validation Checklist - 2026-06-24

## Scope

Add a machine-readable live wrapper checklist to `scenario_plan` so agents can
follow the same preflight, execution, evidence, and log-capture order that the
Robot + RTX golden workflow documents already require.

## Change

- Add `live_validation_checklist` to `scenario_plan` and dry-run payloads.
- Include ordered steps for `mcp_runtime_info`, `kit_app_start`,
  `simulation_get_status`, `scenario_plan`, optional dry-run validation,
  `extension_clear_logs`, `scenario_validate`, redacted Markdown
  `scenario_last_report`, and `extension_capture_logs`.
- Extend the workspace stdio probe default plan-field gate to require the new
  checklist field.
- Document the field in the task guide, scenario invariant, and scenario author
  guide.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py tests\unit\test_standalone_scripts.py tests\unit\test_tools_registration.py tests\unit\test_doc_references.py -q`
  - `124 passed, 1 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; catalog already up to date
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `803 passed, 16 skipped`
- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\robot_rtx_sensor_golden_workflow.yaml --require-plan-fields`
  - passed
  - `live_validation_checklist`: present
  - `live_validation_step_count`: `9`
  - `simulation_state_summary.play_state_missing_count`: `0`
  - `mcp_runtime_info.source_newer_than_import`: `false`

## Public Safety

This artifact records only field names, tool names, relative commands, and
aggregate validation status. It does not include local paths, process IDs,
worker/thread IDs, secrets, or generated local reference paths.
