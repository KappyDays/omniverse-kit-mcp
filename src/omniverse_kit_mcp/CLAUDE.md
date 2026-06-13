<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: FastMCP server package root — entry flow, type boundary, HTTP clients -->

# omniverse_kit_mcp — FastMCP server package root

Entry package for `uv run omniverse-kit-mcp`. Extension REST + Lakehouse REST + OS process calls are bundled with the MCP tool.

## Package Layout

```
src/omniverse_kit_mcp/
├── main.py                # CLI entrypoint (`uv run omniverse-kit-mcp` wired to)
├── config.py              # AppConfig — environment variables → typed config
├── exceptions.py          # custom exceptions
├── mcp/
│   ├── server.py          # FastMCP server assembly (AppConfig + SYSTEM_PROMPT + tool registration)
│   └── prompts.py         # SYSTEM_PROMPT definition
├── clients/
│   ├── isaac_rest_client.py   # → Extension REST (ISAAC_SIM_BASE_URL)
│   └── lakehouse_client.py    # → Lakehouse REST (LAKEHOUSE_BASE_URL)
├── modules/               # domain modules → modules/CLAUDE.md
├── scenario/              # scenario engine → scenario/CLAUDE.md
├── tools/                 # MCP tool registration → tools/CLAUDE.md
└── types/                 # internal dataclass types
    └── common / extension / lakehouse / scenario / simulation / stage / viewport / robot / job / character.py
```

## Entry Flow

```
uv run omniverse-kit-mcp
  → main.py                        (CLI bootstrap)
  → mcp/server.py
      ├─ AppConfig.load_from_env() (config.py)
      ├─ SYSTEM_PROMPT inject      (mcp/prompts.py)
      ├─ clients initialization             (clients/*)
      ├─ modules initialization             (modules/*)
      └─ tool registration                  (tools/module_tools.py + tools/scenario_tools.py)
  → FastMCP stdio server start
```

## Type Boundary Convention (Important)

- **Internal Type**: `@dataclass(slots=True, frozen=True)` — `types/` all
- **Pydantic only at REST boundaries**: Use only `kkr-extensions/.../models/` inside extension
- The MCP server code (the entire `omniverse_kit_mcp` package) does not create a Pydantic model — the REST response is converted to dict → dataclass in the client layer.

## Clients External Communication Protocol

| Client | Target | environment variables |
|--------|--------|-----------|
| `isaac_rest_client.py` | Extension REST `/validation/v1` | `ISAAC_SIM_BASE_URL` (default `http://127.0.0.1:8111`) |
| `lakehouse_client.py` | Lakehouse REST | `LAKEHOUSE_BASE_URL` (default `http://localhost:9000`) |

- All async (httpx based)
- The client is only responsible for raising exceptions in case of a network error — `error_result()` of `modules/base.py` is responsible for wrapping it in ModuleResult.
- Health polling is performed directly by `process_module.py` (MCP server startup itself is independent of Isaac Sim status)

## MCP server import cache (must read during development)

MCP host (Claude Code / Codex CLI) spawns the `omniverse-kit-mcp` server once in stdio when the session starts and caches the Python import. Modifications inside this package (`src/omniverse_kit_mcp/`) **will not be reflected in MCP tool calls until host restart**. Use standalone script for in-session verification:- `scripts/run_scenario_standalone.py <scenario_path>` — Run compiler/runner/modules with the latest code. Relative paths are resolved in the following order: `config.scenario.scenarios_dir` → project root.
- `scripts/run_process_module_standalone.py <start|stop|restart>` — Only ProcessModule runs separately

Since the extension code (`kkr-extensions/`) is a separate process from the MCP server, it is immediately reflected by deleting `kit_app_restart` / `__pycache__`.

## Related Boundaries

- Module responsibility/REST response characteristics: `modules/CLAUDE.md`
- Scenario Engine: `scenario/CLAUDE.md`
- MCP tool registration contract: `tools/CLAUDE.md`
- Inside extension (Pydantic models, REST router): `../../kkr-extensions/CLAUDE.md`