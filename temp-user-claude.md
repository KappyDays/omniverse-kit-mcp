# 세션 3 CLAUDE.md 업데이트 후보 (사용자 검토용)

> 이번 PPTX 제작 세션에서 **코드를 읽어도 알 수 없는** 제약 / 결정 / 함정 10건. 사용자 승인 후 해당 CLAUDE.md 에 반영.

---

## 1. `CLAUDE.md` (루트) — "카메라 조작 규칙" 섹션 신규 추가

**위치**: 루트 CLAUDE.md, "kit.exe USD 로드 — 근본 원인 + 해결 프로토콜" 섹션 다음.

**내용**:

### Camera 조작 규칙 — `/OmniverseKit_Persp` preset 고정

Isaac Sim 5.1 의 viewport 는 `/OmniverseKit_Persp` prim 의 `xformOp:rotateXYZ` 변경을 **간헐적으로만 반영**. 특히 Kit 기본 isometric `[54.74, 0, 135]` 에서 벗어난 custom rotate 는 viewport 가 cached render 를 반환해 움직이지 않는 경우 발생.

**표준 규칙**:
- `xformOp:rotateXYZ = [54.74, 0, 135]` 고정 (Kit 기본 isometric, +X+Y+Z → origin 방향)
- `xformOp:translate` 만 scene scale 에 맞춰 조정:
  - Small (1–3 m): `[5, 5, 4]`
  - Medium (3–8 m): `[8, -8, 5]` 또는 `[10, 10, 7]` (isometric 기준)
  - Large (8–20 m): `[15, 15, 10]` 또는 warehouse `[10, -12, 9]`
- Camera 가 +X+Y+Z 사분면에 있어야 origin 쪽을 isometric rotate 가 비춘다. 반대 사분면에 두면 카메라 뒤쪽이 scene → 흰/검은 화면
- Viewport 재캐시 회피: 설정 변경 후 `simulation_play → (1s sleep) → simulation_stop → viewport_capture` cycle
- **Phase F 에 `viewport_frame_prims(prim_paths, preset="isometric|front|top|side")` MCP tool 추가 예정** — `omni.kit.viewport.utility.frame_camera` 래핑

**이유**: custom rotate 불안정 (세션 3 실측 — slide 9/22 수차례 rotate 설정 viewport 미반영). scene bbox 기반 camera 자동 배치는 Phase F 범위.

---

## 2. `src/isaacsim_mcp/modules/CLAUDE.md` — "Character domain constraints" 섹션 확장

**위치**: modules/CLAUDE.md 의 "Character domain constraints (Extension 실측)" 블록 내부.

**추가 내용**:

### T-pose 유지 방지 — `character_load` 필수

`stage_load_usd` 로 character USD 를 raw reference 로드하면 **AnimationGraph bind 안 됨 → simulation_play 시 T-pose 유지**. `character_load` 는 Biped_Setup rig 자동 bind + `anim_graph_bound=true` 응답. 4개 skin variant (F_Business_02 / F_Medical_01 / male_adult_construction_05_new / male_adult_police_04) 모두 `character_load` 로 로드 시 sanitized path `/World/Characters/{name}` 에 자동 이동 + AnimGraph bind 성공 (세션 3 실측).

**표준 pattern**:
```
character_load(usd_url, prim_path=/World/People/X, position=[...])
→ simulation_play → 1s sleep → simulation_pause  # AnimGraph warm-up
→ character_play_animation(sanitized_path, "Idle")  # 또는 Walk/Run/Sit
→ simulation_play  # advance
```

**주의**: `character_play_animation` 의 `prim_path` 는 `character_load` 응답의 `sanitized_prim_path` 사용 (caller 가 제공한 path 가 아님). 예: caller `/World/People/Worker` 입력 → Extension 이 `/World/Characters/Worker` 로 sanitize → 이후 호출은 sanitized path 사용.

### NavMesh cache lock 회복

`navigation_bake` 가 `"start_navmesh_baking returned False (navmesh cache locked)"` 반환 시 → Kit 내부 NavMesh cache 가 이전 bake 로 lock 상태. 회복:
1. `stage_delete_prim("/World/NavMeshVolume")` 시도 (존재하면)
2. 실패 시 Kit 재시작 (`scripts/kill_kit_zombie.sh` + `run_process_module_standalone.py start`)
3. `stage_new` → scene 재구성 → `simulation_stop → navigation_bake(volume_scale=30)` 재시도

세션 3 실측: 같은 Kit 인스턴스에서 multiple bake 반복 시 약 5 번째부터 cache lock 빈발. Kit 재시작 후 첫 bake 는 항상 성공.

### `stage_load_usd` children=False cold-load 현상

Kit restart 직후 첫 load 시 응답 `detail="type=Xform, children=False"` 로 오는 경우 USD reference 가 아직 resolve 되지 않은 상태. **같은 URL 로 delete + re-load 시 `children=True`** 로 정상 로드 (세션 3 Task 6 실측). Workaround: first load 후 `stage_assert_property` 로 prim 존재 확인, `children=False` 이면 delete + 재로드.

---

## 3. `isaac_extension/CLAUDE.md` — "Physics Ground Plane vs Plane" 주의

**위치**: isaac_extension/CLAUDE.md 의 "GUI-equivalent operations" 섹션 내부.

**추가 내용**:

### Plane prim: 시각 vs Physics 구분

- `stage_create_prim(prim_type="Plane")` → **UsdGeomPlane (시각 plane only, collision 없음)**. Robot 배치 후 `simulation_play` 시 robot 이 plane 을 통과해 자유낙하.
- `window_menu_trigger("Create/Physics/Ground Plane")` → **CollisionPlane + CollisionMesh + PhysicsCollisionAPI 3 prim 자동 생성**. Robot/character 지면 안착 보장. PPTX / NavMesh 시나리오 필수.

세션 3 실측: slide 9 에서 `type=Plane` 생성 후 robot 이 -Z 로 떨어져 viewport 에서 사라짐 → `Create/Physics/Ground Plane` 메뉴 trigger 로 해결.

### `window_menu_trigger` path 공백 변환 규칙

Kit 메뉴 path 에서 **공백은 `/` 로 변환**되어 tree 에 저장됨. 예:
- 메뉴 표시명: `Create > Sensors > RTX Lidar > NVIDIA > Example Rotary`
- `window_menu_trigger(menu_path=...)` 에 전달할 값: `Create/Sensors/RTX/Lidar/NVIDIA/Example Rotary` (not `RTX Lidar`)
- `Camera and Depth Sensors` → `Camera/and/Depth/Sensors`

SoT: `window_menu_list(menu_path="Create")` 응답의 `path` 필드를 그대로 사용.

### RTX Sensor menu click-to-place mode

`Create/Sensors/RTX/Lidar/*`, `Create/Sensors/RTX Radar`, `Create/Sensors/Camera/and/Depth/Sensors/*` 메뉴 trigger 는 `created_prims=[]` 반환 (dialog 대기 interactive mode). viewport click placement 가 필요해 MCP 단독으로는 최종 prim 생성 못함. **즉시 prim 생성**되는 건 `Imu Sensor`, `Contact Sensor` 두 physics sensor 만.

대안: mock `sensor_attach_rtx_*` MCP tool (`UsdGeom.Camera + customData.sensor_type` tag 기반) 이 시각 교육용. 실 sensor data schema 는 Phase G/H refactor 에서 menu action + viewport auto-placement 통합 예정.

---

## 4. `isaac_course/CLAUDE.md` — PPTX 제작 완료 상태

**위치**: isaac_course/CLAUDE.md 상단 "R9. PPTX 세션 분할" 블록 다음.

**추가 내용**:

### R10. 세션 3 완료 산출물 (2026-04-21)

- **PPTX**: `slides/Isaac_Sim_Digital_Twin_Tutorial.pptx` 28 슬라이드 완성 (pptxgenjs)
- **USD 4**: `usd/{asset_sampler,twin1_warehouse,twin2_office,twin3_home}.usd`
- **Captures 57**: 전 슬라이드 viewport + window dual (각 slide 최소 1장)
- **Scripts**: `composite_multi_panel.py` (2x2 + row 합성) · `render_pptx.js` (28 slide) · `render_slides.py` (PowerPoint COM 미리보기)

**재캡처 시 주의**:
- Twin 2/3 는 여러 slide 에 동일 이미지 재사용 상태 — 사용자 요구 시 angle 다양화 필요
- Slide 9 sensor viewport 는 NovaCarter 가 작게 보임 (camera zoom 한계)
- Simple_Room 은 3-wall open 구조 + HDRI 배경 → 외부 건물 view 기본

### R11. `pre-test/` 와 `baselines/` 는 유지

- `pre-test/` — 세션 2 S3 multi-asset load 검증 (16/16 성공 기록). git unstaged, 재검증 시 재사용
- `baselines/{twin1,twin2,twin3}/` — SSIM baseline 저장소. 빈 상태 — 향후 SSIM 회귀 검증 시 채움

---

## 5. `docs/phase-progress.md` — 이미 업데이트 완료

세션 3 종료 시 Task 5~12 ✅ 반영. Last update 2026-04-21.

---

## 적용 방법

위 블록들을 각 파일에 반영할 때:
1. 루트 CLAUDE.md 는 Foundation 섹션 직후에 카메라 규칙 추가
2. modules/CLAUDE.md 는 기존 "Character domain constraints" 를 확장
3. isaac_extension/CLAUDE.md 는 "GUI-equivalent operations" 하단에 append
4. isaac_course/CLAUDE.md 는 R10, R11 추가

승인 후 Edit 로 반영하겠습니다.
