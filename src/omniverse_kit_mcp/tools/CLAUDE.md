<!-- Parent: ../../../CLAUDE.md -->
<!-- Scope: MCP tool surface — FastMCP에 tool 등록 + boundary validation -->

# tools — MCP Tool Surface

FastMCP에 tool을 등록하는 얇은 레이어. 도메인 제약(LakehouseModule query-only 등)은 `modules/CLAUDE.md`, 시나리오 엔진 내부는 `scenario/CLAUDE.md` 참조.

## 파일

- `module_tools.py` — `register_module_tools(mcp, stage, viewport, lakehouse, extension, simulation, process, robot, job, asset, character)` 로 모든 module tool 등록
- `scenario_tools.py` — `register_scenario_tools(mcp, config, stage, viewport, lakehouse, extension, simulation, robot, job, asset, character)` 로 scenario tool 등록. 모든 모듈 인자 필수 — scenario YAML 의 `module: ...` 를 runner 가 dispatch 하려면 여기로 전달되어야 한다
- `__init__.py` — 둘 다 re-export

## Registration 규약

```python
@mcp.tool()
async def stage_load_usd(usd_url: str, prim_path: str, ...) -> str:
    """Docstring은 MCP tool description으로 노출된다 — 간결/구체적으로."""
    meta = make_meta(ModuleName.STAGE)
    request = {...}
    result = await simulation.stage_load_usd(meta, request)
    return _serialize(result)
```

- `@mcp.tool()` 데코레이터 — 함수명이 tool 이름
- `make_meta(ModuleName.X)` 로 `OperationMeta` 생성. module 메서드에 첫 인자로 전달
- 결과는 `_serialize(result)` 로 JSON 문자열 변환 후 return
- Docstring = MCP client UI (Claude Code, Codex CLI 등) 에 표시되는 tool 설명

## Boundary Validation

`scenario_tools.py`의 `_resolve_safe_path()` 가 scenario YAML 경로의 path traversal 방어를 담당:

- 입력 경로가 `SCENARIOS_DIR` (환경변수, 기본 `scenarios/`) 하위가 아니면 거부
- 절대경로/상위경로 참조(`..`) 로 탈출 불가
- 모든 scenario_* tool 은 YAML 경로를 받기 전 이 함수를 통과

## MCP Tools

**Source of truth**: `tests/unit/test_tools_registration.py` 의 `EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS` frozenset 이 모든 tool 집합을 명시. Phase 추가 시 이 두 frozenset 만 업데이트 → count assertion 은 `len()` 으로 자동.

그룹별 비자명한 제약 (전체 이름은 frozenset 참조):

- **Process (`isaac_sim_*` / `process_list_kit_instances`)** — Extension 없이 kit.exe lifecycle 만 제어. `process_list_kit_instances` 는 read-only enumerate — MCP-spawned 외 사용자 GUI 인스턴스 / 다른 MCP 서버까지 모두 반환 (`is_this_mcp_instance` 플래그로 구분). destructive 작업 (Kit `user.config.json` 편집 / settings reset / extension force reload) 전 외부 인스턴스 점검에 사용. Windows-only (PowerShell `Get-CimInstance`)
- **Stage READ/ASSERT (`stage_*`)** — `stage_diff_snapshots` 는 context-aware (선행 두 `stage_capture_snapshot` step id 를 받음). `stage_compute_world_bbox` 는 live USD BBoxCache 기반이고, `stage_visual_alignment_report` 는 reference/candidate bbox 의 XY IoU + center delta 로 visual/physics/acceptance volume misalignment 를 정량화
- **Stage WRITE (`stage_load_usd` / `stage_set_property` / `stage_set_semantic_label` / `stage_create_prim` / `stage_delete_prim`)** — tools layer 는 `SimulationModule` 로 라우팅 (구현 위치가 StageModule 이 아님). `stage_create_prim(prim_type=...)` 은 Cube/Sphere 뿐 아니라 Camera, UsdLux (DistantLight/DomeLight/...) 도 수용
- **Semantic label (`stage_set_semantic_label`)** — `sensor_set_annotator` 가 annotator 만 붙이고 prim 라벨링은 못 하던 hole. `UsdSemantics.LabelsAPI`(`semantics:labels:<label_type>`) + best-effort 레거시 `Semantics` schema 둘 다 author (annotator 가 어느 스키마를 읽든 잡히도록). 라벨은 subtree 로 상속 — 참조 prop 의 부모에 한 번. 미존재 prim 은 400. segmentation/bbox 픽업 동작 검증은 라이브
- **Simulation (`simulation_*`)** — `play` 응답은 비동기 반영 (is_playing=false 가능)
- **Viewport (`viewport_capture` / `viewport_compare_ssim` / `viewport_set_active_camera` / `viewport_focus_prim`)** — GUI 모드 필요. capture 는 detach failure 에 fallback 존재 (Extension CLAUDE 참조). `viewport_focus_prim` 은 GUI F-key/Frame Selected 동등 동작을 Kit viewport framing API 우선, bbox→lookat fallback 으로 수행. `viewport_frame_prims` 는 prim bbox 로 camera eye/target/up 을 계산해 camera placement 시행착오를 줄이고, `viewport_project_points` 는 world point → normalized/pixel 좌표를 반환하며, `viewport_capture_assert` 는 pixel stats 로 black/blank capture 를 빠르게 실패 처리
- **Extension — lifecycle/state (`extension_trigger` / `extension_get_state` / `extension_activate`)** — `trigger` 중복 호출 시 409 `ExtensionBusyError`. `activate(ext_id)` 는 bare ext_id 로 enable (`ExtensionManager.set_extension_enabled_immediate`), 알 수 없는 ext_id 는 HTTP 400 → `EXTENSION_ACTIVATE_ERROR`
- **Extension — UI automation + log capture (`extension_get_ui_tree` / `extension_ui_invoke` / `extension_capture_logs` / `extension_clear_logs`)** — GUI 모드 필요. `get_ui_tree` 는 window substring 매치 + `omni.kit.ui_test` widget iterate (`widget_types=` 인자로 커스텀 allow-list 지정 가능, 기본은 Button/Label/StringField/CheckBox/ComboBox/Float*/Int*/ToolButton/RadioButton/Image/Frame/HStack/VStack/CollapsableFrame/ScrollingFrame/TreeView/Menu/MenuItem/Image/ImageWithProvider/Spacer/Separator). `ui_invoke` 는 click/double_click/type/select/check/uncheck, invalid path 는 HTTP 400. `capture_logs` 는 peek (drain 아님) — 반복 호출 시 같은 range 반환. `clear_logs` 는 ring buffer 완전 비움 — "새 세션" 패턴에 사용 (`since_ms` 자체 추적이 필요 없다면 `clear_logs` 호출 후 시점부터 새로 시작)
- **Window (`window_capture` / `window_list` / `window_ui_list` / `window_ui_show` / `window_menu_list` / `window_menu_trigger`)** — Kit GUI 전체 스크린샷 + 메뉴 클릭 + `omni.ui.Window` 토글. GUI 모드 필요. `window_capture(wait_stable=True)` 는 연속 픽셀 diff 폴링으로 async loading 대기 (sha256 동일성은 FPS overlay 때문에 무용). `window_menu_trigger` 응답에 `created_prims: [...]` 차이 리스트가 포함 — 메뉴 아이템이 실제로 prim 을 만들었는지 확정 판정 (빈 배열이면 silent no-op)
- **Navigation (`navigation_bake` / `navigation_query_path` / `navigation_add_exclude_volume`)** — NavMesh 연산. `bake` 는 **timeline stopped 상태 필수** (playing 중 호출 시 `get_navmesh()` = None silent False Positive) + non-blocking 폴링 (`start_navmesh_baking()` kick + `is_navmesh_baking()` poll + `next_update_async()` yield — Kit HTTP 라우터 응답성 유지). `timeout_s` (기본 300) 로 폴링 상한. `query_path` 는 NavMesh 미베이크 시 동일 폴링 auto-bake (응답 `auto_baked: true`). `add_exclude_volume(prim_path=...)` 는 bbox 기반 Exclude 자동 배치 — chair / low prop step-up artifact 회피용
- **Lakehouse (`lakehouse_query`)** — **query only** (inject/cleanup 없음)
- **Robot (`robot_*`)** — `get/set_joint_positions` 는 articulation 없으면 HTTP 400 (silent no-op 차단). joint I/O 전 `simulation.play → pause` warm-up 필수. `robot_navigate_to` 는 ASYNC (job_id 즉시 반환). `robot_get_joint_config` 는 set_joint_positions symmetric readback — drive stiffness/damping/max_force + lower/upper limits + max_velocity per DOF. `source` 필드가 backend 보고 (`dof_properties` runtime view 또는 `usd_drive_api` 직접 read fallback). IK / drive_physics 디버그 시 사용 (drive 너무 약함 / target out-of-limit / velocity cap 진단)
- **Job (`job_status` / `job_cancel`)** — `job_status` 는 scenario 에서 context-aware (`navigate_step_id` 또는 `job_id`). Robot/Character navigate 모두 동일 polling 경로
- **Asset (`asset_list` / `asset_search`)** — `asset_list` 는 라이브: category 없으면 카테고리 목록, 있으면 S3 directory listing (Isaac 기동 필요, Franka 등 공식 URL 을 하드코드 없이 확보). `asset_search(query, category=None, limit=20)` 는 **오프라인** — `docs/assets/isaac/assets/*.md` 큐레이션 카탈로그를 MCP 서버 프로세스에서 직접 read + 랭킹 → `[{name, url, category, source_file}]` (REST / Isaac 불필요). 자연어 → 구체 USD URL (예: `asset_search("forklift")`), `AssetModule`(생성자 `catalog_dir` 주입, lazy-load + in-memory cache). 진입 워크플로 `docs/invariants/asset-discovery.md`. 마크다운 파서는 `tests/unit/test_asset_inventory_integrity.py` 포맷 규약($VAR prefix·`루트:`·상대경로)에 의존
- **File/Selection/Camera (`stage_save` / `stage_open` / `stage_new` / `stage_get_selection` / `stage_set_selection` / `viewport_set_active_camera`)** — GUI File menu + Stage panel + Viewport toolbar 동등. `stage_open` 은 https:// (Asset Browser URL) 도 수용, `stage_set_selection(expand_in_stage=True)` 로 tree 자동 확장
- **Character (`character_*`)** —
  - `character_load` 는 `/World/Characters/<sanitized_name>` 아래 배치. Biped_Setup rig 자동 로드. response 의 `sanitized_prim_path` 가 실제 USD 배치 경로 (caller 의 `prim_path` 는 echo — 후속 호출은 반드시 sanitized 기준)
  - `character_play_animation.animation_name` 은 Extension Pydantic Literal `"Idle"|"Walk"|"Run"|"Sit"` — 그 외 값 422
  - `character_set_position` 은 USD write 성공 + AnimGraph override (시각 이동 X) — `character_navigate_to` 사용 또는 load 시 `position` 지정
  - `character_navigate_to` 는 ASYNC + timeline playing 필수 (`simulation.stop/pause` 시 0m 이동 후 30s timeout)
  - `character_get_state` 는 Extension 응답 필드 누락 시 `KeyError` (silent fake Idle 방지). `action` 필드는 서버-side 캐시 기반 (AnimGraph readback 은 `"[]"` 로 내려옴)
- **Scenario (`scenario_*`)** — `scenario_validate` / `scenario_plan` / `scenario_list` / `scenario_schema` / `scenario_last_report`. 경로는 `_resolve_safe_path()` 로 SCENARIOS_DIR 경계 강제
- **Robot 심화 (`robot_navigate_path` / `robot_gripper_control` / `robot_set_ee_target` / `robot_get_ee_pose` / `robot_run_franka_pick_place`)** — `navigate_path` 는 ASYNC (`job_id` + `num_waypoints` + `duration_s` 반환, Extension 에서 timeline playing 미통과 시 400 — scenarios/smoke/robot_navigate_path.yaml 참조). `gripper_control` action ∈ {open, close, set}; `set` 은 `target` 필수 (없으면 400). `set_ee_target` 은 Franka 전용 skip-candidate — non-Franka robot_description / Lula module 미import 는 400 명시적 메시지와 함께 실패 → scenarios 에서 `continueOnFailure: true` 로 감싸서 robust run. `robot_get_ee_pose` 는 현재 EE link 의 USD world transform readback — IK solve 가 아니라 controller/ScriptNode 가 실제로 손을 어디까지 움직였는지 확인하는 telemetry tool. `robot_run_franka_pick_place` 는 Isaac Sim 공식 Franka PickPlaceController/RMPflow/ParallelGripper 경로이며 kinematic carry 를 사용하지 않는다; 성공은 controller done + object bbox lift + final distance 로 판정하고, 물체가 그리퍼로 실제 이동하지 않으면 `ROBOT_FRANKA_PICK_PLACE_FAILED` 로 실패시킨다. 공식 controller 의 기본 hover height 는 절대 world Z=0.3 이므로 table-top 객체는 wrapper 가 pick/place z 위로 자동 보정하고 `end_effector_initial_height_source` 로 보고한다; bbox center 가 grasp point 가 아니면 `picking_position` / `end_effector_orientation` 을 명시한다.
- **Character 심화 (`character_play_animation_variant` / `character_load_crowd`)** — `play_animation_variant` 는 variant prefix 로 base Action 결정 (Sit/Walk/Run/Idle) + 스타일 변수 매핑. style variable 은 AnimGraph 에 없어도 silent no-op → response.variables_set 에서 실제 set 된 key 확인. `load_crowd` 는 count 1-100, layout ∈ {grid, line, random}. 개별 character load 실패는 `loaded[].error` 로 수집하고 batch 계속 — success_count 확인 필수.
- **Sensor 심화 (`sensor_attach_contact` / `sensor_attach_imu` / `sensor_set_annotator` / `sensor_lidar_get_point_cloud`)** — contact / imu 는 `isaacsim.sensors.physics` 모듈 부재 시 Xform prim fallback (`backend` 필드가 실제 경로 보고). `set_annotator` 는 annotator 이름 고정 membership — unknown 은 400. 개별 annotator attach 실패는 `skipped` dict 에 수집. `lidar_get_point_cloud` 는 `sensor_attach_rtx_lidar` symmetric readback — sensor 의 `customData.validation_api.annotator` 를 재사용하여 render product + AnnotatorRegistry attach + N tick 대기 + `get_data()` 파싱. 두 shape 지원: structured numpy (`x/y/z/intensity` fields) 또는 polar (`azimuth/elevation/distance` → Cartesian 변환). 비-rtx_lidar prim 은 400, simulation.play 전 호출 시 `num_points=0` + `warning` (silent 빈 cloud 방지). `truncated` 플래그로 `max_points` 컷 표시. `backend` 필드가 `fallback_noop:<exc>` 면 `omni.replicator.core` import 실패. scenarios/smoke/sensor_{contact,imu,annotator_config}.yaml 참조.
- **Physics readback (`physics_get_rigid_body_state`)** — `apply_rigid_body` symmetric readback. `source` 필드가 backend 보고: `physx_runtime` 은 SingleRigidPrim live readout (simulation.play 가 최소 1 tick 후에야 정확), `usd_initial` 은 USD authored 값 (pre-play velocity 반영, mass/COM 은 항상 정확). RigidBodyAPI 미적용 prim 은 HTTP 400. `is_kinematic` / `is_enabled` 는 USD 직접 read 라 항상 정확.
- **Joint drive (`physics_set_joint_drive`)** — `physics_create_joint` 가 joint 만 만들고 actuation 수단이 없던 hole 을 메움. 기존 joint prim 에 `UsdPhysics.DriveAPI(drive_type)` 적용 (`angular`=Revolute / `linear`=Prismatic) + target/velocity/stiffness/damping/max_force. 미존재 joint prim 은 400. `max_force=None` 은 PhysX default(무한) 유지 — 0 으로 보내면 drive 가 힘을 못 냄에 주의. 실제 구동은 RigidBodyAPI + `physics_set_scene` + `simulation_play` 필요 (동작 검증은 라이브).
- **Simulation 심화 (`simulation_step` / `simulation_step_observe` / `simulation_wait_until` / `simulation_set_time`)** — `step(frames)` 은 `forward_one_frame()` 우선, 없으면 play burst 로 fallback (`advance_mode` 필드로 확인). `step_observe` 는 step 직후 prim world pose / articulation joints / EE pose 를 같은 tick 기준으로 모아 반환 — ScriptNode controller 디버그 시 sleep+개별 poll skew 를 줄임. `set_time` 은 즉시 seek — 현재 play state 유지. `wait_until(until_time, timeout_s)` 은 `next_update_async` 로 매 틱 양보하며 current_time 도달까지 대기 (deadlock-safe, sleep+poll 대체) — **timeline PLAYING 필수** (아니면 `timed_out=true`). 응답 `reached`/`timed_out`/`elapsed_s`/`frames_waited`.
- **Replicator (`replicator_create_writer` / `replicator_register_randomizer` / `replicator_trigger_once` / `replicator_trigger_on_time`)** — writer_type ∈ {BasicWriter, KittiWriter, CocoWriter}. `trigger_once` 는 `rep.orchestrator.run_async(num_frames=N)` 우선 + sync `run` 폴백. `trigger_on_time` 은 `rep.trigger.on_time(interval_s)` wrap 으로 Kit 이 스케줄. Timeline play 만으로는 writer 가 flush 하지 않음 — **반드시 trigger_once 또는 on_time 호출**. randomizer type ∈ {position, rotation, lighting}, target 은 glob pattern, config 는 type 별 스펙 (position={volume}, rotation={min_rot,max_rot}, lighting={min_int,max_int}). `omni.replicator.core` extension 미활성 시 backend=`fallback_noop:<ErrorType>` / `fallback_metadata:<ErrorType>`.
- **OmniGraph (`omnigraph_create_node` / `omnigraph_connect` / `omnigraph_execute` / `omnigraph_create_ros2_publisher` / `omnigraph_create_script_controller`)** — `create_node` 은 graph 없으면 자동 생성 (execution evaluator), `graph_existed` 필드로 pre-existence 판정. `execute` 는 `graph.evaluate()` 수동 tick — ActionGraph 가 scene event 대기 중일 때 결정적 실행용. `create_ros2_publisher` 는 OnTick + IsaacCreateRenderProduct + ROS2PublishImage macro; rclpy 없이도 graph 구조는 생성 (response `ros2_available=false`, `nodes_created`/`edges_created` 는 그대로 반환 → skip 시그널을 scenario 가 소비). `create_script_controller` 는 OnPlaybackTick→ScriptNode wiring + `scriptPath` set + best-effort ScriptNode cache reset 을 한 번에 수행 — MCP 는 장면/그래프를 만들고, 실제 Franka pick-place state machine 은 Kit tick 내부에서 돌리는 패턴에 사용. `omni.graph.action` + `isaacsim.ros2.bridge` 중 하나가 미활성이면 unknown type 은 silent drop → `nodes_created` 길이로 실제 생성 개수 확인.
- **Content (`content_browse` / `content_preview` / `content_inspect` / `content_resolve`)** — `omni.client` 의 `list` / `stat` / `normalize_url` 을 asyncio.to_thread 로 비동기화. 엔트리 shape: `{url, name, is_folder, size, modified_time_ns, flags}` (flags & 1<<4 이 folder bit). Nucleus URL 에 login token 이 없으면 backend=`fallback_metadata:ClientLibraryError` 로 보고 (raise 안 함). S3 / https / file:/// 는 token 없이 read-only. `omni.kit.window.content_browser` Kit extension 은 활성화 불필요 — `omni.client` 는 Kit core.
- **Content geometry (`content_inspect`)** — `content_preview` 는 파일 메타(size/mtime)만; `content_inspect` 는 `Usd.Stage.Open` 을 **worker thread(asyncio.to_thread)** 로 열어 default_prim / world bbox(min,max) / meters_per_unit / up_axis / prim_count 반환 (main loop 비차단 — deadlock-safe, 컨텍스트 stage 와 독립). 못 여는 URL 은 `ok=false` + `backend=fallback:*`. bbox 는 best-effort (실패해도 메타는 반환). 실 해석은 Omniverse/HTTP resolver 필요 → 값 산출은 라이브.
- **Kit Python runner (`kit_python_run`)** — Kit main thread 에서 임의 Python 소스 실행. Kit command registry 가 cover 못 하는 작업 (USD relationship 편집, `Usd.EditContext` 워크, `omni.client` 직접 호출 등) 을 GUI Script Editor paste 없이 호출. response 는 `{ok, stdout, stderr, error, traceback, returned}` — 스크립트 예외도 throw 안 하고 payload 로 반환 (caller 가 `ok` 검사). REST 경로 `/commands/python_run` + service method `python_run` — function/path 명에서 `exec` literal 뒤 open-paren 패턴 회피 (보안 hook 가 substring 검사). `return_keys` 로 namespace 변수 캡처. user 코드는 **localhost trusted** 가정 — sandbox 없음.
- **Catalog (`extension_search`)** — optional local generated `docs/references/extensions.json` 쿼리. Public clone 에는 catalog 를 commit 하지 않으므로 파일이 없으면 `EXTENSION_CATALOG_UNAVAILABLE` 반환. REST / Isaac Sim 프로세스 의존 없음. `keyword` 는 name/title/summary/mcp_research_hint/raw_description/keywords 를 substring 매칭, `app` 은 isaacsim/usd_composer 필터, `category` 는 exact match (case-insensitive). 결과는 {name, title, summary, category, apps, key_symbols, mcp_research_hint} per entry.
- **Extension 관리 심화 (`extension_deactivate` / `extension_list_all` / `extension_get_info`)** — `deactivate` 는 `set_extension_enabled_immediate(ext_id, False)` idempotent (이미 비활성이면 `was_enabled=False`). `list_all(enabled_only=False)` 는 Kit 표준 621 ext 전부 enumerate + `{id, full_id, name, version, enabled, path, title}` summary. `get_info(ext_id)` 는 iteration + bare id 매칭 (Kit 107 은 bare dict 에 None 반환) — 미등록 ext 는 404. **Python 모듈 reimport 는 omni.ext.plugin (C++) fswatcher 가 자동 처리** (kit log: `FS Change triggers reloading: <path>` → `Processing ext disable request → on_shutdown → enable → on_startup`). `activate(reload=True)` 는 toggle 만 — sys.modules cache 정리 안 됨. 결론(2026-05-26 갱신): 신뢰할 `.py` reimport 는 **`extension_reload(ext_id)`** (sys.modules purge); fswatcher 자동 reload 는 `_reload_enabled=False` 라 미신뢰. `extension.toml [dependencies]` / native dll / validation_api 자기자신 변경만 Kit restart. ⚠️ reload 시 `ui.Window` zombie 1개 잔존 — `on_shutdown` 표준 cleanup 필수 (`kkr-extensions/docs/lessons-learned.md` L9 정정 + L16 참조).

## 관련 경계

- **형제 CLAUDE.md**:
  - `../modules/CLAUDE.md` — 모듈별 책임 매트릭스 + Character 제약 + base.py 패턴
  - `../modules/integration-facts.md` — 15 도메인 런타임 함정 (비자명)
  - `../scenario/CLAUDE.md` — scenario engine (state_machine · action_registry · context-aware dispatch)
  - `../CLAUDE.md` (src/omniverse_kit_mcp/) — FastMCP 패키지 루트 · type 경계
- **상위**: root `CLAUDE.md` (Foundation · 변경 파급 매트릭스 · Validation Rules)
- **Extension REST endpoint 시그니처**: `../../../kkr-extensions/CLAUDE.md` (`rest_router.py` SoT + 도메인별 비자명 포인트)
- **tool 이름 SoT**: `../../../tests/unit/test_tools_registration.py` frozenset
- **resource 추가**: `../mcp/resources.py` + `../../../tests/unit/test_resources_paths.py`
- tool 등록 검증: `../../../tests/unit/test_tools_registration.py`
