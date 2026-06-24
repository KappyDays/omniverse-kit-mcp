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

## Follow-up Latest-Main Check

After the skill hardening batch, the Isaac workspace-local stdio entry was
rechecked with runtime freshness enabled for both official asset smoke
scenarios:

```powershell
.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\official_asset_catalog_diagnostics.yaml --require-plan-fields --require-plan-field stage_mutation_summary --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field live_validation_checklist
.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --scenario-plan smoke\official_asset_verify_live.yaml --require-plan-fields --require-plan-field stage_mutation_summary --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field live_validation_checklist
```

Both probes passed with `source_newer_than_import=false` and
`restart_required_for_latest_mcp_code=false`.

| Scenario | total_steps | live_validation_step_count | scratch_stage_required | log_capture_recommended |
|---|---:|---:|---|---|
| `official_asset_catalog_diagnostics` | 5 | 8 | `false` | `true` |
| `official_asset_verify_live` | 5 | 9 | `true` | `true` |

The diagnostics scenario is read-only at plan level
(`scratch_stage_required=false`), while the verify-live scenario still requires
scratch/test stage routing before execution.

## Public Safety

The recorded output contains only relative command paths, counts, tool/resource
names, scenario identifiers, and aggregate plan fields. The generated
`tmp_mcp_surface.json` snapshot is ignored and was not promoted to public docs.
