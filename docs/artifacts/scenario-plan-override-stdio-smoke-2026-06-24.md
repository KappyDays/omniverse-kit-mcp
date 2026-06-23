# Scenario Plan Override Stdio Smoke - 2026-06-24

## Scope

Fresh workspace-local Isaac Sim MCP stdio smoke from
`workspaces/isaac/instance-1`. This smoke verified the public MCP surface after
`scenario_plan` gained `input_overrides`.

No Kit app was launched, and no live stage state was mutated. The smoke only
compiled scenario YAML through MCP tools.

## Wrapper

`initialize -> tools/list -> mcp_runtime_info ->
scenario_plan(smoke/trigger_sync_cube.yaml, input_overrides=...) ->
scenario_validate(smoke/trigger_sync_cube.yaml, dry_run=true, input_overrides=...)`

The first ad-hoc direct JSON-RPC framing harness did not finish cleanly under
the Windows command shim, so it was stopped and replaced with the installed MCP
Python client. The MCP client smoke completed successfully.

## Runtime Evidence

- Workspace: `workspaces/isaac/instance-1`.
- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`.
- Registered tools: `152`.
- `restart_required_for_latest_mcp_code=false`.
- `source_newer_than_import=false`.
- `scenario_plan` input schema includes `input_overrides`.

## Scenario Evidence

- Scenario: `smoke/trigger_sync_cube.yaml`.
- Override values:
  - `prim_path=/World/OverrideCube`.
  - `batch_id=2026-06-24-override-smoke`.
- `scenario_plan.variables.prim_path` used the override value.
- `scenario_plan.phases.act[0].args.payload.batch_id` used the override value.
- All `scenario_plan` assert step `prim_path` args used the override value.
- `scenario_validate(dry_run=true).variables.prim_path` used the override value.
- Dry-run `steps` and `total_steps` matched `scenario_plan.total_steps`.
- Dry-run `phase_counts` matched `scenario_plan.phase_counts`.
- Plan total steps: `6`.
- Phase counts: `arrange=1`, `act=1`, `assert=2`, `cleanup=2`.

## Static Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - `19 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed; generated tool catalog stayed up to date and 36 sync tests passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `763 passed, 16 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --format json --redact-samples`
  - `finding_count=0`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples`
  - `finding_count=0`
- `git diff --check`
  - passed

## Raw Evidence

Raw MCP responses and stderr were saved under the ignored workspace scratch
directory. They are intentionally not committed because raw runtime evidence can
include host-local paths or process details.

## Public Hygiene

This artifact contains no local absolute paths, process IDs, worker/thread IDs,
account data, secrets, or raw Kit log snippets.
