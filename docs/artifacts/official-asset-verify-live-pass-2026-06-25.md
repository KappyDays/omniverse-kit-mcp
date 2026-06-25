# Official Asset Verify Live Pass - 2026-06-25

## Scope

Refreshed live evidence for `smoke/official_asset_verify_live.yaml`, the
bounded official NVIDIA asset load-quality proof. The run used the Isaac Sim
workspace-local MCP entry from `workspaces/isaac/instance-1`; Kit was not
started from the repo root.

## Command Sequence

`mcp_runtime_info -> kit_app_start -> simulation_get_status ->
scenario_plan(smoke/official_asset_verify_live.yaml) ->
scenario_validate(smoke/official_asset_verify_live.yaml, dry_run=true) ->
extension_clear_logs ->
scenario_validate(smoke/official_asset_verify_live.yaml,
report_format="json") ->
scenario_last_report(report_format="markdown", redact_local_paths=true) ->
extension_capture_logs(WARN) -> extension_capture_logs(ERROR) ->
simulation_get_status`

## Runtime

- MCP server: `isaacsim-validation-mcp` `1.27.0`
- App profile: `isaac-sim`
- Tool profile: `full`
- Registered tools: `152`
- `source_newer_than_import`: `false`
- `restart_required_for_latest_mcp_code`: `false`
- Kit start/attach status: `ready`
- Initial simulation status: stopped at time `0.0`

## Plan And Dry Run

- Scenario id: `official_asset_verify_live`
- Scenario plan: `5` total steps
- Phase counts: arrange `0`, act `0`, assert `5`, cleanup `0`
- Stage mutation summary: `read_only=false`, `requires_scratch_stage=true`
- Mutation count: `1`
- Mutation kind: `official_asset_verify_stage_probe`
- Diagnostic steps:
  - `check_isaac_catalog`: `official_asset_sync_status`, `app_profile=isaac-sim`
  - `search_pallet_asset`: `official_asset_search`, `query=pallet`,
    `kind=asset`, `min_status=load_verified`, `limit=3`
  - `resolve_pallet_asset`: `official_asset_resolve`, `name_or_id=pallet`,
    `prefer_loadable=true`
  - `get_pallet_entry`: `official_asset_get` for the aluminum pallet URL
- Evidence step: `verify_pallet_asset`, `evidence_kind=official_asset_verify`,
  `timeout_s=180`
- Dry-run validate returned `dry_run=true`, `compiled=true`, matching plan
  fields, and the same live validation checklist.

## Live Result

- Scenario status: `passed`
- Step counts: `5` passed, `0` failed, `0` skipped
- Diagnostic next actions: `0`
- Failure summary entries: `0`
- Artifact paths: `0`
- Final simulation status: stopped at time `0.0`

## Official Asset Evidence

- Step: `verify_pallet_asset`
- Step status: `passed`, attempts `1/1`
- Asset id:
  `url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/common_assets/props/aluminumpallet_a01/aluminumpallet_a01.usd`
- Name: `aluminumpallet_a01.usd`
- Kind: `asset`
- App profile: `isaac-sim`
- Verification status: `load_verified`
- Error: `null`
- Stage load: `ok=true`, prim type `Xform`, load mode `reference_fallback`
- Probe prim path: `/World/OfficialAssetVerify/aluminumpallet_a01`
- Content evidence: `has_default_prim=true`, `prim_count=25`,
  `prim_count_valid=true`
- Load quality: `content_verified_no_bbox`
- BBox valid: `false`
- BBox validation reasons: `empty_flag`, `min_greater_than_max`,
  `sentinel_magnitude`
- Load-quality warning: invalid bbox evidence with content evidence preserved
- Cleanup: `ok=true`
- Timeout: `180.0`
- Elapsed: `1808ms`
- Retry count: `1`

## Redacted Report And Logs

- Redacted Markdown report contained `Evidence Summary`.
- WARN entries after request-scoped `extension_clear_logs`: `3`
- ERROR entries after request-scoped `extension_clear_logs`: `0`
- WARN payload was not copied into this public artifact.

## Public Hygiene

This artifact records only relative workspace/scenario paths, public S3 URLs,
aggregate counts, tool names, verification fields, and redacted report facts.
It excludes local absolute paths, process IDs, worker/thread IDs, raw log
paths, secrets, generated cache paths, and unredacted capture paths.
