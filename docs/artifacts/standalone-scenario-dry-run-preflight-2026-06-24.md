# Standalone Scenario Dry-Run Preflight Evidence - 2026-06-24

## Purpose

Make the cached-MCP bypass path safer after `src/omniverse_kit_mcp` edits by
allowing scenario preflight without live stage mutation.

## Contract

`scripts/run_scenario_standalone.py` now accepts:

- `--dry-run`
- `--input-overrides-json {...}`

Dry-run output prints the same plan-compatible fields as
`scenario_validate(..., dry_run=true)`: `phase_counts`, `evidence_steps`,
`retry_steps`, `phases`, `dry_run`, `steps`, and `compiled`.

## Unit Evidence

Targeted tests cover:

- dry-run does not instantiate REST clients
- JSON input overrides update compiled plan key args
- non-object override JSON fails with exit code 2

Validation command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py tests\unit\test_doc_references.py -q
```

## Robot + RTX Dry-Run Smoke

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run --input-overrides-json '{"lidar_min_points":513}' smoke\robot_rtx_sensor_golden_workflow.yaml
```

Result:

- Exit code: 0
- `scenario_id`: `robot_rtx_sensor_golden_workflow`
- `total_steps`: 32
- `phase_counts`: arrange 11, act 9, assert 5, cleanup 7
- `evidence_steps` included `read_lidar_point_cloud` with
  `min_points=513`, `max_points=512`, `frames_to_wait=180`, and
  `fail_on_warning=true`
- `retry_steps` included the same `read_lidar_point_cloud` key args and retry
  policy
- No live stage mutation occurred because this was compile-time dry-run only

Live Isaac Sim was not rerun; this batch adds a compile-time preflight path only.
