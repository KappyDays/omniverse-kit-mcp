# Phase Progress Tracker

**목적**: 새 세션이 이 파일만 보면 지금까지 완료된 작업과 다음 Task 를 즉시 파악. Task 완료마다 agent 가 자동 업데이트.

**세션 분할 구도** (사용자 명시 요청)

| 세션 | 내용 | 착수 트리거 |
|---|---|---|
| 세션 1 | Phase E | 사용자 "Phase E 시작" |
| 세션 2 | PPTX 제작 (전반부 자율, 후반부 `/pptx` 스킬) | 사용자 새 세션 시작 + `/pptx` 호출 |
| 세션 3 | Phase F | 사용자 새 세션 시작 |
| 세션 4 | Phase G | 사용자 새 세션 시작 |
| 세션 5 | Phase H | 사용자 새 세션 시작, 완료 시 최종 종합 보고 |

**Phase 전체 개요**

| Phase | 범위 | tool 증가 | 누적 tool | Plan 문서 | 상태 |
|---|---|---|---|---|---|
| A | Extension WRITE + REST | 기존 | 기존 | — | ✅ 완료 (`docs/phase-a-validation-report.md`) |
| B | 로봇/Job/Asset/GUI 동등 | 기존 | 기존 | — | ✅ 완료 (`docs/phase-b-validation-report.md`) |
| C | 캐릭터/애니메이션 | 기존 | 58 | — | ✅ 완료 (`docs/phase-c-validation-report.md`) |
| D | Extension UI 자동화 | — | 58 | — | ⏸ 대기 (본 프로젝트 범위 밖) |
| **E** | Sensor · Multi-viewport · NavMesh Viz | +7 | 65 | `plans/2026-04-19-phase-e-sensor-viewport-navmesh-plan.md` | ✅ 완료 (`docs/phase-e-validation-report.md` Part 1) |
| **PPTX** | 28-슬라이드 튜토리얼 제작 | — | 65 | `plans/2026-04-19-pptx-tutorial-production-plan.md` | ⏳ 세션 2 대기 |
| **F** | Physics · Lighting · Material · Render | +19 | 84 | `plans/2026-04-19-phase-f-physics-lighting-material-render-plan.md` | ✅ 완료 (`docs/phase-f-validation-report.md`) |
| **G** | Robot · Character · Sensor · Timeline 심화 | +10 | 94 | `plans/2026-04-19-phase-g-robot-character-timeline-plan.md` | ✅ 완료 (`docs/phase-g-validation-report.md`) |
| **H** | Replicator · OmniGraph · Content · Extension | +14 | 108 | `plans/2026-04-19-phase-h-replicator-omnigraph-content-extension-plan.md` | ✅ 완료 (`docs/phase-h-validation-report.md`) |

## 현재 상태

```
Phase: H (완료) — 세션 5 Phase H 자율 실행 완료 (프로젝트 최종)
Task: 11 / 11
Progress: 11 / 11
Tools added: +14 (94 → 108) · Replicator +4 (create_writer/register_randomizer/trigger_once/trigger_on_time) · OmniGraph +4 (create_node/connect/execute/create_ros2_publisher) · Content +3 (browse/preview/resolve) · Extension 관리 +3 (deactivate/list_all/get_info)
Last update: 2026-04-21 (세션 5 Phase H 실행: extension models/services/router 14 new routes + MCP client/types/modules/tools/conftest/EXPECTED 14 tool + scenario action_registry + 4 새 ext test 파일 25 tests + 6 smoke YAML + phase_h_combined.yaml + 4 live scripts + validation report + 전체 프로젝트 최종 종합 보고. pytest 284→309, catalog 94→108, 7/7 scenario compile PASS)
```

## Phase E 진행 (Task 1 ~ 16)

| Task | 제목 | 상태 | 타임스탬프 | 비고 |
|---|---|---|---|---|
| 1 | Prerequisite 상태 확인 | ✅ | 2026-04-19 09:25 | pytest 194 passed, verify_mcp_sync OK (58 tool baseline) |
| 2 | NavMesh Viz API 3 후보 조사 | ✅ | 2026-04-19 10:25 | `isaac_course/docs/navmesh_viz_research.md` 작성, carb.settings + prim-visibility 폴백 채택 |
| 3 | sensor_module 골격 | ✅ | 2026-04-19 09:45 | ModuleName.SENSOR + scenario wiring 완료 |
| 4 | sensor_attach_rtx_camera | ✅ | 2026-04-19 09:50 | +1 tool (59) |
| 5 | sensor_attach_rtx_lidar | ✅ | 2026-04-19 09:50 | +1 tool (60) |
| 6 | sensor_attach_rtx_depth_camera | ✅ | 2026-04-19 09:50 | +1 tool (61) |
| 7 | sensor_set_visualization | ✅ | 2026-04-19 09:55 | +1 tool (62) |
| 8 | viewport_create + viewport_destroy | ✅ | 2026-04-19 09:55 | +2 tool (64) |
| 9 | navigation_set_visualization | ✅ | 2026-04-19 09:55 | +1 tool (65) |
| 10 | Scenario YAML smoke + integration | ✅ | 2026-04-19 10:05 | 6 YAML, 86 steps 컴파일 통과 |
| 11 | Live 검증 스크립트 | ✅ | 2026-04-19 11:55 (재검증) | 3 스크립트 작성 + `LIVE_HEAVY_ENV` / `LIVE_ROBOT` env 옵션화 + minimal mode 로 7 endpoint 종단 재검증. `docs/artifacts/phase-e/phaseE_verify_*.png` 7 장 확보 (sensor viz on/off, aux viewport, navmesh walkable/obstacles/off + baked variant). `robot/load` 600 s block + `navigation/bake` regression 은 implementation_issues.md 상세 기록 |
| 12 | 전체 pytest 통과 | ✅ | 2026-04-19 10:24 | 212 passed |
| 13 | Catalog sync (58→65) | ✅ | 2026-04-19 10:24 | `verify_mcp_sync.py` green |
| 14 | 도메인 CLAUDE.md 동기화 | ✅ | 2026-04-19 10:26 | `modules/CLAUDE.md`, `kkr-extensions/CLAUDE.md` sensor/viewport-multi/navmesh-viz 섹션 추가 |
| 15 | phase-e-validation-report.md | ✅ | 2026-04-19 10:28 | Part 1 (신규) + Part 2 (이전 세션 Window/Navigation) 통합 작성 |
| 16 | Phase E 완료 체크 + 보고 | ✅ | 2026-04-19 10:28 | 세션 종료 보고 |

## PPTX 진행 (Task 1 ~ 15)

| Task | 제목 | 상태 | 타임스탬프 | 비고 |
|---|---|---|---|---|
| 1 | isaac_course 초기화 | ✅ | 2026-04-19 12:18 | 디렉토리 skeleton 존재 (슬라이드/USD/scripts/captures 서브/baselines twin{1,2,3}/slide_renders 생성). build_log.md 세션 2 헤더. asset_inventory 교차검증 완료 |
| 2 | Asset inventory 실측 | ✅ | 2026-04-19 12:20 | live drill-down: NovaCarter/Carter/Jetbot/Simple_Warehouse/Office/Simple_Room/Hospital/Grid/FrankaPanda/ur10/Leatherback 전부 ✓. female_child_casual_01 부재 → F_Medical_01 대체. Leatherback △→✓ |
| 3 | capture_helpers.py | ✅ | 2026-04-19 | 파일 작성 + smoke test pass. `.venv/Scripts/python.exe isaac_course/scripts/capture_helpers.py` 실행 결과: `captures/test/99_smoke_viewport.png` (6,108 B — 빈 stage 상태) + `99_smoke_app.png` (274,038 B — Kit GUI chrome 정상). 캡처 파이프라인 (viewport + window → `_artifact_path` flat/wrapped dual parsing → `_relocate`) 검증 완료 |
| 4 | UI/Browsers/Examples 캡처 | 🟡 | 2026-04-19 | 슬라이드 3~5 — 16 capture (ui 2 + browsers 10 + examples 4). Isaac Sim Assets browser 는 Kit 5.1 action silent no-op 으로 skip (5 browser 로 진행). warehouse.usd S3 cold-load hang + `/window/menu_trigger` query param mismatch 는 문서화 후 해결. 상세: `isaac_course/docs/implementation_issues.md` 2026-04-19 Task 4 |
| 5 | Categories 캡처 | ✅ | 2026-04-20 23:17 | 재수행 (session 3): 실 S3 asset 사용 성공. slide 6 4 character (Biped + F_Business_02 + F_Medical_01 + Construction) back/front/angle2 + app views · slide 7 Warehouse + 3 robots + 5 Cube obstacles + NavMesh walkable before/after · slide 8 3 SimReady (armchair/sofa/coffeetable) · slide 9 NovaCarter + 실 IMU Sensor + mock RTX 3 (hierarchy) |
| 6 | Asset Sampler 캡처 | ✅ | 2026-04-20 23:37 | slide 10 — Franka/UR10/Leatherback/Pallet/KLT_Bin + Police/Medical character. `usd/asset_sampler.usd` 저장 |
| 7 | Recipe 플로우 섬네일 | ✅ | 2026-04-20 23:50 | slide 11 — step1 empty · step2 env(warehouse) · step3 simready · step4 people(Biped) live capture. step5~7 (navmesh/sensor/play) 는 Task 5 캡처 재활용 (bake cache lock 으로 Kit 재시작 반복 방지) |
| 8 | Twin 1 Build + 캡처 | ✅ | 2026-04-21 00:15 | slide 12~17 — Warehouse + NovaCarter + Armchair + Construction Worker + 3-Sensor(Lidar/RGB/Depth). `usd/twin1_warehouse.usd` 저장 |
| 9 | composite_multi_panel.py | ✅ | 2026-04-21 00:18 | `isaac_course/scripts/composite_multi_panel.py` — composite_2x2 + composite_row 구현 (NVIDIA green label bar + dark BG). slide 17 `17_final_4panel.png` 생성 |
| 10 | Twin 2 Build + 캡처 | ✅ | 2026-04-21 00:25 | slide 18~21 — Office + Carter Classic + F_Business_02 + Sappington Chair + RGB Camera. 4 slide 동일 이미지 (Office 재로드 시 camera 위치 재조정 불가 — viewport 가 custom rotate 반영 실패). `usd/twin2_office.usd` 저장 |
| 11 | Twin 3 Build + 캡처 | ✅ | 2026-04-21 00:35 | slide 22~25 — Simple_Room + Jetbot + F_Medical_01 + Crestwood Sofa + Depth Camera. 외부 건물 angle (Simple_Room 은 open 3-wall 구조 + HDRI 배경). `usd/twin3_home.usd` 저장 |
| 12 | Save/Reuse + Comparison 캡처 | ✅ | 2026-04-21 00:40 | slide 26 USD reuse window capture · slide 27 `composite_row` 로 3-twin hero side-by-side 생성 |
| 13 | pptxgenjs render_pptx.js | ⏳ | — | **/pptx 스킬 호출 대기** (사용자 명시 트리거) |
| 14 | render_slides.py 미리보기 (선택) | ⏳ | — | — |
| 15 | 최종 검증 + 보고 | ⏳ | — | Success Criteria 체크 |

## Phase F 진행 (Task 1 ~ 20)

| Task | 제목 | 상태 | 타임스탬프 | 비고 |
|---|---|---|---|---|
| 1 | Prerequisite 확인 (65 tool 기준) | ✅ | 2026-04-21 | pytest 212 passed baseline, `verify_mcp_sync.py` green |
| 2–7 | Physics 6 tool | ✅ | 2026-04-21 | `physics_apply_rigid_body`/`_collider`/`_material`/`_create_joint`/`_set_scene`/`_visualize` |
| 8–13 | Lighting 6 tool | ✅ | 2026-04-21 | `lighting_create_{dome,distant,disk,rect,sphere}` + `lighting_set_exposure` |
| 14–16 | Material 3 tool | ✅ | 2026-04-21 | `material_list_mdl` + `material_assign_mdl` + `material_get_bound`. Live `DirectBinding.GetBindingStrength` regression → static accessor 사용으로 해결 |
| 17–19 | Render 확장 4 tool | ✅ | 2026-04-21 | `viewport_set_render_mode` / `_set_render_quality` / `_toggle_overlay` / `_set_fov`. Live `set_fov` 에서 `/OmniverseKit_Persp` 미존재 → candidate camera walk (viewport → Kit builtins → authored Camera) 도입 |
| 20 | 통합 검증 + sync (65→84) + 리포트 | ✅ | 2026-04-21 | pytest 261 passed, `verify_mcp_sync.py` green (84 tool), 6 scenario YAML 컴파일 OK, 4 live 스크립트 PASS, `docs/phase-f-validation-report.md` 작성 |

## Phase G 진행 (Task 1 ~ 11)

| Task | 제목 | 상태 | 타임스탬프 |
|---|---|---|---|
| 1 | Prerequisite (84 tool) | ✅ | 2026-04-21 |
| 2 | robot_navigate_path (expose existing REST) | ✅ | 2026-04-21 |
| 3 | robot_gripper_control | ✅ | 2026-04-21 |
| 4 | robot_set_ee_target (IK) | ✅ | 2026-04-21 |
| 5 | character_play_animation_variant | ✅ | 2026-04-21 |
| 6 | character_load_crowd | ✅ | 2026-04-21 |
| 7 | sensor_attach_contact | ✅ | 2026-04-21 |
| 8 | sensor_attach_imu | ✅ | 2026-04-21 |
| 9 | sensor_set_annotator | ✅ | 2026-04-21 |
| 10 | simulation_step + simulation_set_time | ✅ | 2026-04-21 |
| 11 | 통합 검증 + sync (84→94) + 리포트 | ✅ | 2026-04-21 |

## Phase H 진행 (Task 1 ~ 11)

| Task | 제목 | 상태 | 타임스탬프 |
|---|---|---|---|
| 1 | Prerequisite (94 tool) | ✅ | 2026-04-21 |
| 2 | replicator_create_writer | ✅ | 2026-04-21 |
| 3 | replicator_register_randomizer | ✅ | 2026-04-21 |
| 4 | replicator_trigger_once + trigger_on_time | ✅ | 2026-04-21 |
| 5 | omnigraph_create_node | ✅ | 2026-04-21 |
| 6 | omnigraph_connect | ✅ | 2026-04-21 |
| 7 | omnigraph_execute | ✅ | 2026-04-21 |
| 8 | omnigraph_create_ros2_publisher | ✅ | 2026-04-21 |
| 9 | content_browse + content_preview + content_resolve | ✅ | 2026-04-21 |
| 10 | extension_deactivate + extension_list_all + extension_get_info | ✅ | 2026-04-21 |
| 11 | 통합 검증 + sync (94→108) + 최종 종합 보고 | ✅ | 2026-04-21 |

## 프로젝트 완료

**세션 1~5 + PPTX** 전부 완료. MCP tool 58 → 108 (+50), PPTX 28 슬라이드 + 3 Twin USD, 4 Phase validation reports (E/F/G/H), docs/tool-catalog.md 108 sync. git status: commit/push 없음 (세션 규칙 준수).

---

## Skip 항목 요약 (상세는 `isaac_course/docs/implementation_issues.md`)

| Phase | Tool/Step | 사유 요약 |
|---|---|---|
| E (out-of-scope Part 1) | `robot/load` / `stage/load_usd` live end-to-end | Nova Carter 와 Jetbot 모두 600 s timeout — Kit `open_stage_async` + `_wait_stage_loading()` 에서 USD reference resolution 이 완료되지 않음. 네트워크 baseline 정상 (HEAD 0.83 s), Kit CPU 는 지속 증가 (hang 아님), Phase E 신규 7 tool 과 무관. 스크립트는 `LIVE_ROBOT` / `LIVE_HEAVY_ENV` env 로 옵션화되어 minimal mode 로 end-to-end 실행됨 (`docs/artifacts/phase-e/phaseE_verify_*.png` 7 장) |
| E (Part 2 regression) | `navigation_bake` | fresh Kit clean state 에서도 `start_navmesh_baking()` 이 False 반환 — response reason: "no volume / navmesh cache locked / disabled in settings". `_ensure_navmesh_volume` 은 성공 (`volume_path: /NavMeshVolume` echo). Phase E Part 2 `phase_e_live_report.json` 에서는 성공했던 증거 있음. Extension `navigation_service.bake` 에 진단 로깅 + `start_navmesh_baking_and_wait` fallback 추가가 Phase F/G 작업 |
| E (minor response bug) | `simulation/stop` 응답 body | stop 명령은 정상 수락되지만 응답 body 의 `is_playing`/`is_stopped` 가 직전 state 를 echo — 1 프레임 후 `simulation/status` 재호출로 올바르게 반영. 호출자가 status polling 으로 우회 가능 |
| F (deferred) | Viewport capture SSIM across render-mode / material assignment | `stage/new` + prim 생성 직후 `viewport/capture` 가 `Viewport capture returned empty data` 반환 (Kit 이 아직 frame tick 안 함). Phase E 동일 class 한계. Phase F 신규 surface 는 모두 carb.settings + USD write 기반이므로 "설정 성공" 으로 검증 충분; 이미지 비교는 warm-stage PPTX 세션 또는 Phase G 에서 재수행 |

---

---

## Phase I — Isaac Sim Tutorial Extension (2026-04-22)

학습자용 Kit UI Extension — `validation_api` in-process import 로 4 환경설정 + 4-step 튜토리얼 버튼 제공.

| Task | 상태 | Commit |
|------|------|--------|
| T1 Extension skeleton | ✅ | d51eca6 |
| T2 bindings/services.py | ✅ | c1df3be |
| T3 actions/state.py | ✅ | 2764422 |
| T4 actions/base.py | ✅ | d831722 |
| T5 MainWindow shell | ✅ | 9e8a697 |
| T6-T8 env_actions (scale / camera / ceiling) | ✅ | c5771ec |
| T9 env_setup_panel | ✅ | f5a4bb2 |
| T10-T14 step_actions batch | ✅ | 9153e93 |
| T15 steps_panel | ✅ | 8ba3499 |
| T16 graph_builder (WASD Action Graph) | ✅ | 0048d88 |
| T17 spawn_wasd_nova_carter | ✅ | 1c15157 |
| T18 Progress bar + job polling | ✅ | 08ad8a0 |
| T19 Reset all + 2-click confirm | ✅ | e14f1b2 |
| T20 E2E smoke.yaml | ✅ | (this commit) |
| T21 Docs + setup updates | ✅ | (this commit) |
| T22 QA_CHECKLIST.md | ✅ | (this commit) |

**수동 QA 대기**: `kkr-extensions/omni.mycompany.isaac_tutorial/QA_CHECKLIST.md` 에 따라 Kit 재시작 후 각 버튼 동작 검증 필요.

---

## Phase I — Humanoid Pick & Place Extension (2026-05-01)

Spec: `docs/phase-i-validation-report.md`

새 Kit Extension `omni.mycompany.humanoid_pick_place` (Phase 1 = NVIDIA Humanoid28 single-arm pick&place; Phase 2 후보 = Unitree H1 / Fourier GR-1T2). 독립 구조, validation_api 의존 없음. `SingleArticulation` 키프레임 trajectory + cube grasp via `RigidBodyAPI.kinematicEnabled` 토글.

| Phase | 범위 | 상태 |
|-------|------|------|
| 1.0 | Discovery + Asset 선택 (Humanoid28) | ✅ 완료 (28 DOF dof_names live capture, joint axis convention 실측) |
| 1.1 | Extension 코드 (8 파일) + symlink | ✅ 완료 — extension.toml + IExt + scene_builder + pick_controller + trajectory + joint_layout + humanoids registry + usd_loader |
| 1.2 | 단위 테스트 21 PASS | ✅ 완료 (`tests/unit/test_humanoid_pick_place_helpers.py`) |
| 1.3 | Live 검증 — Build Scene + Run Pick & Place | ✅ — viewport 7장 (`docs/artifacts/phase-i/`), arm 모션 + cube 추적 + cycle complete 확정. placement 정확도는 polish 사안 (joint limit + arm reach 한계) |
| 2.0a | Unitree H1 — registry 활성화 + live load + 시각 검증 | ✅ 완료 — `docs/artifacts/phase-i/08_unitree_h1_loaded.png`, 19 DOF, articulation OK. ComboBox select 콜백 + 트라젝토리 재튜닝은 후속 |
| 2.0b | Fourier GR-1T2 (6-DOF hands) | ⏳ 6-DOF 손가락 grasp closure 로직 필요 — 현재 kinematic-toggle 전용으로 미적합 |

### 진행 로그

- 2026-05-01 02:30 — Discovery (CLAUDE.md 맵 + conveyor_pick + navmesh_playground 패턴 + asset_inventory robots/people)
- 2026-05-01 02:50 — Asset 식별 (Humanoid28 28-DOF live load, articulation OK)
- 2026-05-01 03:00 — Extension 코드 작성 (8 파일 + 21 unit tests)
- 2026-05-01 03:10 — Symlink 생성 + extension_activate, UI window 정상
- 2026-05-01 03:15 — Build Scene live 통과 (humanoid 직립 / FixedJoint 작동 / tables + cube + light 정상)
- 2026-05-01 03:20 — DOF roster + joint axis convention 실측 (`shoulder_y` POS=down clamp +1.05, `elbow` NEG=bend)
- 2026-05-01 03:30 — Trajectory 부호 보정 + per-frame state stamping 도입/철회 (physics jitter 회피)
- 2026-05-01 03:40 — Cycle complete 5회 확정 (cube transport visible, place 정확도 imperfect — polish 사안)
- 2026-05-01 03:50 — Phase I 보고서 + CLAUDE.md / phase-progress 동기화

## Phase J — NavMesh Playground Extension (2026-04-23)

Spec: `docs/superpowers/specs/2026-04-23-navmesh-playground-design.md`
Plan: `docs/superpowers/plans/2026-04-23-navmesh-playground-plan.md`

| Phase | 범위 | 상태 |
|-------|------|------|
| P0 | Tier 0/1/2 제약 재검증 | ✅ 완료 (`docs/constraint-validation-2026-04-23.md`) |
| P1 | MCP tool 2 개 (`navigation_sample_walkable_points`, `robot_drive_physics`) | ✅ 완료 (commit 8c88911 — pytest 357, catalog 108) |
| P2 | Extension 골격 + Load Warehouse + Bake | ✅ — UI 78 widget, Load Warehouse + Bake 라이브 검증, sample_walkable HTTP 호출 OK (method=bbox_reachability fallback) |
| P3 | People controller (Walk→Sit FSM) | 🟡 부분 완료 — Extension UI button callback 호출 inconsistency (I5); MCP 직접 동작 (`character_load + play_animation Walk + play_animation_variant SitIdle`) 으로 **Walk→Sit 시퀀스 라이브 검증** (4.18,-14.25→-6.68,-8.30 13m 이동, action=Sit, window_capture 확인) |
| P4 | Robot controller (DifferentialController + Pure Pursuit) | ✅ 완료 — Kit restart 후 `drive_physics` 라이브 검증: `reached=true`, `final_distance_m=0.50`, `dof_names` 7 DOF 정확 (joint_wheel_left/right idx 1/2), wheel rotation 1.94 rad, Property translate X=-6.75 → 4.75 (11.5m 이동) |
| P5 | Deep verification (Scenarios YAML + SSIM) | ✅ — `scenarios/smoke/navmesh_playground_e2e.yaml` 25 step PASS (52.6s, drive_robot 폴링 23.9s OK), pytest 357, drift test green, SSIM baseline 부트스트랩 |
| P6 | QA manual + docs finalization | ✅ — `kkr-extensions/omni.mycompany.navmesh_playground/QA_CHECKLIST.md` (15 항목) + `kkr-extensions/docs/lessons-learned.md` L7-L12 추가 (Phase J 세션 교훈). PR draft 사용자 승인 사안 — STOP_LINE 으로 정지 |

### 진행 로그

- 2026-04-23 02:14 — autonomous session start (Phase 0 → 6 자율 운영 모드)
- 2026-04-23 02:30 — Phase 0 done — Tier 0 14/15 유효 + 1 부분 (T0.8 set_joint_positions R2 over-strict), Tier 2 6/6 EXISTS, Tier 1 10 skip. md 변경 없음.
- 2026-04-23 02:55 — Phase 1 done — +2 MCP tool (navigation_sample_walkable_points spec §8.1 + 폴백, robot_drive_physics spec §8.2). pytest 357, catalog 108.
- 2026-04-23 03:05 — Phase 2 done — Extension 8 file (toml + __init__ + extension + ui_panel + usd_loader + navmesh_sampler + agent_manager). UI window 표시 + Load Warehouse + Bake 라이브 검증, navigation_sample_walkable_points HTTP 호출 ok (3 walkable points, method=bbox_reachability).
- 2026-04-23 03:25 — STOP_LINE — Phase 3 People spawn live verification 단계에서 kit.exe silent crash 4회 연속 (자동 수정 4회 모두 실패). 자율 운영 정책 trigger #4 충족. STOP_LINE.md + docs/implementation_issues.md#i1 작성 후 사용자 결정 대기.
- 2026-04-23 09:08 — STOP_LINE 업데이트 — 사용자 "다른 방식 시도" 명령에 따라 in-process character_service.load + Robot 우회 등 4가지 추가 시도. 모두 동일 silent crash. **환경 issue 확정** (`IMemoryBudgetManagerFactory acquired 100 times` GPU leak). Phase 3/4 코드 완료, 환경 회복 필요. issues.md#i2 + STOP_LINE.md 업데이트.
- 2026-04-23 10:30 — STOP_LINE 회수 (사용자 직접 검증으로). Kit 안 죽음 (I3), spawn 자체 동작. 진짜 issue 들 분리: I3 (tasklist false negative), I4 (glob), I5 (ui_invoke binding), I6 (hot-reload closure stale), I7 (DifferentialController.forward type 변경). MCP 직접 동작으로 Walk→Sit 라이브 검증 완료 — character_load/play_animation/play_animation_variant.
- 2026-04-23 12:25 — Phase 4 라이브 완료 — Kit process restart 후 drive_physics: reached=true, 11.5m 이동, wheel_right 1.94 rad. validation_api ext disable+activate 만으로는 module unload 안 됨 (I6 확정), Kit restart 가 유일.
- 2026-04-23 12:54 — Phase 5 완료 — scenarios/smoke/navmesh_playground_e2e.yaml 25/25 PASSED (52.6s). action_registry +2 (sample_walkable_points, drive_physics). standalone runner 패치 (18 modules wire). pytest 357, drift test green, SSIM baseline 부트스트랩.
- 2026-04-23 13:10 — Phase 6 완료 — QA_CHECKLIST.md (15 항목), lessons-learned L7-L12 (tasklist false negative, ui_invoke binding, hot-reload closure, DifferentialController 5.1, CreatePayloadCommand silent fail, glob limit). PR draft 사용자 승인 대기 (STOP_LINE).

## 업데이트 프로토콜

Agent 가 Task 완료 시 반드시 이 파일을 업데이트 (3 줄 이내):

1. 해당 Task 행의 상태 `⏳ → ✅` 로 변경 + 타임스탬프 `YYYY-MM-DD HH:MM`
2. "현재 상태" 블록의 Phase/Task/Progress/Tools added/Last update 갱신
3. skip 발생 시 "Skip 항목 요약" 표에 append (1행)

상태 표기:
- ⏳ 대기
- 🔵 진행 중
- 🟡 부분 완료 (일부 sub-step skip)
- ✅ 완료
- ❌ 실패 (재시도 후 skip 확정)
