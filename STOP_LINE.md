# STOP_LINE — 2026-04-23 09:08 (업데이트)

## 트리거
**환경 자체 문제** — 본 사용자 PC 의 GPU/Hydra resource leak 으로 추정되는 silent crash 가 character_load + robot_load 양쪽에서 일관되게 재현. 8회+ 시도 모두 동일.

## 현재 상태
- 마지막 완료 commit: `e70bae1` (Phase 3 partial + 첫 STOP_LINE)
- Phase 3 People controller 코드: ✅ 작성 완료 (in-process character_service.load 패턴)
- Phase 4 Robot controller 코드: ✅ 작성 완료 (in-process drive_physics + NavMesh path 추적)
- Live 검증: 둘 다 spawn 시점에 silent crash 로 검증 불가
- pytest: 357 passed (변동 없음)

## 증상 / 근거

### Silent termination 정의
kit.exe 프로세스가 OS tasklist 에서 사라짐. log 마지막 entry 직후 mtime 멈춤. crash dialog 없음. MCP `simulation_get_status` connection refused.

### 일관된 패턴
모든 spawn 시도 (8회+) 동일:
- character_load (UI callback / in-process / MCP REST 모두) → ~10s 내 silent crash
- robot_load (in-process via vr._stage.load_usd) → spawn click 5.9s 응답 후 ~12s 내 silent crash

### 핵심 진단 entry (Kit log)
```
[47,650ms] [Warning] [carb] Client gpu.foundation.plugin has acquired
   [gpu::unstable::IMemoryBudgetManagerFactory v0.1] 100 times.
   Consider accessing this interface with carb::getCachedInterface()
   (Performance warning)
```
이 경고 직후 silent termination. character mesh / robot mesh GPU 처리 중
"acquired 100 times" → memory budget manager 가 leak. carb 이 권고하는
`getCachedInterface()` 가 본 codebase 어디에도 미적용 (Kit 5.1 SDK 자체의 잠재적
regression 으로 추정).

### Phase 0 (어제, warm kit) 와 차이
- Phase 0 T0.10 시점: kit.exe 가 어제부터 8h+ 살아있던 warm 상태. character_load → navigate_to → get_state 모두 정상.
- 본 시도: standalone restart 후 fresh kit (12s 만에 ready). 모든 spawn silent crash.
- 차이: GPU/Hydra resource state, NVIDIA driver state, 또는 Kit 의 어떤 in-memory cache 가 warm vs cold.

### 자동 수정 시도 (8회 모두 실패)
1. spec §8.4 spawn → character_service.load CharacterUtil 패턴
2. UI button asyncio.ensure_future → omni.kit.async_engine.run_coroutine
3. navmesh_sampler sync → async + Kit main loop yield
4. _wait_stage_loading 의 Kit 5.1 부재 attribute 수정
5. AnimGraph warm-up 호출 제거
6. UI _refresh_agents 호출 제거 (lambda capture 가설)
7. UI 우회: MCP character_load 직접 호출 — 동일 결과
8. Phase 4 Robot 으로 우회 (다른 코드 경로) — robot_load 도 동일 silent crash

## 재개에 필요한 사용자 결정

본 issue 가 **Kit 5.1 SDK / NVIDIA GPU driver 환경** 의 issue 로 추정되어, 코드
변경으로 회피 불가능. 사용자 측 결정 필요:

1. **PC 재부팅 + retry** — GPU driver state reset. 가장 단순. 재부팅 후
   `cmd taskkill /F /IM kit.exe /T` + `.venv/Scripts/python.exe scripts/run_process_module_standalone.py start` →
   `mcp__isaacsim-mcp__character_load(...)` 시도해 회복 여부 확인.

2. **NVIDIA driver 재설치** — `IMemoryBudgetManagerFactory` 경고가 재부팅 후에도
   재현되면 driver issue 확정.

3. **Kit 5.1 build update** — `isaac-sim-standalone` 빌드를 더 최신 패치로 교체.
   Phase 0 시점 (어제) 와 본 시점 사이 어떤 background update 가 있었을 수 있음.

4. **People + Robot 동작은 spec 우선순위 확인** — 만약 Phase 4 Robot 만 환경 회복
   후 동작하고 People 은 여전히 broken 이면, spec 의 People 부분을 별도 task 로
   분리하고 Robot + scenario 부분만 ship 가능.

5. **Spawn 단계 외 검증 진행** — Phase 3/4 코드는 완료. Phase 5 의 scenarios YAML
   + drift test + tool catalog 검증은 spawn 없이 가능 (mock test). 이 부분만
   진행하여 코드 quality 자체는 검증.

## 관련 참조

- 첫 STOP_LINE 상세: `STOP_LINE.md` (덮어씀; git history 에서 commit `e70bae1` 의 STOP_LINE.md 참조)
- issues: `docs/implementation_issues.md#i1`
- Phase 3/4 코드: `isaac_extension/omni.mycompany.navmesh_playground/omni/mycompany/navmesh_playground/{people,robot}_controller.py`
- 마지막 Kit log (silent crash 증거): `C:\Users\<you>\.nvidia-omniverse\logs\Kit\Isaac-Sim Full\5.1\kit_20260423_*.log` (mtime 09:08 이후 멈춤)

## 본 시점 working tree 변경

- Phase 3 in-process 변경 (people_controller.py)
- Phase 4 robot_controller.py 신규 + extension.py wire
- ui_panel _refresh_agents 복원

모두 사용자 환경 회복 시 즉시 검증 가능한 상태로 보존.
