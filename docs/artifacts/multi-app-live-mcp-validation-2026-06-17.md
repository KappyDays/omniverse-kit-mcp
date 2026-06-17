# Multi-App Live MCP Validation — 2026-06-17

Scope: verify workspace-local MCP control for the two supported app profiles,
`isaac-sim` and `usd-composer`, across instance 1 and 2. Validation used
first-class MCP tools from Codex worker threads created in each workspace
folder. Standalone `ProcessModule` launch scripts were not used for the final
acceptance path.

## Results

| Workspace | MCP server | Expected app | Port | Result |
|---|---|---:|---:|---|
| `workspaces/isaac/instance-1` | `isaacsim-mcp-1` | `isaac-sim` | 8111 | Pass |
| `workspaces/isaac/instance-2` | `isaacsim-mcp-2` | `isaac-sim` | 8112 | Pass after retry |
| `workspaces/usd-composer/instance-1` | `usdcomposer-mcp-1` | `usd-composer` | 8114 | Pass |
| `workspaces/usd-composer/instance-2` | `usdcomposer-mcp-2` | `usd-composer` | 8115 | Pass |

## Acceptance Evidence

- `kit_app_start` returned `ok=true` with the expected `app_profile`,
  `instance_id`, and `ext_port` for every workspace.
- `process_list_kit_instances` showed the target port with
  `profile_matches=true` and `is_this_mcp_instance=true` after startup.
- `simulation_get_status` returned `ok=true` / `status=passed` for each
  accepted app instance.
- `kit_app_stop` returned `ok=true` for instance-2 and both USD Composer
  validation runs; post-stop process listing showed those target ports gone.
- The first `isaac/instance-2` worker ended with a Codex thread system error.
  A fresh worker thread in the same workspace repeated the full MCP flow and
  passed.

## Security Notes

- No Sketchfab token or external API credential was written to this artifact.
- External asset binaries and converted USD outputs remain runtime artifacts
  under ignored `.omniverse-kit-mcp/`, not tracked source files.
