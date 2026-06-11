# omniverse-kit-mcp

**Drive NVIDIA Isaac Sim 6.0.0 in natural language from Claude Code (or any MCP client).**

An MCP (Model Context Protocol) server that exposes Isaac Sim's GUI surface — stage editing, robot / character animation, multi-viewport capture, physics, lighting, SDG, OmniGraph, content browsing, extension management — as 133 tools plus 5 on-demand resources. Pair it with the bundled Kit Extension and Claude Code controls Isaac Sim end-to-end through stdio.

![python](https://img.shields.io/badge/python-3.11%2B-blue) ![isaac-sim](https://img.shields.io/badge/Isaac%20Sim-6.0.0-green) ![mcp](https://img.shields.io/badge/MCP-stdio-purple)

---

## Architecture

```
┌──────────────┐   stdio (JSON-RPC)   ┌──────────────────────┐
│ Claude Code  │ ◀──────────────────▶ │  omniverse-kit-mcp        │ FastMCP server (Python)
│  (or any     │                      │                      │
│   MCP client)│                      │  • ProcessModule  ─▶ subprocess → kit.exe
└──────────────┘                      │  • 17 domain modules │
                                      │  • 3 scenario tools  │
                                      │  • 5 MCP resources   │
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
                                          kit.exe (Isaac Sim 6.0.0)
```

Two operational paths:

| Path | Purpose | Example tools |
|---|---|---|
| **Subprocess lifecycle** | Start/stop/restart kit.exe — works without Isaac Sim running | `kit_app_start`, `kit_app_stop`, `kit_app_restart` |
| **REST → Extension → Kit SDK** | Scene manipulation while Isaac Sim is running | `stage_load_usd`, `robot_navigate_path`, `replicator_trigger_once`, … |

Scenario tools (`scenario_validate`, `scenario_plan`, …) are orchestrators — they compile an YAML Arrange/Act/Assert/Cleanup document into typed module calls.

---

## Quick Start

**Prerequisites**: Windows 10/11 · Python 3.11+ for the MCP server · [uv](https://docs.astral.sh/uv/) · [Isaac Sim 6.0.0 Standalone](https://developer.nvidia.com/isaac-sim) with bundled Python 3.12 (see next section)

```bash
# 1. Clone and install deps
git clone https://github.com/KappyDays/omniverse-kit-mcp.git
cd omniverse-kit-mcp
cp .env.example .env       # then edit — see "Isaac Sim Setup" below
uv sync

# 2. Verify tooling
uv run pytest tests/                             # should be all green
.venv/Scripts/python.exe scripts/verify_mcp_sync.py   # tool catalog sync check

# 3. Run setup (deps + .env + cleanup of legacy global mcpServers entries)
setup/setup-omniverse-kit-mcp.bat
#    — workspaces/<profile>/instance-<N>/.mcp.json (4 files) ship in-repo
#      with relative `../../..` to repo root; no per-machine generation
#    — see setup/ for details
```

### Isaac Sim Setup

omniverse-kit-mcp does **not auto-detect** the Isaac Sim install location. Default paths in `src/omniverse_kit_mcp/config.py` point at the developer's workstation and must be overridden.

1. **Install** Isaac Sim 6.0.0 Standalone anywhere (e.g. `C:/IsaacSim/`, `D:/programs/isaac-sim-standalone-6.0.0/`)
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
4. **Kit Extension activation is automatic** — on `kit_app_start` the MCP server spawns Kit with `--ext-folder <repo>/kkr-extensions --enable omni.mycompany.validation_api` (plus any IDs in `ISAAC_SIM_EXTRA_EXT_IDS`). No manual Extension Manager toggling required.

Sanity check after first startup: `curl http://127.0.0.1:8111/validation/v1/health` → `{"ok": true, "extension_enabled": true, …}`.

### Manual MCP-Safe Launchers

`setup/launchers/` stores the launcher source of truth. `setup/setup_omniverse_kit_mcp.ps1` copies them into the local app folders:

- `isaac-sim_mcp.bat` / `.ps1` → Isaac Sim standalone folder
- `kkr_usd_composer_mcp.kit.bat` / `.ps1` → USD Composer release folder

Use these for manual double-click launches when MCP also needs to attach. They select the first free instance port (`8111/8112` for Isaac Sim, `8114/8115` for USD Composer) and force `allow_port_range=false`.

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
3. `kit_app_restart` → Kit now enables your extension alongside `validation_api`.

**Option B — Use a different extension folder**

`kkr-extensions/` is the default `--ext-folder` passed to Kit. To point elsewhere, override in `.env`:

```dotenv
ISAAC_SIM_EXT_FOLDER=D:/my-projects/my-kit-extensions
ISAAC_SIM_EXTRA_EXT_IDS=["your.company.awesome"]
```

⚠️ `ISAAC_SIM_EXT_FOLDER` currently accepts a **single path only**. If you need both the repo's built-in extension and an external folder, use Option A (drop into `kkr-extensions/`) — Kit auto-discovers every subfolder there.

**Verifying your extension loaded**

After `kit_app_start`, use the MCP tools:

```python
# Option 1 — list every extension Kit knows (MCP tool, Phase H)
extension_list_all(enabled_only=True)   # filter to currently-enabled

# Option 2 — check one id explicitly
extension_get_info(ext_id="your.company.awesome")
```

Or hit the REST route directly: `POST http://127.0.0.1:8111/validation/v1/extension/get_info {"ext_id":"your.company.awesome"}`.

**Exposing your extension as MCP tools**

Loading is one step; surfacing your extension's functionality as natural-language tools is another. See the "새 MCP tool (`tools/`)" row in root [`CLAUDE.md`](./CLAUDE.md)의 변경 파급 매트릭스 — the 8-step checklist (REST endpoint → client → type → module → `@mcp.tool()` → tests → frozenset → `verify_mcp_sync`) covers the full surface-up path.

### Wiring into Claude Code — workspace folders

Four `.mcp.json` files ship under `workspaces/`, one per Kit instance — each uses a relative `../../..` to the repo root for `uv --directory`, so they work on any clone without per-machine generation. **Each workspace folder provides one Kit MCP entry** for that app/instance instead of registering every app/instance globally. Open Claude Code from inside a workspace folder:

```powershell
cd workspaces/isaac/instance-1     # Isaac Sim instance 1, port 8111
claude
```

| Scenario | CC windows | Folders |
|---|---|---|
| Isaac × 1 | 1 | `workspaces/isaac/instance-1` |
| USD Composer × 1 | 1 | `workspaces/usd-composer/instance-1` |
| Isaac + USD Composer | 2 simultaneously | `workspaces/isaac/instance-1` + `workspaces/usd-composer/instance-1` |
| Isaac × 2 | 2 | `workspaces/isaac/instance-{1,2}` |
| USD Composer × 2 | 2 | `workspaces/usd-composer/instance-{1,2}` |

For server-code development (modifying the MCP server itself), open Claude Code (or codex) at the repo root — no workspace Kit MCP loads there by design, keeping the dev session focused on code. Validate runtime behavior via `scripts/run_*_standalone.py` or by entering a workspace folder.

For a full setup (Extension registration, `.env` defaults, ROS2 path, Windows specifics), see **`setup/`**. Workspace layout and promote-path details live in [`workspaces/README.md`](workspaces/README.md).

### Wiring into Codex CLI — workspace folders

Each workspace folder under `workspaces/` ships a `.codex/` directory with a
workspace MCP server entry plus sandbox/approval/network_access settings. Run
`codex` from that workspace folder to activate the matching Isaac Sim or USD
Composer entry. Any global Codex MCP entries may also be listed.

**First-time setup** (one per machine):

```cmd
:: 1. Install codex CLI (npm-based)
npm install -g @openai/codex

:: 2. Authenticate (ChatGPT account or API key — codex prompts for the method)
codex login

:: 3. Verify installation
codex --version
:: should print 0.130.0 or later
```

**Per session** (Windows PowerShell or cmd):

```cmd
:: Enter the workspace folder for the app you want to drive
cd workspaces\isaac\instance-1

:: Launch codex with that workspace's MCP server available
codex

:: First prompt example (> is codex's input prefix, not a shell redirect)
> Start Isaac Sim, load the Simple_Warehouse environment, place a NovaCarter at the origin.
```

**Two apps concurrently** — open two terminals and `cd` into two different workspace folders:

| Terminal | Workspace | App | Port |
|---|---|---|---|
| A | `workspaces/isaac/instance-1` | Isaac Sim 6.0.0 | 8111 |
| B | `workspaces/usd-composer/instance-1` | USD Composer | 8114 |

Each codex workspace entry owns one `kit.exe` process. The two app instances are
isolated by profile and port.

**Verification after first launch**:

```cmd
codex mcp list
```

The command should include the workspace entry (`isaacsim-mcp-1`, `isaacsim-mcp-2`, `usdcomposer-mcp-1`, or `usdcomposer-mcp-2` depending on the folder). Global Codex MCP entries may appear too.

---

## Project Layout

| Path | Role |
|---|---|
| `src/omniverse_kit_mcp/` | FastMCP server (Python) — tool registration, scenario engine, REST client |
| `kkr-extensions/omni.mycompany.validation_api/` | Kit Extension (FastAPI) — 102 REST endpoints mounted at `/validation/v1` |
| `scenarios/` | YAML scenarios (Arrange / Act / Assert / Cleanup) + JSON Schema |
| `scripts/` | Developer utilities — tool catalog regen, sync verification, per-phase live tests, optional local reference harvest |
| `tests/` | Mock-based pytest suite |
| `setup/` | Windows installer + MCP-safe manual launcher templates + `~/.claude.json` wiring helpers |
| `docs/` | `tool-catalog.md` (auto-generated), `invariants/`, `runbooks/`, `assets/isaac/` + `assets/composer/` (asset URL catalogs), public-safe references |
| `kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/` | Workshop material (design / verification / tests) for the Composer mouse interaction demo |

---

## Surface Overview

Exact list in [`docs/tool-catalog.md`](./docs/tool-catalog.md) (auto-generated).

**Tool domains include**: Process · Stage (read/write/file/selection) · Simulation · Viewport · Window · Extension · Navigation · Sensor · Physics · Lighting · Material · Robot · Character · Asset · Job · Replicator · OmniGraph · Content · Lakehouse · Scenario.

**5 MCP resources** (on-demand; zero session-start token cost):

| URI | Content | MIME |
|---|---|---|
| `isaacsim://tool-catalog` | Full tool catalog with group index | `text/markdown` |
| `isaacsim://sensor-menu` | Isaac Sim `Create > Sensors` full menu (vendor × model) | `text/markdown` |
| `isaacsim://asset-catalog` | Isaac Sim NVIDIA asset catalog index | `text/markdown` |
| `isaacsim://scenario-schema` | JSON Schema for scenario YAML | `application/json` |
| `isaacsim://scenarios` | Available scenario YAML listing | `application/json` |

---

## Typical Workflows

### 1 — Ask the agent (Claude / codex) to build a scene from scratch

> "Load the Simple_Warehouse environment, place a NovaCarter at the origin, drop five SimReady boxes, bake the NavMesh, then capture both the viewport and the Kit window."

The agent combines `asset_list` → `stage_load_usd` → `robot_load` → `physics_apply_rigid_body` → `simulation_stop` → `navigation_bake` → `viewport_capture` + `window_capture` automatically.

### 2 — Run a reproducible scenario

```bash
# Any YAML under scenarios/smoke/ or scenarios/integration/
scenarios/integration/phase_h_combined.yaml
```

From Claude Code or codex: `scenario_validate("phase_h_combined.yaml")` — the runner compiles the YAML, drives Arrange → Act → Assert → Cleanup, and returns a per-step pass/fail report.

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
.venv/Scripts/python.exe scripts/live_test_phase_e.py
.venv/Scripts/python.exe scripts/live_test_physics.py
```

Process-level control without restarting the MCP host (bypasses the MCP import cache):

```bash
.venv/Scripts/python.exe scripts/run_process_module_standalone.py {start|stop|restart}
```

---

## Public Repo Hygiene

The repository intentionally excludes local runtime state and generated research
corpora. In particular, `.env`, `.venv`, `docs/artifacts/**`, workshop
screenshots, generated extension catalogs, and copied reference snapshots are
ignored. Public clones still run the MCP server and tests; `extension_search`
returns `EXTENSION_CATALOG_UNAVAILABLE` until you generate a local
`docs/references/extensions.json`.

Generated local references:

```bash
.venv/Scripts/python.exe scripts/harvest_extension_metadata.py
.venv/Scripts/python.exe scripts/render_catalog_md.py
.venv/Scripts/python.exe -m pytest tests/unit/test_catalog_integrity.py -q
```

These files are for local research and should stay untracked.

For a compact public project summary suitable for open-source support
applications, see [`docs/oss-application-notes.md`](./docs/oss-application-notes.md).

---

## Documentation Map

Everything is reachable from the root `CLAUDE.md` "Scope-specific CLAUDE.md 문서 맵" table. High-signal entries:

- **Operational rules & escalation protocols** → root [`CLAUDE.md`](./CLAUDE.md)
- **Tool surface contract** → [`docs/tool-catalog.md`](./docs/tool-catalog.md) + [`src/omniverse_kit_mcp/tools/CLAUDE.md`](./src/omniverse_kit_mcp/tools/CLAUDE.md)
- **Kit Extension internals** → [`kkr-extensions/CLAUDE.md`](./kkr-extensions/CLAUDE.md)
- **Module integration facts** (Kit / Isaac runtime gotchas — viewport caching, articulation warm-up, NavMesh lock) → [`src/omniverse_kit_mcp/modules/CLAUDE.md`](./src/omniverse_kit_mcp/modules/CLAUDE.md)
- **Scenario authoring guide** → [`scenarios/CLAUDE.md`](./scenarios/CLAUDE.md)
- **Asset URL catalogs** → [`docs/assets/isaac/asset_inventory.md`](./docs/assets/isaac/asset_inventory.md) (Isaac Sim 6.0 bundle) + `docs/assets/composer/` (Composer scope)
- **Open-source application notes** → [`docs/oss-application-notes.md`](./docs/oss-application-notes.md)

---

## Status

133 MCP tools + 5 resources covering stage / robot / character / sensor / multi-viewport / physics / lighting / material / SDG / OmniGraph / content / extension domains. Two Kit app profiles (Isaac Sim, USD Composer) with multi-instance support. See [`docs/tool-catalog.md`](./docs/tool-catalog.md) for the full surface.

## License

MIT. See [`LICENSE`](./LICENSE).
