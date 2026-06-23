# MCP Usage Guide

Use this guide before opening the full generated tool catalog. It routes common
tasks to the first MCP tools to try and the canonical project docs to read next.
The generated signature reference remains `docs/tool-catalog.md`.

## Task Routes

| Task | First tools | Then read |
|---|---|---|
| Start, attach, or inspect the app | `mcp_runtime_info`, `kit_app_start`, `simulation_get_status` | `docs/invariants/live-worker-coordination.md`, `docs/invariants/process-lifecycle.md` |
| Check running Kit instances before recovery work | `process_list_kit_instances`, `mcp_runtime_info` | `docs/invariants/multi-app.md`, `docs/invariants/process-lifecycle.md` |
| Choose an official NVIDIA asset or material | `official_asset_sync_status`, `official_asset_search`, `official_asset_resolve`, `official_asset_verify` | `docs/references/official-asset-catalog.md`, `docs/invariants/asset-discovery.md` |
| Build a visible scene | `official_asset_search`, `asset_search`, `stage_load_usd`, `viewport_frame_prims`, `viewport_capture_assert` | `docs/invariants/usd-load.md`, `docs/invariants/visual-validation.md` |
| Inspect or edit the USD stage | `stage_capture_snapshot`, `stage_compute_world_bbox`, `stage_set_property`, `stage_create_prim` | `src/omniverse_kit_mcp/tools/CLAUDE.md` |
| Diagnose a failed live action | Read-only probes first: `mcp_runtime_info`, `simulation_get_status`, `extension_capture_logs`, `stage_capture_snapshot` | `docs/tool-diagnostic-map.md`; then the relevant `docs/runbooks/*.md` if a known failure pattern matches |
| Drive a reproducible scenario | `scenario_plan`, `scenario_validate`, `scenario_last_report(report_format="markdown")` for quick triage or default JSON for exact fields | `docs/invariants/scenario-validation.md`, `scenarios/CLAUDE.md` |
| Prove the robot + RTX sensor golden path | `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)`, `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)`, `scenario_last_report(report_format="markdown")` for lidar/timeline/capture highlights; if lidar is empty, inspect `empty_reason` and `diagnostics.suggested_next` before widening the smoke | `docs/invariants/scenario-validation.md`, `src/omniverse_kit_mcp/modules/integration-facts.md` |
| Work with robot or character motion | `robot_list_arm_profiles`, `robot_load`, `robot_probe_arm_profile`, `character_load`, `job_status` | `src/omniverse_kit_mcp/modules/CLAUDE.md`, `docs/invariants/scenario-validation.md` |
| Attach RTX sensors to a robot manually | Prefer the smoke scenario route; if manual, follow the robot + RTX sensor sequence in the invariant before calling `sensor_attach_rtx_lidar` / `sensor_lidar_get_point_cloud`; set `min_points>0` and read `empty_reason`/`diagnostics.suggested_next` on zero-point results | `docs/invariants/scenario-validation.md`, `src/omniverse_kit_mcp/modules/integration-facts.md` |
| Capture GUI or menu evidence | `window_capture`, `window_list`, `window_menu_list`, `window_menu_trigger` | `docs/invariants/visual-validation.md`, `src/omniverse_kit_mcp/tools/CLAUDE.md` |
| Find a missing capability to wrap | `extension_search`, then duplicate-check `docs/tool-catalog.md` | `docs/references/CLAUDE.md`, `docs/invariants/mcp-tool-add.md` |

Standalone scenario runs print JSON plus Markdown; follow the scenario
validation invariant for report-field triage.

For `official_asset_*` zero-result or not-found responses, inspect
`diagnostics.reason`, `diagnostics.suggested_next`, and
`diagnostics.fallback_tool_order` before falling back to `asset_search`.

## Timeline Control

`simulation_play`, `simulation_pause`, and `simulation_stop` return timeline
state after the Kit update loop has accepted the command. Treat their
`is_playing` / `is_stopped` fields as the settled post-action state; check
`timeline_settled` and `timeline_settle_updates` when diagnosing slow or stale
timeline transitions. Use `simulation_get_status` when a later step needs an
independent read-back.

## Profile Selection

`MCP_SERVER_TOOL_PROFILE` controls registration-time tool exposure:

| Profile | Use |
|---|---|
| `full` | Default compatibility mode. Registers the complete generated tool surface. |
| `core` | Smaller everyday authoring and diagnostics surface. |
| `app` | Slim app-workflow surface with invariant tool names across `ISAAC_MCP_APP_PROFILE`; unsupported app-specific capabilities fail at runtime with capability errors. |
| `custom` | Starts from `core`, then applies `MCP_SERVER_TOOL_INCLUDE` and `MCP_SERVER_TOOL_EXCLUDE` tokens. |

Set `MCP_SERVER_TOOL_PROFILE=full` and restart the MCP host to roll back to the
complete compatibility surface.

Call `mcp_runtime_info` after MCP host startup to confirm the active
`tool_profile`, `app_profile`, registered `tool_count`, omitted groups/tools,
and custom include/exclude tokens before comparing a slim profile against the
full catalog.

## Exact Signatures

After choosing the likely task route, use `docs/tool-catalog.md` for exact tool
names, signatures, parameters, and generated descriptions. Do not edit that file
by hand; regenerate it with `scripts/verify_mcp_sync.py`.
