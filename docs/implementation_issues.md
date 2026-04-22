# Implementation Issues — NavMesh Playground (Phase J)

## I1 — People spawn 후 Kit silent crash (Phase 3, 2026-04-23)

**증상**: NavMesh Playground extension 의 Spawn @ Random Walkable (Type=People, count=1) 클릭 후, ~10s 이내에 kit.exe 가 silent termination. 회복 후 동일 시도 4회 연속 동일 결과.

**시도한 자동 수정**:
1. people_controller 의 `safe_load_character` 가 spec §8.4 패턴 (Biped + skin 을 동일 prim_path child) 사용 → character_service.load 의 검증된 패턴 (CharacterUtil + 별도 Biped_Setup at /World/Characters/Biped_Setup) 으로 재작성.
2. UI button callback `asyncio.ensure_future(_run())` → `omni.kit.async_engine.run_coroutine(_run())` 로 변경 (Kit main loop 직접 schedule).
3. `navmesh_sampler.sample_walkable_points` 를 sync → async 화 + 5 attempts 마다 `app.next_update_async()` yield.
4. `_wait_stage_loading` 가 `UsdContext.is_new_stage_loading()` (Kit 5.1 부재 attribute) 호출 → `isaacsim.core.utils.stage.is_stage_loading` 사용으로 수정.

**Kit 로그 진단** (마지막 entry: `kit_20260423_032225.log`):
```
[75,283ms] [Warning] [omni.hydra] Mesh '/World/Characters/Biped_Setup/biped_demo_meters/Body_Mesh' update topology/point without updating normal, fallback to smooth normal.
[75,292ms] [Warning] [omni.fabric.plugin] Warning: attribute animationGraph not found for path /World/Characters/People_01/female_adult_business_02/ManRoot/female_adult_business_02
[75,463ms] [Info] [omni.physx.plugin] Physics USD: Physics scene not found. A temporary default PhysicsScene prim was added automatically!
[75,606ms] [Warning] [omni.anim.asset] Animation graph '/World/Characters/Biped_Setup/CharacterAnimation' is not assigned a valid skeleton
[75,606ms] [Warning] [omni.anim.asset] Failed to compile asset '/World/Characters/Biped_Setup/CharacterAnimation':
```

이후 **로그 더 이상 안 쓰임** (mtime stops). tasklist 에 kit.exe 없음 — silent termination.

**가설 (검증 안 됨)**:
- (a) AnimGraph compile fail 후 carb 또는 omni.anim 의 cleanup 경로에서 Python GIL 또는 deadlock-recipe deadlock 변종 trigger.
- (b) `ApplyAnimationGraphAPICommand` 의 `paths=[skel_root_path]` 이 valid 한 SkelRoot 임에도, Biped_Setup 의 AnimationGraph 가 character 의 skeleton 과 binding 시점에 mismatch — 이는 character_service.load 와 동일한 sequence 임에도 다른 결과.
- (c) UI button callback 환경 vs FastAPI handler 환경의 미세한 event loop / threading 차이 — character_service 는 항상 FastAPI 에서 호출되므로 검증되지 않은 코드 경로.

**Stop-the-line 트리거**: 본 STOP_LINE 작성 시점 기준, 같은 증상 (`People spawn → ~10s 후 silent kit termination`) 자동 수정 시도 4회 모두 실패. 자율 운영 정책 #4 ("동일 증상 자동 수정 시도 4 회 이상 실패") 충족.

**필요한 사용자 결정**:
1. character_service.load 를 navmesh_playground 가 직접 호출하도록 독립 정책 일시 완화 (실제로는 `from isaacsim.replicator.agent.core.stage_util import CharacterUtil` 직접 import 가 가능하므로 정책 위반은 아님; 위 수정 #1 이 이미 적용됨에도 동일 증상).
2. UI callback → MCP REST 분리: People spawn 을 UI 가 직접 호출하지 않고, Extension 내부 REST endpoint 를 추가해 ASYNC Job 으로 처리 (validation_api 스타일).
3. spec §8.3a 의 People FSM 자체를 단순화: 직접 character_load (validation_api MCP) 호출 → AnimGraph 가 자동으로 binding 보장. 즉 navmesh_playground extension 은 spawn 만 trigger 하고 character_load 는 외부 호출 통과.

## 회복 절차 (재현 시)

```bash
cmd //c "taskkill /F /IM kit.exe /T"
cmd //c "taskkill /F /IM hub.exe /T"
.venv/Scripts/python.exe scripts/run_process_module_standalone.py start
```
