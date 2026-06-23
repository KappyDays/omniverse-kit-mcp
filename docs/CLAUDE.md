<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Project document root — live tool catalog + references + pull-docs -->

# docs — Document root

omniverse-kit-mcp records “what you can do now” (tool catalog) and “what you need to read before working” (invariants / runbooks / references) separately. Root CLAUDE.md "Required pull-doc before work" table is the entry point.

## file structure

| file/subdirectory | role | update rule |
|---------------------|------|--------------|
| `mcp-usage-guide.md` | **Task-first MCP gateway** — route common work to first tools and canonical pull-docs before loading the full catalog | Keep short; link invariants/runbooks instead of duplicating rules |
| `tool-catalog.md` | **All full-mode MCP tools now callable** — signature, description, parameters. Exact generated reference after using the task guide | **Auto-generated**. `scripts/generate_tool_catalog.py` Re-execution required. `tests/unit/test_tool_catalog_sync.py` detects drift |
| `tool-diagnostic-map.md` | **Error/Failure Diagnosis** — Question → MCP read-only tool inverted index + debugging workflow | When a new diagnostic pattern is discovered |
| `invariants/` | **Must-read pull-docs before work** — asset discovery / USD load / process lifecycle / live worker coordination / MCP tool addition / module addition / extension reload / UI invoke / scenario validation / multi-app / visual-validation / public repo hygiene: 12 files. The "Required pull-doc before work" table in root CLAUDE.md is the entry point. | Hard cap ≤200 lines. Add new permanent rules here |
| `runbooks/` | **Failure-response pull-docs** — kit-stdin-deadlock / cold-boot-timeout / hub-orphan / env-sub-config / kit-dep-solver-fail / multi-app / scene-reexport-lock: 7 files. Ignored in normal development flow, referenced only in case of failure | Hard cap ≤300 lines. Add new failure types here |
| `references/` | public-safe curated refs. Local generated extension catalog / snapshots are ignored | Details: `references/CLAUDE.md` |
| `artifacts/` | Live validation output. Result storage used by validation script | Live test script is written directly |
| `oss-application-notes.md` | public OSS support application summary. Repo purpose / maintenance signal / public boundary clearance without personal information | Short disclosure description for application/README upon renewal |

## tool-catalog.md — auto-regeneration rules

1. When registering a new MCP tool via the selected wrapper or changing the existing tool signature **Must be regenerated**:
   ```
   .venv/Scripts/python.exe scripts/generate_tool_catalog.py
   ```
2. Or all at once: `.venv/Scripts/python.exe scripts/verify_mcp_sync.py` (run regen + pytest drift check together)
3. Commit must include the `docs/tool-catalog.md` change. If you push without it, `test_tool_catalog_sync` will fail.
4. **Do not allow humans to edit this file manually** — it will be overwritten on the next regen. If typos/clarifications need improvement, edit the `tools/module_tools.py` docstring and regen.

## Root referencing this directory from external sessions

- Another Claude Code session / LLM asked "What can you do with omniverse-kit-mcp" → start with `docs/mcp-usage-guide.md`; use `docs/tool-catalog.md` only for exact signatures and the complete full-mode surface.
- When looking for Kit SDK unpublished API → Check for duplicate existing `docs/tool-catalog.md` → If there is local generated catalog, `extension_search` → Actual Kit source/official document.

## Related Boundaries

- Tool registration contract: `../src/omniverse_kit_mcp/tools/CLAUDE.md`
- tool name SoT: frozenset of `../tests/unit/test_tools_registration.py`
- catalog regeneration: `../scripts/CLAUDE.md`
- Extension REST contract: `../kkr-extensions/CLAUDE.md`
