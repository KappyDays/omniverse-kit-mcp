# Implementation Plan: NVIDIA Official Asset Catalog + MCP Search

Status: ready
Created: 2026-06-19
Target: `<local-user-path>\workspace\omniverse-kit-mcp`

## Goal

Add a repo-local system that catalogs NVIDIA official assets and materials exposed by selected Omniverse Kit browser extensions per app/profile/version, then lets MCP search, resolve, and verify those entries before using them in future Isaac Sim or USD Composer work.

V1 targets:
- Isaac Sim 6.0.0 / Kit 110.1.1 via `workspaces/isaac/instance-1`
- USD Composer profile via `workspaces/usd-composer/instance-1`
- Providers: `omni.kit.browser.asset`, `omni.simready.explorer`, `omni.kit.browser.material`
- Material app overrides from `omni.kit.window.material` must be reflected.

## Required Reading

Read these before implementation:
- `CLAUDE.md`
- `AGENTS.md`
- `docs/CLAUDE.md`
- `docs/references/CLAUDE.md`
- `docs/invariants/asset-discovery.md`
- `docs/invariants/usd-load.md`
- `docs/invariants/live-worker-coordination.md`
- `docs/invariants/mcp-tool-add.md`
- `docs/invariants/module-add.md`
- `src/omniverse_kit_mcp/CLAUDE.md`
- `src/omniverse_kit_mcp/modules/CLAUDE.md`
- `src/omniverse_kit_mcp/tools/CLAUDE.md`
- `scripts/CLAUDE.md`
- `tests/CLAUDE.md`

Use CodeGraph before broad source reads because this repo has `.codegraph/`.

## Scope

### In

- Create a generated, gitignored official asset/material catalog area under `docs/references/official-assets/`.
- Add a resumable sync/verification script for provider roots, item discovery, URL validation, and full load/assign verification.
- Add MCP tools for searching, resolving, reading, status-checking, and on-demand verifying official catalog entries.
- Keep existing `asset_search` behavior intact.
- Add unit tests and tool-catalog regeneration for all new MCP surface.
- Document the sync workflow and stale snapshot behavior.

### Out

- Do not integrate `isaacsim.gui.content_browser` or the existing curated Isaac markdown inventory into the new schema in V1.
- Do not commit full generated catalog snapshots.
- Do not use UI scraping as the canonical discovery source unless live settings/S3 traversal cannot explain a provider.
- Do not add external or third-party assets.

## Verified Facts

- Existing extension metadata catalog is local/ignored via `docs/references/extensions.json`; `CatalogModule` powers `extension_search`.
- Existing offline `asset_search` reads only `docs/assets/isaac/assets/*.md`.
- Current SimReady markdown shorthand maps `aluminumpallet_a01/a02` to only `aluminumpallet_a01`; the new catalog must expand actual discovered variants individually.
- Isaac Sim installation contains:
  - `omni.kit.browser.asset-1.3.16`
  - `omni.simready.explorer-1.1.4`
  - `omni.kit.browser.material-1.6.5`
- Provider roots are declared in extension settings and can be overridden by app `.kit` settings.
- USD Composer source `.kit` overrides `omni.kit.browser.material` folders to `Materials/2023_2_1/Automotive`, `Materials/2023_2_1/Base`, and `vMaterials_2`.
- Live Kit work must be delegated to workspace worker sessions, not started from the repo root.

## Assumptions / Decisions

- Full generated snapshots and per-entry verification logs are local ignored artifacts. Commit only code, tests, schema/runbook docs, and small summaries.
- Canonical item ID should be stable and URL-based, with provider/app/version appearances stored separately.
- `provided_in` means the app/provider exposed the item. `loadable_in` means the app/profile actually loaded or assigned it successfully.
- Automatic selection should prefer current app/profile loadability over provider membership.
- If snapshot app/kit versions are stale, tools may return warned candidates but must force verification before actual use.
- Verification artifact policy is JSON-only. Viewport images are not required for catalog batch verification.

## Files / Subsystems

Likely implementation areas:
- `scripts/`: add official catalog sync/verify script and document it in `scripts/CLAUDE.md`.
- `src/omniverse_kit_mcp/modules/`: add an official catalog module or extend a catalog/asset module with typed dataclass results.
- `src/omniverse_kit_mcp/tools/module_tools.py`: register new `official_asset_*` tools.
- `src/omniverse_kit_mcp/clients/isaac_rest_client.py`: add only endpoints needed for on-demand verification if existing tools are insufficient.
- `kkr-extensions/.../validation_api/`: add read-only effective settings endpoint only if `kit_python_run`/existing content/material/stage tools are not enough for a stable public interface.
- `tests/`: add mock/unit tests for schema, search, stale detection, registration, and script fixtures.
- `docs/references/`: add public-safe schema/runbook docs; generated full data stays ignored.

## Interfaces / Contracts

Add these MCP tools unless implementation research finds a better minimal naming set:

- `official_asset_search(query, kind=None, app_profile=None, provider=None, min_status="url_validated", allow_stale=True, limit=20)`
  - Searches generated snapshots.
  - Returns candidates with id, kind, name, canonical_url, provider evidence, app/version evidence, status, stale warning, and use-before-verify flag.
- `official_asset_resolve(name_or_id, kind=None, app_profile=None, prefer_loadable=True)`
  - Resolves an item to a concrete USD or MDL assignment target and evidence.
- `official_asset_get(asset_id)`
  - Returns the full catalog entry.
- `official_asset_sync_status(app_profile=None)`
  - Reports latest snapshot metadata, app/kit/provider versions, counts, stale status, and failure summary.
- `official_asset_verify(asset_id, app_profile=None, timeout_s=None)`
  - Performs on-demand live verification for one selected item.

Expected verification states:
- `discovered`
- `url_validated`
- `inspect_verified`
- `load_verified`
- `assign_verified`
- `failed`
- `stale`

Item shape must include:
- `id`, `kind`, `name`, `aliases`, `canonical_url`
- `provider`, `source_root`, `category`
- `app_profile`, `app_version`, `kit_version`
- `extension_id`, `extension_version`
- `provided_in`, `loadable_in`
- `verification_status`, `checked_at`, `elapsed_ms`
- `bbox`, `meters_per_unit`, `up_axis`, `prim_count`
- `error`

## Implementation Steps

1. Add ignored generated paths for `docs/references/official-assets/` snapshots/logs/latest pointer, preserving public-safe docs.
2. Define official catalog dataclasses/types and JSON schema helpers. Keep Pydantic out of MCP server internals.
3. Implement snapshot loader, staleness check, URL-based dedup, alias/variant expansion, app/provider merge, and search/ranking.
4. Implement resumable script:
   - discovers effective provider roots per app/profile from live settings or static `.kit` + extension defaults,
   - recursively lists S3/content roots,
   - expands `.usd/.usda` assets and MDL/material entries,
   - writes progress and JSONL verification records,
   - supports resume and per-entry retries.
5. Implement full verification mode:
   - asset: `stage_load_usd`, collect bbox/units/prim_count, cleanup, record timing/error,
   - material: create test prim, assign material, read binding, cleanup, record timing/error,
   - default safety: sequential per app, asset timeout 120s, material timeout 45s, retry 1.
6. Add MCP module methods and tools for search/resolve/get/status/on-demand verify.
7. Update tool registration SoT, mock client, `docs/tool-catalog.md` via `scripts/verify_mcp_sync.py`, and tool caveats in `src/omniverse_kit_mcp/tools/CLAUDE.md`.
8. Add docs for sync workflow, snapshot policy, stale behavior, and how future scene-building should use `official_asset_search` before falling back to legacy `asset_search`.

## Validation

Run targeted checks first:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py -q
.venv\Scripts\python.exe -m pytest tests/unit/test_asset_module.py tests/unit/test_catalog_module.py -q
.venv\Scripts\python.exe scripts/verify_mcp_sync.py
```

Add new tests as needed, then run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/ -q
```

For live validation, use workspace workers:
- Isaac: `workspaces/isaac/instance-1`
- Composer: `workspaces/usd-composer/instance-1`

Do not start Kit from repo root for ordinary live work.

## Acceptance Criteria

- `official_asset_search("aluminumpallet_a01", app_profile="isaac-sim")` returns the concrete SimReady USD entry with app/kit/provider evidence.
- Variants such as `aluminumpallet_a01` and `aluminumpallet_a02` are separate entries when both are discovered.
- Material search returns assignable MDL/material targets and records app-specific material root differences.
- `official_asset_sync_status` reports counts and stale warnings for both target profiles.
- Full generated snapshot is ignored by git; repo status only contains intended code/docs/tests.
- All required unit and sync drift checks pass.

## Risks / Stop Conditions

- Stop if a provider root cannot be explained by live effective settings or static app/extension configuration.
- Stop if full verification causes repeated Kit hangs; preserve JSONL progress and report the failing provider/item range.
- Stop if URL validation indicates a broad NVIDIA bucket/prefix migration; treat it as an inventory sync problem first.
- Stop if adding MCP tools cannot satisfy the 7-place update contract in `docs/invariants/mcp-tool-add.md`.

## GOAL Prompt

You are in `<local-user-path>\workspace\omniverse-kit-mcp`. Implement the ready plan at `docs/artifacts/implementation-plans/2026-06-19-official-asset-catalog-mcp-implementation-plan.md`.

Goal: add a repo-local NVIDIA official asset/material catalog system for Omniverse Kit apps, plus MCP search/resolve/status/on-demand verify tools. V1 targets Isaac Sim 6.0.0/Kit 110.1.1 via `workspaces/isaac/instance-1` and USD Composer via `workspaces/usd-composer/instance-1`. Providers are `omni.kit.browser.asset`, `omni.simready.explorer`, and `omni.kit.browser.material`; reflect `omni.kit.window.material` app overrides.

Read first: `CLAUDE.md`, `AGENTS.md`, `docs/CLAUDE.md`, `docs/references/CLAUDE.md`, `docs/invariants/asset-discovery.md`, `docs/invariants/usd-load.md`, `docs/invariants/live-worker-coordination.md`, `docs/invariants/mcp-tool-add.md`, `docs/invariants/module-add.md`, `src/omniverse_kit_mcp/CLAUDE.md`, `src/omniverse_kit_mcp/modules/CLAUDE.md`, `src/omniverse_kit_mcp/tools/CLAUDE.md`, `scripts/CLAUDE.md`, and `tests/CLAUDE.md`. Use CodeGraph before broad source reads.

Key requirements: generated full snapshots/logs live under gitignored `docs/references/official-assets/`; commit only code, tests, schema/runbook docs, and small summaries. Keep existing `asset_search` intact. Add `official_asset_search`, `official_asset_resolve`, `official_asset_get`, `official_asset_sync_status`, and `official_asset_verify` unless research finds a better minimal equivalent. Canonical item IDs should be URL-based; store `provided_in` separately from `loadable_in`. Stale snapshots may return warned candidates but must force verify before use.

Implement a resumable sync/verify script. It must discover effective provider roots per app/profile, recursively list S3/content roots, expand actual `.usd/.usda` and material items individually, and write JSON/JSONL progress. Full verification is sequential per app: asset timeout 120s, material timeout 45s, retry 1. Asset verify uses `stage_load_usd`, bbox/units/prim_count, cleanup. Material verify creates a test prim, assigns material, reads binding, cleanup. Artifact policy is JSON-only.

Validation: update all 7 MCP-tool contract places, mocks, tool frozenset, and `docs/tool-catalog.md` via `.venv\Scripts\python.exe scripts/verify_mcp_sync.py`. Run targeted unit tests and then `.venv\Scripts\python.exe -m pytest tests/unit/ -q`. Live work must use workspace workers, not repo-root Kit launch.
