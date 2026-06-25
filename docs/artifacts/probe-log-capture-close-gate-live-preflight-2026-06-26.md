# Probe Log-Capture Close Gate Live Preflight

Date: 2026-06-26

Scope: workspace-local Isaac Sim MCP live preflight for the
`probe_mcp_surface.py` log-capture close gate. This did not run a scenario and
did not mutate a stage.

## Command

- `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --live-preflight --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract`

## Result

- Exit code: 0.
- Runtime gate was fresh: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- Kit attach/status preflight passed through the workspace-local Isaac Sim MCP
  entry. The local process ID from the raw command output is intentionally not
  recorded here.
- `extension_clear_logs` passed and reported `data.capture_running=true`.
- `extension_capture_logs(level=WARN, stop_after_capture=true)` passed the new
  close gate with:
  - `data.capture_running=false`
  - `data.capture_stop_requested=true`
  - `data.capture_stop_completed=true`
  - `data.capture_stop_timed_out=false`
  - `data.capture_stop_timeout_s=1.0`
- The generated `tmp_mcp_surface.json` snapshot is ignored and was not promoted
  as public evidence.

## Public Boundary

No raw local absolute paths, process IDs, worker/thread IDs, secrets, raw Kit
logs, local capture paths, or generated catalog records are included.
