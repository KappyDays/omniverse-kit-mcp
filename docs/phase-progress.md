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
| **E** | Sensor · Multi-viewport · NavMesh Viz | +7 | 65 | `plans/2026-04-19-phase-e-sensor-viewport-navmesh-plan.md` | ⏳ 세션 1 대기 |
| **PPTX** | 28-슬라이드 튜토리얼 제작 | — | 65 | `plans/2026-04-19-pptx-tutorial-production-plan.md` | ⏳ 세션 2 대기 |
| **F** | Physics · Lighting · Material · Render | +19 | 84 | `plans/2026-04-19-phase-f-physics-lighting-material-render-plan.md` | ⏳ 세션 3 대기 |
| **G** | Robot · Character · Sensor · Timeline 심화 | +10 | 94 | `plans/2026-04-19-phase-g-robot-character-timeline-plan.md` | ⏳ 세션 4 대기 |
| **H** | Replicator · OmniGraph · Content · Extension | +14 | 108 | `plans/2026-04-19-phase-h-replicator-omnigraph-content-extension-plan.md` | ⏳ 세션 5 대기 |

## 현재 상태

```
Phase: (아직 시작 안 함)
Task: —
Progress: 0 / 0
Tools added: 0 (기준 58)
Last update: 2026-04-19 (초기화)
```

## Phase E 진행 (Task 1 ~ 16)

| Task | 제목 | 상태 | 타임스탬프 | 비고 |
|---|---|---|---|---|
| 1 | Prerequisite 상태 확인 | ⏳ | — | pytest/sync/phase A~C 참조 |
| 2 | NavMesh Viz API 3 후보 조사 | ⏳ | — | `isaac_course/docs/navmesh_viz_research.md` 작성 |
| 3 | sensor_module 골격 | ⏳ | — | ModuleName.SENSOR 추가 |
| 4 | sensor_attach_rtx_camera | ⏳ | — | +1 tool |
| 5 | sensor_attach_rtx_lidar | ⏳ | — | +1 tool |
| 6 | sensor_attach_rtx_depth_camera | ⏳ | — | +1 tool |
| 7 | sensor_set_visualization | ⏳ | — | +1 tool |
| 8 | viewport_create + viewport_destroy | ⏳ | — | +2 tool |
| 9 | navigation_set_visualization | ⏳ | — | +1 tool |
| 10 | Scenario YAML smoke + integration | ⏳ | — | 6 YAML |
| 11 | Live 검증 스크립트 | ⏳ | — | 3 스크립트 |
| 12 | 전체 pytest 통과 | ⏳ | — | — |
| 13 | Catalog sync (58→65) | ⏳ | — | `verify_mcp_sync.py` |
| 14 | 도메인 CLAUDE.md 동기화 | ⏳ | — | `modules/`, `isaac_extension/` |
| 15 | phase-e-validation-report.md | ⏳ | — | — |
| 16 | Phase E 완료 체크 + 보고 | ⏳ | — | — |

## PPTX 진행 (Task 1 ~ 15)

| Task | 제목 | 상태 | 타임스탬프 | 비고 |
|---|---|---|---|---|
| 1 | isaac_course 초기화 | 🟡 부분완료 | 2026-04-19 | 구조/CLAUDE.md/README 선행 작성됨. live asset_list 추가 필요 |
| 2 | Asset inventory 실측 | ⏳ | — | `asset_list` 순회 → `asset_inventory.md` ✓ 확정 채우기 |
| 3 | capture_helpers.py | ⏳ | — | — |
| 4 | UI/Browsers/Examples 캡처 | ⏳ | — | 슬라이드 3~5 |
| 5 | Categories 캡처 | ⏳ | — | 슬라이드 6~9 |
| 6 | Asset Sampler 캡처 | ⏳ | — | 슬라이드 10 |
| 7 | Recipe 플로우 섬네일 | ⏳ | — | 슬라이드 11 |
| 8 | Twin 1 Build + 캡처 | ⏳ | — | 슬라이드 12~17 |
| 9 | composite_multi_panel.py | ⏳ | — | 4-panel 합성 |
| 10 | Twin 2 Build + 캡처 | ⏳ | — | 슬라이드 18~21 |
| 11 | Twin 3 Build + 캡처 | ⏳ | — | 슬라이드 22~25 |
| 12 | Save/Reuse + Comparison 캡처 | ⏳ | — | 슬라이드 26~27 |
| 13 | pptxgenjs render_pptx.js | ⏳ | — | 28 슬라이드 조립 |
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
| — | — | (아직 없음) |

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
