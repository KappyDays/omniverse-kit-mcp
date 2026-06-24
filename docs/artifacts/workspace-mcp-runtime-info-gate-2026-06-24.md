# Workspace MCP Runtime Info Gate - 2026-06-24

## Scope

Strengthen the workspace-local stdio MCP probe so runtime profile and import
freshness can be used as a failing gate, not only as informational output. This
lets parent/root sessions confirm that the Isaac worker entry is running the
expected profile before robot, RTX sensor, official asset, or scenario proof
work.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh
```

## Result

- Exit code: `0`
- MCP server: `isaacsim-validation-mcp v1.27.0`
- Tool count from `tools/list`: `152`
- Resource count from `resources/list`: `5`
- `mcp_runtime_info.tool_profile`: `full`
- `mcp_runtime_info.app_profile`: `isaac-sim`
- `mcp_runtime_info.tool_count`: `152`
- `mcp_runtime_info.source_newer_than_import`: `false`
- `mcp_runtime_info.restart_required_for_latest_mcp_code`: `false`
- `mcp_runtime_info.has_mcp_runtime_info_tool`: `true`

## Public Safety

This artifact records only relative command paths, aggregate counts, profile
names, and boolean freshness fields. The generated `tmp_mcp_surface.json`
snapshot is ignored and was not promoted to public docs.
