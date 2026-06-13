# omniverse-kit-mcp — Project Instructions

<!-- 🛑 DO-NOT-EDIT protected areas (allow contraction / preserve purpose / auto-verify G1-G7):
(1) DO-NOT-EDIT-START/END block of §"DO-NOT-EDIT Residual"
(2) §"Environment Variables" `ISAAC_SIM_EXTRA_EXT_IDS` row inline -->

## Session entry

- **Only this file** Automatically loads every turn (CC behavior). Codex CLI has `AGENTS.md` as the entry point — no nested auto-load — cap / writing rule: §meta
- **Actual live MCP entry point**: `workspaces/<app>/instance-N/.mcp.json` (server spawns when you open CC in that folder). app ∈ {isaac, usd-composer}, N ∈ {1,2}. Details: `workspaces/README.md` · `docs/invariants/multi-app.md`

## ⚠️ Required pull-doc before work

| work | Read first |
|---|---|
| Build scene / select asset (add robot·character·env·prop) | `docs/invariants/asset-discovery.md` |
| USD load (`stage_load_usd` / `robot_load` / `character_load` / `stage_open`) | `docs/invariants/usd-load.md` |
| Isaac Sim startup/shutdown/hang | `docs/invariants/process-lifecycle.md` |
| Root parent ↔ workspace live MCP worker coordination | `docs/invariants/live-worker-coordination.md` |
| New MCP tool features research (dictionary) | `docs/references/CLAUDE.md` |
| Add new MCP tool | `docs/invariants/mcp-tool-add.md` |
| New module/scenario action | `docs/invariants/module-add.md` |
| Extension `.py` edit/reload | `docs/invariants/ext-reload.md` |
| Extension UI automation (`extension_ui_invoke`) | `docs/invariants/ui-invoke.md` |
| Scenario YAML Authoring | `docs/invariants/scenario-validation.md` |
| `viewport_capture` / scene build / use new NVIDIA asset | `docs/invariants/visual-validation.md` |
| Add multi-app / Modify kit app profile / rename repo/directory | `docs/invariants/multi-app.md` |
| Catalog sync after kit/app version update | skill `/omniverse-kit-extension-catalog-sync` (`.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md`) |
| Asset URL 404 / inventory update | skill `/omniverse-asset-inventory-sync` (`.claude/skills/omniverse-asset-inventory-sync/SKILL.md`) |
| Document hierarchy sweep after session operation | skill `/omniverse-docs-sweep` (`.claude/skills/omniverse-docs-sweep/SKILL.md`) |
| Absence of MCP tool required for omniverse work → Surface upgrade | skill `/omniverse-mcp-tool-upgrade` (`.claude/skills/omniverse-mcp-tool-upgrade/SKILL.md`) |
| Error/failure diagnosis (hypothesis verification first) | `docs/tool-diagnostic-map.md` |

Fault diagnosis is `docs/runbooks/` (kit-stdin-deadlock · cold-boot-timeout · hub-orphan · env-sub-config · kit-dep-solver-fail · multi-app · scene-reexport-lock).

## ⚠️ DO-NOT-EDIT Residual

<!-- DO-NOT-EDIT-START: Text / Reproduction / Recovery `docs/runbooks/kit-stdin-deadlock.md`. Automatic Verification G1-G7 -->
⚠️ **`subprocess.Popen(... stdin=subprocess.DEVNULL)` REQUIRED** — If missing, MCP child kit.exe cold boot hang (L17). Location: `src/omniverse_kit_mcp/modules/process_module.py::start`. Verification value 240 s → 13 s. **"extra_ext_ids race" diagnosis is incorrect** — stdin pipe is the actual cause.
<!-- DO-NOT-EDIT-END -->

## Validation Rules

- **R1** Actual output is an actual asset — no substitution of primitive. However, prototype/test/demo fixtures are allowed as primitive. Details: `docs/invariants/scenario-validation.md`
- **R1a** NavMesh bake after recalling `simulation_stop` (`load → stop → bake → query → play → navigate`) — Body `kkr-extensions/docs/kit-sdk-pitfalls.md` NavMesh §
- **R2** Robot operation (`set_joint_positions` / `navigate_*` / `drive_physics`) requires `simulation_play` state (except `robot_load`) — Detailed `src/omniverse_kit_mcp/modules/CLAUDE.md` Robot
- **R3** After `viewport_capture`, `Read` tool visual verification obligation — blank/black, retry backlight/camera/asset adjustment

## Change Ripple Matrix

| change target | fix together |
|-----------|----------|
| New MCP tool | 7 places (`docs/invariants/mcp-tool-add.md`) + 1 manual `scripts/verify_mcp_sync.py` |
| New module/scenario action | `docs/invariants/module-add.md` |
| REST endpoint | client + tool registration + test + `kkr-extensions/CLAUDE.md` |
| MCP resource | `src/omniverse_kit_mcp/mcp/resources.py` + `tests/unit/test_resources_paths.py` + verify_mcp_sync |
| CLAUDE.md new directory | This matrix + document map bi-directional update |

## Key Decisions

- **LakehouseModule** query only (interview spec confirmed) — Body `src/omniverse_kit_mcp/modules/CLAUDE.md` LakehouseModule
- **Type boundary**: Internal `@dataclass(slots=True, frozen=True)`, Pydantic only Extension REST boundary. Pydantic is banned in MCP server code — See `src/omniverse_kit_mcp/CLAUDE.md` "Type Boundary Convention"
- **MCP server import cache**: spawn + import cache once at session start. `src/omniverse_kit_mcp/` modifications are not reflected until the MCP host (Claude Code / Codex CLI) is restarted. In-session verification is `scripts/run_process_module_standalone.py` / `scripts/run_scenario_standalone.py`
- **Test SoT**: EXPECTED frozenset of `tests/unit/test_tools_registration.py`
- **Use only uv** (prohibit `pip install`); Add package `uv add` / `uv add --dev` — New PC procedure `setup/CLAUDE.md`

## Environment Variables

| variable | default | explanation |
|------|-------|------|
| `ISAAC_SIM_BASE_URL` | `http://127.0.0.1:8111` | Extension REST |
| `ISAAC_MCP_APP_PROFILE` | `isaac-sim` | Kit app profile — `isaac-sim` or `usd-composer`. Details: `docs/invariants/multi-app.md` |
| `ISAAC_MCP_INSTANCE_ID` | `1` | Multi-instance (1..2 persistent limit, `le=2` guard). offset to profile base_port (Isaac 8111-12 / USD Composer 8114-15) |
| `ISAAC_SIM_STARTUP_TIMEOUT` | `120.0` | ProcessModule health wait upper bound. Details: `docs/invariants/process-lifecycle.md` |
| `ISAAC_SIM_EXTRA_EXT_IDS` | config.py bundle | <!-- ⛔ DO-NOT-EDIT: "extra_ext_ids race" diagnosis is invalid (see L17 `docs/runbooks/kit-stdin-deadlock.md`) --> JSON array. 8 13s passed after stdin DEVNULL fix |
| `ISAAC_SIM_EXTRA_EXT_FOLDERS` | `[]` | JSON array. Add `--ext-folder` to each out-of-tree extension folder (permanently register external extension folder). If the list is empty, it is the same as the current one. |
| `LAKEHOUSE_BASE_URL` | `http://localhost:9000` | Lakehouse REST |

## Subagent / Multiagent dispatch pattern

Subagent / multi-agent context does not automatically load sub-CLAUDE.md. Specify `Read docs/invariants/<relevant>.md first` in the dispatch prompt or include the required context directly.
Live MCP worker dispatch includes `docs/invariants/live-worker-coordination.md` and Quiet Parent Contract directly in the prompt.

## Document Map

| file | responsibility |
|------|------|
| `src/omniverse_kit_mcp/CLAUDE.md` | FastMCP server root (entry/type boundary/clients) |
| `src/omniverse_kit_mcp/modules/CLAUDE.md` | Module matrix + Character constraint + base.py pattern (→ `integration-facts.md` · `process-ops.md`) |
| `src/omniverse_kit_mcp/scenario/CLAUDE.md` | Scenario Engine (Arrange/Act/Assert/Cleanup + action_registry) |
| `src/omniverse_kit_mcp/tools/CLAUDE.md` | MCP tool registration contract + caveat by group |
| `kkr-extensions/CLAUDE.md` | Extension development nav hub (→ `docs/*` basics / pitfalls / recipe / reuse / lessons-learned) |
| `scenarios/CLAUDE.md` | YAML Authoring |
| `tests/CLAUDE.md` | pytest unit |
| `setup/CLAUDE.md` | Installation / New PC |
| `scripts/CLAUDE.md` | development script |
| `docs/CLAUDE.md` | tool-catalog / references / pull-docs |
| `docs/assets/isaac/` | NVIDIA Isaac Sim 6.0 asset URL catalog SoT (`asset_inventory.md` entry point + per-category `assets/*.md`) — entry workflow `docs/invariants/asset-discovery.md` |

## Meta — Rules for Writing CLAUDE.md

- **Line hardcap**: root ≤150 · sub-CLAUDE.md ≤150 · `docs/invariants/*.md` ≤200 · `docs/runbooks/*.md` ≤300 (`test_doc_integrity.py` A3/A4/A6/A8/A9 guards, env override possible)
- **Transfer / Delete**: When increasing, transfer `docs/invariants/*.md` (must read before working) + Update the above pull-doc table, `docs/runbooks/*.md` for error response. **Delete is limited to stale** (outdated / duplicate / unused pointer)
- **`lessons-learned.md` is historical incident log** (Confirmed in Phase 3 Task 3.3) — Addition of new permanent rules is prohibited. Accumulating only accident evidence/reproduction procedures
- **sub-CLAUDE.md rules**: Directory-specific rules only. Do not overlap roots / invariants — cross-cutting is replaced with pointer
