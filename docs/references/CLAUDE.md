<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: docs/references/ Editing rules + public-safe reference management -->

# docs/references/ — Editing rules & public-safe reference management

> Only curated references are placed in public repo. Local Kit/Isaac Sim/USD
> Composer installation metadata or external document snapshots can be created, but not committed.
>No.

## Reference file map

| file/subdirectory | Use | Regeneration method |
|---------------------|------|---------------------------|
| `sensor_menu_catalog.md` | All sensors in `Create > Sensors` menu — vendor × model grouping + `window_menu_trigger` menu_path | Recall `window_menu_list(menu_path="Create")` after starting Isaac Sim |
| `extensions.json` / `extensions-catalog.md` / `harvest-progress.json` | Locally installed extension catalog (ignored in public repo) | `harvest_extension_metadata.py` + `render_catalog_md.py` |
| `app-specific/` / `testbed-snapshot/` | Local research enrichment material (ignored in public repo) | Recreate locally when needed / Store separately |

## MCP function research order (task-driven, based on autonomous loop)

Research flow when trying to perform user natural language tasks with MCP. Each step depends on the results of the previous step.

0. **Duplicate check**: Search for an existing MCP tool corresponding to the task in `docs/tool-catalog.md`. If so, reuse (end this flow).
1. **Check for duplicate existing tools**: Search MCP tool corresponding to the task in `docs/tool-catalog.md`.
2. **Search if local catalog exists**: `extension_search(...)` or ignored
   Identification of candidate exts in `docs/references/extensions-catalog.md`. If not, go to the next step
   Proceed and regenerate the catalog locally if necessary.
3. **Exploring the actual source** — Check directly from the installation path for each app:
   - Isaac Sim: `<isaac-sim-root>/exts`, `extscache`, `kit/extscore`
   - USD Composer: `<usd-composer-root>/exts`, `extscache`, `extsbuild`, `kit/extscore`
   - **Command pattern search tip**: Many exts expose one-time operations in the form of `omni.kit.commands.execute("<CommandName>", **kwargs)`. Candidate search: Look up related exts with MCP's `extension_search("<keyword>")` → Those ending with `.commands` take precedence (e.g. `omni.kit.commands`, `omni.physx.commands`, `omni.fabric.commands`, `omni.kit.graph.usd.commands`). Execute: 1-line call to `kit_command_execute("<CommandName>", payload)` in MCP (e.g. `CreateConveyorBelt` in `isaacsim.asset.gen.conveyor`).
4. **Official document**: Check the NVIDIA / Omniverse official document directly, and only durable rules
   Summary of project docs.

## Sensor request response sequence

When a user requests to “use a specific sensor”:

1. Search for the vendor/model in `sensor_menu_catalog.md`
2. Check menu_path (e.g. `Create/Sensors/RTX Lidar/Ouster/OS1`)
3. Generate USD prim by calling `window_menu_trigger(menu_path=...)` (physical sensor schema)
4. Check the new prim path with the `created_prims` field
5. Adjust mount_offset / mount_rotation with `stage_set_property` if necessary

The mock sensor (`sensor_attach_rtx_*` MCP tool) is for visual education. If you need real sensor data, use this catalog path.

## Editing Rules

- `sensor_menu_catalog.md` is tracked because it is an MCP resource source.
- The creation catalog / snapshot is `.gitignore` target. No commits to public repo.
- The durable rule found in the catalog is `docs/invariants/` or `docs/invariants/` instead of the original dump.
  Summary transfer to `docs/runbooks/`.

## extensions.json v2 schema notes

- `schema_version: 2` — based on apps map (v1 is supported only in render for backward compat).
- App name for `apps.<app>`: `"isaacsim"` / `"usd_composer"` (two allowed). present is fixed to `true`.
- `apps.<app>.source_dir` Allowed values: Isaac Sim = `exts` / `extscache` / `extsDeprecated` / `kit/extscore`. USD Composer = `exts` / `extscache` / `extsbuild`.
- `apps.<app>.deprecated: true` is automatically set only in Isaac Sim `extsDeprecated/`.
- `enrichment_status` Allowed values: Only 3 types: `"enriched"` / `"skipped"` / `"bootstrap"`. The `skipped` item must be set to `skipped_reason`.
- `api_delta_note` — Autoset only when the major.minor versions of two apps are different (ignore patch diff). Manual editing possible.
- `mcp_research_hint` (v2) == `mcp_extension_idea` (v1). v2 only field name.

## Catalog regeneration scenario

| Situation | command |
|------|------|
| Change extscache in either app (new ext/version up) | `uv run python scripts/harvest_extension_metadata.py` → `uv run python scripts/render_catalog_md.py` |
| MD resynchronization after JSON modification | `uv run python scripts/render_catalog_md.py` |
| v1 legacy single-app mode (deprecated) | `uv run python scripts/harvest_extension_metadata.py --mode v1-bootstrap [--resume]` |
| Abandon existing enrichment and re-harvest (destructive) | `uv run python scripts/harvest_extension_metadata.py --no-preserve-enrichment` |
| change testbed source | `uv run python scripts/sync_testbed_snapshot.py` |
| Rebuilt from scratch | sync_testbed → harvest → render → enrichment manual loop |

## harvest-progress.json interpretation

- Each phase status: `pending` → `running` → `complete`.
- v2 multi-app harvest does not cover the v1 bootstrap phase and supports parallel traces (candidate for future redesign — retaining v1 markers for now).
- Manual enrichment step only (Sonnet loop). The rest is automatically scripted.

## MCP tool: `extension_search` (Phase E implementation completed)

`extension_search(keyword, app, category, limit)` is locally generated
Search only when `extensions.json` is present. If there is no file in public clone
Returns `EXTENSION_CATALOG_UNAVAILABLE`. Implementation:
`src/omniverse_kit_mcp/modules/catalog_module.py`.

## Catalog synchronization after kit/app updateCanonical procedure is `/omniverse-kit-extension-catalog-sync` skill (`.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md`). Called by the user when updating Kit / Isaac Sim / USD Composer installation → 6-step workflow (diff → integrity → harvest → render → enrichment → commit). SKILL.md is SoT for procedures, invariants, and stop-conditions.

## Related Boundaries

- Parent document root: `../CLAUDE.md`
- tracked MCP resource source: `sensor_menu_catalog.md`
- ignored local generated refs: `extensions.json`, `extensions-catalog.md`,
  `harvest-progress.json`, `app-specific/`, `testbed-snapshot/`
- Regeneration script convention: `../../scripts/CLAUDE.md`