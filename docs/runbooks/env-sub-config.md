<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Diagnosis of silent failure where .env variable is ignored -->
# env sub-config silent failure (L14)

If `ISAAC_SIM_*` / `LAKEHOUSE_*` / `MCP_*` / `SCENARIO_*` of `.env` are silently ignored,
Enter this file.

## Symptoms (Actual measurement on 2026-04-23)

- Always ignore `ISAAC_SIM_STARTUP_TIMEOUT=120.0` of `.env` → Use default 240.0
- Always ignore `ISAAC_SIM_EXTRA_EXT_IDS=[7 entries]` of `.env` → Default only 4 active →
  `omni.mycompany.navmesh_playground`, etc. not registered
- Silent failure with no effect even if user/operator changes `.env`
- The code/variable names are all correct, but it doesn’t work.

## Root cause

pydantic-settings v2 is installed on the sub-`BaseSettings` instance created with `default_factory`.
**Do not propagate `env_file` from parent**. `AppConfig(BaseSettings)`
Even if you have `model_config = SettingsConfigDict(env_file=".env")`, sub-config
(`IsaacSimProcessConfig`, etc.) becomes `Field(default_factory=IsaacSimProcessConfig)`
When instantiated, each sub-config is an independent BaseSettings instance → `env_file` of the parent
Not propagated → If there is no own `env_file`, only refer to OS environment variables.

## Fix application location

`src/omniverse_kit_mcp/config.py` (SoT). Every sub-`BaseSettings` to its own `env_file=".env"`
Specify:

```python
class IsaacSimProcessConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ISAAC_SIM_",
        env_file=".env",      # CRITICAL — must be specified on each sub-config
        extra="ignore",
    )
    ...
```

Target sub-config (applies all):
-`IsaacSimConfig`
-`IsaacSimProcessConfig`
-`LakehouseConfig`
-`MCPServerConfig`
-`ScenarioConfig`

## Verification (required before PR)

```bash
.venv/Scripts/python.exe -c "from omniverse_kit_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout, len(ac.isaac_sim_process.extra_ext_ids))"
```

→ The value of `.env` must be reflected (e.g. 120.0 / 7).

Permanent regression detection (automatic): `tests/integration/test_env_sub_config.py` (E14-1 / E14-2 /
E14-3 — Verify that all sub-`BaseSettings` have `env_file=".env"` by AST parsing).

## Prevent recurrence (checklist when adding new sub-config)

When adding a new `class XYZConfig(BaseSettings)`, you must:
1.Specify `model_config = SettingsConfigDict(env_prefix="XYZ_", env_file=".env", extra="ignore")`
2. test_env_sub_config.py E14-3 automatically verifies — no additional code required

## Related Boundaries

- L14 accident record original text: `kkr-extensions/docs/lessons-learned.md`
- Config SoT: `src/omniverse_kit_mcp/config.py`
- Process life cycle invariants: `docs/invariants/process-lifecycle.md`
- Permanent regression test: `tests/integration/test_env_sub_config.py`