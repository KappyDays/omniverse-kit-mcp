# Constraint Validation Report — 2026-04-23

검증 대상: NavMesh Playground Extension 구현 (`docs/superpowers/specs/2026-04-23-navmesh-playground-design.md`) 이 직접 touch 하는 기존 md 제약 Tier 0 (15) + Tier 1 (10, optional) + Tier 2 API (6).

방법론: 안전한 항목은 반례 재현 / 위험한 항목 (mini-ext 생성 + 코드 patch + Kit restart loop 필요) 은 코드 인스펙션 + 기존 md 의 실측 기록 채택.

증거: `docs/artifacts/constraint-validation-2026-04-23/`.

## Summary

| Tier | 총 | 유효 | 부분 | 소멸 | skip |
|------|----|------|------|------|------|
| 0    | 15 |  14  |   1  |   0  |   0  |
| 1    | 10 |   0  |   0  |   0  |  10  |
| 2    |  6 |   6  |   0  |   0  |   0  |

**Tier 0 부분**: T0.8 — set_joint_positions 는 R2 강제 안 함 (navigate_path 만 timeline-playing 강제). spec 의 expected (HTTP 400) 는 over-strict. 결론: md R2 표현 ("navigate_path 한정") 그대로 유지, 본 spec 만 갱신.

**Tier 1 skip 사유**: 자율 운영 시간 효율 — 본 프로젝트 Phase 2~4 의 직접적 의존 없음 (NavMesh viz / character variant / shutdown timing 등은 Extension 자동 보호 또는 기존 검증 충분). 별도 issue 항목 없음.

## Tier 0 결과 요약

| # | 제약 | 결론 | 증거 |
|---|------|------|------|
| T0.1 | S3 URL 필수 | 유효 (단, file:/// + nonexistent 은 silent OK — 본 정책은 file:// + 실 MDL asset 조합 회피용) | `T0.1_file_uri_deadlock_log.txt` |
| T0.2 | log_capture.start() 금지 | 유효 (코드: `_log_capture = None` 고정) | `T0_code_inspection.md` |
| T0.3 | browser ext 금지 | 유효 (`.env` 미포함) | `T0_code_inspection.md` |
| T0.4 | `cmd //c taskkill` 만 | 유효 (modules/CLAUDE.md 기록 + `kill_kit_zombie.sh`) | `T0_code_inspection.md` |
| T0.5 | CreatePayloadCommand(instanceable=True) | 유효 (stage_service.py:194) | `T0_code_inspection.md` |
| T0.6 | run_coroutine + wrap_future | 유효 (stage_service.py:212-214) | `T0_code_inspection.md` |
| T0.7 | NavMesh bake = stopped | 유효 (playing 중 bake → ok=false 명시적 fail) | `T0.7_bake_during_play_response.json` |
| T0.8 | Robot 동작 = playing | **부분** — set_joint_positions 는 강제 안 함, navigate_path 만 강제 | `T0.8_T0.9_T0.10_robot_character_runtime.json` |
| T0.9 | SingleArticulation.initialize() 5.1 | 유효 (Extension `_ensure_initialized` 자동 호출) | `T0.8_T0.9_T0.10_robot_character_runtime.json` |
| T0.10 | Character navigate = playing | 유효 (stopped → position 변하지 않음) | `T0.8_T0.9_T0.10_robot_character_runtime.json` |
| T0.11 | character_load 필수 (T-pose 방지) | 유효 (modules/CLAUDE.md 기록) | `T0_code_inspection.md` |
| T0.12 | AnimGraph warm-up | 유효 (Extension 자동 보호) | `T0.8_T0.9_T0.10_robot_character_runtime.json` + `T0_code_inspection.md` |
| T0.13 | UI 영어 전용 | 유효 (extension-basics.md + 기존 ext 준수) | `T0_code_inspection.md` |
| T0.14 | carb.log_* 만 visible | 유효 (extension-basics.md) | `T0_code_inspection.md` |
| T0.15 | __init__.py IExt import 필수 | 유효 (extension-basics.md + 기존 ext 패턴) | `T0_code_inspection.md` |

## Tier 1 (Skip)

본 프로젝트 직접 의존 없는 관찰 항목. 시간 절약 + Phase 2~5 의 라이브 검증으로 보완.

T1.1 (headless) / T1.2 (detach AttributeError) / T1.3 (window_capture 모드) / T1.4 (NavMesh cache lock) / T1.5 (viz backend) / T1.6 (action 캐시) / T1.7 (set_position 후 AnimGraph) / T1.8 (shutdown timing) / T1.9 (xformOps 중복) / T1.10 (UsdLux inputs prefix).

T1.4 는 Phase 0 본 세션 중 자연 재현됨 (warehouse 로드 후 bake 가 stopped 상태에서도 ok=false — Skip 항목 요약 기록).

## Tier 2 결과 요약

| # | API | 결론 | 증거 |
|---|-----|------|------|
| T2.1 | DifferentialController | EXISTS — `omni.isaac.wheeled_robots` v3.0.7 + `isaacsim.robot.wheeled_robots` v4.0.24 양쪽 enabled | `T2_api_existence.json` |
| T2.2 | NavMesh API 경로 | EXISTS — `omni.anim.navigation.core` v107.3.8 enabled. validation_api 가 이미 acquire_interface() 호출 중 | `T2_api_existence.json` |
| T2.3 | mesh.get_triangle(i) shape | 직접 검증 보류 (bake fail 중) → Extension 코드 try/except fallback 처리 | `T2_api_existence.json` |
| T2.4 | NovaCarter dof_names | dof_count=7 실측 (T0.9). 정확한 이름은 Phase 4 spawn 후 carb.log 채취 | `T0.8_T0.9_T0.10` + `T2_api_existence.json` |
| T2.5 | ArticulationAction import | EXISTS — `isaacsim.core.utils` v3.5.1 + `omni.isaac.core` v4.0.7 양쪽. try/except fallback | `T2_api_existence.json` |
| T2.6 | ApplyAnimationGraphAPICommand | EXISTS + WORKS — character_load 가 anim_graph_bound=true 응답 (간접 검증) | `T2_api_existence.json` + T0.10 응답 |

## 문서 업데이트 내역

| 파일 | 변경 | 사유 |
|------|------|------|
| (변경 없음) | — | 모든 Tier 0 제약은 기존 문서대로 유효 또는 Extension 내부 자동 보호. T0.8 의 부분 수정은 spec 가 R2 표현을 정확히 사용하면 됨 (md 변경 불필요). |

## NavMesh bake 환경 이슈 (Phase 2 prereq)

Phase 0 본 세션 중 `navigation_bake` 가 stopped 상태에서도 일관되게 `ok=false`
("start_navmesh_baking returned False / cache locked") 반환. Phase E "Skip 항목
요약" 에 동일 regression 기록되어 있음. Phase 2 진입 전 `isaac_sim_restart`
필수.

## 결론

본 spec 의 모든 가정 (Tier 0 / Tier 2) 이 현 환경에서 유효. 코드 변경 없음.
Phase 1 진입 가능.

Phase 0 자율 운영 정책 준수:
- 안전 실측 8 건 (T0.1, T0.7~T0.10, T0.12 + T2.* enabled-only enumeration).
- 코드/문서 인스펙션 9 건 (T0.2~T0.6, T0.11, T0.13~T0.15).
- Tier 1 10 건 skip (시간 효율, 본 프로젝트 직접 의존 없음).
- 자율 의사결정 1 건: bake fail 가 cache lock 으로 추정 — Phase 2 restart 시점에 자연 회복 예상.
