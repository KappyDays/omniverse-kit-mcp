<!-- Parent: CLAUDE.md -->
<!-- Scope: 도메인별 런타임 제약 — 특정 도메인 코드/시나리오 작성 시 검색용 참조 -->

# Integration Facts — REST 소비자 관점

도메인별 비자명한 런타임 제약. 모듈/서비스 코드만 읽어도 알 수 없는 것.
새 기능 추가 시 해당 도메인 sub-section 에 bullet 추가. 작업 전 필수 숙지는
`../../../docs/invariants/*.md` pull-doc 참조.

## ⚠️ Cross-cutting Hazards (이 파일을 읽을 때 항상 유효)

- **USD asset 로드**: S3 URL 필수 / `log_capture.start()` 금지 / browser ext 금지 — 상세: `../../../docs/invariants/usd-load.md`
- **NavMesh bake**: `simulation_stop` 후에만 유효 bake (R1a) — 상세: `../../../docs/invariants/scenario-validation.md`
- **Robot 동작**: `simulation_play` 상태 필수 (R2) — 상세: `../../../docs/invariants/scenario-validation.md`

## Simulation / Timeline
- **`simulation/play` 비동기 반영**: 응답 시점 `is_playing=false` 가능. 수 초 뒤 `get_status` 재확인
- **`simulation_step` advance mode**: Kit 버전별 `omni.timeline.forward_one_frame()` 존재 여부 다름 → `hasattr` 체크 후 사용, 없으면 play → N × `next_update_async()` → pause (was_playing 보존). response `advance_mode` ∈ {forward_one_frame, play_burst}

## Viewport
- **GUI 모드 필수**: `--no-window` / headless 에서 `viewport_capture` 가 빈 데이터
- **Isaac Sim 5.1 detach 호환**: `omni.replicator.core` annotator.detach 가 HydraTexture 객체에서 `AttributeError` (`_get_node_path` 문자열 가정) → `viewport_service` 가 detach 실패를 try/except 으로 감싸고 `omni.kit.viewport.utility.capture_viewport_to_file` 폴백
- **연속 capture 재캐시**: 5.1 viewport capture 는 동일 PNG 반복 가능. 프레임 변화 필요 시 사이에 `simulation.play` 삽입
- **`ViewportModule.create` idempotent**: 같은 `viewport_name` 재호출 시 `existed=True` + 기존 window 반환. `omni.kit.viewport.window.ViewportWindow` 1차 → `create_viewport_window` 폴백. `destroy` 도 idempotent (`destroyed=false` if missing)
- **`viewport_set_fov` camera candidate walk**: fresh stage 에서 `/OmniverseKit_Persp` 가 session layer 거주 → `GetPrimAtPath` IsValid=False. `ViewportRenderService._candidate_camera_paths` 가 `get_viewport_from_window_name` → Kit 내장 camera (Persp/Top/Front/Right) → `stage.Traverse()` 첫 `UsdGeom.Camera` 순서 폴백. `focalLength = (horizontalAperture/2) / tan(fov/2)` 역산
- **`viewport_toggle_overlay(overlay="axis")` user.config.json 오염 방지 경로 필수** (2026-04-21 실측): `/persistent/app/viewport/displayOptions/axis = bool` 저장 시 Kit 이 부모 키를 dict 으로 `user.config.json` 에 영속 저장 → Kit 5.1 `omni.kit.viewport.window-107.2.0/legacy.py:226` 의 `_setup_viewport_options` 는 같은 키를 **int bitmask 로 읽어** `settings & 0x1` 수행 → `TypeError: dict & int` → `ViewportWindow.__init__` 중도 실패 → `_ViewportWindow__viewport_layers` 미생성 → viewport_widgets_manager / measure tool / physx.supportui 가 **이후 모든 Kit 기동에서** 연쇄 실패. 올바른 경로: `/persistent/app/viewport/<viewport_name>/Viewport0/guide/axis/visible` (현재 `viewport_render_service._axis_key_for_viewport`). 회복: `~/AppData/Local/ov/data/Kit/Isaac-Sim Full/5.1/user.config.json` 에서 `persistent.app.viewport.displayOptions` dict 키 삭제 → 재기동 시 int bitmask 로 재저장됨

## Process / Health / Code reload
- **프로세스 종료**: `taskkill /f /im kit.exe` 는 Git Bash 에서 옵션 파싱 실패 → `cmd //c "taskkill /F /IM kit.exe /T"` 또는 `powershell.exe -NoProfile -Command "Stop-Process -Name kit -Force"` 사용
- **kit.exe 런타임 플래그**: `--ext-folder PATH` + `--enable EXT_ID` — 둘 다 있어야 Extension Manager 토글 없이 자동 활성
- **Health endpoint**: `GET http://127.0.0.1:8111/validation/v1/health` 200 응답이 ProcessModule readiness 기준
- **Code reload**: Extension 코드 수정 → `__pycache__` 삭제 → `kit_app_restart`. Manager 토글로는 반영 안 됨

## Stage / USD 로드 프로토콜 (변경 금지)
> `../../../docs/invariants/usd-load.md` 가 4 줄 요약. 이 섹션이 근본 원인 + 해결 3 요소 + 재발 진단의 상세.

- **근본 원인**: `LogCaptureService` 의 carb log callback 이 등록된 상태에서 Kit 5.1 MDL resolver 가 S3 asset 의 Materials.usd 를 열면 `"Disabling base URL to resolve MDL identifier 'OmniPBR.mdl'"` 반복 → Python callback 이 carb thread 에 GIL 경합 → Kit main event loop deadlock → 모든 MCP tool 92 s timeout
- **해결 3 요소** (baseline — 변경 시 hang 재발):
  1. Extension `on_startup` 에서 `self._log_capture = None` (NOT `get_log_capture_service().start()`) — `extension_capture_logs` / `clear_logs` MCP tool 은 현재 no-op
  2. `stage_service.load_usd` 는 `omni.kit.async_engine.run_coroutine(_main_loop_impl())` + `asyncio.wrap_future(future)` — FastAPI event loop ≠ Kit main event loop 이므로 Kit main loop 에 명시적 schedule
  3. `omni.kit.commands.execute("CreatePayloadCommand", instanceable=True, ...)` — GUI drag&drop scene_drop_delegate 와 동등 경로
- **URL 정책**: S3 필수 (`file:///` 금지). Prefix:
  - `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/...`
  - `https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/...`
  - `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/{ArchVis,DigitalTwin,Vegetation}/...`
  - SoT: `../../../docs/assets/isaac/asset_inventory.md`
- **`stage_open` vs `stage_load_usd`**: 전자는 root stage 교체 (scene 전환), 후자는 `/World/<name>` Payload 추가 (multi-asset composition)
- **실측** (2026-04-20 hang 해결 후): Simple_Warehouse 2.4 s / NovaCarter 3.1 s / Biped_Setup 2.6 s / SimReady cold 10~57 s / multi-asset composition OK
- **재발 시 진단 순서**:
  1. Kit log `C:\Users\<you>\.nvidia-omniverse\logs\Kit\Isaac-Sim Full\5.1\kit_*.log` 마지막 entry 가 `"Disabling base URL to resolve MDL identifier"` 반복 후 silent = deadlock 확정
  2. `simulation_get_status` 가 92 s timeout → Kit main loop 차단
  3. `cmd //c "taskkill /F /IM kit.exe /T"` — PowerShell `Stop-Process` 는 Access Denied 확정
  4. `.venv/Scripts/python.exe scripts/run_process_module_standalone.py start` 로 fresh restart
- **금지 사항**: `log_capture.start()` 재활성 / `file:///` 로컬 캐시 / `.env ISAAC_SIM_EXTRA_EXT_IDS` 에 `isaacsim.asset.browser` / `omni.kit.window.content_browser` 추가 / S3 load 실패 시 skip/fallback/placeholder — 모두 금지

## ASYNC Job
- **규약**: job 기반 endpoint (`/robot/navigate`, `/character/navigate`, `/robot/navigate_path`) 는 `{job_id}` 즉시 반환. 폴링: `GET /jobs/{job_id}` / 중단: `POST /jobs/{job_id}/cancel`. 상세: `../../../kkr-extensions/CLAUDE.md §"ASYNC Job pattern"`

## Robot / IK
- **R2 (timeline playing 필수)**: `navigate_to` / `navigate_path` / `get/set_joint_positions` 는 `omni.timeline.is_playing()` 필수. Extension `robot_service.navigate_path` 는 미통과 시 HTTP 400
- **`RobotModule.navigate_to`**: `xformOp:translate` linear interp over `duration_s` (60 fps). 베이스 이동 전용 — 관절/IK 는 `set_joint_positions` 사용
- **`robot_gripper_control` DOF 자동 감지**: `SingleArticulation.dof_names` 에서 `finger` / `gripper` substring. Franka 매치, UR10 불일치 → 400. `simulation_play → pause` warm-up 후 호출
- **`robot_set_ee_target` Franka 전용**: `_resolve_lula_modules()` 가 `isaacsim.robot_motion.motion_generation.lula` → `omni.isaac.motion_generation.lula` 순 시도. 비Franka robot_description 은 `load_supported_robot_motion_policy_configs` KeyError → 400. scenario 에서 `continueOnFailure: true` 로 감쌀 것

## Character / AnimGraph
> 세밀한 함정은 `CLAUDE.md §"Character domain constraints"` (sibling) 참조.

- **`character_play_animation_variant` unwired variable tolerant**: `sit_style` / `walk_style` / `run_style` 가 Biped_Setup AnimGraph 에 없어도 base Action 은 항상 set. `response.variables_set` 이 실제 적용된 key
- **`character_load_crowd` random seed 고정**: `_layout_positions("random", ...)` 는 `random.Random(0)` — 테스트 재현성. Live 에서 다른 seed 필요 시 center offset shuffle 또는 loader 상위 wrap

## Asset / Content
- **`AssetModule.list`**: `isaacsim.storage.native.get_assets_root_path()` 이 기본으로 공개 S3 반환 (Nucleus 없이 browse). `omni.client.list` 를 `asyncio.to_thread` 로 감쌈. 카테고리: `robots/environments/props/people/materials/isaaclab`
- **검증 asset 규칙 (R1)**: `RobotModule.load` / `CharacterModule.load` / `stage_load_usd` 테스트는 primitive 대용 금지. `AssetModule.list` 로 탐색 가능한 실 USD 만 사용. 상세: `../../../docs/invariants/scenario-validation.md`
- **Content 는 `omni.client` 기반**: Nucleus 외 S3 / 로컬 URL 도 동일 API. Nucleus URL 은 login token 없으면 403 → MCP 경계에서 `backend=fallback_metadata:<ErrorType>` 보고. `content_browser` / `asset.browser` Kit extension 은 **기동 시 활성화 금지** (MDL resolver hang)

## NavMesh
- **R1a (canonical 시퀀스)**: `load assets → simulation.stop → navigation.bake → navigation.query_path → simulation.play → robot.navigate_path`. `bake` 는 playing 중 호출 시 True 반환하지만 `get_navmesh()` = None (silent False Positive) — 호출자가 `simulation.stop` 명시
- **non-blocking 폴링**: `navigation_service.bake` / `_bake_if_needed` 가 `start_navmesh_baking()` + `is_navmesh_baking()` + `app.next_update_async()`. `_and_wait` 변형 절대 금지 (Kit Python 단일 스레드 점유로 HTTP 라우터 starved). `timeout_s` (기본 300 s) 상한, `elapsed_ticks` 로 진행
- **cache lock 회복**: 동일 Kit 에서 5+ 회 반복 시 `"start_navmesh_baking returned False"` 빈발. ① `stage_delete_prim("/World/NavMeshVolume")` → 재시도 ② 실패 시 Kit 재시작. 반복 bake scenario 는 fresh Kit 권장
- **visualization backend 우선순위**: `set_visualization` 이 `carb.settings /persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh` 토글 우선. 실패 시 `NavMeshVolume` prim `visibility` 폴백. response `backend` ∈ {`carb_settings`, `prim_visibility`}.
- **`add_exclude_volume(prim_path=...)`**: `stage.compute_world_bbox` 내부 호출하여 bbox 기반 Exclude 자동 배치 — chair / low prop step-up artifact 회피

## Sensor
- **공통 Camera prim 기반**: Lidar / Depth 도 `UsdGeom.Camera` + `customData.validation_api.sensor_type` tag. 실제 annotator attach 는 capture 시. `set_visualization(on|off)` 은 prim visibility 공통 토글
- **Physics sensor (Contact/IMU) Xform fallback**: `isaacsim.sensors.physics.{ContactSensor, IMUSensor}` 미활성 시 `CreatePrimWithDefaultXformCommand` → Xform 생성 + `customData.validation_api.sensor_type={contact,imu}` stamp. `response.backend` 필드가 실제 경로 (`isaacsim.sensors.physics` | `fallback_xform:<ErrorType>`)
- **`sensor_set_annotator` MCP lax / Extension strict**: MCP 는 `list[str]` 통과, Extension 이 고정 집합 {rgb, depth, semantic_segmentation, instance_segmentation, normals, motion_vectors, distance_to_camera, distance_to_image_plane} membership 검증. 미지 annotator 는 400. attach 실패는 `response.skipped[name]` 수집

## Physics / Material / Lighting
- **`UsdPhysics.CollisionAPI` 는 `rigidBodyEnabled` 의존**: `physics_apply_collider` 단독 적용 prim 은 정적 collider — 중력/힘 반응 원하면 `physics_apply_rigid_body(dynamic=True)` 추가. 첫 `physics_set_scene` 은 반드시 arrange 단계
- **`MaterialBindingAPI.DirectBinding.GetBindingStrength` 는 Kit 5.1 Python 바인딩에서 AttributeError**: `binding.GetDirectBinding().GetBindingRel()` 로 rel 획득 후 정적 `UsdShade.MaterialBindingAPI.GetMaterialBindingStrength(rel)` 호출이 정답. `MaterialService.get_bound` 가 이 패턴 — 새 Material 연산 추가 시 동일 사용

## Replicator / SDG
- **writer 는 명시적 orchestrator tick 필요**: `create_writer` 만으로는 파일 쓰지 않음. `trigger_once(num_frames=N)` 또는 `trigger_on_time(interval_s=...)` 별도 호출 필수. `simulation_play` 는 PhysX tick 만 — orchestrator 와 별개
- **`trigger_once` 버전 호환**: `rep.orchestrator.run_async` (신) 우선, 없으면 `run` (구) 폴백
- **MDL heavy asset 로드 직후 연속 trigger 시 deadlock 위험** — `log_capture` 기본 비활성 (`_log_capture = None`) 유지 필수

## OmniGraph
- **ActionGraph 는 scene event 의존**: `omni.graph.action.OnTick` / `OnLoaded` 는 `simulation_play` tick 등 scene event 없으면 비발화. Scenario 에서 결정적 실행 필요 시 `omnigraph_execute(graph_path)` 로 `graph.evaluate()` 수동 호출
- **`create_ros2_publisher` 부분 생성 가능**: `isaacsim.core.nodes.IsaacCreateRenderProduct` + `isaacsim.ros2.bridge.ROS2PublishImage` 매크로. 한쪽 ext 미활성 시 `og.Controller.edit` 이 unknown type silent skip → response `nodes_created` 길이로 실제 생성 수 확인

## Extension 관리
- **`get_info` iteration 경로 우선**: Kit 107.x 는 `get_extension_dict(bare_id)` 가 None. `get_extensions()` 순회 → `name==ext_id` 매칭 → summary 구성 → `full_id` 로 raw dict 재조회하여 dependencies / title 보강. 미등록 ext 는 KeyError → HTTP 404
- **`deactivate`**: `set_extension_enabled_immediate(id, False)` — 이미 비활성이면 `was_enabled=False` idempotent. Python 모듈 import 는 살아있음 — 재 import 필요 시 `activate(id, reload=True)` 조합

## Window / UI
- **두 도메인 분리**: `WindowModule` = Kit GUI 레벨 (`omni.ui.Window` / `omni.kit.menu.utils`), `ExtensionModule.ui_*` = widget 레벨 (`omni.kit.ui_test`). GUI 조작 시퀀스: `window_menu_trigger` → (lazy-instantiated browser 는 `ui_list` 재조회) → `extension_get_ui_tree(window=...)` → `extension_ui_invoke` → `window_capture`. 세부: `../../../kkr-extensions/CLAUDE.md §"Window capture & UI automation"`
- **headless caveat**: `get_ui_tree` / `ui_invoke` / `window_list` / `window_ui_list` / `window_capture` 는 GUI 모드에서만. `--no-window` 에서 `omni.ui` no-op. `extension_activate` / `capture_logs` 는 headless OK
- **`isaacsim.exp.full.kit` preset 은 `isaacsim.asset.browser` 미포함**: `Window > Browsers > Isaac Sim Assets` menu 는 존재하지만 창 생성 안 됨 (`menu_trigger` silent no-op). 필요 시 `ISAAC_SIM_EXTRA_EXT_IDS` 에 추가. 실제 창 title 은 `Isaac Sim Assets [Beta]` (menu label 과 상이)

## 관련 경계

- 모듈 책임 매트릭스 + Character 제약 + base.py 패턴: `CLAUDE.md` (sibling)
- ProcessModule 운영 매뉴얼: `process-ops.md` (sibling)
- USD 로드 invariants: `../../../docs/invariants/usd-load.md`
- Scenario validation (R1/R1a/R2/R3): `../../../docs/invariants/scenario-validation.md`
- Process lifecycle invariants: `../../../docs/invariants/process-lifecycle.md`
- UI automation invariants: `../../../docs/invariants/ui-invoke.md`
