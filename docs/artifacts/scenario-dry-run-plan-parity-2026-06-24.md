# Scenario Dry-Run Plan Parity Evidence - 2026-06-24

## Purpose

Reduce accidental live stage mutation by making
`scenario_validate(..., dry_run=true)` expose the same preflight fields as
`scenario_plan`.

## Contract

Dry-run validation keeps its compatibility fields:

- `dry_run`
- `steps`
- `compiled`

It also returns the plan payload:

- `scenario_id`, `name`, `tags`, `defaults`, and `variables`
- `total_steps` and `phase_counts`
- `evidence_steps`
- `retry_steps`
- `phases`

This lets an agent already preparing `scenario_validate` inspect evidence gates,
retry thresholds, automatic cleanup, and variable-substituted args without a
separate tool call or stage mutation.

## Unit Evidence

Validation command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py tests\unit\test_doc_references.py -q
```

Live Isaac Sim was not rerun; this batch changes only compile-time dry-run
payload shape.
