# Workspace MCP Scenario Plan Smoke - 2026-06-24

## Scope

Verify that the Isaac workspace-local stdio MCP entry can expose the same
robot/RTX scenario plan fields added for simulation play-state preflight. This
is a bounded result-shape smoke only; it does not launch Kit, mutate a stage, or
execute `scenario_validate`.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --scenario-plan smoke\robot_rtx_sensor_golden_workflow.yaml --require-plan-fields
```

## Result

- MCP server: `isaacsim-validation-mcp v1.27.0`
- Tool count: `152`
- Resource count: `5`
- `scenario_plan` target: `robot_rtx_sensor_golden_workflow`
- `total_steps`: `32`
- Required fields present:
  - `simulation_state_summary`
  - `simulation_state_steps`
  - `timeline_control_steps`
- `simulation_state_summary.play_state_missing_count`: `0`
- `simulation_state_summary.requires_play_count`: `2`
- `simulation_state_steps` count: `2`
- `timeline_control_steps` count: `7`

## Public Safety

The recorded output contains only relative command paths, counts, tool/resource
names, scenario identifiers, and aggregate plan fields. The generated
`tmp_mcp_surface.json` snapshot is ignored and was not promoted to public docs.
