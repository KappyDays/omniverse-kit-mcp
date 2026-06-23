# Isaac Sim 6.0.0 Upgrade Source Of Truth

This document is the single source of truth for upgrading this repository from
Isaac Sim 5.1 / Kit 107 to Isaac Sim 6.0.0 / Kit 110.1.1. Every agent thread
must read this document before planning, editing, testing, or delegating work.

If this document conflicts with `AGENTS.md`, `CLAUDE.md`, or
`docs/invariants/*.md`, the repository rules win. Update this document before
continuing.

## Current Snapshot

Recorded on 2026-06-10; merge consolidation updated on 2026-06-11.

- Source checkout: `<repo-root>`
- Current source branch: `main`
- Upgrade implementation branch: `codex/isaac-sim-6-live-upgrade`
- Merge target: `main`
- Historical dirty/untracked source state is recorded below for audit context.
  Always check fresh `git status` before acting.
- Previous execution worktree `<retired-codex-worktree>` is no
  longer present in `git worktree list` or on disk. Do not rely on any files
  that were said to exist only in that worktree.
- This document is the durable restart anchor and completion record for the
  Isaac Sim 6.0.0 upgrade.
- Do not commit, push, stage, or create PRs unless the user explicitly asks.

Historical implementation worktree:

```text
Path: <codex-worktrees>\isaac6-live\omniverse-kit-mcp
Branch: codex/isaac-sim-6-live-upgrade
Baseline SHA: e9039e0c3719a8923f31d3b8560d558af3ce276b
Status: complete before merge; static gates and required Isaac Sim 6.0 live gates passed.
Optional BehaviorAgent variant demos remain tolerated with explicit evidence.
```

Important: `verify_mcp_sync.py` is expected to return non-zero while
`docs/tool-catalog.md` has regenerated but uncommitted changes, because the
script is designed as a commit-prep guard. When staging/committing is forbidden,
use `pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py`
as the no-stage drift check and record the `verify_mcp_sync.py` reason.

Dirty source checkout observed before this SoT rewrite:

```powershell
M .gitignore
M AGENTS.md
M README.md
M kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/robot_service.py
M scenarios/CLAUDE.md
M src/omniverse_kit_mcp/mcp/prompts.py
M tests/unit/test_mcp_prompt_guidance.py
M tests/unit/test_robot_ext_tools.py
M workspaces/README.md
?? docs/isaac-sim-6.0.0-upgrade-sot.md
?? scenarios/controllers/
?? tests/unit/test_pick_place_controller_asset.py
```

Before implementation, create a fresh isolated worktree and copy this file into
it. Never clean or reset the source checkout to make the upgrade easier.

## Local Isaac Sim 6.0.0 Install

The user supplied this install root:

```text
<isaac-sim-6.0-root>
```

Verified local evidence:

- Install root exists.
- `kit\kit.exe` exists.
- `apps\isaacsim.exp.full.kit` exists and should be the primary app file.
- `VERSION` contains `6.0.0-rc.59+release.41464.5f2772bc.gl`.
- `python.bat` runs Python `3.12.13`.
- `extscache` includes Isaac and Kit extension directories with `+110.1.1`.
- Useful app files under `apps\` include:
  - `isaacsim.exp.full.kit`
  - `isaacsim.exp.full.fabric.kit`
  - `isaacsim.exp.full.newton.kit`
  - `isaacsim.exp.full.streaming.kit`
  - `isaacsim.exp.action_and_event_data_generation.full.kit`
  - `isaacsim.exp.base.kit`
  - `isaacsim.exp.base.python.kit`

Worktree-local environment values for live work:

```dotenv
ISAAC_SIM_KIT_EXE=<isaac-sim-6.0-root>/kit/kit.exe
ISAAC_SIM_KIT_FILE=<isaac-sim-6.0-root>/apps/isaacsim.exp.full.kit
ISAAC_SIM_STARTUP_TIMEOUT=600.0
ISAAC_MCP_APP_PROFILE=isaac-sim
ISAAC_MCP_INSTANCE_ID=1
```

Use a worktree-local `.env` or per-command environment variables. Do not edit a
shared `.env` in the source checkout.

## Official 6.0 Facts That Drive The Upgrade

Use the official NVIDIA 6.0.0 documentation as primary source for unstable
facts. Key references:

- Isaac Sim 6.0.0 docs:
  `https://docs.isaacsim.omniverse.nvidia.com/6.0.0/index.html`
- Release notes:
  `https://docs.isaacsim.omniverse.nvidia.com/6.0.0/overview/release_notes.html`
- 6.0 migration guide index:
  `https://docs.isaacsim.omniverse.nvidia.com/6.0.0/migration_guides/isaac_sim_6_0/index.html`
- Workstation installation:
  `https://docs.isaacsim.omniverse.nvidia.com/6.0.0/installation/install_workstation.html`
- Python environment:
  `https://docs.isaacsim.omniverse.nvidia.com/6.0.0/installation/install_python.html`

Upgrade-driving facts already verified from official docs:

- Isaac Sim 6.0 removes `omni.isaac.*` compatibility shims. Migrate to
  `isaacsim.*`.
- `isaacsim.core.api`, `isaacsim.core.prims`, and `isaacsim.core.utils` are
  deprecated. Preferred `isaacsim.core.experimental.*`,
  `isaacsim.core.simulation_manager`, and related documented replacements.
- Isaac Sim Python package installation requires Python 3.12, and the bundled
  Python environment is Python 3.12.
- Camera migration target is `isaacsim.sensors.experimental.rtx` using
  `RtxCamera`, `CameraSensor`, and `TiledCameraSensor`.
- RTX Lidar/Radar/Acoustic migration target is
  `isaacsim.sensors.experimental.rtx`. New creation uses authoring classes such
  as `Lidar.create(...)` wrapped by runtime classes such as `LidarSensor`.
- Physics sensor migration target is `isaacsim.sensors.experimental.physics`.
  IMU/contact/raycast sensors use authoring `create(...)` APIs and runtime
  sensor wrappers instead of old command-based creation.
- ROS2 OmniGraph migration requires upstream Isaac compute/read nodes for
  transform tree and joint state publishing.
- Replicator Agent moves from IRA 0.x to IRA 1.x in Isaac Sim 6.0 and is a
  breaking architectural/API/configuration change.
- ROS workspace notes mention the internal ROS library path moving to
  `isaacsim.ros2.core`.

Do not choose runtime API names from memory. For every runtime migration,
record either the official page URL or local install source path that justified
the chosen API.

## Thread And Worktree Policy

- Use Codex `thinking="xhigh"` for child review or implementation threads.
- Do not use `thinking="max"`; accepted values are `none`, `minimal`, `low`,
  `medium`, `high`, and `xhigh`.
- Work in a new isolated worktree/branch for implementation.
- Suggested branch: `codex/isaac-sim-6-live-upgrade`.
- Suggested worktree root:
  `<codex-worktrees>\isaac6-live\omniverse-kit-mcp`
- If a worktree starts detached, attach a branch before editing.
- Copy this SoT into the worktree before editing if the branch does not contain
  it.
- Keep the source checkout read-only except for explicit user-approved SoT
  maintenance.
- Do not delete worktrees that contain uncommitted upgrade work.

## Mandatory Startup Order

Every resumed session starts here:

1. Read this document.
2. Read root `AGENTS.md`.
3. Read root `CLAUDE.md`.
4. Use root `CLAUDE.md` "Required pull-docs before work" table to choose pull-docs.
5. Enumerate local rules:
   ```powershell
   rg --files -g CLAUDE.md
   rg --files docs/invariants -g "*.md"
   rg --files docs/runbooks -g "*.md"
   ```
6. Read all minimum pull-docs below.
7. Before editing a path, walk from repo root to that path and read everything
   applicable `CLAUDE.md`.
8. If a `CLAUDE.md` references `.claude/skills/*/SKILL.md`, read the relevant
   skill before acting.
9. Use `uv`; never use `pip install`.
10. Preserve DO-NOT-EDIT regions.

Minimum pull-docs for this upgrade:

-`docs/CLAUDE.md`
-`docs/invariants/multi-app.md`
-`docs/invariants/process-lifecycle.md`
-`docs/invariants/ext-reload.md`
-`docs/invariants/ui-invoke.md`
-`docs/invariants/mcp-tool-add.md`
-`docs/invariants/module-add.md`
-`docs/invariants/asset-discovery.md`
-`docs/invariants/usd-load.md`
-`docs/invariants/scenario-validation.md`
-`docs/invariants/visual-validation.md`
-`docs/references/CLAUDE.md`
-`.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md`
-`.claude/skills/omniverse-asset-inventory-sync/SKILL.md`
-`.claude/skills/omniverse-docs-sweep/SKILL.md`
- `.claude/skills/omniverse-mcp-tool-upgrade/SKILL.md` if a missing MCP tool
  blocks live verification.

Read runbooks only when the matching failure appears:

-`docs/tool-diagnostic-map.md`
-`docs/runbooks/cold-boot-timeout.md`
-`docs/runbooks/kit-stdin-deadlock.md`
-`docs/runbooks/hub-orphan.md`
-`docs/runbooks/env-sub-config.md`
-`docs/runbooks/kit-dep-solver-fail.md`
-`docs/runbooks/multi-app.md`
-`docs/runbooks/scene-reexport-lock.md`

## Upgrade Scope

The target is Isaac Sim 6.0.0-primary. Isaac Sim 5.1 remains only as historical
context in incident logs, old validation artifacts, and clearly marked
compatibility notes.

Upgrade all current surfaces:| Surface | Scope |
|---|---|
| Launch/profile/config | `types/profile.py`, `config.py`, `process_module.py`, `.env.example`, setup scripts, workspace docs |
| MCP server metadata | package docstrings, prompts, resources, tool catalog regeneration |
| Extension services | validation API services/models/feature guards under `kkr-extensions/` |
| Demo extensions | `omni.mycompany.navmesh_playground` robot/people/USD loading code |
| Scenarios | smoke/integration YAML and any controllers under `scenarios/` |
| Assets | `docs/assets/isaac/**`, inventory tests, asset search docs |
| Catalogs | extension harvest/render/diff scripts and catalog tests |
| Docs | README, AGENTS, CLAUDE hierarchy, invariants, runbooks only if failure procedures changed |
| Tests | unit/static tests for every changed contract |
| Live validation | Kit boot, REST health, MCP tools, sensor/robot/character/navmesh/ROS2/Replicator scenarios |
| Local skills | update only when the workflow itself is stale for Isaac 6.0 |

## Current 5.1 Inventory Command

Before editing, run and save the output summary in this document or a linked
artifact:

```powershell
rg -n "5\.1|5\.1\.0|Kit 107|107\.3|Python 3\.11|Assets/Isaac/5\.1|Isaac-Sim Full/5\.1|isaac-sim-standalone-5\.1|omni\.isaac|isaacsim\.core\.api|isaacsim\.core\.prims|isaacsim\.core\.utils|isaacsim\.sensors|isaacsim\.robot_motion|isaacsim\.robot\.wheeled_robots|isaacsim\.ros2\.bridge" README.md AGENTS.md CLAUDE.md .env.example setup docs scripts src tests kkr-extensions scenarios
```

Classify every finding:

- Runtime break risk.
- Test or verification drift.
- Documentation drift.
- Asset/catalog drift.
- Historical note that should remain unchanged.

Do not bulk replace. Every edit must be tied to one class above.

## Phase 0: Recovery And Preflight

Goal: establish a clean execution base after context compression.

- [ ] Create or enter a new isolated worktree.
- [ ] Copy this SoT into the worktree if absent.
- [ ] Record worktree path, branch, baseline SHA.
- [ ] Record `git status --short --branch` for source and worktree.
- [ ] Record whether branch started from `main`.
- [ ] Record the source checkout dirty list as user-owned.
- [ ] Create worktree-local `.env` or equivalent process env with the Isaac
      6.0 paths above.
- [ ] Verify install files:
      - `kit\kit.exe`
      - `apps\isaacsim.exp.full.kit`
      - `python.bat`
      - `VERSION`
      - `exts`, `extscache`, `extsInternal`
- [ ] Verify Isaac Python:
      ```powershell
      & "<isaac-sim-6.0-root>\python.bat" -c "import sys; print(sys.version); print(sys.executable)"
      ```
- [ ] Run baseline static checks when possible:
      ```powershell
      uv run pytest tests/
      .venv/Scripts/python.exe scripts/verify_mcp_sync.py
      ```
- [ ] If baseline fails before upgrade edits, classify as pre-existing and
      decide whether it blocks migration.

## Phase 1: Launch, Profile, Setup

Files to audit and update:

- `src/omniverse_kit_mcp/types/profile.py`
- `src/omniverse_kit_mcp/config.py`
- `src/omniverse_kit_mcp/modules/process_module.py`
- `.env.example`
- `setup/setup_omniverse_kit_mcp.ps1`
- `setup/CLAUDE.md`
- `README.md`
- `AGENTS.md`
- `workspaces/README.md`
- `workspaces/isaac/CLAUDE.md`
- tests asserting profile defaults or launch command construction

Required outcomes:

- Isaac profile defaults and examples point to Isaac Sim 6.0.0.
- Primary kit file is `apps/isaacsim.exp.full.kit`.
- Ports remain `8111` and `8112` for Isaac unless `multi-app.md` is updated
  by explicit design.
- `ISAAC_MCP_INSTANCE_ID` remains 1..2.
- `subprocess.Popen(..., stdin=subprocess.DEVNULL)` remains protected.
- stdout/stderr log redirection remains intact.
- ROS environment setup prefers `exts/isaacsim.ros2.core/<distro>/lib` when
  present and documents Windows/Humble vs Ubuntu/Jazzy differences.
- `kit-dep-solver-fail` absolute ext-folder rule remains valid for the new
  standalone install.

Targeted checks:

```powershell
uv run pytest tests/unit/test_config_multi_app.py
uv run pytest tests/unit/test_process_module_multi_app.py
uv run pytest tests/unit/test_kit_launchers.py
```

## Phase 2: Extension Catalog Sync

Use `.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md`.

Files to audit and update:

- `scripts/harvest_extension_metadata.py`
- `scripts/render_catalog_md.py`
- `scripts/diff_catalog.py`
- `tests/unit/test_catalog_integrity.py`
- `tests/unit/test_harvest_bootstrap.py`
- `tests/unit/test_render_catalog.py`
- `docs/references/CLAUDE.md` if workflow changed

Required outcomes:

- Isaac Sim app version reflects local `VERSION`.
- Kit version reflects local `+110.1.1` evidence.
- Install-root detection can find the supplied standalone install.
- `exts`, `extscache`, `extsInternal`, and `extsDeprecated` are handled.
- Removed extensions stay in generated local JSON as skipped with reason.
- Ignored generated catalogs are not committed.

Required checks:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_catalog_integrity.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_harvest_bootstrap.py tests/unit/test_render_catalog.py -q
.venv/Scripts/python.exe scripts/diff_catalog.py --verbose
.venv/Scripts/python.exe scripts/harvest_extension_metadata.py
.venv/Scripts/python.exe scripts/render_catalog_md.py
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

If generated ignored catalog files are large, report their counts and do not
stage them.

## Phase 3: Runtime API Migration

Use official docs and local source. Record evidence for every runtime API
decision.

### Core API

Audit:

- `kkr-extensions/**/*.py`
- `scenarios/controllers/**/*.py`
- `src/**/*.py`
- tests that mention `isaacsim.core.api`, `isaacsim.core.prims`, or
  `isaacsim.core.utils`

Required outcomes:

- No active runtime dependency on `omni.isaac.*`.
- `isaacsim.core.api/prims/utils` usage is either migrated or explicitly
  isolated with evidence and a deprecation note.
- Stage-loading checks must use
  `isaacsim.core.experimental.utils.stage.is_stage_loading` first and retain
  `USDContext.get_stage_loading_status()` as fallback.
- Remaining `isaacsim.core.prims` / `isaacsim.core.utils.types` usage is
  allowed only in robot/physics runtime wrappers where the 6.0 experimental
  articulation API is not a drop-in replacement. Those call sites must be lazy,
  live-tested, and recorded as a deprecation-watch item rather than a forgotten
  5.1 dependency.
- Tests assert 6.0-first behavior.

### Sensor API

Audit:

- `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/sensor_service.py`
- `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/models/sensor.py`
- `_app_features.py`
- `src/omniverse_kit_mcp/types/sensor.py`
- sensor scenarios and live scripts
- sensor unit tests

Required outcomes:

- Camera/depth/RTX paths use or explicitly bridge toward
  `isaacsim.sensors.experimental.rtx`.
- Lidar creation no longer depends blindly on removed old command
  registration. If a deprecated command remains as a fallback, response
  fields must state backend and limitation.
- Contact/IMU use or explicitly bridge toward
  `isaacsim.sensors.experimental.physics`.
- Response models expose backend/evidence clearly.

Targeted checks:

```powershell
uv run pytest tests/unit/test_sensor_tools.py tests/unit/test_sensor_ext_tools.py
```

### Robot And Motion

Audit:

- `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/robot_service.py`
- `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/models/robot.py`
- `kkr-extensions/omni.mycompany.navmesh_playground/**`
- `scenarios/controllers/**`
- robot scenarios/live scripts/tests

Required outcomes:

- `omni.isaac.*` fallbacks are removed or isolated as historical compatibility
  paths that are never needed for 6.0 quality gates.
- Lula/cMotion/PINK paths are verified from local install or official docs.
- Wheeled robot controller path and return type are verified.
- R2 remains: robot motion requires `simulation_play` except `robot_load`.

Targeted checks:

```powershell
uv run pytest tests/unit/test_robot_ext_tools.py
```

### Character, NavMesh, And Replicator Agent

Audit:

- `character_service.py`
- `navmesh_playground` people/character code
- `isaacsim.replicator.agent.core` usage
- character and replicator scenarios/live scripts/tests

Required outcomes:

- Replicator Agent 1.x breaking changes are reflected.
- Character paths do not rely on 5.1-only `Biped_Setup.usd` unless local 6.0
  evidence proves it exists and works.
- `character_load` remains the safe path for rig/AnimGraph binding.
- Shutdown cleanup remains explicit.

### OmniGraph And ROS2

Audit:

- `omnigraph_service.py`
- `_app_features.py`
- ROS2 scenarios/live scripts/tests
- process ROS environment setup

Required outcomes:

- Replace 5.1 `isaacsim.ros2.bridge` assumptions with 6.0 extension IDs and
  nodes verified from local install.
- Use compute/read nodes required by official ROS2 OmniGraph migration docs.
- Keep partial graph creation explicit in response fields.

## Phase 4: Assets, Scenarios, Sensor Menu

Use `.claude/skills/omniverse-asset-inventory-sync/SKILL.md`, but update or
override any 5.x-only skill assumptions before relying on it.

Files to audit and update:

- `docs/assets/isaac/asset_inventory.md`
- `docs/assets/isaac/assets/*.md`
- `docs/assets/composer/README.md`
- `tests/unit/test_asset_inventory_integrity.py`
- `tests/unit/test_asset_module.py`
- `docs/invariants/asset-discovery.md`
- `docs/invariants/usd-load.md`
- `docs/invariants/visual-validation.md`
- `docs/references/sensor_menu_catalog.md`
- `scripts/live_test_*.py`
- `scenarios/**/*.yaml`

Required outcomes:

- `$ISAAC` points to the verified 6.0 S3 prefix when assets exist:
  `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac`
- All listed USD URLs pass HEAD or live content browse validation.
- Missing 5.1 character assets are not guessed. Resolve through local install,
  official docs, or live `content_browse`.
- Scenario YAML uses real assets only; no primitive placeholders.
- Sensor menu catalog is recaptured from Isaac 6.0 Create menu when live Kit is
  available.

Required checks:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_asset_inventory_integrity.py tests/unit/test_asset_module.py -q
.venv/Scripts/python.exe scripts/diff_asset_inventory.py --verbose
```

## Phase 5: Documentation Hierarchy

Update current docs, not historical incident logs, unless a history entry is
actually being corrected.

Files to audit:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- local `CLAUDE.md` files for edited paths
- `docs/invariants/*.md`
- `docs/runbooks/*.md` only if failure/debug procedures changed
- `docs/references/CLAUDE.md`
- `.claude/skills/*/SKILL.md` only when workflow is stale

Required outcomes:

- Active docs say Isaac Sim 6.0.0, not 5.1.
- Historical 5.1 incidents remain clearly historical.
- Root `CLAUDE.md` DO-NOT-EDIT regions are untouched.
- Pull-First architecture remains intact.
- Local skills do not silently encode 5.x assumptions for a 6.0 upgrade path.

Required checks:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_doc_integrity.py -q
```

Run `.claude/skills/omniverse-docs-sweep/SKILL.md` near the end if docs changed
beyond this SoT.

## Phase 6: Static Verification Gate

Static completion requires fresh output from the current implementation
worktree:

```powershell
uv run pytest tests/
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
.venv/Scripts/python.exe scripts/diff_asset_inventory.py --verbose
```

Also run targeted tests for each changed surface. Do not claim success from old
thread summaries.

If `verify_mcp_sync.py` regenerates `docs/tool-catalog.md`, either make the
catalog clean or report exactly why it is dirty. Do not stage without user
approval.

## Phase 7: Live Verification Gate

Live verification is required for a complete upgrade.

Run in or against `workspaces/isaac/instance-1`:

```powershell
codex mcp list
```

Then verify in this order:

1. `kit_app_start`.
2. Health endpoint: `http://127.0.0.1:8111/validation/v1/health`.
3. `extension_list_all` and `extension_get_info` for required extension IDs.
4. Extension catalog harvest/diff/render against the local 6.0 install.
5. `content_browse` and `asset_search` for 6.0 assets.
6. `stage_open` and `stage_load_usd` with 6.0 asset URLs.
7. `viewport_capture(return_stats=true)`.
8. Final visual validation of at least one meaningful capture.
9. RTX camera, lidar, depth camera creation or explicit supported replacement.
10. Contact and IMU creation or explicit supported replacement.
11. Lidar point cloud or GMO readback if supported.
12. Robot load, articulation readback, joint read/write, drive physics.
13. Gripper, IK, and EE pose where supported by selected robot.
14. Character load, animation, navigation, cleanup/shutdown safety.
15. NavMesh bake, query, and sample.
16. ROS2 graph structure creation; ROS2 runtime may be blocked if external ROS2
    dependencies are missing, but graph-node migration must still be checked.
17. Replicator writer/randomizer trigger.
18. Scenario smoke suite.

Visual validation rule:

- Blank, black, or near-zero variance captures are failures unless a known
  unsupported live environment explains them.
- Add lighting, warmup frames, camera correction, or asset framing and retry.

Suggested live/ad-hoc scripts:

- Phase D: `scripts/live_test_extension_ui.py`
- Phase E: `scripts/live_test_phase_e.py`,
  `scripts/live_test_sensor.py`, `scripts/live_test_navmesh_viz.py`,
  `scripts/live_test_viewport_multi.py`
- Phase F: `scripts/live_test_physics.py`,
  `scripts/live_test_lighting.py`, `scripts/live_test_material.py`,
  `scripts/live_test_viewport_render.py`
- Phase G: `scripts/live_test_character_crowd.py`,
  `scripts/live_test_robot_ext.py`,
  `scripts/live_test_sensor_contact_imu.py`,
  `scripts/live_test_timeline.py`
- Phase H: `scripts/live_test_replicator.py`,
  `scripts/live_test_omnigraph.py`, `scripts/live_test_content.py`,
  `scripts/live_test_extension_ext.py`
- GUI-equivalent gap: `scripts/live_test_gui_equiv.py`

These scripts are not abandoned artifacts. They are manual phase smoke tools.
The official regression path remains unit/static tests plus
`scenarios/*.yaml` through `scenario_validate`.

Isaac Sim 6.0 live deltas discovered during execution:

- `INavMesh.query_shortest_path` no longer accepts `agent_radius` /
  `agent_height` kwargs. The 6.0 binding expects a `NavAgentDesc` positional
  argument with `radius`, `height`, and `collision_gap` fields. Keep the
  compatibility wrappers in `navigation_service.py` and
  `navmesh_playground/navmesh_sampler.py`; do not reintroduce direct
  `mesh.query_shortest_path(..., agent_radius=..., agent_height=...)` calls.
- `robot_load` must use `CreatePayloadCommand`, not `CreateReferenceCommand`.
  Unlike static `stage_load_usd`, robot payloads are `instanceable=False`
  because runtime articulation traversal and child-prim writes need editable
  prims. `robot_load` also rejects pending/running async jobs and stops the
  timeline before mutating the stage.
- `simulation_step` must not default to `timeline.forward_one_frame()` after
  Replicator/HydraTexture work in Isaac Sim 6.0. The stable path is play-burst
  advancement with `set_time_fallback` when the timeline refuses to advance.
- `omni.mycompany.ui_demo` / `omni.mycompany.ui_demo_advanced` are optional in
  this 6.0 worktree. Phase D/E scripts must skip demo-only UI checks with
  exit 0 when the extensions are not registered, while still running core UI,
  menu, navigation, viewport, and stage checks.
- RTX Lidar prims are not viewport cameras in Isaac Sim 6.0. Passing the
  OmniLidar/schema prim as `viewport_create.camera_path` or
  `viewport_capture.camera_prim_path` can crash native
  `rtx.sensors.lidar.core`. Use `sensor_set_visualization` plus a regular
  camera/viewport capture, or `sensor_lidar_get_point_cloud`. `ViewportService`
  guards this now.
- BehaviorAgent `custom_action` in Isaac Sim 6.0 requires the action name as a
  positional argument. Adapter code must call `custom_action("Sit")` first and
  keep `action_name=` only as a legacy fallback. Some character skins can still
  load/render while their BehaviorAgent handle is unavailable; variant demos
  remain optional and must use `continueOnFailure`.

## Completion Semantics

Use these exact statuses:

- `not-started`: no upgrade implementation has begun in the current worktree.
- `static-in-progress`: static/code/docs migration is underway.
- `static-complete`: static migration and static gates passed, live gates not
  completed.
- `live-in-progress`: live Isaac 6.0 validation is underway.
- `live-blocked`: a live gate cannot run because of a concrete external
  prerequisite.
- `blocked`: implementation cannot safely continue without user input or
  contradictory evidence resolution.
- `complete`: all static and required live gates passed, with evidence.

Do not call the upgrade complete while any required live gate is unrun,
failed, or blocked.

External blockers may include:

- Isaac Sim 6.0 install path missing.
- GPU/driver/runtime prevents Kit from booting.
- ROS2 external runtime missing. In this case, graph structure can still pass
  while ROS2 message transport is blocked or skipped with evidence.
- Official docs and local source disagree on an API path.
- Required MCP tool is missing and must be added through
  `.claude/skills/omniverse-mcp-tool-upgrade/SKILL.md`.

## Evidence Ledger

Append concise evidence here as work proceeds. Do not erase old entries unless
they are clearly wrong; add a correction entry instead.

| Date | Status | Evidence |
|---|---|---|
| 2026-06-10 | local-install-found | User supplied Isaac 6.0 standalone path; root, `kit.exe`, app `.kit`, VERSION, and Python 3.12.13 verified. |
| 2026-06-10 | previous-worktree-missing | `git worktree list` shows only source checkout; `<retired-codex-worktree>` is absent. Reconstruct upgrade in a fresh worktree. |
| 2026-06-10 | official-docs-checked | Release notes, Python environment docs, sensor migration pages, ROS2 OmniGraph migration, and Replicator Agent migration guide checked. |
| 2026-06-10 | worktree-created | Implementation worktree `<codex-worktrees>\isaac6-live\omniverse-kit-mcp` on branch `codex/isaac-sim-6-live-upgrade`, baseline `e9039e0c3719a8923f31d3b8560d558af3ce276b`. |
| 2026-06-10 | baseline-static-green | Before upgrade edits in the worktree: `uv run pytest tests/` = 481 passed, 15 skipped; `.venv\Scripts\python.exe scripts\verify_mcp_sync.py` = OK, 9 catalog/registration checks passed; `codex mcp list` inside `workspaces/isaac/instance-1` showed `isaacsim-mcp-1` enabled. |
| 2026-06-10 | phase-1-static-green | Launch/profile/setup changed to 6.0 paths and ROS lib detection prefers `exts/isaacsim.ros2.core/<distro>/lib`. Targeted tests: `test_config_multi_app.py` 19 passed, `test_process_module_multi_app.py` 11 passed, `test_kit_launchers.py` 4 passed. |
| 2026-06-10 | phase-2-static-green | Extension catalog scripts updated for local 6.0 install, Kit `110.1.1`, `extsInternal`, and source counts. Targeted tests: `test_harvest_bootstrap.py` 76 passed, `test_catalog_integrity.py` 14 skipped when generated catalog absent, `test_render_catalog.py` 5 passed. |
| 2026-06-10 | phase-3-sensor-static-green | Sensor feature guards and services migrated toward `isaacsim.sensors.experimental.rtx` / `isaacsim.sensors.experimental.physics`; lidar response exposes backend. Targeted tests: `test_sensor_tools.py` 10 passed, `test_sensor_ext_tools.py` 6 passed. |
| 2026-06-10 | phase-3-robot-static-green | Removed active `omni.isaac.*` robot fallbacks from validation API and navmesh playground robot paths. Targeted test: `test_robot_ext_tools.py` 8 passed. |
| 2026-06-10 | phase-3-character-static-green | Local 6.0 install lacks public `Biped_Setup.usd` and `stage_util.CharacterUtil`; character loaders now payload 6.0 skins, ensure shared motion library, and apply BehaviorAgent/IRA APIs with a legacy-compatible adapter. Targeted tests: `test_character_module.py test_character_ext_tools.py` = 15 passed; combined character/robot/sensor target set = 39 passed; compileall of changed extension character/navmesh files passed. |
| 2026-06-10 | phase-4-assets-green | Isaac asset catalog moved to `$ISAAC=.../Assets/Isaac/6.0/Isaac`; `Biped_Setup`/removed Festo entries dropped; Fanuc CRX path corrected to `crx10ia_l`. `test_asset_inventory_integrity.py` = 8 passed; `scripts/diff_asset_inventory.py --verbose` = 112 URLs, 0 invalid. |
| 2026-06-10 | docs-surface-updated | README, AGENTS, root/local `CLAUDE.md`, invariants, local asset skill, scenario authoring docs, active tool descriptions, and generated `docs/tool-catalog.md` updated to 6.0 terminology. Historical 5.1 incident logs and captured references remain clearly historical. |
| 2026-06-10 | core-api-static-audit | Active `omni.isaac.*` robot/character fallbacks removed. Stage-loading checks now prefer `isaacsim.core.experimental.utils.stage.is_stage_loading`. Remaining `isaacsim.core.prims` / `isaacsim.core.utils.types` imports are lazy robot/physics runtime wrappers that require live validation because the 6.0 `isaacsim.core.experimental.prims.Articulation` API is not a 1:1 replacement for `SingleArticulation` action/readback semantics. |
| 2026-06-10 | current-targeted-static-green | After SoT/doc/code updates: `uv run pytest tests/unit/test_render_catalog.py tests/unit/test_asset_inventory_integrity.py tests/unit/test_asset_module.py -q` = 26 passed; `uv run pytest tests/unit/test_character_module.py tests/unit/test_character_ext_tools.py tests/unit/test_sensor_tools.py tests/unit/test_sensor_ext_tools.py tests/unit/test_robot_ext_tools.py -q` = 39 passed; `uv run pytest tests/unit/test_config_multi_app.py tests/unit/test_process_module_multi_app.py tests/unit/test_kit_launchers.py tests/unit/test_harvest_bootstrap.py tests/unit/test_catalog_integrity.py -q` = 110 passed, 14 skipped. |
| 2026-06-10 | catalog-sync-no-stage | `.venv\Scripts\python.exe scripts\verify_mcp_sync.py` regenerated `docs/tool-catalog.md`; registration/catalog pytest inside the script passed (9 passed), then script exited non-zero only because the generated catalog is uncommitted and staging is forbidden without user approval. Follow-up `uv run pytest tests/unit/test_tools_registration.py tests/unit/test_tool_catalog_sync.py -q` = 9 passed. |
| 2026-06-10 | full-static-green | `uv run pytest tests/` after current upgrade edits = 483 passed, 15 skipped in 36.96s. `uv run pytest tests/unit/test_doc_integrity.py -q` = 8 passed. Compileall for changed validation_api/navmesh extension services/controllers passed. |
| 2026-06-10 | extension-catalog-local-green | `scripts/harvest_extension_metadata.py` against local 6.0 install produced local ignored `docs/references/extensions.json`: total 637 unique extensions, Isaac source counts `exts=114`, `extscache=487`, `extsDeprecated=26`, `extsInternal=7`, `kit/extscore=3`. Four harvest warnings are all missing default USD Composer dirs under `C:\USDComposer`; expected for an Isaac-only worktree. `scripts/render_catalog_md.py` succeeded. `test_catalog_integrity.py` with local catalog = 13 passed, 1 skipped. `scripts/diff_catalog.py --verbose` after harvest = 0 added/removed/version/category drift for both apps (`usd_composer current=0 fresh=0`). |
| 2026-06-10 | live-kit-green | Local 6.0 standalone started from `<isaac-sim-6.0-root>` with `kit.exe` + `apps/isaacsim.exp.full.kit`; instance 1 ready on port 8111. |
| 2026-06-10 | live-sensor-green | `scripts/live_test_sensor_contact_imu.py` passed. Contact backend reported `fallback_xform:ValueError`; IMU backend reported `isaacsim.sensors.experimental.physics.IMU.create`; annotators include rgb/semantic. |
| 2026-06-10 | live-robot-crash-root-caused | Isaac 6.0 crashed when robot payload mutation happened while a NovaCarter navigation job/timeline was active. Root cause was unsafe stage mutation during active async job/physics state, not just the USD command. |
| 2026-06-10 | live-robot-green | `RobotService.load` now uses `CreatePayloadCommand(instanceable=False)`, parent Xform creation, active-job rejection, and timeline-stop guard. `LIVE_ROBOT=1 scripts/live_test_robot_ext.py` passed: `navigate_path` terminal `done`, gripper open/close OK, `set_ee_target` IK success via `isaacsim.robot_motion`. |
| 2026-06-10 | live-simulation-green | `simulation_step` now uses play-burst advancement and `set_time_fallback`; Replicator-to-timeline sequence no longer crashes. Fresh `scripts/live_test_timeline.py` passed with `mode=play_burst`, `set_time` current time `3.5`. |
| 2026-06-10 | live-navigation-api-fixed | Runtime introspection through `/validation/v1/commands/python_run` showed `NavAgentDesc(radius, height, collision_gap)`. `navigation_service.py` and `navmesh_playground` now wrap `query_shortest_path` with 6.0 `NavAgentDesc` first and old kwargs fallback. `scripts/live_test_phase_e.py` passed: core query path `ok=True`, `points=2`; `scripts/live_test_navmesh_viz.py` passed with all visualization backends `carb_settings`. |
| 2026-06-10 | live-ui-demo-optional-green | `scripts/live_test_extension_ui.py` exits 0 with an explicit SKIP when `omni.mycompany.ui_demo` is not registered. `scripts/live_test_phase_e.py` skips demo-only UI and still runs core window/menu/navigation/viewport checks. |
| 2026-06-10 | live-gui-equiv-green | `scripts/live_test_gui_equiv.py` passed stage new/create/select/camera/capture/save/open/assert checks against the 6.0 instance. |
| 2026-06-10 | live-other-phase-smokes-green | Prior live phase smokes in this worktree passed for NavMesh visualization, character crowd (animation variant tolerated BehaviorAgent handle unavailability), Replicator, OmniGraph, GUI equivalent, and timeline after the simulation fallback fix. |
| 2026-06-10 | live-phase-e-scenario-crash-fixed | First `integration/phase_e_combined.yaml` run crashed Kit at `capture_lidar_panel`; Kit log backtrace was in `rtx.sensors.lidar.core.plugin.dll`. Root cause: scenario passed RTX Lidar prim as viewport camera. Fix: `ViewportService` rejects RTX Lidar/non-camera prims as camera sources, Phase E YAML uses RGB/depth viewports plus Lidar debug visualization, and quotes `mode: "off"`. Re-run passed: 26 steps passed, 0 failed/skipped, three viewport artifacts. |
| 2026-06-10 | live-phase-g-scenario-green-with-optional-variant | `integration/phase_g_combined.yaml` passed after BehaviorAgent `custom_action` positional-signature fix. Required robot load/contact/IMU/crowd/navigation/assert/cleanup steps passed. Optional `visitor_sit_optional` may still report 400 `BehaviorAgent handle not available` and is intentionally `continueOnFailure`. |
| 2026-06-10 | live-phase-h-scenario-green | `integration/phase_h_combined.yaml` passed: 29 steps passed, 0 failed/skipped for content preview, warehouse load, physics cubes, randomizers, BasicWriter, OmniGraph execute, and cleanup. |
| 2026-06-10 | final-static-green | Final static gates after live fixes: `uv run pytest tests/` = 503 passed, 2 skipped; `.venv\Scripts\python.exe scripts\verify_mcp_sync.py` = OK, catalog up-to-date, registration/catalog-sync 9 passed; `.venv\Scripts\python.exe scripts\diff_asset_inventory.py --verbose` = 112 URLs, 0 invalid; `git diff --check` = exit 0 with LF→CRLF warnings only. |

## Stop Conditions

Stop and report if:

- A live failure indicates process lifecycle or dependency solver trouble that
  needs user action.
- Local 6.0 source and official docs disagree on a runtime API that affects
  implementation.
- A required invariant would be violated.
- `verify_mcp_sync.py` fails after tool/resource changes and cannot be fixed
  cleanly.
- A 7-place MCP tool edit cannot be completed cleanly.
- The only available path is to overwrite or discard user-owned dirty changes.

Do not stop merely because one live gate is unavailable. Continue independent
static, unit, documentation, and live gates where safe.

## Final Report Template

Final report must include:

- Branch and worktree path.
- Files changed.
- `CLAUDE.md` files read.
- Pull-docs read.
- Runbooks read, if any.
- Official docs used.
- Local skills used.
- Tests/checks run with exact outcomes.
- Live checks run with exact outcomes.
- Commands not run and why.
- Remaining risks.
- Final status from `Completion Semantics`.

Use precise language. If live verification is blocked, say `live-blocked`, not
complete.
