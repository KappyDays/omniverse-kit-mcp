<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Build scene / select asset (add robot·character·environment·prop·simready) Required knowledge before starting work -->
# Asset Discovery — Invariants

Create a scene or add robot / character / environment / prop / SimReady asset
**Before** Read this file. NVIDIA·Isaac Sim 6.0 has rich real assets (robots 90+,
Provides environments 10, people·animations, props, SimReady 1000+) — remembered URLs
Don't go for or primitive (Cube/Sphere), but **find the actual asset in the catalog first**.

This document follows the Validation Rule **R1** ("Only real assets — no primitive substitution").
Operationalize with **entry workflow**, not validation.

## Discovery workflow (4 steps)

1. **Categorizing Request Types** — What to Place? (robot / character / environment / prop /
simready/etc). See mapping table below.
2. **Get URL** — Natural language needs → concrete USD URL. **`asset_search` priority** (Offline, Isaac
(operates even when not started). As an auxiliary catalog markdown directly Read, live `asset_list` /
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

The three paths are complementary. **Planning stage / If Isaac is not started, `asset_search` is 1st.**

1. **`asset_search(query, category=None, limit=20)` — Primary, offline.** Curation markdown
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

## R1 operationalize — real assets only

- **No primitive substitution**: Creating a Cube when the request is “Release the robot” is a False Positive.
Secure and load the actual NVIDIA asset URL using Catalog/`asset_search`.
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
