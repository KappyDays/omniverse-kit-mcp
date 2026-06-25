# Official Asset Catalog

Generated NVIDIA official asset/material snapshots live under the ignored
`docs/references/official-assets/` directory. Commit code, tests, this schema
note, and small human summaries only; do not commit full snapshots, progress
files, or verification JSONL logs.

## Files

`scripts/sync_official_asset_catalog.py` writes JSON-only artifacts:

- `latest.json` — latest merged catalog used by `official_asset_*` tools.
- `latest-<app_profile>.json` — latest per-profile pointer used when
  `official_asset_*` receives `app_profile` (for example,
  `latest-isaac-sim.json` and `latest-usd-composer.json`).
- `snapshots/<run_id>.json` — immutable run snapshot.
- `progress/<run_id>.json` — resumable discovery progress.
- `verification/<run_id>.jsonl` — per-item verification records.
- `verification/<run_id>-summary.json` — generated per-profile/provider
  verification counts for broad live runs.
- `verification/latest-summary.json` — latest generated verification summary.
- `verification-on-demand.jsonl` — records from `official_asset_verify`.

## Schema

Catalog root:

```json
{
  "schema_version": 1,
  "generated_at": "2026-06-19T00:00:00Z",
  "generator": "scripts/sync_official_asset_catalog.py",
  "snapshots": [],
  "items": []
}
```

Each item uses a URL-based canonical id and keeps provider membership separate
from live verification:

```json
{
  "id": "url:https://example.com/asset.usd",
  "kind": "asset",
  "name": "asset.usd",
  "aliases": ["asset"],
  "canonical_url": "https://example.com/asset.usd",
  "provider": "omni.simready.explorer",
  "source_root": "https://example.com/",
  "category": "Props",
  "extension_id": "omni.simready.explorer",
  "extension_version": "1.1.4",
  "provided_in": [
    {
      "app_profile": "isaac-sim",
      "app_version": "6.0.0",
      "kit_version": "110.1.1",
      "provider": "omni.simready.explorer"
    }
  ],
  "loadable_in": [
    {
      "app_profile": "isaac-sim",
      "app_version": "6.0.0",
      "kit_version": "110.1.1",
      "verification_status": "load_verified",
      "checked_at": "2026-06-19T00:00:00Z"
    }
  ],
  "verification_status": "load_verified"
}
```

Allowed statuses are `discovered`, `url_validated`, `inspect_verified`,
`load_verified`, `assign_verified`, `failed`, `skipped`, and `stale`.

Asset load verification records must include quality evidence before they can
be trusted as `load_verified`:

- `load_quality` — `valid`, `content_verified_no_bbox`, `empty_content`,
  or `failed`.
- `load_quality_warning` — human-readable reason when quality is not `valid`.
- `bbox_valid` and `bbox_validation_reasons` — rejects sentinel, empty,
  non-finite, reversed, or zero-extent bboxes.
- `has_authored_children`, `has_default_prim`, and `prim_count_valid` —
  content evidence used with bbox sanity.

A successful `stage_load_usd` call is not enough by itself. The verifier must
also record content evidence from authored children, default prim, or prim
count. Some official USD files are valid libraries or composition roots with no
geometry bbox; when they have content evidence, keep them `load_verified` with
`load_quality=content_verified_no_bbox`, `bbox_valid=false`, and the quality
warning recorded. Only missing content evidence or failed API calls should
produce `failed`.

## Workflow

Run discovery without launching Kit from the repo root:

```powershell
.venv\Scripts\python.exe scripts\sync_official_asset_catalog.py --profiles isaac-sim usd-composer --verify url --resume
```

For full verification, start or attach Kit from the matching workspace worker
first, then run the script against that running REST endpoint. Verification is
sequential per app, retries once, and defaults to 120 s for assets and 45 s for
materials.

For broad official verification, prefer longer per-item timeouts (for example,
`--asset-timeout-s 180 --material-timeout-s 180`) and stop to audit if official
assets unexpectedly fail or timeout. Do not accumulate large failure batches
before checking whether the verifier, REST lifecycle, path sanitization, or load
timing is at fault.

Use an existing URL/discovery snapshot for broad live verification chunks so
each chunk avoids re-crawling S3:

```powershell
.venv\Scripts\python.exe scripts\sync_official_asset_catalog.py `
  --source-run-id full-url-both-20260619-1 `
  --run-id full-live-20260619-1 `
  --profiles isaac-sim `
  --verify full `
  --verify-kind asset `
  --verify-limit 50 `
  --resume
```

`--verify-limit` processes the next not-yet-classified candidates after reading
`verification/<run_id>.jsonl`. Existing `load_verified`, `assign_verified`,
`failed`, or `skipped` records are rehydrated into the snapshot and not rerun
unless `--rerun-classified` is passed.

Use `--verify-id` to rerun exact items without offset arithmetic. The value can
be either the item `id` (`url:<canonical_url>`) or the bare canonical URL. Pair
it with `--rerun-classified` when auditing an item already classified as
`failed` or `skipped` in the same run.

S3 LIST keys are URL-escaped when converted to canonical URLs. This matters for
official folders such as `Floor Lamps` and `Table Lamps`; literal spaces in a
canonical URL are a tooling/path-sanitization bug, not evidence that the asset
is missing.

## Provider Coverage

Provider coverage is app-profile specific. The current USD Composer profile
loads some browser extensions from the per-user Kit cache, for example
`%LOCALAPPDATA%/ov/data/Kit/KKR USD Composer/0.1/exts/<bucket>/...`, not only
from the app install tree. The sync script includes those profile-specific
cache roots when the app `.kit` package title/version identifies the cache.

For USD Composer, `omni.kit.browser.material` is discovered through the
Composer material extension and app `.kit` overrides. `omni.kit.browser.asset`
and `omni.simready.explorer` may be live registered/enabled from the Composer
user cache; when present, their extension settings provide the same official
Asset Browser and SimReady roots used for catalog discovery. If a future
profile snapshot reports empty roots for enabled browser providers, inspect the
live extension path first before concluding the app lacks coverage.

## Tool Use

Use `official_asset_search` before legacy `asset_search` when selecting NVIDIA
official browser-extension assets or materials. Stale snapshot hits can be
returned with warnings, but any result with `verify_required_before_use=true`
must be passed to `official_asset_verify` before stage placement or material
assignment.
For repeatable scratch/test-stage live proof, use `docs/mcp-usage-guide.md` and
`docs/invariants/scenario-validation.md` §"Official asset scenario proof sequence";
the proof must assert `--expect-live-status passed`,
`official_asset_verify:verification_status=load_verified`,
`official_asset_verify:kind=asset`,
`official_asset_verify:app_profile=isaac-sim`, and
`official_asset_verify:load_quality=content_verified_no_bbox` when proving the Isaac Sim asset
workflow.
For repeatable read-only catalog diagnostics, use
`smoke/official_asset_catalog_diagnostics.yaml`; keep
`stage_mutation_summary.read_only=true` and assert
`--expect-live-status passed`,
`--expect-live-failure-step-error get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND`,
`search_known_miss:diagnostics.reason=query_no_match` plus
`get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`.
Current public proof anchors include
`docs/artifacts/official-asset-verify-stop-guard-refresh-2026-06-26.md` for the
bounded live proof and
`docs/artifacts/official-asset-tool-order-dry-run-refresh-2026-06-26.md` for
the docs-only tool-order dry-run.

Carry the same `app_profile` through `official_asset_search`,
`official_asset_resolve`, `official_asset_get`, and `official_asset_verify` when
the workflow starts from a profile-specific latest pointer such as
`latest-isaac-sim.json`. Exact id/URL lookups are still profile-scoped when an
`app_profile` is supplied; a hit from a different app profile must be treated as
not found and recovered through the reported diagnostics rather than verified or
used directly.

Direct `official_asset_verify` on-demand response accepts an Isaac Sim asset proof
only when the response preserves `data.verification_status=load_verified`,
`data.kind=asset`, `data.app_profile=isaac-sim`, and `data.load_quality`
(`content_verified_with_bbox` or `content_verified_no_bbox`). Direct proof is a
bounded operator check; use the scenario/probe wrapper from
`docs/mcp-usage-guide.md` when repeatable public evidence or field assertions are
required. On failure, inspect `data.diagnostics.reason`,
`data.diagnostics.asset_checks` or `data.diagnostics.material_checks`,
`data.diagnostics.error_type`, `data.diagnostics.suggested_next`, and
`data.diagnostics.fallback_tool_order` before retrying or falling back to
legacy `asset_search`. The direct verifier writes ignored
`verification-on-demand.jsonl`; do not commit generated verification records.

When `official_asset_search` returns zero candidates, or when
`official_asset_resolve`, `official_asset_get`, or `official_asset_verify`
cannot find an entry, inspect `data.diagnostics.reason`, `candidate_counts`,
`available_profiles`, `available_providers`, `suggested_next`, and
`fallback_tool_order` before widening the workflow. Prefer the listed official
catalog recovery steps before using legacy `asset_search`. In scenario runs,
`scenario_last_report(report_format="markdown", redact_local_paths=true)` gives
the public-safe triage view for `diagnostics.reason`, available profile/provider
filters, key `diagnostics.candidate_counts` values, `suggested_next`, and
`diagnostics.fallback_tool_order`; use default JSON `scenario_last_report` for
exact fields in the same MCP host.
If `official_asset_sync_status(app_profile=...)` reports `profile_count=0`,
inspect `data.diagnostics.available_profiles` and
`data.diagnostics.available_providers` before assuming the catalog is empty.

Runtime result fields that identify the catalog location are public-safe.
Catalogs inside this repository are reported as project-relative POSIX paths;
catalogs injected from an external or temporary directory are reported as
`<external-catalog>/<filename>` instead of a host-local absolute path.
`official_asset_sync_status` also redacts provider extension directories as
`<external-extension>/<directory-name>` while preserving public source-root
URLs.
