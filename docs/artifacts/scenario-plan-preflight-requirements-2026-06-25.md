# Scenario Plan Preflight Requirements Smoke - 2026-06-25

## Scope

Added `scenario_plan.preflight_requirements` and the same field to
`scenario_validate(..., dry_run=true)` so agents can read consolidated
runtime/scratch/log/play/retry gates before live stage mutation.

## Static Evidence

- Targeted pytest:
  `tests/unit/test_scenario_integration.py tests/unit/test_tools_registration.py tests/unit/test_standalone_scripts.py tests/unit/test_doc_references.py tests/unit/test_doc_integrity.py -q`
  -> `153 passed, 2 skipped`
- MCP sync:
  `scripts/verify_mcp_sync.py` -> `verify_mcp_sync OK`
- Whitespace:
  `git diff --check` -> pass

## Dry-Run Evidence

`scripts/run_scenario_standalone.py --dry-run scenarios/smoke/robot_rtx_sensor_golden_workflow.yaml`
exposed:

- `preflight_requirements.runtime_info.required=true`
- `preflight_requirements.runtime_info.checks` includes profile/freshness checks
  plus robot probe unknown-profile typed error/fallback contract checks.
- `preflight_requirements.scratch_stage.required=true`
- `preflight_requirements.log_capture.recommended=true`
- `preflight_requirements.simulation_play_gate.missing_before_required_step_count=0`
- `preflight_requirements.retry_gate.retry_step_count=1`

## Workspace-Local MCP Evidence

`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 ... --require-plan-fields`
reported:

- `required_fields_present.preflight_requirements=true`
- `preflight_requirement_keys`: `log_capture`, `retry_gate`, `runtime_info`,
  `scratch_stage`, `simulation_play_gate`
- `preflight_runtime_info_checks` includes
  `robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE`,
  `robot_probe_unknown_profile_error_data_path=data.checks.probe.evidence`, and
  `robot_probe_unknown_profile_fallback_tool_order`
- `scratch_stage_required=true`
- `log_capture_recommended=true`

This smoke used the workspace-local Isaac Sim stdio MCP entry and did not run
the mutating scenario.
