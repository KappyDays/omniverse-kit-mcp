# Runtime Fresh After Evidence Error Code Guard - 2026-06-26

## Scope

This artifact records a workspace-local MCP runtime preflight after the
scenario reporter and probe tests were updated to preserve and assert
`evidence_summary[].error_code`.

## Command Shape

The bounded preflight used the workspace-local Isaac Sim MCP configuration with
`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1
--runtime-info --expect-tool-profile full --expect-app-profile isaac-sim
--expect-tool-count 152 --require-runtime-fresh
--require-robot-probe-error-contract`.

## Evidence

- Exit code: `0`.
- `tool_profile=full`.
- `app_profile=isaac-sim`.
- `tool_count=152`.
- `source_newer_than_import=false`.
- `restart_required_for_latest_mcp_code=false`.
- `robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE`.
- `robot_probe_unknown_profile_fallback_tool_order` stayed
  `robot_list_arm_profiles -> robot_probe_arm_profiles -> official_asset_search -> asset_search -> robot_load`.

## Public Boundary

This was a runtime-info preflight, not a live stage mutation. It records no local absolute paths,
worker/thread IDs, process IDs, secrets, temp snapshot contents, generated
catalog JSON, generated verification JSONL, or raw Kit logs.
