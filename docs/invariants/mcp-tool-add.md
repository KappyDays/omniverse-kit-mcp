<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Essential knowledge before starting work on adding a new MCP tool -->
# Add MCP Tool — Invariants

> **This document is for “additional steps” only.** Determining which Kit API/ext to wrap
> **research phase** is the public-safe flow of `docs/references/CLAUDE.md`
> (Check for existing tool duplication → optional local catalog → actual ext source → official document)
> Follow first. If you refer to this document without research,
> Duplicate existing `@mcp.tool()` / Risk of selecting wrong Kit API.

Adding a new `@mcp.tool()` means modifying 7 places simultaneously + passing auto-regen catalog + drift test**
3-step. If you miss even one place, `verify_mcp_sync.py` / drift pytest fails.

## Checklist for editing 7 places simultaneously

When adding a new MCP tool, you must also change:

1. **Extension REST endpoint** — `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/` or router
2. **REST client** — Add `src/omniverse_kit_mcp/clients/isaac_rest_client.py` method
3. **Module wrapper** — typed async method in `src/omniverse_kit_mcp/modules/` domain module
4. **MCP tool registration** — `@mcp.tool()` decorator function of `src/omniverse_kit_mcp/tools/module_tools.py`
5. **Mock client** — MockIsaacRestClient in `tests/conftest.py` + new method
6. **Tool name SoT** — `EXPECTED_MODULE_TOOLS` of `tests/unit/test_tools_registration.py`
or add `EXPECTED_SCENARIO_TOOLS` to frozenset
7. **Tool group caveat** — `src/omniverse_kit_mcp/tools/CLAUDE.md` One line in that group section

## Regeneration (required one-time manual execution)

```bash
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

Run these commands together:
1. `scripts/generate_tool_catalog.py` — Recreate `docs/tool-catalog.md`
2. `pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py` —
drift inspection
3. `git status` — Check the generated file unchanged

## Drift verification (required before commit)

```bash
uv run pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py
```

- `tests/unit/test_tools_registration.py` — Registered tool set ↔ EXPECTED_*_TOOLS frozenset
Exact match (FAIL for both missing/exceeded)
- `tests/unit/test_tool_catalog_sync.py` — `docs/tool-catalog.md` is synchronous with the current registration state.

## Add/Move MCP Resource (separate procedure)

When adding/moving `@mcp.resource(uri=...)`:
1. `src/omniverse_kit_mcp/mcp/resources.py` decorator function + `RESOURCE_SOURCES` dict mapping
update (file-backed = `Path`, Python-backed = `None`)
2. Add/remove URI to `EXPECTED_RESOURCES` in `tests/unit/test_resources_paths.py`
3. `uv run pytest tests/unit/test_resources_paths.py` — FAIL if mapping is misaligned

## Prohibited during reconfiguration operation

Do not add new tools while CLAUDE.md Pull-First reconfiguration is in progress (Operating Invariant —
MCP surface invariant).

## Related Boundaries

- Tool registration contract + caveat by group: `src/omniverse_kit_mcp/tools/CLAUDE.md`
- Module Responsibility Matrix: `src/omniverse_kit_mcp/modules/CLAUDE.md`
- Test strategy: `tests/CLAUDE.md`
- Catalog regen script details: `scripts/CLAUDE.md`
- Type boundary (dataclass vs Pydantic): `src/omniverse_kit_mcp/CLAUDE.md`
- Apart from adding a new module / scenario action: `docs/invariants/module-add.md`
