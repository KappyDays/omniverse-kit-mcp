# MCP Surface Improvement Consensus

Date: 2026-06-22

Scope: improvement plan for `omniverse-kit-mcp` MCP usability, token efficiency,
tool discoverability, official asset selection, and backward-compatible rollout.

This document consolidates six read-only GPT-5.5 xhigh subagent reviews plus a
parent integration review. It is a plan artifact only; it does not change the
current MCP runtime behavior.

## Current State

- The default MCP surface exposes 152 tools in `docs/tool-catalog.md`.
- `create_mcp_server()` registers all module and scenario tools in default
  `full` profile; opt-in profiles register selected subsets.
- `docs/tool-catalog.md` is generated from the live full FastMCP server.
- `tests/unit/test_tools_registration.py` asserts the exact default tool set.
- `verify_mcp_sync.py` is the required drift gate for tool surface changes.
- Official NVIDIA asset/material catalog support is functional and useful for
  autonomous asset search, resolve, verification, and placement workflows.
- The remaining official asset issue is a single Isaac SimReady load failure,
  not a general catalog-system blocker.

## Subagent Perspectives

| Reviewer | Perspective | Main Finding |
|---|---|---|
| A | Tool surface and token efficiency | Reduce schema load with opt-in tool profiles; keep current full mode as default. |
| B | Live Omniverse workflow | Improve startup/preflight workflow first; do not add more tools unless repeated friction proves it. |
| C | Official asset catalog | Harden selection state with additive verification overlays and richer status fields. |
| D | Documentation and onboarding | Add a task-oriented MCP usage gateway before sending agents to the full tool catalog. |
| E | Backward compatibility and safety | Tool names/signatures are public API; default behavior must remain the full current surface. |
| F | Implementation architecture | Use registration-time slimming, not schema mutation; add profile-aware registration incrementally. |

## Consensus

1. Keep the current full tool surface as the default compatibility mode.
2. Add tool-profile support only as an opt-in mode.
3. Do not rename, remove, or change signatures of existing tools during slimming.
4. Slim by registering fewer tools at server startup, not by mutating generated
   schemas or collapsing tools into a single dispatcher.
5. Add a tool metadata registry so registration, profile filtering, and catalog
   grouping share one source of truth.
6. Keep `docs/tool-catalog.md` generated from the full compatibility surface.
7. Improve human/agent entrypoints with a short task-oriented usage guide.
8. Improve official asset selection with additive fields and verification
   overlays; do not break existing `official_asset_*` result shapes.
9. Treat profile slimming as a usability/token optimization, not a security
   boundary. Tools such as `scenario_validate` or `kit_python_run` can still
   expose broad capability when available.

## Non-Goals

- Do not remove the current 152-tool default surface.
- Do not make USD Composer or Isaac Sim use app-prefixed tool names.
- Do not manually edit `docs/tool-catalog.md`.
- Do not hide tools by default before profile tests and rollback are in place.
- Do not add a new startup diagnostic tool unless documented workflow use shows
  repeated failure with the existing preflight tools.
- Do not run broad Composer live-load sweeps just to prove token-slimming work.

## Proposed Architecture

### Configuration

Add a server setting:

```text
MCP_SERVER_TOOL_PROFILE=full|core|app|custom
```

Default: `full`.

Optional later settings:

```text
MCP_SERVER_TOOL_INCLUDE=<comma-separated tool or group names>
MCP_SERVER_TOOL_EXCLUDE=<comma-separated tool or group names>
```

### Profiles

`full`

- Current behavior.
- Registers every current tool.
- Must remain the default.
- Must keep `EXPECTED_ALL_TOOLS` and the generated full catalog contract intact.

`core`

- Small everyday authoring/debugging surface.
- Candidate groups: process/runtime, stage read/write, simulation basics,
  viewport/window basics, content, official asset search/resolve/status/verify,
  extension logs/state, and minimal scenario planning.
- Excludes high-volume or specialized domains such as robot, character, sensor,
  replicator, OmniGraph, ROS2-style helpers, and advanced physics/robot demos.

`app`

- App-workflow slim profile with invariant public tool names across
  `ISAAC_MCP_APP_PROFILE`.
- Keep runtime-guarded capability tools registered even when a Kit app may not
  support them; unsupported operations must return `CAPABILITY_NOT_SUPPORTED`
  or the app-specific graceful error at call time.
- Do not overload the existing `KitAppProfile.supported_module_groups`; keep
  app support, runtime guards, and MCP exposure independently reviewable.

`custom`

- Experimental include/exclude selection.
- Always has one-step rollback: set `MCP_SERVER_TOOL_PROFILE=full` and restart
  the MCP host.

### New Metadata Module

Add `src/omniverse_kit_mcp/tools/tool_profiles.py`.

Suggested responsibilities:

- `ToolMeta(name, group, app_profiles, workflow_tags, risk_level, default_profiles)`
- known group definitions
- profile definitions
- include/exclude parsing
- selection result with included and omitted tools
- helper/wrapper for selected registration

### Registration Flow

Current:

```text
create_mcp_server(config)
  -> register_module_tools(mcp, ...)
  -> register_scenario_tools(mcp, ...)
```

Proposed:

```text
create_mcp_server(config)
  -> build_tool_selection(config)
  -> register_module_tools(mcp, ..., selection=selection)
  -> register_scenario_tools(mcp, ..., selection=selection)
```

Inside registration functions, replace raw `@mcp.tool()` with a local wrapper
that only registers a function when selected. In `full`, every current tool must
register exactly as it does today.

## Documentation Plan

Add a short task gateway, for example `docs/mcp-usage-guide.md`.

It should route agents by task before they load the full catalog:

| Task | First Tools | Then Read |
|---|---|---|
| Start or attach app | `mcp_runtime_info`, `kit_app_start`, `simulation_get_status` | `live-worker-coordination.md`, `process-lifecycle.md` |
| Choose NVIDIA official asset/material | `official_asset_sync_status`, `official_asset_search`, `official_asset_resolve`, `official_asset_verify` | `official-asset-catalog.md`, `asset-discovery.md` |
| Build visible scene | asset search/resolve, `stage_load_usd`, viewport capture tools | `usd-load.md`, `visual-validation.md` |
| Diagnose failure | read-only probe first | `tool-diagnostic-map.md` |
| Add missing capability | duplicate check, `extension_search`, source research | `docs/references/CLAUDE.md`, `mcp-tool-add.md` |
| Scenario workflow | `scenario_plan`, `scenario_validate`, `scenario_last_report` | `scenario-validation.md` |

Follow-up docs cleanup:

- Fix README tool-count drift. README currently describes an older count while
  the generated catalog reports 152 tools.
- Point README and `docs/CLAUDE.md` to the task gateway before the full catalog.
- Keep canonical rules in `docs/invariants/*.md`; do not duplicate them in the
  gateway.
- Keep `docs/tool-catalog.md` generated-only.

## Official Asset Hardening Plan

These are additive changes and should not alter existing defaults:

1. Read on-demand verification evidence as an overlay so a just-verified item can
   influence later `official_asset_search` / `official_asset_resolve` results
   without requiring a full sync.
2. Preserve richer load-quality evidence in search/resolve outputs:
   `load_quality`, `bbox_valid`, warning fields, and evidence provenance.
3. Add a machine-readable `failure_class` while keeping
   `verification_status`.
4. Normalize `skipped` as a first-class status or explicitly mark it
   non-selectable with reason fields.
5. Surface provider coverage in `official_asset_sync_status`, including source
   provenance such as install tree, user cache, `.kit` override, or missing root.
6. Document the autonomous selection algorithm:
   status -> search with app_profile -> resolve -> verify if needed ->
   load/assign -> visual or placement validation.

## Live Workflow Improvement Plan

No new tool is required yet. Prefer a documented preflight bundle using existing
tools:

1. `mcp_runtime_info`
2. `process_list_kit_instances` before destructive/recovery work
3. `kit_app_start`
4. `simulation_get_status`
5. `extension_clear_logs` before risky live action
6. risky call
7. `extension_capture_logs(level="WARN")` after failure

Promote this to a wrapper tool only if future sessions repeatedly skip the
bundle or misreport startup/lifecycle state.

## Rollout Phases

Phase 0: Planning and docs

- Add this plan.
- Add task gateway doc.
- Fix README count drift.
- No runtime behavior change.

Phase 1: Metadata only

- Add `tool_profiles.py`.
- Classify every expected tool.
- Replace generator grouping with metadata.
- Acceptance: zero `Unclassified` tools in generated catalog.
- Default server behavior unchanged.

Phase 2: Full-mode wrapper

- Add profile selection plumbing.
- Register through the wrapper while `full` remains behavior-identical.
- Acceptance: default `create_mcp_server(AppConfig())` exposes the same exact
  tool set as today.

Phase 3: Opt-in profiles

- Add `core`, `app`, and `custom`.
- Add profile-aware tests.
- `mcp_runtime_info` reports active profile, app profile, registered/tool
  counts, included/omitted groups, omitted tools, and custom include/exclude
  tokens.
- Keep full mode as rollback.

Phase 4: Schema/docstring slimming

- Shorten long docstrings only after task gateway/resources exist.
- Keep must-not safety warnings in either the tool description, system prompt,
  or linked resource.
- Do not change signatures as part of docstring slimming.

Phase 5: Official asset selection hardening

- Add overlay and richer status fields.
- Update tests and official catalog docs.
- Preserve backward-compatible result shapes.

## Test Strategy

Minimum checks for implementation phases:

```text
.venv\Scripts\python.exe scripts\verify_mcp_sync.py
.venv\Scripts\python.exe -m pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py -q
.venv\Scripts\python.exe -m pytest tests/unit/test_config_multi_app.py -q
.venv\Scripts\python.exe -m pytest tests/unit/ -q
git diff --check
```

Additional profile-specific tests:

- full profile equals current `EXPECTED_ALL_TOOLS`
- core/app profiles are strict subsets
- core/app profiles include `mcp_runtime_info`
- every tool has metadata group coverage
- generated full catalog remains canonical
- local slim env vars cannot poison `verify_mcp_sync.py`
- invalid profile values fail clearly
- `mcp_runtime_info` reports profile, app profile, counts, omitted surface, and
  custom include/exclude tokens

## Compatibility Review

Verdict: existing MCP usage remains safe if this plan is implemented in phases
and `full` stays default.

Must preserve:

- all existing tool names
- all existing signatures
- all existing defaults
- current result JSON compatibility
- generated full `docs/tool-catalog.md`
- `verify_mcp_sync.py` as the drift gate
- workspace-local `.mcp.json` behavior

Known risks:

- Hiding a useful tool in app/core profile can confuse agents.
- App profiles can accidentally hide cross-app common USD tools if they reuse
  coarse module support lists.
- A compact dispatcher would reduce count but hurt name-based clients and
  per-tool schema discoverability.
- Short docstrings can remove safety context if task guides/resources are not
  in place first.

Mitigations:

- default `full`
- one-env rollback
- `mcp_runtime_info` profile reporting
- profile-aware tests
- generated full catalog remains unchanged
- deprecate before any future removal

## Final Recommendation

Do not add more domain tools right now. The next best improvement is:

1. Add task-oriented MCP usage guide.
2. Add tool metadata and fix catalog grouping.
3. Add opt-in `core` and `app` profiles with `full` as default.
4. Harden official asset selection state additively.

This improves token efficiency and agent usability without breaking the current
MCP workflows that already work.
