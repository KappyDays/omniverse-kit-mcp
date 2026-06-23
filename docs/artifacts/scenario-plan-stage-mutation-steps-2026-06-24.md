# Scenario Plan Stage Mutation Steps - 2026-06-24

## Scope

`scenario_plan` and `scenario_validate(..., dry_run=true)` now expose
`stage_mutation_steps` so agents can identify stage/live-scene side effects
before running Isaac Sim live validation.

## Evidence

- `smoke/official_asset_catalog_diagnostics.yaml`
  - `stage_mutation_summary.read_only`: `true`
  - `stage_mutation_steps`: `[]`
  - Confirms the sync/search/resolve/get catalog diagnostic chain is read-only.
- `smoke/official_asset_verify_live.yaml`
  - `stage_mutation_summary.read_only`: `false`
  - `stage_mutation_summary.mutation_count`: `1`
  - `stage_mutation_steps`: 1 row
  - Row: `verify_pallet_asset`,
    `mutation_kind=official_asset_verify_stage_probe`
  - Confirms live verify is explicitly marked as a temporary stage probe.
- `smoke/robot_rtx_sensor_golden_workflow.yaml`
  - `stage_mutation_summary.read_only`: `false`
  - `stage_mutation_summary.mutation_count`: `18`
  - `stage_mutation_steps`: 18 rows
  - Includes `stage_reset`, `stage_load_usd`, `lighting_create_dome`,
    `robot_load`, lidar target `stage_create_prim`, RTX camera/lidar attach,
    sensor visualization toggle, and cleanup `stage_delete_prim` rows.
  - Unit guard:
    `tests/unit/test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_routes_through_runner`.
- `smoke/trigger_sync_cube.yaml`
  - `stage_mutation_summary.read_only`: `false`
  - `stage_mutation_summary.mutation_count`: `1`
  - `stage_mutation_steps`: 1 row
  - Row: `sync_extension`,
    `mutation_kind=extension_trigger_potential_stage_effect`
  - Confirms arbitrary extension trigger operations are surfaced before live
    execution while reset-only internal cleanup remains unmarked unless it
    explicitly requests `reset_stage_changes=true`.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run smoke\official_asset_catalog_diagnostics.yaml
.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run smoke\official_asset_verify_live.yaml
.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run smoke\robot_rtx_sensor_golden_workflow.yaml
.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run smoke\trigger_sync_cube.yaml
.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_routes_through_runner -q
```
