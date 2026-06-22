# MCP Profile Stdio Smoke - 2026-06-22

Purpose: verify MCP protocol behavior after tool profile slimming follow-up.

Method: Python MCP stdio client launched each workspace-local server entry with
`cmd /c uv --directory ../../.. run --no-sync omniverse-kit-mcp`. The smoke did
not call `kit_app_start`, did not launch Kit GUI, and did not mutate a stage.

Calls per case:

- `list_tools`
- `mcp_runtime_info`
- `official_asset_sync_status(app_profile=<explicit profile>)`

| Workspace | App profile | Tool profile | list_tools | runtime tool_count | omitted | official_asset_sync_status |
|---|---|---:|---:|---:|---:|---|
| `workspaces/isaac/instance-1` | `isaac-sim` | `full` default | 152 | 152 | 0 | ok |
| `workspaces/isaac/instance-1` | `isaac-sim` | `app` | 148 | 148 | 4 | ok |
| `workspaces/usd-composer/instance-1` | `usd-composer` | `full` default | 152 | 152 | 0 | ok |
| `workspaces/usd-composer/instance-1` | `usd-composer` | `app` | 148 | 148 | 4 | ok |

Additional app-profile invariant checked in `app` cases:

- `robot_load`
- `sensor_attach_rtx_camera`
- `sensor_set_annotator`
- `omnigraph_create_ros2_publisher`

All cases reported `source_newer_than_import=false`.
