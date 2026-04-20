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
| **F** | Physics · Lighting · Material · Render | +19 | 84 | `plans/2026-04-19-phase-f-physics-lighting-material-render-plan.md` | ⏳ 세션 3 대기 |
| **G** | Robot · Character · Sensor · Timeline 심화 | +10 | 94 | `plans/2026-04-19-phase-g-robot-character-timeline-plan.md` | ⏳ 세션 4 대기 |
| **H** | Replicator · OmniGraph · Content · Extension | +14 | 108 | `plans/2026-04-19-phase-h-replicator-omnigraph-content-extension-plan.md` | ⏳ 세션 5 대기 |

## 현재 상태

```
Phase: PPTX (세션 3 — Task 12 까지 완료, Task 13 pptxgenjs /pptx 스킬 대기)
Task: 12 / 15 완료
Progress: 12 / 15
Tools added: 0 (65 유지) · Extension config.py ui_demo 2개 기본값 제거
Last update: 2026-04-21 (세션 3: Task 5 재수행 (실 S3 + NavMesh obstacles before/after) + Task 6~12 산출 + sensor_menu_catalog.md 체계화 + ui_demo auto-activate 비활성 + Twin 1/2/3 USD + asset_sampler.usd 저장 + slide 17 4-panel composite + slide 27 3-twin comparison composite)
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
| 11 | Live 검증 스크립트 | ✅ | 2026-04-19 11:55 (재검증) | 3 스크립트 작성 + `LIVE_HEAVY_ENV` / `LIVE_ROBOT` env 옵션화 + minimal mode 로 7 endpoint 종단 재검증. `PhaseE/phaseE_verify_*.png` 7 장 확보 (sensor viz on/off, aux viewport, navmesh walkable/obstacles/off + baked variant). `robot/load` 600 s block + `navigation/bake` regression 은 implementation_issues.md 상세 기록 |
| 12 | 전체 pytest 통과 | ✅ | 2026-04-19 10:24 | 212 passed |
| 13 | Catalog sync (58→65) | ✅ | 2026-04-19 10:24 | `verify_mcp_sync.py` green |
| 14 | 도메인 CLAUDE.md 동기화 | ✅ | 2026-04-19 10:26 | `modules/CLAUDE.md`, `isaac_extension/CLAUDE.md` sensor/viewport-multi/navmesh-viz 섹션 추가 |
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

| Task | 제목 | 상태 | 타임스탬프 |
|---|---|---|---|
| 1 | Prerequisite 확인 (65 tool 기준) | ⏳ | — |
| 2–7 | Physics 6 tool | ⏳ | — |
| 8–13 | Lighting 6 tool | ⏳ | — |
| 14–16 | Material 3 tool | ⏳ | — |
| 17–19 | Render 확장 4 tool | ⏳ | — |
| 20 | 통합 검증 + sync (65→84) + 리포트 | ⏳ | — |

## Phase G 진행 (Task 1 ~ 11)

| Task | 제목 | 상태 | 타임스탬프 |
|---|---|---|---|
| 1 | Prerequisite (84 tool) | ⏳ | — |
| 2–4 | Robot 확장 3 tool | ⏳ | — |
| 5–6 | Character 확장 2 tool | ⏳ | — |
| 7–9 | Sensor 확장 3 tool | ⏳ | — |
| 10 | Timeline 확장 2 tool | ⏳ | — |
| 11 | 통합 검증 + sync (84→94) + 리포트 | ⏳ | — |

## Phase H 진행 (Task 1 ~ 11)

| Task | 제목 | 상태 | 타임스탬프 |
|---|---|---|---|
| 1 | Prerequisite (94 tool) | ⏳ | — |
| 2–4 | Replicator 4 tool | ⏳ | — |
| 5–8 | OmniGraph 4 tool | ⏳ | — |
| 9 | Content 3 tool | ⏳ | — |
| 10 | Extension 확장 3 tool | ⏳ | — |
| 11 | 통합 검증 + sync (94→108) + 최종 종합 보고 | ⏳ | — |

---

## Skip 항목 요약 (상세는 `isaac_course/docs/implementation_issues.md`)

| Phase | Tool/Step | 사유 요약 |
|---|---|---|
| E (out-of-scope Part 1) | `robot/load` / `stage/load_usd` live end-to-end | Nova Carter 와 Jetbot 모두 600 s timeout — Kit `open_stage_async` + `_wait_stage_loading()` 에서 USD reference resolution 이 완료되지 않음. 네트워크 baseline 정상 (HEAD 0.83 s), Kit CPU 는 지속 증가 (hang 아님), Phase E 신규 7 tool 과 무관. 스크립트는 `LIVE_ROBOT` / `LIVE_HEAVY_ENV` env 로 옵션화되어 minimal mode 로 end-to-end 실행됨 (`PhaseE/phaseE_verify_*.png` 7 장) |
| E (Part 2 regression) | `navigation_bake` | fresh Kit clean state 에서도 `start_navmesh_baking()` 이 False 반환 — response reason: "no volume / navmesh cache locked / disabled in settings". `_ensure_navmesh_volume` 은 성공 (`volume_path: /NavMeshVolume` echo). Phase E Part 2 `phase_e_live_report.json` 에서는 성공했던 증거 있음. Extension `navigation_service.bake` 에 진단 로깅 + `start_navmesh_baking_and_wait` fallback 추가가 Phase F/G 작업 |
| E (minor response bug) | `simulation/stop` 응답 body | stop 명령은 정상 수락되지만 응답 body 의 `is_playing`/`is_stopped` 가 직전 state 를 echo — 1 프레임 후 `simulation/status` 재호출로 올바르게 반영. 호출자가 status polling 으로 우회 가능 |

---

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
