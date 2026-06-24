# Workspace MCP Official Asset Plan Smoke - 2026-06-24

## Scope

Verify that the Isaac workspace-local stdio MCP entry exposes official asset
scenario plan diagnostics and evidence rows before live stage mutation. This is
a bounded result-shape smoke only; it does not launch Kit, mutate a stage, or
execute `scenario_validate`.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --scenario-plan smoke\official_asset_verify_live.yaml --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps
```

## Result

- MCP server: `isaacsim-validation-mcp v1.27.0`
- Tool count: `152`
- Resource count: `5`
- `scenario_plan` target: `official_asset_verify_live`
- `total_steps`: `5`
- Required fields present:
  - `diagnostic_steps`
  - `evidence_steps`
  - `stage_mutation_steps`
- `simulation_state_summary.play_state_missing_count`: `0`
- `simulation_state_summary.requires_play_count`: `0`
- `simulation_state_steps` count: `0`
- `timeline_control_steps` count: `0`

## Public Safety

The recorded output contains only relative command paths, counts, tool/resource
names, scenario identifiers, and aggregate plan fields. The generated
`tmp_mcp_surface.json` snapshot is ignored and was not promoted to public docs.
