# Scenario Validation Invariant Triage Linkage - 2026-06-24

## Purpose

Keep the durable Robot + RTX scenario invariant aligned with the newer report
and dry-run fields used by agents before and after live validation.

## Contract

- Before live stage mutation, `scenario_plan` or
  `scenario_validate(..., dry_run=true)` should expose matching
  `phase_counts`, `evidence_steps`, and `retry_steps`.
- Agents should inspect `retry_steps[].key_args` before running bounded lidar
  success or failure proofs.
- Failed Robot + RTX reports should start with `failure_summary`, then drill
  into `diagnostic_next_actions`, retry failures, evidence rows, and logs.

## Unit Evidence

Validation command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py -q
```

Live Isaac Sim was not rerun; this batch updates durable guidance and doc
guards only.
