# Official Asset Verify Live Smoke — 2026-06-23

> Historical evidence. Do not use this artifact as the current repeatable proof
> command or load-quality contract. Current official asset live proof must follow
> `docs/mcp-usage-guide.md`, `docs/invariants/scenario-validation.md`, and the
> current artifacts:
> `docs/artifacts/official-asset-verify-live-pass-2026-06-25.md` and
> `docs/artifacts/official-asset-verify-close-gate-live-refresh-2026-06-26.md`.
> Those current gates require `scenario_validate(..., dry_run=true)` before live
> execution and assert `load_quality=content_verified_no_bbox`.

## Scope

Bounded Isaac Sim worker smoke for one official catalog asset using
`official_asset_verify`. This confirms the on-demand verifier result shape for
asset load quality, cleanup, and log capture without committing generated
catalog or verification JSONL files.

## Worker

- Workspace: `workspaces/isaac/instance-1`
- App profile: `isaac-sim`
- MCP runtime: `tool_profile=full`, `tool_count=152`
- Wrapper:
  `mcp_runtime_info -> kit_app_start -> simulation_get_status ->
  extension_clear_logs -> official_asset_sync_status(app_profile="isaac-sim") ->
  official_asset_search(app_profile="isaac-sim", min_status="load_verified") ->
  official_asset_get(app_profile="isaac-sim") ->
  official_asset_verify(app_profile="isaac-sim", timeout_s=180) ->
  simulation_get_status -> extension_capture_logs(level="WARN") ->
  extension_capture_logs(level="ERROR")`

## Catalog Candidate

- Query: `pallet`
- Search count: `3`
- Selected item: `aluminumpallet_a01.usd`
- Provider: `omni.simready.explorer`
- Candidate status before rerun: `load_verified`
- Candidate id:
  `url:https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/common_assets/props/aluminumpallet_a01/aluminumpallet_a01.usd`

## Verification Result

- MCP result: `ok=true`, `status=passed`
- `verification_status=load_verified`
- `load_quality=valid`
- `load_quality_warning=null`
- `bbox_valid=true`
- `bbox_validation_reasons=[]`
- `has_authored_children=true`
- `has_default_prim=true`
- `prim_count_valid=true`
- `prim_count=25`
- `attempt=1`
- `retry_count=1`
- `timeout_s=180.0`
- `elapsed_ms=3821`
- Verification prim path: `/World/OfficialAssetVerify/aluminumpallet_a01`
- Cleanup: `ok=true`, same prim path
- Timeline before and after verify: stopped (`is_playing=false`,
  `is_stopped=true`)

## Logs

- WARN capture: `ok=true`, `count=3`, `log_truncated=false`
- ERROR capture: `ok=true`, `count=0`, `log_truncated=false`
- WARN categories:
  - `Semantics.SemanticsAPI is deprecated` from the Kit semantics extension.
  - `material:binding not found` under the temporary
    `/World/OfficialAssetVerify/aluminumpallet_a01/.../Looks` path.

The WARN records did not contradict the verifier's load-quality evidence:
content inspection returned authored/default-prim evidence, a valid bbox, and
cleanup succeeded.

## Notes

The live smoke was run in a single workspace-local MCP session. A later attempt
to call `extension_capture_logs` from a fresh one-shot stdio host failed with a
connection error because that host did not preserve the previous live/log-capture
state. For official asset live evidence, capture WARN/ERROR logs in the same MCP
host session that performs `official_asset_verify`.

## Scenario Regression Smoke

After promoting the flow to `smoke/official_asset_verify_live.yaml`, a
workspace-local Isaac Sim MCP smoke reran the same asset through
`scenario_validate` after a `validation_api` restart.

- Wrapper:
  `mcp_runtime_info -> process_list_kit_instances -> kit_app_start ->
  simulation_get_status -> kit_app_restart -> simulation_get_status ->
  extension_clear_logs -> scenario_plan(smoke/official_asset_verify_live.yaml)
  -> scenario_validate(smoke/official_asset_verify_live.yaml) ->
  scenario_last_report(report_format="markdown") ->
  extension_capture_logs(level="WARN") ->
  extension_capture_logs(level="ERROR")`
- External Kit instances before restart: `0`
- `scenario_plan`: `arrange=0`, `act=0`, `assert=4`, `cleanup=0`
- `scenario_validate`: `status=passed`, `4 passed`, `0 failed`, `0 skipped`
- `verify_pallet_asset`: `status=passed`, `duration_ms=2976`,
  `verification_status=load_verified`, `load_mode=reference_fallback`
- Load-quality evidence: `load_quality=content_verified_no_bbox`,
  `has_default_prim=true`, `prim_count_valid=true`, `prim_count=25`
- Cleanup evidence: selection clear returned `ok=true`; temporary prim delete
  returned `ok=true`
- WARN capture after scenario: `count=0`
- ERROR capture after scenario: `count=0`

This smoke specifically covers the regression where the reference fallback used
to remove and redefine the temporary Xform prim, which could leave Kit property
widgets holding an expired prim handle.
