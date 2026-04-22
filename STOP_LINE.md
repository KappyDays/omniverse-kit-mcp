# STOP_LINE — 2026-04-23 03:25

## 트리거
**조건 #4** (자율 운영 정책) — "동일 증상 자동 수정 시도 4회 이상 실패":
NavMesh Playground Extension 의 **People spawn 후 ~10s 내 kit.exe silent crash** 가 4회 연속 재현. 4가지 자동 수정 모두 동일 결과.

## 현재 상태
- 마지막 완료 Task: **Phase 2 Task 2.6** (Extension skeleton + Load Warehouse + NavMesh Bake live verification — commit `22600f2`)
- 다음 대기 Task: **Phase 3 Task 3.1 Step 5** (People Walk→Sit live smoke). Phase 3 코드 작성 완료 (people_controller.py + ui_panel agent rows + extension wiring) 되어 있으나 spawn live 검증 단계에서 막힘.
- git HEAD: `22600f2` (Phase 2 마지막 commit). Phase 3 변경은 아직 uncommitted (working tree).
- pytest: 357 passed (Phase 1 시점, 변동 없음).

## 증상 / 근거

### 재현 시나리오 (4회 모두 동일)
1. `isaac_sim_start` (standalone, 15s) → activate `omni.mycompany.navmesh_playground` → window_ui_show.
2. Load Warehouse click → /World/Warehouse OK (19s, 정상).
3. simulation_stop → Bake click (1.5~2.4s, click 자체는 정상).
4. Spawn @ Random Walkable click (Type=People, count=1, sit=SitIdle) → 2~4s 응답.
5. **~10s 후 tasklist 에 kit.exe 없음** (silent termination).

### Kit log 분석 (`kit_20260423_032225.log` 마지막 entry)
```
[75,283ms] [Warning] [omni.hydra] Mesh '/World/Characters/Biped_Setup/biped_demo_meters/Body_Mesh' update topology/point without updating normal, fallback to smooth normal.
[75,292ms] [Warning] [omni.fabric.plugin] Warning: attribute animationGraph not found for path /World/Characters/People_01/female_adult_business_02/ManRoot/female_adult_business_02
[75,463ms] [Info] [omni.physx.plugin] Physics USD: Physics scene not found. A temporary default PhysicsScene prim was added automatically!
[75,606ms] [Warning] [omni.anim.asset] Animation graph '/World/Characters/Biped_Setup/CharacterAnimation' is not assigned a valid skeleton
[75,606ms] [Warning] [omni.anim.asset] Failed to compile asset '/World/Characters/Biped_Setup/CharacterAnimation':
```
이후 로그 안 쓰임. Kit silent termination.

### 자동 수정 시도 4회
1. `safe_load_character` 를 spec §8.4 패턴 → character_service.load 검증 패턴 (CharacterUtil + 별도 Biped_Setup) 으로 재작성.
2. UI button callback `asyncio.ensure_future` → `omni.kit.async_engine.run_coroutine` 변경.
3. `navmesh_sampler.sample_walkable_points` sync → async 화 + Kit main loop yield 추가.
4. `_wait_stage_loading` 의 `UsdContext.is_new_stage_loading()` (Kit 5.1 부재 attribute) → `isaacsim.core.utils.stage.is_stage_loading` 수정.

## 재개에 필요한 사용자 결정

1. **Phase 3 spawn 경로 변경**: People spawn 을 navmesh_playground extension 내부에서 직접 처리하는 대신, MCP `character_load` (validation_api 검증 경로) 호출로 바꿀까? 즉 navmesh_playground UI 는 MCP 서버에 spawn request 만 보내고, 실제 character_load 는 validation_api 가 처리. 이는 spec §"독립 구조" 정책의 약한 위반이지만, character_service.load 가 동일 단계로 안정 동작하는 검증된 코드이므로 가장 빠른 해결책.

2. **Phase 4 진행 결정**: Phase 3 People 이 막혔지만 Phase 4 Robot 은 다른 코드 경로 (DifferentialController + 물리 바퀴, character 없음). Phase 3 보류 + Phase 4 진행 → Phase 5 시 Robot 만 검증한 부분 Scenario 가능.

3. **`character_service.load` 의 정확한 binding sequence 재현**: 위 수정 #1 에서 character_service.load 를 1:1 모방했음에도 silent crash. 이는 (a) UI button callback vs FastAPI handler 의 event loop 환경 차이, (b) 어떤 implicit state (예: `_log_capture`, simulation_play 상태) 가 character_service 호출 전에 ensured, 인 것일 수 있음. character_service.load 의 더 deep 한 prerequisite 를 검증해 봐야 함.

## 관련 참조

- issues 상세: `docs/implementation_issues.md#i1`
- artifacts: 본 stop-the-line 시점 viewport PNG 없음 (Kit 가 이미 죽어서 capture 불가). 
- Kit log: `C:\Users\<you>\.nvidia-omniverse\logs\Kit\Isaac-Sim Full\5.1\kit_20260423_032225.log` (75,606ms 시점 AnimGraph compile fail 이후 silent crash)
- spec: `docs/superpowers/specs/2026-04-23-navmesh-playground-design.md` §8.3a People FSM, §8.4 USD loader
- plan: `docs/superpowers/plans/2026-04-23-navmesh-playground-plan.md` Phase 3 Task 3.1 Step 1~5
- 비교 검증된 코드: `isaac_extension/omni.mycompany.validation_api/omni/mycompany/validation_api/services/character_service.py:63` (load), `:828` (_ensure_biped_setup), `:870` (_wait_stage_loading)

## 진행 가능한 영역 (사용자 승인 시)

본 STOP_LINE 동안 commit 안 된 Phase 3 임시 변경:
- `isaac_extension/omni.mycompany.navmesh_playground/omni/mycompany/navmesh_playground/people_controller.py` (신규)
- `isaac_extension/omni.mycompany.navmesh_playground/omni/mycompany/navmesh_playground/usd_loader.py` (safe_load_character 재작성, _wait_stage_loading 수정)
- `isaac_extension/omni.mycompany.navmesh_playground/omni/mycompany/navmesh_playground/navmesh_sampler.py` (async 화)
- `isaac_extension/omni.mycompany.navmesh_playground/omni/mycompany/navmesh_playground/ui_panel.py` (spawn callback + agent rows + reset all)
- `isaac_extension/omni.mycompany.navmesh_playground/omni/mycompany/navmesh_playground/extension.py` (PeopleController wire)

이 변경들은 기능적으로 silent crash 까지는 가는 정도 — commit 시 Phase 3 partial. 사용자 결정 시까지 working tree 에 보존.
