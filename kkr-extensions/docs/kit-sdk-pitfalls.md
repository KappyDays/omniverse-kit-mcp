<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Isaac Sim / Kit SDK 실측 기반 함정 모음 — 5.1 historical + 6.0 current deltas -->

# Kit SDK 함정 모음

Isaac Sim / Kit 환경에서 실제 마주친 함정들. 5.1 / Kit 107 historical 항목은 보존하고, 6.0 / Kit 110 기준으로 결론이 바뀐 항목은 본문에 current delta 를 명시한다. 새 Extension 이 해당 도메인 API 를 건드릴 때 여기부터 검색.

---

## Stage / USD 로드

### Viewport capture — `omni.syntheticdata._get_node_path` AttributeError

Isaac Sim 5.1 의 `omni.syntheticdata._get_node_path` 가 `render_product` (HydraTexture) 를 문자열로 간주하고 `.split()` 을 호출해 `AttributeError`. 단, 에러는 `rgb_annot.get_data()` **이후** `detach([rp])` 내부에서 발생하므로 데이터 자체는 확보된 상태.

구현 규약:
1. `get_data()` 결과는 별도 보관
2. `detach([rp])` 는 `try/except Exception` 으로 감싸 비치명 처리
3. data 가 None/empty 이면 `capture_viewport_to_file` 폴백 (PNG 저장 후 읽기)

### `CreatePrimWithDefaultXformCommand` 후 xformOps 존재

이 명령으로 만든 prim 은 이미 `xformOp:translate / rotate / scale` 가 추가된 상태 → `AddTranslateOp()` 다시 부르면 중복. `prim.GetAttribute("xformOp:translate").Set(...)` 사용.

### UsdLux intensity 는 `inputs:intensity`

`stage_create_prim(prim_type="DistantLight"|"DomeLight"|...)` 로 만든 UsdLux prim 의 강도는 **`inputs:intensity`** (USD 2023+ schema). `intensity` 로 호출하면 `"Attribute 'intensity' not found"`. 색상 `inputs:color`, 온도 `inputs:colorTemperature` 등 `inputs:*` prefix 동일.

### Plane prim 함정 — 시각 vs Physics

`stage_create_prim(prim_type="Plane")` 은 UsdGeomPlane (**시각 plane only, collision 없음**) → robot / character 가 `simulation_play` 시 plane 을 통과해 자유낙하. Physics 가 필요한 지면은 `window_menu_trigger("Create/Physics/Ground Plane")` 호출 — `CollisionPlane + CollisionMesh + PhysicsCollisionAPI` 3-prim 자동 생성 (`omni.physxui` action).

### S3 MDL-heavy asset 로드 deadlock

별도 문서 참조 → `usd-load-deadlock-recipe.md`.

---

## Articulation / Robot

### Isaac Sim 5.1 은 `SingleArticulation.initialize()` 필수

4.x 기준 "initialize 없이 set/get OK" 는 5.1 에서 더 이상 적용 안 됨. 초기화 없이 joint I/O 시 `NoneType.link_names` 내부 에러. 호출자가 articulation 진입 시 순차 적용:

1. `_assert_articulation(prim_path)` — prim 유효성 + PhysxArticulationAPI/Root 를 `Usd.PrimRange` 로 재귀 탐색. 없으면 `ValueError` → HTTP 400 (silent no-op 차단)
2. `_ensure_initialized(art)` — `SingleArticulation.initialize()` 자동 호출. idempotent 이므로 중복 호출 안전

PhysX 가 articulation view 를 populate 하려면 **최소 1 physics step** 이 돌아야 하므로 scenario 는 `simulation_play → pause` 를 arrange 에 배치해 warm-up. 없으면 `_ensure_initialized` 도 실패 가능 → `continueOnFailure: true` 로 감쌀 것.

### Gripper DOF 자동 감지

`SingleArticulation.dof_names` 에서 `finger` / `gripper` substring 매칭으로 자동 감지. `action ∈ {open, close, set}`; open/close 는 `get_dof_limits()` → `dof_properties` 순서로 limits 읽고 Franka-default 0.04 / 0.0 fallback.

### Lula IK — 모듈 경로 두 가지

`_resolve_lula_modules()` 가 `isaacsim.robot_motion.motion_generation.lula` 와 `omni.isaac.motion_generation.lula` 중 importable 경로 선택, 실패 시 `ValueError → 400`. Isaac Sim 5.1 은 `load_supported_motion_policy_config(robot_description, "RMPflow")` 로 URDF/robot_description path 를 획득한다. 구버전 호환 fallback 으로 `load_supported_robot_motion_policy_configs(...)` 도 유지한다.

---

## Character / AnimGraph

### SkelRoot 사전 검증 + AnimGraph ready retry

Character 관련 API (`play_animation`, `navigate`, `set_position`, `get_state`) 진입 시 순차 적용:

1. `_assert_skel_root(prim_path)` — prim 유효성 + `UsdSkel.Root` 재귀 탐색. 없으면 HTTP 400
2. `_ensure_animation_ready(prim_path)` — `omni.anim.graph.core.get_character(prim_path)` 가 None 이면 (graph registry populate 지연) 1-frame `simulation_play → pause` warm-up 후 재시도. 여전히 None 이면 HTTP 500

`ApplyAnimationGraphAPICommand` 실행 직후에는 아직 AnimGraph registry 에 populate 안 됨 — scenario arrange 에 `simulation.play → pause` 명시 권장.

### Shutdown hang 방지

`kit_app_stop` 이전에 `simulation.play → step → stop` (최종 physics tick) 이 없으면 AnimGraph / NavMesh 내부 핸들 정리 타이밍 문제로 kit.exe 셔다운 hang. scenario cleanup 에 반드시 포함.

### USD prim 이름 `_sanitize_prim_name` 필수

USD prim 이름 규칙은 **`[A-Za-z0-9_]`** 만. 하이픈 / 점 / 공백 / leading digit 이 들어가면 `Sdf.Path` / `CreatePrimCommand` 가 `"... is not a valid path"` HTTP 400. 대표 케이스: DH_Characters_Extended UUID `02c80685-06e3-11ef-ae8a-f4b30194174e` → `c_02c80685_06e3_11ef_ae8a_f4b30194174e`.

응답에 `prim_path` (caller echo) + `sanitized_prim_path` (실제 USD 배치 경로) 양쪽 반환 — 후속 호출은 **반드시 `sanitized_prim_path` 기준**.

### play_animation_variant 의 variable split

`_parse_variant(variant)` 가 prefix (Sit/Walk/Run/Idle) 로 split. `SitReading` → base=`Sit`, style_var=`sit_style`, style_value=`reading`. base 는 `graph.set_variable("Action", base)` 로 무조건 set, style_var 는 try/except 로 silent no-op (AnimGraph 에 variable 없으면 Kit 내부 조용히 실패). `response.variables_set` 이 실제 적용된 key 리스트.

---

## NavMesh

### Bake 는 timeline stopped 필수

playing 중 호출 시 `start_navmesh_baking_and_wait()` 가 True 를 반환해도 **`get_navmesh()` 는 None / 빈 mesh** (False Positive). `stage/load_usd`, `robot/load`, `stage/create_prim`, `stage/set_property`, `viewport/capture(settle_frames)`, `window/capture` 는 모두 timeline 을 advance / 재생시킬 수 있으므로 bake 직전에 `simulation/stop` 을 한 번 더 명시. service 내부엔 precondition 체크 없음 — 호출자 책임.

### 표준 시퀀스

`load assets → setup cameras → stop → bake → query_path → play → navigate_path`.

### NavMeshVolume 자동 생성

`navigation_bake` 는 Stage 에 `NavMeshVolume` prim 이 하나도 없으면 `CreateNavMeshVolumeCommand(volume_type=0, scale=40m)` 로 Include 볼륨 자동 생성 후 `start_navmesh_baking_and_wait()`. 기존 볼륨이 있으면 재사용. 응답에 `agent_max_radius` / `area_count` / `mesh_signature` 포함 — **None 이면 bake 실패**.

### Step-up caveat (chair walkable 오판)

기본 NavMesh 는 chair / low prop 을 walkable 로 판정 가능 (agent_max_step_height ≈ seat height). 캐릭터가 의자 위에 올라선 채 Sit 재생되는 artifact 발생.

회피:
- (a) `navigation/add_exclude_volume?prim_path=<chair>` 로 bbox 기반 Exclude 자동 배치
- (b) NavMesh agent_max_step_height 를 chair seat 이하로 낮춤

### set_visualization backend

`carb.settings.get_settings().set("/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh", mode=="walkable")` + obstacles 키 토글. 실패 시 `NavMeshVolume` prim 의 `visibility` 토글로 폴백. Response `backend: "carb_settings"|"prim_visibility"` 로 어느 경로가 이겼는지 보고.

---

## Sensor

### Sensor 종류별 stamp 패턴

`services/sensor_service.py` 가 `CreatePrimWithDefaultXformCommand(prim_type="Camera")` 로 부모 robot 아래 Camera prim 생성 + `mount_offset` / `mount_rotation` 을 xformOp 로 설정. 센서 종류는 `customData.validation_api.sensor_type` ∈ {rtx_camera, rtx_lidar, rtx_depth_camera} 로 stamp — `set_visualization` 이 재방문 시 이 태그만 읽어 dispatch.

- **RTX Camera**: UsdGeom.Camera + `horizontalAperture=20.955`, `focalLength=24.0` 기본
- **RTX Lidar**: Camera prim 기반 + `config_preset` (`Example_Rotary` 등) + `annotator: "RtxSensorCpuIsaacCreateRTXLidarScanBuffer"` customData 기록. 실제 Lidar 데이터 획득은 `isaacsim.sensors.rtx` extension 활성 + capture 시점에 annotator attach 필요
- **RTX Depth Camera**: Camera prim + `annotator: "distance_to_camera"` metadata. viewport capture 가 depth annotator 를 attach 해 grayscale distance map 생성

### Contact / IMU 는 fallback 패턴

`from isaacsim.sensors.physics import ContactSensor` 시도 → 성공 시 ContactSensor 생성자 호출 (prim 자동 생성). ImportError / RuntimeError 시 `CreatePrimWithDefaultXformCommand(prim_type="Xform")` 로 fallback + `xformOp:translate` 설정. customData 에 `backend` (성공 경로 or `fallback_xform:<ErrorType>`) stamp.

IMU `mount_orientation` 은 `[qw, qx, qy, qz]` **scalar-first** quaternion, `numpy.array` 로 변환 후 `IMUSensor(..., orientation=np.array(quat))` 전달.

---

## Replicator / Writers

### BasicWriter channel kwargs

`rep.WriterRegistry.get("BasicWriter")` + `writer.initialize(output_dir=..., rgb=True, distance_to_camera=True, semantic_segmentation=...)`. writer 인스턴스는 service 내부 dict (`self._writers[writer_id]`) 에 보관 — 세션 lifetime. output_dir 은 `os.makedirs(exist_ok=True)` 자동 생성.

> ⚠️ validation_api REST 의 `depth` kwarg 는 내부에서 `distance_to_camera=True` 로 매핑됨. REST 레벨에서는 `depth` 사용, `rep.WriterRegistry` 레벨에서는 `distance_to_camera`.

### Orchestrator trigger

- `trigger_once`: `rep.orchestrator.run_async(num_frames=N)` 우선, 미구현 Kit build 에서는 sync `run(num_frames=N)` 폴백
- `trigger_on_time`: `with rep.trigger.on_time(interval=s)` wrap. interval < simulation tick (0.016 s) 시 큐 buildup 경고
- Timeline play 만으로는 writer 가 flush 하지 않음 — **명시 trigger 필수**

---

## OmniGraph

### ActionGraph 생성 + 재사용

`og.get_graph_by_path(graph_path)` 확인 후 없으면 `og.Controller.edit({"graph_path": ..., "evaluator_name": "execution"}, {})` 로 ActionGraph 생성. 있으면 재사용 + `graph_existed=True`.

Node 생성은 `og.Controller.edit(graph, {Keys.CREATE_NODES: [(name, type)]})`. 속성 경로: `/GraphPath/NodeName.outputs:<attr>` → `/GraphPath/NodeName.inputs:<attr>`.

### ROS2 publisher 구성

OnTick + `isaacsim.core.nodes.IsaacCreateRenderProduct` + `isaacsim.ros2.bridge.ROS2PublishImage` 3 개 노드 + 3 개 connection. `rclpy` import 시도로 `ros2_available` 판정. 두 extension 이 미활성이면 unknown node type 은 `og.Controller.edit` 이 silent skip → response `nodes_created` 길이로 실제 생성 수 확인. **ROS2 런타임 없이도 graph 구조는 생성됨**.

### graph.evaluate() 수동 실행

ActionGraph 가 scene event 대기 중일 때 결정적으로 한 번 실행시킴. 미존재 graph 는 `ValueError → 400`.

---

## Viewport / Window capture

### Viewport-owned overlay UI — `Frame` 아래 단일 root 필수

`viewport_window.get_frame(name)` 으로 만든 viewport overlay frame 에 `ui.Placer` / `ui.Button` /
`ui.Image` 를 여러 개 직접 추가하면 Kit build 에 따라 마지막 child 만 보이는 증상이 발생한다.
실측 증상: Button A/B 를 둘 다 생성했는데 마지막에 그린 Button B 만 viewport 에 표시됨.

안전 패턴:
1. `with frame:` 바로 아래에는 단일 root container 만 둔다. 보통 `ui.ZStack(width=ui.Fraction(1), height=ui.Fraction(1))`.
2. 여러 absolute-position widget 은 그 root `ZStack` 안에서 `ui.Placer(offset_x=..., offset_y=...)` 로 배치한다.
3. state 전환(Button HUD → Preview → Detail → Back) 때는 `frame.clear()` 후 새 root `ZStack` 을 다시 만든다.

### `omni.ui.Button` 은 context manager 가 아님

Kit 107 / USD Composer 계열에서 `ui.Button` 인스턴스는 `with button:` 패턴을 지원하지 않는다.
이미지를 버튼 안에 child 로 넣으려고 `with ui.Button(...): ui.Image(...)` 또는 `with button:` 을 쓰면
`TypeError("'omni.ui._ui.Button' object does not support the context manager protocol")`.

이미지 tile 을 클릭 가능하게 만들 때의 안전 패턴:
1. `ui.ZStack(width=..., height=...)` 를 만든다.
2. 배경 `ui.Rectangle` + `ui.Image(..., width=ui.Pixel(w), height=ui.Pixel(h))` 를 배치한다.
3. 맨 위에 투명 `ui.Rectangle(opaque_for_mouse_events=True, style={"background_color": 0x00000000})` 를 올린다.
4. 투명 rect 에 `set_mouse_pressed_fn` 또는 `set_mouse_released_fn` 을 연결한다.

### Viewport overlay 버튼은 `content_clipping=True` + `ui.Button`

Viewport 위에 뜨는 버튼이 Stage prim 선택을 막아야 하면 `ui.Button` 을 실제 event target 으로 두고,
그 주변을 `ui.ZStack(..., content_clipping=True)` 같은 Stack container 로 감싼다.
NVIDIA No-Code UI 문서도 Viewport UI 가 기본적으로 Prim 선택을 막지 않으며, Stack 의 content clipping 을
켜야 mouse click 을 consume 한다고 설명한다.

주의:
1. `ui.Rectangle + ui.Label + 투명 ui.Rectangle(mouse callback)` 합성 버튼은 클릭 callback 은 실행될 수 있지만,
   Viewport selection 까지 안정적으로 차단하지 못하고 hover style 도 잃기 쉽다.
2. 버튼 스타일은 parent stack 에 style dict 를 주고 `Button`, `Button:hovered`, `Button:pressed`,
   `Button.Label` selector 를 사용한다. `Button.Label` 이 text color / font size 를 제어하는 공식 selector 다.
3. 이미지 preview tile 처럼 Button child 가 필요 없는 영역은 위의 투명 Rectangle hit layer 패턴을 계속 사용해도 된다.
   실제 HUD 버튼과 preview tile 의 event 패턴을 섞지 않는다.

### 색상 변경 UI 는 `ColorWidget` 사용

Extension panel 에서 사용자가 색상이나 투명도를 바꾸는 설정은 항상 `omni.ui.ColorWidget(r, g, b, a)` 로 노출한다.
`StringField("RRGGBB")` + `IntDrag(alpha)` 조합은 입력 오류, commit timing, 색상 preview 부재 때문에 운영 UI 로 쓰지 않는다.

안전 패턴:
1. 내부 저장값은 기존 Kit style 과 맞춰 ABGR int 로 유지해도 된다.
2. panel build/sync 시 ABGR int 를 RGBA float `(0.0..1.0)` 로 변환해 `ColorWidget` child model 에 넣는다.
3. `ColorWidget.model.add_end_edit_fn(...)` 에서 child model 의 `r,g,b,a` 값을 읽어 다시 ABGR int 로 pack 한다.
4. Button/Hover/Text/Panel/Overlay/Border 등 여러 색상도 같은 helper 를 공유한다.

### Viewport point picking 은 `request_query` 단독 의존 금지

`ViewportAPI.request_query(pixel, callback)` 은 async callback 이며, 좌표계/전달 timing 이 Kit app/build 별로 다를 수 있다.
매 프레임 새 query 를 보내며 이전 callback 을 generation 으로 무효화하면 callback 이 도착하기 전에 stale 처리되어
hover highlight / description overlay 가 전혀 뜨지 않을 수 있다.

Top-view 처럼 고정 camera 가 정해진 모드에서는 fallback 을 함께 둔다:
1. viewport-local pixel `(x, y)` 를 camera projection 기준 NDC 로 변환한다.
2. USD camera prim 의 world transform 으로 ray(origin, direction)를 직접 만든다.
3. whitelist prim 에 대해 PhysX raycast → USD BBox raycast 순서로 hit 를 구한다.
4. `request_query` 는 best-effort fast path 로 두고, 직접 camera-ray path 를 deterministic fallback 으로 둔다.

### Multi-viewport 생성

`omni.ui.Workspace.get_window(name)` 으로 동명 창 존재 확인 → `existed=true` 이면 재사용. 존재하지 않으면 `omni.kit.viewport.window.ViewportWindow(name, width, height)` 시도, 실패 시 `omni.kit.viewport.utility.create_viewport_window` 폴백. 3 tick `next_update_async` 대기로 첫 프레임 settle. destroy 는 idempotent (존재 안 해도 200 응답).

### Window capture 전략

- 대상 윈도우: `kernel32.GetCurrentProcessId()` + `user32.EnumWindows` 로 가장 큰 visible top-level (Kit 메인은 class `GLFW30`, title 에 "Isaac Sim" / "Omniverse" / "Kit" 포함)
- 캡처: `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=0x2)` → 실패 시 `PrintWindow(.., 0)` → 최종 `BitBlt` 폴백. DWM / RTX 합성 윈도우는 반드시 **0x2 플래그** 필요 (검은 화면 방지)
- 순수 `ctypes` + PIL 로만 구현 (pywin32/mss 미의존)

### wait_stable 모드 — async UI 로딩 대기

`wait_stable=true` 를 주면 `stable_interval_s` 간격으로 재캡처하며 **연속 L1 픽셀 diff** (128×128 grayscale 다운샘플, 0-1 스케일) 가 `stable_diff_threshold` (기본 0.01) 미만을 `stable_consecutive` 회 (기본 2) 넘으면 반환. `sha256` 비교는 **사용 불가** (FPS 오버레이 / Timeline cursor 가 매 프레임 픽셀 바꿈). `stable_max_wait_s` (기본 45 s) 초과 시 `stabilized: false` + 마지막 capture 반환.

---

## UI Window / Menu Introspection

### omni.kit.ui_test 사용법

- `omni.kit.ui_test.find/find_all()` 은 **sync**, `WidgetRef.click/double_click/input()` 은 **async**
- Path grammar 는 typed: `"Win Title//Frame/**/Button[*]"` 처럼 widget class 를 명시해야 매치. `**/*` 는 `*` 가 인덱스 wildcard 로만 해석되어 0 매치
- `ui_invoke(action=type)` 는 `WidgetRef.input(text, clear_before_input=True)` + `end_key=ENTER`. Omni ui `StringField` 는 Enter 로 commit — 생략 시 model 에 값 미반영. 타이핑 후 `app.next_update_async()` 4 프레임 돌려 post-state 읽기

### Menu introspection

- Kit 2.x 에는 `get_menu_dict()` **없음**. `omni.kit.menu.utils.get_merged_menus()` 만 사용
- 반환은 **flat dict**. 키는 `_` 구분자 hierarchy — 예: `"Window_Browsers"` ↔ `Window > Browsers` submenu. 중첩 구조 아님
- 값은 `{items: [MenuItemDescription], action_prefix: str, sub_menu: ..., delegate: ...}` wrapper dict — `items` 키 안에 실제 리프 아이템 리스트. `top_items` 를 list 로 간주하면 0 개 잘못 집계
- 메뉴 아이템 trigger 는 `omni.kit.actions.core.execute_action(ext_id, action_id)` — 실제 클릭 경로와 동일. `onclick_action` tuple 이 없으면 `(action_prefix, item_name)` 관례로 synthesize 가능하나 등록된 action 과 실제로 매칭 안 될 수 있음 → trigger 성공 응답만으로 판단 금지

### Browser 창 lazy instantiation

- `Workspace.get_window(name)` 은 **exact title match** 만. Browser 창의 `[Beta]` / `[Experimental]` suffix 가 menu label 과 항상 일치하지 않음 → case-insensitive substring scan 으로 fallback
- Browser 류 창은 **lazy-instantiated** — 첫 `show_window` 호출 전까지 `get_windows()` 에 등록 안 됨. 전체 Browser 집합 자동 순회 시: `menu_list(Window/Browsers)` → 각 항목 `menu_trigger` → `ui_list` 재조회 순서 필수
- Browser 썸네일 로딩은 **extension 별 상이** — `isaacsim.asset.browser` (`Isaac Sim Assets [Beta]`) 는 첫 open 시 NVIDIA 공개 S3 를 실시간 crawl. 즉시 capture 시 빈 그리드. `omni.kit.browser.asset` / `omni.simready.explorer` 는 cached catalog 포함 → 즉시 populate. S3-crawl 은 show 후 10~30 s settle 필요

### Browser / content browser 는 deadlock root cause 가 아님

과거 `isaacsim.asset.browser` / `omni.kit.window.content_browser` 금지 가설은 2026-04-25 자동 검증으로 무효화. deadlock 인과는 **carb log hook 등록 + MDL resolver 결합**이며, 최신 baseline 은 `docs/invariants/usd-load.md` 의 결론을 따른다.

Browser 계열 extension 은 첫 open 때 S3 thumbnail/catalog crawl 로 UI settle 시간이 길어질 수 있다. 따라서 capture/test 에서는 10-30 s settle 을 고려하되, USD load hang 의 root cause 로 취급하거나 `.env` 에서 금지 목록처럼 관리하지 않는다.

---

## Extension 관리 / carb 로그

### ExtensionManager API 함정

- `manager.set_extension_enabled_immediate(ext_id, True)` **반환값이 진실의 원천**
- `manager.get_extension_dict(bare_id)` 는 Kit 107.3 에서 bare id 에 대해 **None 반환** (full qualified `{name}-{version}` 필요) — 유효성 검증 용으로 **사용 금지**
- `activate` 는 enable-immediate 호출 결과 False 시 `ValueError → 400`. `reload=True` 는 enable 상태에서도 off/on 사이클을 돌려 Python package 재 import

### LogCaptureService 규약

- `carb.logging.acquire_logging().add_logger(cb)` 콜백 시그니처 **5-arg** `(source, level, filename, line, msg)` — 공식 문서 6-arg (tid 포함) 는 구버전
- Level 정수: VERBOSE=-2, INFO=-1, WARN=0, ERROR=1, FATAL=2
- 콜백은 **carb 스레드에서 호출**되므로 `_on_log` 는 절대 raise 안 함 (try/except swallow)
- `add_logger` handle 은 `on_shutdown` 에서 `remove_logger` — 생략 시 Extension reload 간 중복 엔트리
- `query(since_ms, level, source_filter, limit)` 은 thread-safe snapshot peek (drain 아님) — 반복 호출 시 같은 range 에 같은 엔트리 반환. Kit console 이 chatty 하므로 `ext_id` substring filter 필수

---

## ASYNC Job 패턴

`services/job_service.py` 의 `JobService`:

- `start_job(coro_factory)` 이 `asyncio.create_task` 로 background 실행 + task reference 를 `_tasks[job_id]` 에 보관 (cancel 용)
- job dict: `{status, progress, result, error, created_at_ms, updated_at_ms}`. terminal state `done` / `error` / `canceled` 는 TTL 1h 후 sweep (cleanup loop 120s)
- **모든 예외는 반드시 try/except 으로 `error` 상태에 저장**. silent catch (pass) 금지 — 호출자가 실패 원인 확인 필요
- `cancel(job_id)` 은 `Task.cancel()` + `status=canceled`. 이미 terminal 이면 현재 상태 리턴 (idempotent). Navigate coroutine 은 `try/finally` 로 `stop_animation` 을 보장 (취소 후 중간 프레임 freeze 방지)
- Extension 재시작 시 in-flight job 전부 손실 → HTTP 404. 장기 작업은 호출 측 재시도 정책 필요
- **`JobService.get_status`, `cancel` 은 sync 메서드** (async 아님). in-process import 재사용 시 `await` 하지 말 것
