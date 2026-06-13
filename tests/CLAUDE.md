<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Unit tests — pytest-based mock verification, excluding live E2E -->

# tests — Unit Tests

Mock-based unit testing. Verifies module logic and tool registration without the actual Isaac Sim / Lakehouse.

## run

```bash
uv run pytest tests/
uv run pytest tests/unit/test_stage_module.py -v    # single file
```

Automatic collection of `tests/` according to the settings of `[tool.pytest]` in `pyproject.toml`.

## Structure

```
tests/
├── conftest.py                         # shared fixtures (MockIsaacRestClient / MockLakehouseClient)
├── unit/
│   ├── test_*_module.py                # per-domain module unit tests (mock HTTP client based)
│   ├── test_scenario_runner.py         # loader/compiler unit
│   ├── test_scenario_integration.py    # runner integration (SimulationModule routing, diff_snapshots/job ctx)
│   └── test_tools_registration.py      # EXPECTED_MODULE_TOOLS / EXPECTED_SCENARIO_TOOLS frozenset SoT
└── fixtures/                           # JSON/YAML snapshots — mock response source
```

GUI-equiv live verification is `scripts/live_test_gui_equiv.py` — unit tests are mock-based, so file system-dependent functions such as save/open are only for live.

## Test Strategy

- **Mock HTTP client**: Mock `IsaacRestClient` / `LakehouseClient` and verify that the module calls the correct endpoint + converts the response into a typed result.
- **Fixture file**: Place the same JSON/YAML snapshot as the actual response in `fixtures/` and inject it as a mock return value.
- **Scenario runner**: Verify state_machine flow (Arrange→Act→Assert→Cleanup, Cleanup finally guaranteed) while mocking all modules. `continueOnFailure: true` does not affect the phase terminal (branch to helper `_phase_has_fatal_failure()`)
- **Tool registration**: `test_tools_registration.py` — `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` Set frozenset to SoT and verify that it exactly matches the registered set (FAIL for all omissions/excesses). Count assertion derives `len()` → No need to modify literal when adding phase

## Scope Restrictions (IMPORTANT)

- **There is no live Isaac Sim / Lakehouse integration test in `tests/`**
- Actual end-to-end verification is performed with `scenarios/*.yaml` + `scenario_validate` MCP tool

## Add test

- New module method → Add mock-based case to the corresponding `tests/unit/test_<domain>_module.py`
- New MCP tool → Add tool registration confirmation to `test_tools_registration.py`
- Add action_registry branch and state_machine flow case to new scenario action → `test_scenario_runner.py`

## Related Boundaries

- Module implementation: `../src/omniverse_kit_mcp/modules/CLAUDE.md`
- Tool registration contract: `../src/omniverse_kit_mcp/tools/CLAUDE.md`
- Scenario Engine: `../src/omniverse_kit_mcp/scenario/CLAUDE.md`