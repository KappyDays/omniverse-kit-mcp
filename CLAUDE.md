# omniverse-kit-mcp — Project Instructions

<!-- Protected regression facts live in docs/invariants and docs/runbooks; root only routes. -->

## Session entry

- **Only this file** Automatically loads every turn (CC behavior). Codex CLI has `AGENTS.md` as the entry point — no nested auto-load — cap / writing rule: §meta
- **Actual live MCP entry point**: `workspaces/<app>/instance-N/.mcp.json` (server spawns when you open CC in that folder). app ∈ {isaac, usd-composer}, N ∈ {1,2}. Details: `workspaces/README.md` · `docs/invariants/multi-app.md`
- **App launch requests**: Treat launch/open/start of Isaac Sim, USD Composer,
  or another Omniverse app as live MCP work. Read
  `docs/invariants/live-worker-coordination.md` and use the matching
  `workspaces/<app>/instance-N` entry.

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
| Public commit/push review | `docs/invariants/public-repo-hygiene.md` |
| Catalog sync after kit/app version update | skill `/omniverse-kit-extension-catalog-sync` (`.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md`) |
| Asset URL 404 / inventory update | skill `/omniverse-asset-inventory-sync` (`.claude/skills/omniverse-asset-inventory-sync/SKILL.md`) |
| Document hierarchy sweep after session operation | skill `/omniverse-docs-sweep` (`.claude/skills/omniverse-docs-sweep/SKILL.md`) |
| Absence of MCP tool required for omniverse work → Surface upgrade | skill `/omniverse-mcp-tool-upgrade` (`.claude/skills/omniverse-mcp-tool-upgrade/SKILL.md`) |
| Error/failure diagnosis (hypothesis verification first) | `docs/tool-diagnostic-map.md` |

Fault diagnosis is `docs/runbooks/` (kit-stdin-deadlock · cold-boot-timeout · hub-orphan · env-sub-config · kit-dep-solver-fail · multi-app · scene-reexport-lock).

## Protected Regression Pointers

- Kit child process stdin guard: `stdin=subprocess.DEVNULL` in
  `src/omniverse_kit_mcp/modules/process_module.py::start`. Read
  `docs/invariants/process-lifecycle.md` and
  `docs/runbooks/kit-stdin-deadlock.md` before changing launch behavior.

## Validation Rules

- **R1** Actual output is an actual asset — no substitution of primitive. However, prototype/test/demo fixtures are allowed as primitive. Details: `docs/invariants/scenario-validation.md`
- **R1a** NavMesh bake after recalling `simulation_stop` (`load → stop → bake → query → play → navigate`) — Body `kkr-extensions/docs/kit-sdk-pitfalls.md` NavMesh §
- **R2** Robot operation (`set_joint_positions` / `navigate_*` / `drive_physics`) requires `simulation_play` state (except `robot_load`) — Detailed `src/omniverse_kit_mcp/modules/CLAUDE.md` Robot
- **R3** After `viewport_capture`, `Read` tool visual verification obligation — blank/black, retry backlight/camera/asset adjustment
- **R4** Before public commit/push, review current files and pending history for
  user-specific paths, secrets, and generated local references. Use
  `docs/invariants/public-repo-hygiene.md` and
  `scripts/review_public_hygiene.py`; `tests/unit/test_public_repo_hygiene.py`
  guards drift.

## Change Routing

High-ripple work follows the Required pull-doc table first: MCP tools use
`mcp-tool-add.md`, modules/scenario actions use `module-add.md`, extension
REST work uses `kkr-extensions/CLAUDE.md`, and docs hierarchy changes preserve
the local `CLAUDE.md` map plus tests.

## Key Decisions

- **Type boundary**: internal `@dataclass(slots=True, frozen=True)`; Pydantic
  only at the Extension REST boundary. See `src/omniverse_kit_mcp/CLAUDE.md`.
- **MCP import cache**: `src/omniverse_kit_mcp/` changes need host restart or
  standalone verification. See `scripts/CLAUDE.md`.
- **Use only uv**: never `pip install`; dependency workflow is `setup/CLAUDE.md`.

## Environment Variables

Environment details are situational: app/profile/ports in
`docs/invariants/multi-app.md`, startup timeout and process launch in
`docs/invariants/process-lifecycle.md`, installation and dependency setup in
`setup/CLAUDE.md`, module-specific env in local docs.

## Subagent / Multiagent dispatch pattern

Subagent / multi-agent context does not automatically load sub-CLAUDE.md. Include
the relevant pull-docs and local `CLAUDE.md` paths in dispatch prompts.

## Document Map

Walk from root to the target path and read every applicable local `CLAUDE.md`.
Use `docs/CLAUDE.md` as the docs index and `docs/assets/isaac/asset_inventory.md`
as the Isaac asset catalog entry point.

## Meta — Rules for Writing CLAUDE.md

- **Line hardcap**: root ≤150 · sub-CLAUDE.md ≤150 · `docs/invariants/*.md` ≤200 · `docs/runbooks/*.md` ≤300 (`test_doc_integrity.py` A3/A4/A6/A8/A9 guards, env override possible)
- **Transfer / Delete**: When increasing, transfer `docs/invariants/*.md` (must read before working) + Update the above pull-doc table, `docs/runbooks/*.md` for error response. **Delete is limited to stale** (outdated / duplicate / unused pointer)
- **`lessons-learned.md` is historical incident log** (Confirmed in Phase 3 Task 3.3) — Addition of new permanent rules is prohibited. Accumulating only accident evidence/reproduction procedures
- **sub-CLAUDE.md rules**: Directory-specific rules only. Do not overlap roots / invariants — cross-cutting is replaced with pointer
