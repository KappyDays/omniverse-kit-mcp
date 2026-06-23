# Official Asset Current-HEAD Smoke - 2026-06-23

## Scope

Workspace-local Isaac Sim MCP smoke from `workspaces/isaac/instance-1`.
The goal was to prove the current `official_asset_*` app-profile workflow and
diagnostics shape without mutating the stage.

## Sequence

1. `codex mcp list`
2. MCP stdio client against `isaacsim-mcp-1`
3. `mcp_runtime_info`
4. `kit_app_start`
5. `simulation_get_status`
6. `extension_clear_logs`
7. `official_asset_sync_status(app_profile="isaac-sim")`
8. `official_asset_search(query=<known-miss>, kind="asset", app_profile="isaac-sim")`
9. `official_asset_search(query="pallet", kind="asset", app_profile="isaac-sim")`
10. `official_asset_resolve(first_candidate, app_profile="isaac-sim")`
11. `official_asset_get(first_candidate, app_profile="isaac-sim")`
12. `extension_capture_logs(level="WARN")`
13. `extension_capture_logs(level="ERROR")`

`official_asset_verify` was intentionally not run in this smoke because it can
load or assign content in the live stage. This batch only validates
profile-specific catalog result shape and recovery diagnostics.

## Runtime Evidence

- Required tools missing: none.
- Runtime profile: `tool_profile=full`, `app_profile=isaac-sim`,
  `tool_count=152`, `source_newer_than_import=false`,
  `stale_source_modules=[]`.
- Kit: `ok=true`, `status=started`, `app_profile=isaac-sim`,
  `instance_id=1`, `ext_port=8111`.
- Simulation status: `is_playing=false`, `is_stopped=true`,
  `time_codes_per_second=60.0`.
- Logs after official asset calls: WARN count `0`, ERROR count `0`.
- Post-run process check: no `kit.exe` process remained.

## Result-Shape Evidence

- `official_asset_sync_status(app_profile="isaac-sim")`
  - `catalog_path=docs/references/official-assets/latest-isaac-sim.json`
  - `catalog_identity.path=docs/references/official-assets/latest-isaac-sim.json`
  - `catalog_identity.run_id=full-live-isaac-insertfix-20260620-1`
  - `profile_count=1`
  - counts: `items=6338`, `asset=6338`, `load_verified=6337`,
    `failed=1`
  - provider `extension_dir` values were redacted to
    `<external-extension>/omni.kit.browser.asset-1.3.16` and
    `<external-extension>/omni.simready.explorer-1.1.4`
  - provider local path leak count: `0`
- Known-miss `official_asset_search`
  - `ok=true`, `status=passed`, `count=0`
  - `diagnostics.reason=query_no_match`
  - `candidate_counts.total_entries=6338`
  - `candidate_counts.query_matches=0`
  - `fallback_tool_order=[
    official_asset_sync_status,
    official_asset_search,
    official_asset_resolve,
    official_asset_verify,
    asset_search
    ]`
- Hit `official_asset_search(query="pallet")`
  - `ok=true`, `status=passed`, `count=3`
  - first candidate: `aluminumpallet_a01.usd`,
    provider `omni.simready.explorer`, status `load_verified`,
    `verify_required_before_use=false`, target keys `[usd_url]`
- `official_asset_resolve(first_candidate, app_profile="isaac-sim")`
  - `ok=true`, `status=passed`
  - resolved status `load_verified`
  - target keys `[usd_url]`
  - `verify_required_before_use=false`
- `official_asset_get(first_candidate, app_profile="isaac-sim")`
  - `ok=true`, `status=passed`
  - `verification_status=load_verified`
  - `verify_required_before_use=false`
  - `stale_warning=null`
  - `provided_in_count=1`, `loadable_in_count=1`

## Fix Captured By This Smoke

The first live smoke found that `official_asset_sync_status` redacted catalog
paths but still returned host-local provider `extension_dir` values from the
generated snapshot. The fix keeps generated catalog files unchanged and redacts
provider extension directories only in the public MCP result shape.

Unit coverage now injects a synthetic provider `extension_dir` under the
official catalog fixture and asserts the sync-status response contains no local
path fragment.

## Public Evidence Note

Raw MCP server logs included host-local launch and temp-log paths. This
committed artifact intentionally keeps only public-safe catalog paths,
placeholder extension paths, counts, status fields, and recovery diagnostics.
