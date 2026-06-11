<!-- Parent: ../../../CLAUDE.md -->
<!-- Scope: Domain modules — HTTP/OS 호출 래핑, MCP tool 레이어에 typed 메서드 제공 -->
<!-- Siblings: ../tools/CLAUDE.md (tool 등록), ../scenario/CLAUDE.md (시나리오 엔진) -->

# modules — Domain Modules

각 모듈은 하나의 도메인을 담당. HTTP client (IsaacRestClient / LakehouseClient) 또는 OS 호출 (subprocess) 을 래핑해서 `ModuleResult[T]` 를 반환하는 typed async 메서드로 노출한다.

## 모듈 책임 매트릭스 (IMPORTANT)

| 모듈 | 파일 | 책임 |
|------|------|------|
| `StageModule` | `stage_module.py` | READ / ASSERT / DIFF — snapshot, diff_snapshots, assert_prim_exists, assert_property + **Selection** (get/set_selection) |
| `SimulationModule` | `simulation_module.py` | Timeline (play/pause/stop/status/step/set_time) + **Stage WRITE** (load_usd / set_property / create_prim / delete_prim) + **File** (stage_save / open / new). `step(frames)` 은 Isaac Sim 6.0 안정 경로인 play-burst 우선 + `set_time_fallback` |
| `ProcessModule` | `process_module.py` | kit.exe lifecycle — kit_app_start / stop / restart / **list_kit_instances** (read-only Win32_Process enumerate, MCP/GUI 모두 포함, `is_this_mcp_instance` 플래그) |
| `ExtensionModule` | `extension_module.py` | Custom Extension 제어 — trigger / get_state / reset / activate / deactivate / list_all / get_info / get_ui_tree (ui_test widget walk) / ui_invoke / capture_logs / clear_logs |
| `ViewportModule` | `viewport_module.py` | capture / compare_ssim / set_active_camera / focus_prim (F-key/Frame Selected equivalent) / create (secondary window, `existed` 플래그로 idempotent) / destroy (idempotent `destroyed=false` if missing) + set_render_mode (`/rtx/rendermode`) / set_render_quality (`/rtx/pathtracing/spp` + denoiser) / toggle_overlay (per-overlay carb key) / set_fov (candidate camera walk → focalLength 역산) |
| `LakehouseModule` | `lakehouse_module.py` | **query only** — inject/cleanup 없음 (Key Decision) |
| `RobotModule` | `robot_module.py` | list_arm_profiles (built-in Isaac Sim 6.0 arm catalog + support matrix) / load (USD payload + articulation 감지; robot payload 는 `instanceable=False`, active job 거부, playing timeline stop) / get/set_joint_positions (SingleArticulation, auto-initialize) / navigate_to (→ Job) / navigate_path (multi-waypoint → Job, timeline playing 필수) / gripper_control (finger|gripper DOF auto-detect, Franka-default 0.04/0.0 fallback) / set_ee_target (Lula IK, shipped motion-policy key가 있는 arm family 전반) / run_franka_pick_place (공식 PickPlaceController/RMPflow/ParallelGripper + bbox lift/place 검증) / **drive_physics (DifferentialController + Pure Pursuit, physics-based wheel joint velocities, ASYNC Job, R2 강제, 자동 wheel DOF resolve)** |
| `JobModule` | `job_module.py` | status (폴링), cancel (Task.cancel) — ASYNC Job 제어 |
| `AssetModule` | `asset_module.py` | list — GUI Asset Browser 동등 (S3 카탈로그 directory listing) |
| `CharacterModule` | `character_module.py` | load (6.0 character skin + BehaviorAgent/IRA bind) / play_animation (Idle/Walk/Run/Sit + optional target) / play_animation_variant (prefix-split → base Action + best-effort style) / load_crowd (N character skins grid/line/random) / set_position (kinematic XForm) / stop_animation / navigate_to (→ Job) / get_state |
| `WindowModule` | `window_module.py` | Kit GUI — list_windows / list_ui_windows / show_ui_window (title fuzzy) / list_menu_items / trigger_menu (diff-based `created_prims`) / capture (PrintWindow + wait_stable 픽셀 diff) |
| `NavigationModule` | `navigation_module.py` | NavMesh — bake (stopped 상태 필수) / query_path (auto-bake on demand; Isaac Sim 6.0 `NavAgentDesc` wrapper) / add_exclude_volume (bbox 자동 Exclude) / set_visualization (`viewNavMesh` carb.settings 우선, prim visibility 폴백) / **sample_walkable_points (area-weighted barycentric on baked NavMesh; 폴백: bbox-rejection + reachability via query_shortest_path)** |
| `SensorModule` | `sensor_module.py` | attach_rtx_camera/depth_camera (`UsdGeom.Camera` + `customData.validation_api.sensor_type` tag) / attach_rtx_lidar (6.0 OmniLidar/schema prim + tag; viewport camera 로 사용 금지) / set_visualization (sensor_type 기반 dispatch) / attach_contact / attach_imu (`isaacsim.sensors.experimental.physics` → Xform fallback) / set_annotator (`omni.replicator.core.AnnotatorRegistry` + 고정 이름 집합 검증) |
| `PhysicsModule` | `physics_module.py` | apply_rigid_body (RigidBodyAPI + MassAPI) / apply_collider (CollisionAPI + mesh 한정 MeshCollisionAPI + approximation enum) / apply_material (PhysicsMaterialAPI + MaterialBindingAPI "physics" purpose) / create_joint ({Fixed,Revolute,Prismatic,Spherical}) / set_scene (UsdPhysics.Scene + gravity + solver iter + `/physics/timeStepsPerSecond`) / visualize (/physics/visualization* carb 키 모드별 활성) |
| `LightingModule` | `lighting_module.py` | create_{dome,distant,disk,rect,sphere} (USD 2023+ `inputs:*` prefix) + set_exposure (`/rtx/post/tonemap/exposure`). `_ensure_parent_scope` 로 parent 자동 생성 |
| `MaterialModule` | `material_module.py` | list_mdl (kit install tree 재귀 스캔) / assign_mdl (`CreateMdlMaterialPrimCommand` + `BindMaterialCommand`) / get_bound (정적 `GetMaterialBindingStrength(rel)`) |
| `ReplicatorModule` | `replicator_module.py` | create_writer (BasicWriter/KittiWriter/CocoWriter + rgb/depth/semantic_segmentation) / register_randomizer (position=scatter_3d / rotation=modify.pose / lighting=modify.attribute intensity) / trigger_once (`rep.orchestrator.run_async` 우선) / trigger_on_time (`rep.trigger.on_time`) |
| `OmnigraphModule` | `omnigraph_module.py` | create_node (`og.Controller.edit` CREATE_NODES, graph auto-create, `graph_existed` 플래그) / connect (`og.Controller.connect`) / execute (`graph.evaluate()` 수동 tick) / create_ros2_publisher (OnTick + IsaacCreateRenderProduct + ROS2PublishImage macro — 부분 생성 가능) |
| `ContentModule` | `content_module.py` | browse (`omni.client.list` + `asyncio.to_thread`, recursive + max_depth + max_entries 상한) / preview (`omni.client.stat`) / resolve (`omni.client.normalize_url` / `make_absolute_url` 폴백) |

**주의**: `stage_load_usd` / `stage_set_property` / `stage_create_prim` / `stage_delete_prim` 는 tools 레이어에서 `SimulationModule` 로 라우팅. 새 Stage WRITE 동작 추가 시 `SimulationModule` 에 구현 (stage_module 아님).

**Articulation 사전 검증 + 자동 초기화**: Extension `robot_service._assert_articulation()` 이 PhysxArticulationAPI 여부를 `Usd.PrimRange` 재귀로 체크. 없으면 HTTP 400 → MCP module 이 `ROBOT_GET/SET_JOINTS_ERROR` 로 래핑. `_ensure_initialized(art)` 가 `SingleArticulation.initialize()` 를 자동 호출. initialize 는 PhysX 가 최소 1회 physics step 후에만 동작하므로 scenario arrange 에 `simulation_play → pause` warm-up 필수.

## Character domain constraints (Extension 실측)

Character 모듈은 BehaviorAgent/IRA / NavMesh 런타임 상태에 민감하므로 별도 모음.

**Runtime ready retry**: `character_service._ensure_animation_ready(prim_path)` 는 6.0 BehaviorAgent adapter 를 우선 사용하고, legacy AnimGraph handle 이 있으면 호환 경로로 사용한다. 등록 지연 시 1-frame `simulation_play → pause` warm-up 후 재시도. 여전히 None 이면 HTTP 500. `play_animation` / `navigate_to` / `get_state` / `set_position` 모두 이 가드 통과. Scenario arrange 에 `simulation.play → pause` 명시하여 결정적 타이밍 확보 권장.

**T-pose 방지 — character_load 필수**: `stage_load_usd` 로 character USD 를 raw reference 로드하면 BehaviorAgent/IRA binding 이 누락되어 simulation_play 시 T-pose 또는 정지 상태가 될 수 있다. **반드시 `character_load`** (6.0 character skin payload + BehaviorAgent/IRA API bind + `anim_graph_bound=true` 호환 필드). 표준 pattern: `character_load(...) → simulation_play → 1s sleep → simulation_pause → character_play_animation("Idle") → simulation_play`. 후속 호출은 반드시 응답의 `sanitized_prim_path` 사용 (F_Business_02 등 skin variant 는 `/World/Characters/{name}` 로 자동 이동).

**Navigate cancel finally**: `character_service._navigate_coro` 는 `try/finally` 로 감싸 JobService 가 cancel / timeout 시에도 `stop_animation` 보장 — 중간 프레임 freeze 방지.

**Shutdown safety (testbed #14)**: scenario cleanup 은 `simulation.play → stop` (최종 physics tick) 을 `kit_app_stop` 이전에 반드시 실행. 생략 시 character runtime / NavMesh 내부 핸들 정리 타이밍 문제로 kit.exe 셔다운 hang. `scenarios/smoke/character_control.yaml` 이 canonical pattern.

**kit.exe 추가 extension**: `IsaacSimProcessConfig.extra_ext_ids` 에 `isaacsim.replicator.agent.core` / `omni.anim.graph.bundle` / `omni.anim.navigation.bundle` 가 기본 포함 (BehaviorAgent/IRA + NavMesh 호환 경로). `ISAAC_SIM_EXTRA_EXT_IDS` 로 override 가능하지만 **JSON array 형식만 수용** (pydantic-settings v2 제약).

**set_position 은 USD write + runtime override 가능**: `SingleXFormPrim.set_world_pose` 가 `xformOp:translate` 에 정상 write (response `position` 필드 정확). 다음 timeline tick 에 character runtime 이 내부 world transform state 로 xformOp 를 덮어쓸 수 있다. 권장: 시각 이동은 `navigate_to`, 초기 위치는 `load(position=[...])`, USD round-trip 검증은 `set_position`.

**get_state.action 은 서버 캐시 기반**: 일부 runtime readback 은 `"[]"` 같은 토큰 리스트로 내려와 신뢰 불가. `CharacterService` 가 per-SkelRoot-path `_last_action` dict 유지 — `play_animation` / `stop_animation` write, `get_state` read. `is_navigating = action in ("Walk","Run")` 계산 이 기반. scenario assertion 에서 신뢰 가능.

**Navigate 는 timeline playing 필수**: `character.navigate_to` Job 은 BehaviorAgent/IRA / NavMesh tick 의존. `simulation.stop` / `pause` 상태면 target 만 설정되고 advance 안 됨 → timeout 후 `_navigate_coro finally: stop_animation` → Job terminal. **"Job done" ≠ "target 도달"**. Traversal 검증은 `get_state.position` 또는 navigate 전 `simulation.play` 명시.

## base.py 패턴

모든 모듈 메서드는 `ModuleResult[T]` 반환. `ok_result(data, started_ms=...)` / `error_result(msg, started_ms=..., error_code=...)` 팩토리 사용.

```python
started = int(time.time() * 1000)
try:
    raw = await self._client.some_call(request)
    return ok_result(SomeResult.from_raw(raw), started_ms=started)
except Exception as exc:
    return error_result(str(exc), started_ms=started, error_code="SOME_ERROR")
```

## Integration Facts (도메인별 런타임 제약)

15 개 도메인 (Simulation/Viewport/Process/USD/Job/Robot/Character/Asset/NavMesh/Sensor/Physics/Replicator/OmniGraph/Extension/Window) 의 비자명한 런타임 제약은 별도 파일:

→ **[`integration-facts.md`](integration-facts.md)** (sibling)

## ProcessModule 운영 매뉴얼

kit.exe hang / zombie / `.env` 미반영 등 운영 이슈 + stdin/stdout 규약 + 결정 트리 + 4종 함정 + standalone 경로:

→ **[`process-ops.md`](process-ops.md)** (sibling)

## 관련 경계

- **형제 CLAUDE.md**:
  - `../tools/CLAUDE.md` — MCP tool 등록 규약 + tool 그룹별 caveat
  - `../scenario/CLAUDE.md` — scenario engine + `action_registry` + context-aware dispatch
  - `../CLAUDE.md` (src/omniverse_kit_mcp/) — FastMCP 서버 패키지 루트 (entry flow · type 경계)
- **형제 pull-doc**: `integration-facts.md` (도메인 런타임 제약), `process-ops.md` (ProcessModule 운영)
- **상위**: root `CLAUDE.md` (pull-doc 인덱스 · 변경 파급 매트릭스 · Validation Rules · Key Decisions)
- **Extension 내부 규칙** (Pydantic · omni.services.core · carb.log_warn): `../../../kkr-extensions/CLAUDE.md`
- **새 MCP tool 구현 전 참조**: `../../../docs/references/CLAUDE.md` (기존 tool 중복 확인 → optional local catalog → 실제 ext 소스 / 공식 문서)
- **작업 전 필수 pull-doc**: `../../../docs/invariants/` (usd-load / process-lifecycle / mcp-tool-add / module-add / ui-invoke / scenario-validation / ext-reload)
