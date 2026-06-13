<!-- Parent: ../../../CLAUDE.md -->
<!-- Scope: Scenario engine — YAML → Arrange/Act/Assert/Cleanup execution engine -->

#scenario — Scenario Engine

Read the YAML scenario and execute it in the following order: Arrange → Act → Assert → Cleanup. The MCP tool layer (`tools/scenario_tools.py`) wraps this engine and exposes it to tools such as `scenario_validate`.

## State machine

The execution steps are in a fixed order:

```
Arrange ─► Act ─► Assert ─► Cleanup (always, finally)
```

- **Arrange**: Pre-state preparation (stage_load_usd, stage_create_prim, lakehouse_query, etc.). Lakehouse injection is not possible (query only)
- **Act**: Action to be verified (extension_trigger, simulation_play, etc.)
- **Assert**: State verification (stage_assert_prim_exists, stage_assert_property, viewport_compare_ssim, etc.)
- **Cleanup**: Clean up resources — **Always run as a final block** (Guaranteed even if the assertion fails, Key Decision)

## File role

| file | Role |
|------|------|
| `loader.py` | YAML file → raw dict |
| `schema.py` | JSON Schema (`SCENARIO_SCHEMA`) + module enum |
| `compiler.py` | raw dict → `CompiledScenario` (type verification + variable substitution) |
| `action_registry.py` | **YAML `args` dict → typed request mapping** + `CONTEXT_AWARE_ACTIONS` set. When adding a new action, be sure to add a branch here |
| `context.py` | Execution context — sharing artifact / step_data between steps |
| `runner.py` | loader → compiler → state_machine → reporter orchestrator. All ModuleName enums must be registered in the module dispatch dict. `_phase_has_fatal_failure()` excludes `continueOnFailure: true` step from phase terminal |
| `state_machine.py` | Arrange/Act/Assert/Cleanup steps |
| `reporters.py` | Execution result → markdown/json report |

## Add new action flow

1. Add module method to `modules/<domain>_module.py` (returns `ok_result` / `error_result`)
2. Register MCP tool as `@mcp.tool()` decorator in `tools/module_tools.py`
3. Add YAML args → typed request builder to `scenario/action_registry.py` (`_REGISTRY` dict)
4. If it is a context-aware action, add `(ModuleName.X, "action")` to `CONTEXT_AWARE_ACTIONS` + add branch to `runner._execute_context_aware`
5. `scenarios/schema/scenario.schema.json` action enum + args schema update (SoT)
6. Synchronize `SCENARIO_SCHEMA` of `scenario/schema.py` with schema.json
7. Add routing regression test to `tests/unit/test_scenario_integration.py`

## Context-aware action pattern

Most actions are executed with only the `args` dict, but some actions require pulling the result of the previous step from ctx:

| module | action | ctx reference |
|--------|--------|---------|
| `stage` | `diff_snapshots` | `before_step_id`, `after_step_id` → `ctx.get_step_data(step_id)` eliminates 2 StageSnapshots |
| `job` | `status` | `navigate_step_id` → Resolve `*NavigateResult.job_id` of the preceding `robot.navigate_to` / `character.navigate_to` to duck-typed `getattr(prior, "job_id", None)` and polling (`poll_interval_s`, `max_polls`, `expected_status`). `job_id` can also be specified directly. Cancel using `job.cancel` or MCP tool `job_cancel` |

Runner flow: If the action is in `CONTEXT_AWARE_ACTIONS`, dispatch it to `_execute_context_aware`. If not, use the existing path (`build_request` → typed request → module method).

## Module ↔ action routing

Stage WRITE actions (`stage_load_usd`, `stage_set_property`, `stage_create_prim`, `stage_delete_prim`) are actually implemented in `SimulationModule`, so they must all be **`module: simulation`** in YAML / action_registry. `module: stage` only supports READ/ASSERT/DIFF (StageModule holding method).

## Schema synchronization (important)

- **Source of truth**: `scenarios/schema/scenario.schema.json`
- The dataclass type of `scenario/schema.py` must always match schema.json.
- If there is a mismatch, a runtime error occurs while executing `scenario_validate` — first modify schema.json and then reflect it in schema.py

## Related Boundaries

- **Brother CLAUDE.md**:
  - `../modules/CLAUDE.md` — Module responsibility matrix + Character constraints + base.py pattern (module to be dispatched by scenario runner)
  - `../modules/integration-facts.md` — 15 domain runtime constraints (non-obvious trap)
  - `../modules/process-ops.md` — ProcessModule Operation Manual (hang/.env)
  - `../tools/CLAUDE.md` — MCP tool registration convention + `_resolve_safe_path` boundary
  - `../CLAUDE.md` (src/omniverse_kit_mcp/) — package entry flow
- **YAML author's perspective**: `../../../scenarios/CLAUDE.md` (This file is internal to the engine, that file is a user guide)
- **Parent**: root `CLAUDE.md`