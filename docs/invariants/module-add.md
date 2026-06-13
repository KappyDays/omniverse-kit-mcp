<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Required knowledge before starting work on adding a new domain module -->
# Add Module — Invariants

When adding a new domain module (`StageModule`, `RobotModule` same units), 7 locations are modified simultaneously
necessary. If action_registry / scenario schema / runner dispatch do not match
scenario YAML is silently skipped or runner KeyError is raised.

## Checklist for editing 7 places simultaneously

When adding new module `<XYZ>Module`:

1. **Module enum** — Added to enum `ModuleName` of `src/omniverse_kit_mcp/types/common.py`
2. **Module Implementation** — New `<xyz>_module.py` to `src/omniverse_kit_mcp/modules/` (base.py
(returns `ModuleResult[T]` according to pattern)
3. **Scenario schema (Python)** — typed of `src/omniverse_kit_mcp/scenario/schema.py`
Add request structure
4. **Scenario schema (JSON)** — action of `scenarios/schema/scenario.schema.json`
update validator
5. **Runner dispatch** — in the dispatch dict of `src/omniverse_kit_mcp/scenario/runner.py`
Add module mapping
6. **Register Tool** — `src/omniverse_kit_mcp/tools/scenario_tools.py` or
Addition of `@mcp.tool()` function of `src/omniverse_kit_mcp/tools/module_tools.py`
7. **Server wiring** — Create a module instance of `src/omniverse_kit_mcp/mcp/server.py`
   + tool registration call
8. **Update Module Responsibility Matrix** — Add 1 row to table for `src/omniverse_kit_mcp/modules/CLAUDE.md`

## Add module method (new method of existing module)

1. Module method implementation
2. **Action registry** — typed by `src/omniverse_kit_mcp/scenario/action_registry.py`
Add request builder
3. Tests — Add mock-based case to `test_<xyz>_module.py` in `tests/unit/`

## Add Scenario action (separate from Module method)

Simultaneously modify the following files per action:
1. `src/omniverse_kit_mcp/scenario/action_registry.py`
2. `scenarios/schema/scenario.schema.json`
3. `src/omniverse_kit_mcp/scenario/schema.py`
4. Add case to `tests/unit/test_scenario_integration.py`
5. `scenarios/CLAUDE.md` Creation Guide Updated

## ASYNC Job pattern (long-running operation)

Long-term operation like `character.navigate_to` / `robot.navigate_path`:
- Use `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/job_service.py::start_job` (coro_factory argument)
- `try-except` required (silent catch prohibited)
- Tool returns `job_id`, MCP host (Claude Code / Codex CLI) polls `job_status`

## Related Boundaries

- Module Responsibility Matrix: `src/omniverse_kit_mcp/modules/CLAUDE.md`
- Scenario engine (Arrange/Act/Assert/Cleanup, action_registry, context-aware dispatch):
  `src/omniverse_kit_mcp/scenario/CLAUDE.md`
- Scenario YAML Author: `scenarios/CLAUDE.md`
- Scenario validation rules: `docs/invariants/scenario-validation.md`
- Tool registration contract (follow-up of 7 simultaneous modifications): `docs/invariants/mcp-tool-add.md`
- Test strategy: `tests/CLAUDE.md`
