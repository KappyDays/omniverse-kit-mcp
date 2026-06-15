<!-- Parent: ../CLAUDE.md -->
<!-- Scope: scripts/ — dev / live / sync helpers -->

# scripts — Developer Scripts

**Category**:

| script | Purpose | When to use |
|----------|------|-----------|
| `generate_tool_catalog.py` | Regenerate `docs/tool-catalog.md` | Register a new `@mcp.tool()` / change the existing tool signature **must be done immediately** |
| `verify_mcp_sync.py` | regen + drift test 1 command | Pre-block drift by executing tool changes before committing them |
| `run_process_module_standalone.py <start\|stop\|restart>` | Low-level ProcessModule control without MCP server import cache | Recovery/diagnosis/import-cache bypass only. Normal app launch requests must use a `workspaces/<app>/instance-N` live worker and `kit_app_start`. |
| `run_scenario_standalone.py <scenario_path>` | Run scenario runner with the latest `src/` code | Bypass MCP import cache and modify scenario live verification |
| `live_test_extension_ui.py` | Phase D — Extension UI automation (ui_invoke/ui_tree) + carb log capture live | Phase verification — `docs/artifacts/phase-d/` |
| `live_test_phase_e.py` · `live_test_sensor.py` · `live_test_navmesh_viz.py` · `live_test_viewport_multi.py` | Phase E — sensor (RTX cam/lidar/depth)·navmesh viz·multi viewport live | → `docs/artifacts/phase-e/` |
| `live_test_physics.py` · `live_test_lighting.py` · `live_test_material.py` · `live_test_viewport_render.py` | Phase F — Physics, lighting (6 types), material, render mode live | → `docs/artifacts/phase-f/` |
| `live_test_character_crowd.py` · `live_test_robot_ext.py` · `live_test_sensor_contact_imu.py` · `live_test_timeline.py` | Phase G — Crowd·Robot ext(navigate/gripper/ee)·Contact/IMU·Timeline live | Manual execution during Isaac Sim startup (stdout report) |
| `live_test_replicator.py` · `live_test_omnigraph.py` · `live_test_content.py` · `live_test_extension_ext.py` | Phase H — replicator·omnigraph·content·extension mgmt live REST | → `docs/artifacts/phase-h/` |
| `live_test_gui_equiv.py` | GUI-equiv live — stage save/open/selection, etc. **FS dependent** (mock not possible) Verification | unit test gap reinforcement (see tests/CLAUDE.md) |
| `harvest_extension_metadata.py` · `render_catalog_md.py` · `sync_testbed_snapshot.py` | Kit Extension Reference Local Recollection | ignored `docs/references/extensions*.json/md` When needed |
| `diff_catalog.py` | Current local `extensions.json` vs fresh harvest comparison (added / removed / version_bumped / category_changed) | Determine whether local sync is necessary after kit/app version bump — workflow is `/omniverse-kit-extension-catalog-sync` skill |
| `diff_asset_inventory.py` | HTTP HEAD verification of all USD/USDA URLs of `docs/assets/isaac/assets/*.md` to NVIDIA S3. 404/NET/5xx reporting | When reporting asset path failure or after updating Isaac Sim 6.x / SimReady asset bucket — workflow is `/omniverse-asset-inventory-sync` skill |
| `rebuild_scene.py <builder.py> --out <out.usd> [--reopen]` | Rebuild thin USD with anonymous-layer + `dont_write_bytecode` (bypass lock/registry/pycache) | When the Live Kit opens USD and re-export fails silently. Details: `../docs/runbooks/scene-reexport-lock.md` |

## Additional rules

- **MCP import cache bypass**: Modifying the `src/omniverse_kit_mcp/` code will not be reflected in MCP tool calls until the MCP host (Claude Code / Codex CLI) is restarted. `run_scenario_standalone.py` / `run_process_module_standalone.py` is imported as a fresh Python process at every execution, so the latest code is reflected immediately. Extension code changes (`kkr-extensions/`) are immediately reflected as `kit_app_restart`.
- **Do not use standalone start for ordinary app launch**: Root `.env` legacy
  overrides (`ISAAC_SIM_KIT_EXE` / `ISAAC_SIM_KIT_FILE`) can override
  profile defaults and launch the wrong `.kit` app. For "start Isaac/Composer",
  use the workspace-local MCP worker and `kit_app_start`.
- **Live script output**: Saved to `docs/artifacts/phase-{id}/` (e.g. `docs/artifacts/phase-e/`). The `PHASE_*_DIR` constant in each script is set to this path. Copy the original capture saved in `%TEMP%/validation_api_captures/` to a meaningful name.
- **`live_test_*.py` personality**: **Manual ad-hoc phase verification tool** that directly hits `/validation/v1/*` with standalone httpx (pytest not collected — test signal unaffected). **The official path of domain regression is `scenarios/*.yaml` + `scenario_validate`** (Arrange→Act→Assert→Cleanup). live_test is for surfaces not covered by scenario (save/open, UI automation, viewport create/destroy) or quick one-shot inspection — add new regressions as scenario.
- **verify_mcp_sync.py requires exit 0**: This script must end with 0 before committing the new tool. If non-zero, regen or frozenset updates are missing.

## Procedure for adding a new script

1. Add file to `scripts/`, OK even if `__init__.py` is empty
2. Add one row to this file table (Purpose + Execution Conditions)
3. The “Scope-specific CLAUDE.md” table in root CLAUDE.md already has the `scripts/CLAUDE.md` pointer, so no further modification is required.

## Related Boundaries

- Tool catalog product convention: `../docs/CLAUDE.md`
- Complete flow of adding a new MCP tool: "Change propagation matrix" row "New MCP tool" in root `../CLAUDE.md`
- Inside Scenario runner: `../src/omniverse_kit_mcp/scenario/CLAUDE.md`
