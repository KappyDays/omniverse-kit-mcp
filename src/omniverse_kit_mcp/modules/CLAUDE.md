<!-- Parent: ../../../CLAUDE.md -->
<!-- Scope: Domain modules — Wrapping HTTP/OS calls, providing typed methods to the MCP tool layer -->
<!-- Siblings: ../tools/CLAUDE.md (tool registration), ../scenario/CLAUDE.md (scenario engine) -->

# modules — Domain Modules

Each module is responsible for one domain. Wraps an HTTP client (IsaacRestClient / LakehouseClient) or OS call (subprocess) and exposes it as a typed async method that returns `ModuleResult[T]`.

## Module Responsibility Matrix (IMPORTANT)| module | file | responsibility |
|------|------|------|
| `StageModule` | `stage_module.py` | READ / ASSERT / DIFF — snapshot, diff_snapshots, assert_prim_exists, assert_property + **Selection** (get/set_selection) |
| `SimulationModule` | `simulation_module.py` | Timeline (play/pause/stop/status/step/set_time) + **Stage WRITE** (load_usd / set_property / create_prim / delete_prim) + **File** (stage_save / open / new). `step(frames)` is the Isaac Sim 6.0 stable path play-burst priority + `set_time_fallback` |
| `ProcessModule` | `process_module.py` | kit.exe lifecycle — kit_app_start / stop / restart / **list_kit_instances** (read-only Win32_Process enumerate, includes both MCP/GUI, `is_this_mcp_instance` flag) |
| `ExtensionModule` | `extension_module.py` | Custom Extension Control — trigger / get_state / reset / activate / deactivate / list_all / get_info / get_ui_tree (ui_test widget walk) / ui_invoke / capture_logs / clear_logs |
| `ViewportModule` | `viewport_module.py` | capture / compare_ssim / set_active_camera / focus_prim (F-key/Frame Selected equivalent) / create (secondary window, idempotent with `existed` flag) / destroy (idempotent `destroyed=false` if missing) + set_render_mode (`/rtx/rendermode`) / set_render_quality (`/rtx/pathtracing/spp` + denoiser) / toggle_overlay (per-overlay carb key) / set_fov (candidate camera walk → focalLength inversion) |
| `LakehouseModule` | `lakehouse_module.py` | **query only** — no inject/cleanup (Key Decision) |
| `RobotModule` | `robot_module.py` | list_arm_profiles (built-in Isaac Sim 6.0 arm catalog + support matrix, recommended dynamic/static-only probe groups, per-profile probe-mode reasons, known dynamic probe hazards, known pick/place playback blockers) / load (USD payload + articulation detection; robot payload is `instanceable=False`, active job rejected, playing timeline stop) / get/set_joint_positions (SingleArticulation, auto-initialize) / get_joint_config_static (USD joint prim metadata without play; diagnostic only, not write-order proof) / navigate_to (→ Job) / navigate_path (multi-waypoint → Job, playing timeline required) / gripper_control (finger|gripper DOF auto-detect, Franka-default 0.04/0.0 fallback) / set_ee_target (Lula IK, across arm family with shipped motion-policy key) / run_franka_pick_place (official PickPlaceController/RMPflow/ParallelGripper + bbox lift/place validation) / **drive_physics (DifferentialController + Pure Pursuit, physics-based wheel joint velocities, ASYNC Job, R2 force, auto wheel DOF resolve)** |
| `JobModule` | `job_module.py` | status (polling), cancel (Task.cancel) — ASYNC Job Control |
| `AssetModule` | `asset_module.py` | list — GUI Asset Browser equivalent (S3 catalog directory listing) / search — offline Isaac catalog / external_asset_* — prepare-only external free asset search-download-convert into ignored `.omniverse-kit-mcp/` cache, no stage placement |
| `CharacterModule` | `character_module.py` | load (6.0 character skin + BehaviorAgent/IRA bind) / play_animation (Idle/Walk/Run/Sit + optional target) / play_animation_variant (BehaviorAgent task-first dispatch where available, direct SkelAnimation bind via `dispatch_mode="skel"`, graph fallback) / load_crowd (N character skins grid/line/random) / set_position (kinematic XForm) / stop_animation / navigate_to (→ Job) / get_state |
| `WindowModule` | `window_module.py` | Kit GUI — list_windows / list_ui_windows / show_ui_window (title fuzzy) / list_menu_items / trigger_menu (diff-based `created_prims`) / capture (PrintWindow + wait_stable pixel diff) |
| `NavigationModule` | `navigation_module.py` | NavMesh — bake (required stopped state) / query_path (auto-bake on demand; Isaac Sim 6.0 `NavAgentDesc` wrapper) / add_exclude_volume (bbox auto Exclude) / set_visualization (`viewNavMesh` carb.settings priority, prim visibility fallback) / **sample_walkable_points (area-weighted barycentric on baked NavMesh; fallback: bbox-rejection + reachability via query_shortest_path)** |
| `SensorModule` | `sensor_module.py` | attach_rtx_camera/depth_camera (`USDGeom.Camera` + `customData.validation_api.sensor_type` tag) / attach_rtx_lidar (6.0 OmniLidar/schema prim + tag; prohibited to use as viewport camera) / set_visualization (dispatch based on sensor_type) / attach_contact / attach_imu (`isaacsim.sensors.experimental.physics` → Xform fallback) / set_annotator (`omni.replicator.core.AnnotatorRegistry` + fixed name set verification) || `PhysicsModule` | `physics_module.py` | apply_rigid_body (RigidBodyAPI + MassAPI) / apply_collider (CollisionAPI + mesh bound MeshCollisionAPI + approximation enum) / apply_material (PhysicsMaterialAPI + MaterialBindingAPI "physics" purpose) / create_joint ({Fixed,Revolute,Prismatic,Spherical}) / set_scene (USDPhysics.Scene + gravity + solver iter + `/physics/timeStepsPerSecond`) / visualize (/physics/visualization* carb key active by mode) |
| `LightingModule` | `lighting_module.py` | create_{dome,distant,disk,rect,sphere} (USD 2023+ `inputs:*` prefix) + set_exposure (`/rtx/post/tonemap/exposure`). Automatically generate parent with `_ensure_parent_scope` |
| `MaterialModule` | `material_module.py` | list_mdl (kit install tree recursive scan) / assign_mdl (`CreateMdlMaterialPrimCommand` + `BindMaterialCommand`) / get_bound (static `GetMaterialBindingStrength(rel)`) |
| `ReplicatorModule` | `replicator_module.py` | create_writer (BasicWriter/KittiWriter/CocoWriter + rgb/depth/semantic_segmentation) / register_randomizer (position=scatter_3d / rotation=modify.pose / lighting=modify.attribute intensity) / trigger_once (`rep.orchestrator.run_async` priority) / trigger_on_time (`rep.trigger.on_time`) |
| `OmnigraphModule` | `omnigraph_module.py` | create_node (`og.Controller.edit` CREATE_NODES, graph auto-create, `graph_existed` flags) / connect (`og.Controller.connect`) / execute (`graph.evaluate()` manual tick) / create_ros2_publisher (OnTick + IsaacCreateRenderProduct + ROS2PublishImage macro — partial creation possible) |
| `ContentModule` | `content_module.py` | browse (`omni.client.list` + `asyncio.to_thread`, recursive + max_depth + max_entries upper limit) / preview (`omni.client.stat`) / resolve (`omni.client.normalize_url` / `make_absolute_url` fallback) |

**Note**: `stage_load_usd` / `stage_set_property` / `stage_create_prim` / `stage_delete_prim` are routed to `SimulationModule` in the tools layer. When adding a new Stage WRITE operation, implemented in `SimulationModule` (not stage_module).

**Articulation pre-verification + automatic initialization**: Extension `robot_service._assert_articulation()` checks whether `USD.PrimRange` is PhysxArticulationAPI recursively. If not, HTTP 400 → MCP module is wrapped with `ROBOT_GET/SET_JOINTS_ERROR`. `_ensure_initialized(art)` automatically calls `SingleArticulation.initialize()`. Since initialize operates only after PhysX has completed at least one physics step, `simulation_play → pause` warm-up is required for scenario arrange. `robot_get_joint_config_static` intentionally avoids `SingleArticulation` and uses USD prim traversal only; use it for hazardous profile triage evidence, not for `set_joint_positions` ordering.

**Robot probe controllability classification**: `RobotArmProfileProbeResult.mcp_controllability` is the explicit evidence class for MCP controllability claims. Only `dynamic_joint_control` proves dynamic joint read/write via safe nudge. `dynamic_joint_read_only` lacks write proof, `static_load_articulation_metadata` is static hazard-triage evidence only, and `blocked_*` rows are blockers rather than controllability proof. Do not infer pick/place validation from any probe classification; probe rows carry `probe_proves_pick_place=false`, `pick_place_validation_status`, and `pick_place_validation_reason`, and batch rows summarize counts plus profile maps such as `mcp_controllability_profiles`, `probe_capability_level_name_profiles`, and `pick_place_validation_status_profiles`.

## Character domain constraints (Extension actual measurements)

The Character module is sensitive to BehaviorAgent/IRA/NavMesh runtime state and is therefore collected separately.

**Runtime ready retry**: `character_service._ensure_animation_ready(prim_path)` uses the 6.0 BehaviorAgent adapter first, and if there is a legacy AnimGraph handle, it is used as a compatible path. If registration is delayed, retry after 1-frame `simulation_play → pause` warm-up. If it is still None, HTTP 500. `play_animation` / `navigate_to` / `get_state` / `set_position` all pass this guard. It is recommended to secure critical timing by specifying `simulation.play → pause` in Scenario arrange.

**T-pose prevention — character_load required**: If character USD is loaded as a raw reference with `stage_load_usd`, BehaviorAgent/IRA binding may be missing, resulting in T-pose or stop state during simulation_play. **Must be `character_load`** (6.0 character skin payload + BehaviorAgent/IRA API bind + `anim_graph_bound=true` compatible field). Standard pattern: `character_load(...) → simulation_play → 1s sleep → simulation_pause → character_play_animation("Idle") → simulation_play`. Subsequent calls must use `sanitized_prim_path` in the response (skin variants such as F_Business_02 are automatically moved to `/World/Characters/{name}`).

**Navigate cancel finally**: `character_service._navigate_coro` is wrapped with `try/finally` to ensure `stop_animation` even when JobService cancels/timeouts — preventing mid-frame freeze.

**Shutdown safety (testbed #14)**: Scenario cleanup must run `simulation.play → stop` (final physics tick) before `kit_app_stop`. If omitted, kit.exe hangs due to character runtime / NavMesh internal handle cleaning timing issue. `scenarios/smoke/character_control.yaml` has canonical pattern.

**kit.exe additional extension**: `IsaacSimProcessConfig.extra_ext_ids` includes `isaacsim.replicator.agent.core` / `omni.anim.graph.bundle` / `omni.anim.navigation.bundle` by default (BehaviorAgent/IRA + NavMesh compatible path). It can be overridden with `ISAAC_SIM_EXTRA_EXT_IDS`, but **only accepts JSON array format** (pydantic-settings v2 limitation).

**set_position allows USD write + runtime override**: `SingleXFormPrim.set_world_pose` writes normally to `xformOp:translate` (response `position` field is correct). At the next timeline tick, the character runtime can overwrite xformOp with the internal world transform state. Recommendation: `navigate_to` for time movement, `load(position=[...])` for initial position, `set_position` for USD round-trip verification.**get_state.action is based on server cache**: Some runtime readbacks come down to a list of tokens like `"[]"`, making them unreliable. `CharacterService` maintains per-SkelRoot-path `_last_action` dict — `play_animation` / `stop_animation` write, `get_state` read. `is_navigating = action in ("Walk","Run")` calculation is based on this. Reliable in scenario assertions.

**Navigate requires timeline playing**: `character.navigate_to` Job depends on BehaviorAgent/IRA / NavMesh tick. In the case of `simulation.stop` / `pause`, only the target is set and no advance is made → after timeout, `_navigate_coro finally: stop_animation` → Job terminal. **"Job done" ≠ "target reached"**. For traversal verification, specify `get_state.position` or `simulation.play` before navigating.

## base.py pattern

All module methods return `ModuleResult[T]`. Use `ok_result(data, started_ms=...)` / `error_result(msg, started_ms=..., error_code=...)` factory.

```python
started = int(time.time() * 1000)
try:
    raw = await self._client.some_call(request)
    return ok_result(SomeResult.from_raw(raw), started_ms=started)
except Exception as exc:
    return error_result(str(exc), started_ms=started, error_code="SOME_ERROR")
```

## Integration Facts (runtime constraints by domain)

Non-obvious runtime constraints for 15 domains (Simulation/Viewport/Process/USD/Job/Robot/Character/Asset/NavMesh/Sensor/Physics/Replicator/OmniGraph/Extension/Window) are in separate files:

→ **[`integration-facts.md`](integration-facts.md)** (sibling)

## ProcessModule Operation Manual

kit.exe hang / zombie / `.env` not reflected, etc. Operational issues + stdin/stdout protocol + decision tree + 4 types of traps + standalone path:

→ **[`process-ops.md`](process-ops.md)** (sibling)

## Related Boundaries

- **Brother CLAUDE.md**:
  - `../tools/CLAUDE.md` — MCP tool registration protocol + caveat by tool group
  - `../scenario/CLAUDE.md` — scenario engine + `action_registry` + context-aware dispatch
  - `../CLAUDE.md` (src/omniverse_kit_mcp/) — FastMCP server package root (entry flow · type boundary)
- **Brother pull-doc**: `integration-facts.md` (domain runtime constraints), `process-ops.md` (ProcessModule operation)
- **Top**: root `CLAUDE.md` (pull-doc index · Change ripple matrix · Validation Rules · Key Decisions)
- **Extension internal rules** (Pydantic · omni.services.core · carb.log_warn): `../../../kkr-extensions/CLAUDE.md`
- **Reference before implementing new MCP tool**: `../../../docs/references/CLAUDE.md` (Check existing tool duplication → optional local catalog → actual ext source / official document)
- **Required pull-doc before work**: `../../../docs/invariants/` (usd-load / process-lifecycle / mcp-tool-add / module-add / ui-invoke / scenario-validation / ext-reload)
