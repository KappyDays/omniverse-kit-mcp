# omniverse-kit-mcp

**Drive NVIDIA Isaac Sim 5.1 in natural language from Claude Code (or any MCP client).**

An MCP (Model Context Protocol) server that exposes Isaac Sim's GUI surface — stage editing, robot / character animation, multi-viewport capture, physics, lighting, SDG, OmniGraph, content browsing, extension management — as 107 tools plus 3 on-demand resources. Pair it with the bundled Kit Extension and Claude Code controls Isaac Sim end-to-end through stdio.

![python](https://img.shields.io/badge/python-3.11%2B-blue) ![isaac-sim](https://img.shields.io/badge/Isaac%20Sim-5.1-green) ![mcp](https://img.shields.io/badge/MCP-stdio-purple)

---

## Architecture

```
┌──────────────┐   stdio (JSON-RPC)   ┌──────────────────────┐
│ Claude Code  │ ◀──────────────────▶ │  omniverse-kit-mcp        │ FastMCP server (Python)
│  (or any     │                      │                      │
│   MCP client)│                      │  • ProcessModule  ─▶ subprocess → kit.exe
└──────────────┘                      │  • 17 domain modules │
                                      │  • 4 scenario tools  │
                                      │  • 3 MCP resources   │
                                      └──────────────────────┘
                                                 │ HTTPX  (POST /validation/v1/*)
                                                 ▼
                                     ┌──────────────────────────────┐
                                     │ omni.mycompany.validation_api │ Kit Extension (FastAPI)
                                     │  • 102 REST endpoints         │
                                     │  • services/*.py calls        │  omni.kit.commands
                                     │                               │  omni.usd / pxr.*
                                     └──────────────────────────────┘
                                                 │
                                          kit.exe (Isaac Sim 5.1)
```

Two operational paths:

| Path | Purpose | Example tools |
|---|---|---|
| **Subprocess lifecycle** | Start/stop/restart kit.exe — works without Isaac Sim running | `isaac_sim_start`, `isaac_sim_stop`, `isaac_sim_restart` |
| **REST → Extension → Kit SDK** | Scene manipulation while Isaac Sim is running | `stage_load_usd`, `robot_navigate_path`, `replicator_trigger_once`, … |

Scenario tools (`scenario_validate`, `scenario_plan`, …) are orchestrators — they compile an YAML Arrange/Act/Assert/Cleanup document into typed module calls.

---

## Quick Start

**Prerequisites**: Windows 10/11 · Python 3.11+ · [uv](https://docs.astral.sh/uv/) · [Isaac Sim 5.1 Standalone](https://developer.nvidia.com/isaac-sim) (see next section)

```bash
# 1. Clone and install deps
git clone https://github.com/<your-org>/omniverse-kit-mcp.git
cd omniverse-kit-mcp
cp .env.example .env       # then edit — see "Isaac Sim Setup" below
uv sync

# 2. Verify tooling
uv run pytest tests/                             # should be all green
.venv/Scripts/python.exe scripts/verify_mcp_sync.py   # catalog drift check

# 3. Wire into Claude Code  (~/.claude.json)
#    — see setup/ for helper scripts
```

### Isaac Sim Setup

omniverse-kit-mcp does **not auto-detect** the Isaac Sim install location. Default paths in `src/omniverse_kit_mcp/config.py` point at the developer's workstation and must be overridden.

1. **Install** Isaac Sim 5.1.0 Standalone anywhere (e.g. `C:/IsaacSim/`, `D:/programs/isaac-sim-5.1.0/`)
2. **Note** the two files you'll reference:
   - `<install>/kit/kit.exe` — the Kit application binary
   - `<install>/apps/isaacsim.exp.full.kit` — the experience config
3. **Override** in `.env` (prefix `ISAAC_SIM_` maps to `IsaacSimProcessConfig` fields):
   ```dotenv
   ISAAC_SIM_KIT_EXE=C:/IsaacSim/kit/kit.exe
   ISAAC_SIM_KIT_FILE=C:/IsaacSim/apps/isaacsim.exp.full.kit
   # Optional: cold-boot + shader compile budget (default 240s → 600s recommended)
   ISAAC_SIM_STARTUP_TIMEOUT=600.0
   ```
4. **Kit Extension activation is automatic** — on `isaac_sim_start` the MCP server spawns Kit with `--ext-folder <repo>/kkr-extensions --enable omni.mycompany.validation_api` (plus any IDs in `ISAAC_SIM_EXTRA_EXT_IDS`). No manual Extension Manager toggling required.

Sanity check after first startup: `curl http://localhost:8011/validation/v1/health` → `{"ok": true, "extension_enabled": true, …}`.

### Using Your Own Kit Extension

The MCP server always ships the built-in `omni.mycompany.validation_api` Extension (that's what exposes the 102 REST endpoints). You can additionally load **your own Kit Extension** on the same Isaac Sim instance in one of two ways.

**Option A — Drop it under the repo's extension folder (simplest)**

1. Place your extension at `kkr-extensions/<your.ext.id>/` with the standard Kit layout:
   ```
   kkr-extensions/
   ├── omni.mycompany.validation_api/      # built-in
   └── your.company.awesome/               # your extension
       ├── config/extension.toml
       └── your/company/awesome/...
   ```
2. Add its id to `ISAAC_SIM_EXTRA_EXT_IDS` in `.env` (JSON array, pydantic-settings v2):
   ```dotenv
   ISAAC_SIM_EXTRA_EXT_IDS=["omni.anim.graph.bundle","omni.replicator.core","your.company.awesome"]
   ```
3. `isaac_sim_restart` → Kit now enables your extension alongside `validation_api`.

**Option B — Use a different extension folder**

`kkr-extensions/` is the default `--ext-folder` passed to Kit. To point elsewhere, override in `.env`:

```dotenv
ISAAC_SIM_EXT_FOLDER=D:/my-projects/my-kit-extensions
ISAAC_SIM_EXTRA_EXT_IDS=["your.company.awesome"]
```

⚠️ `ISAAC_SIM_EXT_FOLDER` currently accepts a **single path only**. If you need both the repo's built-in extension and an external folder, use Option A (drop into `kkr-extensions/`) — Kit auto-discovers every subfolder there.

**Verifying your extension loaded**

After `isaac_sim_start`, use the MCP tools:

```python
# Option 1 — list every extension Kit knows (MCP tool, Phase H)
extension_list_all(enabled_only=True)   # filter to currently-enabled

# Option 2 — check one id explicitly
extension_get_info(ext_id="your.company.awesome")
```

Or hit the REST route directly: `POST http://localhost:8011/validation/v1/extension/get_info {"ext_id":"your.company.awesome"}`.

**Exposing your extension as MCP tools**

Loading is one step; surfacing your extension's functionality as natural-language tools is another. See the "새 MCP tool (`tools/`)" row in root [`CLAUDE.md`](./CLAUDE.md)의 변경 파급 매트릭스 — the 8-step checklist (REST endpoint → client → type → module → `@mcp.tool()` → tests → frozenset → `verify_mcp_sync`) covers the full surface-up path.

Minimal `~/.claude.json` entry (recommended form — bypasses `uv run` file locks):

```json
{
  "mcpServers": {
    "omniverse-kit-mcp": {
      "type": "stdio",
      "command": "C:/path/to/omniverse-kit-mcp/.venv/Scripts/omniverse-kit-mcp.exe",
      "args": []
    }
  }
}
```

Start Claude Code; 107 Isaac Sim tools are available immediately.

For a full setup (Extension registration, `.env` defaults, ROS2 path, Windows specifics), see **`setup/`**.

---

## Project Layout

| Path | Role |
|---|---|
| `src/omniverse_kit_mcp/` | FastMCP server (Python) — tool registration, scenario engine, REST client |
| `kkr-extensions/omni.mycompany.validation_api/` | Kit Extension (FastAPI) — 102 REST endpoints mounted at `/validation/v1` |
| `scenarios/` | YAML scenarios (Arrange / Act / Assert / Cleanup) + JSON Schema |
| `scripts/` | Developer utilities — catalog regen, sync verification, per-phase live tests |
| `tests/` | Mock-based pytest suite (309 tests) |
| `setup/` | Windows installer + `~/.claude.json` wiring helpers |
| `docs/` | `tool-catalog.md` (auto-generated), `phase-progress.md`, per-phase validation reports, live artifacts, `assets/isaac/` + `assets/composer/` (asset URL catalogs) |
| `isaac-pick-place/` · `usd-mouse-interact/` | Workshop material (design / verification / captures / tests) — extensions live in `kkr-extensions/` |

---

## Surface Overview

Exact list in [`docs/tool-catalog.md`](./docs/tool-catalog.md) (auto-generated).

**18 tool domains**: Process · Stage (read/write/file/selection) · Simulation · Viewport · Window · Extension · Navigation · Sensor · Physics · Lighting · Material · Robot · Character · Asset · Job · Replicator · OmniGraph · Content · Lakehouse · Scenario.

**3 MCP resources** (on-demand; zero session-start token cost):

| URI | Content | MIME |
|---|---|---|
| `isaacsim://tool-catalog` | Full tool catalog with group index | `text/markdown` |
| `isaacsim://sensor-menu` | Isaac Sim `Create > Sensors` full menu (vendor × model) | `text/markdown` |
| `isaacsim://scenario-schema` | JSON Schema for scenario YAML | `application/json` |

---

## Typical Workflows

### 1 — Ask Claude to build a scene from scratch

> "Load the Simple_Warehouse environment, place a NovaCarter at the origin, drop five SimReady boxes, bake the NavMesh, then capture both the viewport and the Kit window."

Claude combines `asset_list` → `stage_load_usd` → `robot_load` → `physics_apply_rigid_body` → `simulation_stop` → `navigation_bake` → `viewport_capture` + `window_capture` automatically.

### 2 — Run a reproducible scenario

```bash
# Any YAML under scenarios/smoke/ or scenarios/integration/
scenarios/integration/phase_h_combined.yaml
```

From Claude Code: `scenario_validate("phase_h_combined.yaml")` — the runner compiles the YAML, drives Arrange → Act → Assert → Cleanup, and returns a per-step pass/fail report.

### 3 — Generate synthetic data (SDG)

Chain Replicator tools: `replicator_create_writer("BasicWriter", output_dir)` → `replicator_register_randomizer("position", "/World/Boxes/*", …)` → `replicator_trigger_once(num_frames=10)`.

---

## Development

```bash
# Add a new MCP tool — touch-point checklist in CLAUDE.md "변경 파급 매트릭스"
# Core steps:
#   1. Extension side: models/ + services/ + rest_router.py
#   2. MCP side: clients/isaac_rest_client.py + types/ + modules/ + tools/
#   3. Registration: EXPECTED_MODULE_TOOLS in tests/unit/test_tools_registration.py
#   4. Regen + drift test:
.venv/Scripts/python.exe scripts/verify_mcp_sync.py

# Full test suite (mock-based)
uv run pytest tests/

# Live REST smoke (Isaac Sim must be running)
.venv/Scripts/python.exe scripts/live_test_phase_e.py      # Phase E artifacts -> docs/artifacts/phase-e/
.venv/Scripts/python.exe scripts/live_test_physics.py      # -> docs/artifacts/phase-f/
```

Process-level control without restarting Claude Code (bypasses the MCP import cache):

```bash
.venv/Scripts/python.exe scripts/run_process_module_standalone.py {start|stop|restart}
```

---

## Documentation Map

Everything is reachable from the root `CLAUDE.md` "Scope-specific CLAUDE.md 문서 맵" table. High-signal entries:

- **Operational rules & escalation protocols** → root [`CLAUDE.md`](./CLAUDE.md)
- **Tool surface contract** → [`docs/tool-catalog.md`](./docs/tool-catalog.md) + [`src/omniverse_kit_mcp/tools/CLAUDE.md`](./src/omniverse_kit_mcp/tools/CLAUDE.md)
- **Kit Extension internals** → [`kkr-extensions/CLAUDE.md`](./kkr-extensions/CLAUDE.md)
- **Module integration facts** (Kit 5.1 gotchas — viewport caching, articulation warm-up, NavMesh lock) → [`src/omniverse_kit_mcp/modules/CLAUDE.md`](./src/omniverse_kit_mcp/modules/CLAUDE.md)
- **Scenario authoring guide** → [`scenarios/CLAUDE.md`](./scenarios/CLAUDE.md)
- **Phase-by-phase history** → `docs/phase-{a..i}-validation-report.md`
- **Asset URL catalogs** → [`docs/assets/isaac/asset_inventory.md`](./docs/assets/isaac/asset_inventory.md) (Isaac Sim 5.1 bundle) + `docs/assets/composer/` (Composer scope)

---

## Status

Phases A through H are ✅ complete (108 → 107 tools + 3 resources after scenario_schema demotion). See `docs/phase-progress.md` and each `phase-*-validation-report.md` for deliverables, live validation evidence, and known limitations.

## License

(add project license here)
