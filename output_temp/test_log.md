# Phase C 재검증 로그 (2026-04-18)

**목적**: 사용자 질문에 대한 정직한 답변 + 실제 동작 검증. 초기 smoke scenario (`scenarios/smoke/character_control.yaml`) 은 15/15 PASSED 였으나 다음 한계가 있었음:

1. Biped_Setup rig (시각 X) 만 테스트
2. Viewport capture 검은색 (기본 조명/카메라 미설정)
3. Timeline paused 상태에서 navigate → 실제 이동 0m (30s timeout 으로 PASS)
4. MCP tool 경로 미검증 (서버 import cache 로 `character_*` tool UI 노출 X)

## 2차 재검증 (2026-04-18 오후)

사용자가 출력물 검토 후 다음 요청:
1. PNG 4 는 Walk 중 캡처로 보이지만 실제로는 Idle → 재캡처
2. L2 (get_state.action="[]") 수정
3. L1 ("불가피" 표현) 정밀 설명

### L2 수정 — `_last_action` 캐시 추가

**Commit**: (이번 세션 commit 참조)

`CharacterService.__init__` 에 `_last_action: dict[str, dict[str, Any]]` 추가. `play_animation` / `stop_animation` 이 per-SkelRoot 경로로 last action + walk_speed 기록. `get_state` 가 **캐시 우선 조회**, fallback 으로 AnimGraph variable.

**Live 검증**:
- fresh load 직후 (fallback 경로): `action: "Idle"`, `is_navigating: false`
- play_animation(Walk) 후: `action: "Walk"`, `is_navigating: true` ✅
- play_animation(Sit) 후: `action: "Sit"`, `is_navigating: false` ✅
- stop_animation 후: `action: "Idle"`, `is_navigating: false` ✅

### L1 정밀 설명 — "불가피" 는 과장된 표현. 정확한 거동

**내 이전 주장** (부정확): "AnimGraph 가 매 프레임 xformOp:translate 를 덮어씀"

**실제 거동** (2026-04-18 live 재검증):

1. `character.set_position([x,y,z])` → Extension `character_service.set_position`
2. `SingleXFormPrim.set_world_pose([x,y,z])` 가 **USD 의 xformOp:translate 를 정상적으로 씀**
3. `SingleXFormPrim.get_world_pose` readback 도 [x, y, z] 를 반환 (response 에 echo)
4. 여기까지는 성공. 그러나 **다음 timeline tick 에서 AnimGraph 가 자체 계산한 world transform 으로 xformOp:translate 를 덮어씀**
5. `character.get_state` (다음 tick 이후) 는 `ag.get_character(skel).get_world_transform()` 로 읽는데, 이는 AnimGraph 내부 state 기준

**AnimGraph 내부 state 갱신 트리거** (live 관찰):
- `character.load(..., position=[x,y,z])` — 로드 시 초기 위치 설정 (작동)
- `character.navigate_to(target=[x,y,z])` — PathPoints 경로 따라가며 도착 시 target 을 새 내부 state 로 기록 (작동)
- `character.set_position([x,y,z])` — USD 에는 쓰지만 AnimGraph 내부 state 는 **업데이트 안 됨** → 다음 tick 에 원래 state 로 복원

**증거 (live)**:
- `set_position([1, 1, 0])` 호출 (character 가 [5, 3, 0] 에 있을 때)
- response: `{"position":[1, 1, 0]}` (readback 성공)
- 다음 tick (simulation.play 1s) 후 `get_state`: `[5, 3, 0]` ← AnimGraph 가 자체 state 로 복원

**"불가피" 는 틀림 — 가능한 회피법**:

| 방법 | 설명 | 실용도 |
|------|------|--------|
| A. `character.load(..., position=[x,y,z])` | 초기 로드 시 설정 | 로드 시점만 가능 |
| B. `character.navigate_to(target=[x,y,z])` | PathPoints 경로로 유도, 도착하면 AnimGraph state 업데이트 | **추천** — scenario 에서 traversal 검증 가능 |
| C. Unbind AnimGraph → set_position → rebind | `DeleteAnimationGraphAPICommand` (추정) | 파괴적, graph state 손실 |
| D. AnimGraph 에 "teleport" API 가 있다면 | `graph.set_variable("Root Position", [...])` 같은 것 | **미검증 — omni.anim.graph.core 문서 추가 조사 필요** |
| E. `stop_animation` → 일정 시간 후 set_position | AnimGraph 가 Idle 에서 tick 하더라도 root 복원하는지 | **작동 안 함 — 테스트에서 확인** |

**결론**: `set_position` API 자체는 USD 레벨 속성 쓰기에 유용 (snapshot / auditing / stage_save-reload). 시각 이동이 목적이면 `navigate_to` 를 써야 한다. API 계약은 "USD-level write succeeds + AnimGraph overrides on next tick" 로 문서화. `set_position` 을 완전 제거할 수도 있지만 USD 검증 시나리오 (예: "/World/Characters/X/xformOp:translate == [0,0,0] 로 stage_save" 의 arrange) 에서 활용 가능하므로 유지.

**Phase C+ polish 후보**: AnimGraph 에 teleport-equivalent variable 조사. 있다면 `character.set_position` 이 내부적으로 그걸 부르도록 수정.

## 3차 재검증 캡처 (2026-04-18)

L2 수정 + 재캡처 후 output_temp/ 최종:

| 파일 | 내용 | 검증 |
|------|------|------|
| `01_empty_scene_with_camera_light.png` | 내가 만든 /World/Cam (rotation 미설정) → 하늘 봄 → 검은색 | 실패 기록 |
| `02_scene_with_dome_light.png` | DomeLight 추가, viewport_capture 재캐시 (sha256 동일 반복) | 실패 기록 |
| `03_f_business_loaded.png` | F_Business 로드됐으나 capture 여전히 동일 cache 반환 | 실패 기록 |
| `03_two_characters_loaded.png` | **/OmniverseKit_Persp 전환 후 — 두 캐릭터 시각 확인** (좌 DH UUID 건설작업자, 우 F_Business 비즈니스여성) | ✅ 로드 성공 |
| `04_OLD_walk_completed_idle.png` | 이전 라벨링 오류 (sleep 4s 가 Walk 완료 후 Idle pose) | rename 로 구분 |
| `04_walking_actually_moving.png` | **✅ Walk 중 stride pose** — F_Business [0,0,0]→[3,0,0] 이동 중 0.8s 지점, 오른발 앞 왼발 뒤 stride 명확 | 의도대로 |
| `05_after_navigate.png` | DH 캐릭터 [3,0,0]→[5,0,0] navigate 완료, 화면 밖 이동 (F_Business 만 남음) | traversal 증거 |
| `06_sitting_pose.png` | **✅ Sit pose** — 무릎 굽힘, 엉덩이 낮춤, 명확한 앉은 자세. get_state `action:"Sit"`, `is_navigating:false` | L2 fix + Sit 의도대로 |

## 1차 재검증 결과 (참고용)

기존 기록 유지. 아래는 1차 재검증에서 발견된 것들:

### 테스트 대상 asset (S3, Nucleus 불필요)

| 경로 | 설명 | 결과 |
|------|------|------|
| `.../People/Characters/Biped_Setup.usd` | AnimationGraph + skeleton rig (시각 X) | 이전 smoke 에서 검증 |
| `.../People/Characters/F_Business_02/F_Business_02.usd` | Female business 캐릭터 (728 KB, 텍스처 포함) | ✅ 로드 성공, 시각 확인 |
| `.../People/DH_Characters_Extended/02c80685-.../02c80685-...usd` | DH UUID 건설 작업자 (UUID 기반) | ✅ sanitize 후 로드 성공 |

### Bug 발견 & 수정 (1차) — `_sanitize_prim_name` 누락

`character_service.load()` 가 `requested_prim_path` 있을 때 `_sanitize_prim_name` 을 skip. DH UUID 하이픈 → USD path 검증 실패. 수정: 양쪽 branch 모두 sanitize. (commit `3bc7cd0`)

## 알려진 한계 (최종 상태)

| # | 한계 | 상태 |
|---|------|------|
| L1 | `set_position` 이 AnimGraph-bound 캐릭터 시각 이동 못시킴 | **문서화** — "USD-level write + AnimGraph override" 로 계약 명시. navigate_to 로 회피 |
| L2 | `get_state.action` 항상 `"[]"` | **수정 완료** (이번 세션) — `_last_action` 캐시 |
| L3 | Timeline paused navigate 는 0m 이동 | **문서화** — scenario 저자가 `simulation.play` 명시 |
| L4 | Viewport capture baseline dark/empty | **문서화** — DomeLight + /OmniverseKit_Persp 권장 |
| L5 | viewport_capture 재캐시 (동일 sha256 반복) | **문서화** — Isaac Sim 5.1 known bug |
