<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Build scene / select asset (add robot·character·environment·prop·simready) Required knowledge before starting work -->
# Asset Discovery — Invariants

Create a scene or add robot / character / environment / prop / SimReady asset
**Before** Read this file. NVIDIA·Isaac Sim 6.0 has rich real assets (robots 90+,
Provides environments 10, people·animations, props, SimReady 1000+) — remembered URLs
Do not use remembered URLs or primitive stand-ins for user-facing deliverables;
**find the actual asset in the catalog first**.

This document follows Validation Rule **R1**: actual outputs use actual assets,
while controlled prototype/test/demo fixtures may use primitives. Operationalize
with **entry workflow**, not validation.

## Discovery workflow (4 steps)

1. **Categorizing Request Types** — What to Place? (robot / character / environment / prop /
simready/etc). See mapping table below.
2. **Get URL** — Natural language needs → concrete USD URL. Prefer
**`official_asset_search`** when `docs/references/official-assets/latest.json`
exists (generated NVIDIA browser-extension catalog; stale hits require
`official_asset_verify` before use), then **`asset_search`** (Offline, Isaac
operates even when not started). As an auxiliary catalog markdown directly Read, live `asset_list` /
`content_browse`. “URL Acquisition Path” below.
3. **Check load safety conditions** — Compliance with load conditions of `docs/invariants/usd-load.md` (full HTTPS
S3 URL, `file://` prohibited, automatic stop-guard during play, skip/fallback/placeholder prohibited).
4. **Load** — `stage_load_usd` (composition) / `stage_open` (scene replacement) / `robot_load` /
`character_load`. character must be `character_load` (raw reference is T-pose).

## Request Type → Catalog File Mapping

Catalog SoT entry point: `docs/assets/isaac/asset_inventory.md` (index). Required Category
Read only files — no unnecessary token consumption.

| request type | catalog file to read | rod tool |
|---|---|---|
| Robot (AMR, humanoid, quadruped, arm, gripper, drone) | `docs/assets/isaac/assets/robots.md` | `robot_load` |
| Environment / Scene (warehouse, office, hospital, grid) | `docs/assets/isaac/assets/environments.md` | `stage_open` (replacement) / `stage_load_usd` |
| People / Characters / Animation | `docs/assets/isaac/assets/people.md` | `character_load` |
| Industrial prop (pallet, forklift, shelf, KLT) | `docs/assets/isaac/assets/props.md` | `stage_load_usd` |
| Furniture/Boxes/Containers (SimReady 1000+) | `docs/assets/isaac/assets/simready.md` | `stage_load_usd` |
| RL Learning / Materials / Examples / Sensor USD | `docs/assets/isaac/assets/other.md` | By use |

## URL acquisition path

The four paths are complementary. **Planning stage / If Isaac is not started,
`official_asset_search` is 1st when generated; otherwise `asset_search` is 1st.**

0. **`official_asset_search(query, kind=None, app_profile=None, provider=None)` —
Generated official catalog, offline.** Searches ignored NVIDIA official
asset/material snapshots from browser providers. Use `official_asset_resolve`
for concrete USD/MDL targets and `official_asset_verify` when stale or not
load/assign verified for the target app.
For repeatable live proof or public evidence, route through
`docs/invariants/scenario-validation.md` §"Official asset scenario proof sequence"
and `docs/mcp-usage-guide.md`; the proof must assert
`official_asset_verify:verification_status=load_verified`,
`official_asset_verify:kind=asset`, and
`official_asset_verify:app_profile=isaac-sim` on the `official_asset_verify`
evidence row.
Direct on-demand `official_asset_verify` response is only bounded operator
evidence. Accept it before placement only after checking
`data.verification_status=load_verified`, `data.kind`, `data.app_profile`, and
`data.load_quality` (`content_verified_with_bbox` or
`content_verified_no_bbox` for asset loads). On failed records inspect
`data.diagnostics.reason`, `data.diagnostics.asset_checks` or
`data.diagnostics.material_checks`, `data.diagnostics.error_type`,
`data.diagnostics.suggested_next`, and `data.diagnostics.fallback_tool_order`
before retrying or falling back to `asset_search`. `official_asset_verify`
appends ignored `verification-on-demand.jsonl`; commit only redacted stable
fields and keep generated verification files out of public artifacts.
1. **`asset_search(query, category=None, limit=20)` — Legacy curated catalog, offline.** Curation markdown
Read the catalog directly from the MCP server process + ranking → `[{name, url, category,
   source_file}]`. Live REST / Isaac Startup **Not Required**. Example: `asset_search("forklift")`,
`asset_search("warehouse", category="environments")`. (Natural language such as “Find a forklift”
A first-level path that maps the query to a concrete USD URL.)
2. **`asset_list(category, subpath)` — Live, S3 directory listing.** Requires Isaac startup.
Latest folder not in catalog / To check exact file name. The `is_folder=false` entry is
   spawnable URL.
3. **`content_browse(url, max_entries)` — live, omni.client list.** SimReady 1000+ species
Alphabetical pagination (`$SIM` root). If the catalog contains only prose summaries, check the correct file name.

> SimReady canonical rule: `$SIM/{name}/{name}.usd`. Catalog prefix (`$ISAAC` / `$SIM`)
> declared at the top of the catalog file — replace it with a full HTTPS URL (`file://` is prohibited).

## R1 operationalize — real assets first

- **No primitive substitution**: Creating a Cube when the request is “Release the robot” is a False Positive.
Secure and load the actual NVIDIA asset URL using Catalog/`asset_search`.
- **Fixture exception**: Prototype / unit test / smoke demo / diagnostic scenes may use controlled primitive
fixtures when the primitive is the test object itself, not a substitute for a requested real asset. Example:
robot pick/place playback demo uses a 0.04 m cube fixture, and explicit real object assets still must pass
bbox/fit/visual preflight.
- **No remembered URLs**: Use catalog SoT or `asset_search` result URLs instead of hardcoded/remembered URLs.
(avoiding 404/version drift). URL 404 / inventory update is a skill
  `/omniverse-asset-inventory-sync`.
- **Prohibit skip/fallback in case of load failure**: `usd-load.md` Prohibited — Must be performed after root cause analysis
make it successful

## Related Boundaries

- Catalog SoT entry point + format convention: `docs/assets/isaac/asset_inventory.md` (+ `assets/*.md`)
- Load safety conditions (deadlock prevention baseline): `docs/invariants/usd-load.md`
- Visual verification (Read duty after capture, R3): `docs/invariants/visual-validation.md`
- Character T-pose prevention / BehaviorAgent·IRA constraint: `src/omniverse_kit_mcp/modules/CLAUDE.md`
- asset_search tool registration / caveat: `src/omniverse_kit_mcp/tools/CLAUDE.md` (Asset group)
- URL 404 / inventory update skill: `.claude/skills/omniverse-asset-inventory-sync/SKILL.md`
