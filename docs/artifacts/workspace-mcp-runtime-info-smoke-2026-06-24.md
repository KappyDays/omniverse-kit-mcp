# Workspace MCP Runtime Info Smoke - 2026-06-24

## Scope

Verify that the Isaac workspace-local stdio MCP entry can expose compact
`mcp_runtime_info` diagnostics from a parent/root session without launching Kit
or mutating a stage.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces\isaac\instance-1 --runtime-info
```

## Result

- MCP server: `isaacsim-validation-mcp v1.27.0`
- Tool count from `tools/list`: `152`
- Resource count from `resources/list`: `5`
- `mcp_runtime_info.tool_profile`: `full`
- `mcp_runtime_info.app_profile`: `isaac-sim`
- `mcp_runtime_info.registered_tool_count`: `152`
- `mcp_runtime_info.omitted_tool_count`: `0`
- `mcp_runtime_info.included_group_count`: `22`
- `mcp_runtime_info.source_newer_than_import`: `false`
- `mcp_runtime_info.restart_required_for_latest_mcp_code`: `false`
- `mcp_runtime_info.has_mcp_runtime_info_tool`: `true`

## Public Safety

This artifact records only relative command paths, aggregate tool/resource
counts, profile names, and boolean freshness fields. The generated
`tmp_mcp_surface.json` snapshot is ignored and was not promoted to public docs.
