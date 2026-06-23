# Official Asset Verify Live Smoke — 2026-06-23

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
