# Workspace Live Preflight Current Gate - 2026-06-26

## Scope

This records a workspace-local live preflight before rerunning mutating live
proofs. The command used `workspaces/isaac/instance-1` and did not call
`scenario_validate` or mutate a stage.

## Runtime Result

- MCP server: `isaacsim-validation-mcp v1.27.0`
- Tool profile: `full`
- App profile: `isaac-sim`
- Tool count: 152
- Resource count: 5
- `source_newer_than_import=false`
- `restart_required_for_latest_mcp_code=false`
- Robot probe unknown-profile contract present with
  `ROBOT_PROBE_UNKNOWN_PROFILE`,
  `data.checks.probe.evidence`, and fallback order
  `robot_list_arm_profiles`, `robot_probe_arm_profiles`,
  `official_asset_search`, `asset_search`, `robot_load`.

## Live Preflight Result

- `kit_app_start`: `ok=true`, `status=ready`; the instance was already running
  and healthy. The raw process ID was intentionally not copied.
- `simulation_get_status`: `ok=true`, `status=passed`,
  `data.is_playing=false`, `data.current_time=0.0`.
- `extension_clear_logs`: `ok=true`, `status=passed`,
  `data.capture_running=true`.
- `extension_capture_logs(level="WARN", stop_after_capture=true)`: `ok=true`,
  `status=passed`, `data.capture_running=false`,
  `data.capture_stop_requested=true`, `data.capture_stop_completed=true`,
  `data.capture_stop_timed_out=false`, `data.capture_stop_timeout_s=1.0`.

## Boundary

This artifact is a public-safe summary. It excludes local absolute paths,
process IDs, worker/thread IDs, secrets, raw logs, local capture paths, and
generated catalog/cache records. The generated `tmp_mcp_surface.json` snapshot
remained ignored by `.gitignore` as `tmp_*.json`.
