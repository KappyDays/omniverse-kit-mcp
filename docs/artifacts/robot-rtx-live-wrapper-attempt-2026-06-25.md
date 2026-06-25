# Robot RTX Live Wrapper Attempt - 2026-06-25

## Scope

Added the `--scenario-validate-live` option to `scripts/probe_mcp_surface.py`
so a parent/root session without first-class live MCP tools can run the
documented workspace-local wrapper:

`mcp_runtime_info -> kit_app_start -> simulation_get_status -> scenario_plan ->
scenario_validate(dry_run=true) -> extension_clear_logs -> scenario_validate ->
scenario_last_report(redacted markdown) -> extension_capture_logs`

The option requires `--workspace`, `--scenario-plan`, and
`--scenario-validate-dry-run`.

## Live Attempt Result

The workspace-local Isaac Sim instance-1 live attempt did not produce a
`scenario_last_report` or viewport evidence. The probe process and workspace MCP
server were alive, and the Isaac Sim validation REST port remained open, but
health checks timed out and the Kit GUI was not responding. The run was stopped
as a hang before any public success claim.

Recovery used the documented process helper for `isaac-sim` instance 1 only.
Raw process identifiers and host-local paths are intentionally omitted.

## Follow-Up

- Keep the new live wrapper support, because it encodes the correct canonical
  call order and redacted report/log capture path.
- Treat this attempt as failure evidence, not robot/RTX success evidence.
- Before rerunning the full golden workflow, use the live wrapper with line
  buffered output and consider a bounded controlled-failure override or a
  smaller read-only/live preflight to isolate where Kit stops responding.

## Non-Stage Live Preflight Follow-Up

After adding `--live-preflight`, the workspace-local Isaac Sim instance-1
preflight completed without stage mutation:

- `mcp_runtime_info`: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, source freshness clean.
- `kit_app_start`: `ok=true`, `status=started`.
- `simulation_get_status`: `ok=true`, `is_playing=false`, `current_time=0.0`.
- `extension_clear_logs`: `ok=true`.
- `extension_capture_logs(level=WARN, stop_after_capture=true)`: `ok=true`.

This narrows the previous hang to the mutating robot/RTX scenario path rather
than workspace MCP startup, Kit attach, timeline status, or request-scoped log
capture.
