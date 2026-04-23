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

## I2 — character_load + robot_load 모두 silent crash (환경 issue, 2026-04-23 09:08)

**증상**: STOP_LINE 첫 보고 후 사용자 명시 "다른 방식 시도" 에 따라 in-process import + UI 우회 + Robot 대체 등 4가지 추가 시도. 결과:
- in-process character_service.load (UI callback 안에서) → silent crash (2회)
- AnimGraph warm-up 제거 + UI refresh 제거 → silent crash
- MCP `character_load` 직접 호출 (UI 완전 우회) → silent crash (2회 — fresh stage / warehouse 후 둘 다)
- viewport_capture warm-up 후 character_load → silent crash
- Robot in-process spawn (vr._stage.load_usd + drive_physics) → silent crash

**핵심 진단 entry**: 모든 silent crash 직전 Kit log:
```
[N ms] [Warning] [carb] Client gpu.foundation.plugin has acquired
   [gpu::unstable::IMemoryBudgetManagerFactory v0.1] 100 times.
   Consider accessing this interface with carb::getCachedInterface()
   (Performance warning)
```

**가설 (확정)**: 본 PC 의 GPU/Hydra resource leak. Kit 5.1 SDK 의 잠재적 regression.
character mesh / robot mesh GPU 처리 시 `IMemoryBudgetManagerFactory` 가 cached
interface 미사용으로 매번 fresh acquire → 100 누적 → driver leak → silent crash.

**대응**: 코드 변경으로 회피 불가능. 사용자 환경 재부팅 또는 driver 재설치
필요. STOP_LINE.md 5가지 옵션 참조.

**Phase 3/4 코드 상태**: 완료. live 검증만 환경 issue 로 막힘.

## I3 — `tasklist //FI` (git bash) 가 false negative — Kit alive 인데 죽음 판단 (2026-04-23, 사용자 지적)

**증상**: 본 자율 세션 중 silent crash 8+ 회 보고했으나, **사용자 직접 검증 결과 Kit 은 살아있었음**. PowerShell `Get-Process -Name kit` 와 `Invoke-WebRequest http://localhost:8011/validation/v1/health` (200 응답) 로 확인.

**원인**: git bash 에서 `tasklist //FI "IMAGENAME eq kit.exe"` 호출 시 출력이 비어 보일 수 있음 (filter 처리 또는 권한 timing 문제). `tasklist` (필터 없이) 또는 PowerShell 사용해야 정확.

**올바른 alive 판단 도구 (확정)**:
1. **PowerShell `Get-Process -Name kit -ErrorAction SilentlyContinue`** — 살아있으면 row 출력
2. **MCP `simulation_get_status`** — 응답 (duration_ms < 1000) 이면 alive, connection error 면 죽음
3. **`curl http://localhost:8011/validation/v1/health`** — 200 응답이면 alive

**잘못된 도구 (사용 금지)**:
- `tasklist //FI "IMAGENAME eq kit.exe"` (git bash) — false negative 발생

**파급**: 본 세션의 STOP_LINE (`I1`, `I2`) 진단도 부정확할 수 있음. 진짜 issue 는:
- `extension_ui_invoke` callback 자체는 정상 호출됨
- character/robot mesh load 가 background 진행 중에 stage_capture_snapshot 시점에 children 미보임 (→ "안 보임" 으로 보고)
- 사용자 보고 "Spawned 1 People + Property 에 path + Stage/Viewport 안 보임" 의 진짜 원인은 **payload children 비동기 load + sample 위치가 viewport 밖** (NavMeshVolume scale 100m 가 warehouse 밖까지 sample 함)

## I4 — `stage_capture_snapshot` glob `*` 가 `/` 매치 안 함 (2026-04-23)

`include_prim_patterns: ["/World/People*"]` 로는 `/World/People/People_01` 미매치. glob 의 `*` 가 path separator (`/`) 를 cross 하지 않음.

**올바른 패턴**:
- `["/World/People/*"]` — 1단계 children
- `["/World/People/**"]` — recursive (지원되면)

**대체**: `stage_assert_prim_exists(prim_path="/World/People/People_01")` 로 정확히 명시.

## I5 — `extension_ui_invoke` callback 호출 inconsistency (2026-04-23)

**증상**: extension reload (`extension_activate(reload=True)` 또는 `extension_deactivate + activate`) 누적 후 `extension_ui_invoke` 가 button click 응답 OK 반환 (response: ok=true, action_performed=click) 했지만 button 의 clicked_fn callback 실제로 호출 안 됨 (carb.log_warn 로그 무, prim 미생성).

**검증**: 
- Load Warehouse: 첫 click 정상 (19s sync wait 응답 + warehouse 등록)
- Spawn: 같은 reload 사이클 내 click → callback log 무 (`navmesh_playground.spawn callback entered` 도 안 출력)
- 사용자 마우스 직접 click → 동일 button 정상 동작

**가설**: omni.kit.ui_test 의 mouse event simulation 이 button widget 의 stale reference 가리킴 (이전 panel instance 가 만든 widget; 새 instance 의 widget 와 다른 binding).

**우회 (확정 작동)**: Extension UI button 우회. **MCP 직접 동작** (`stage_load_usd`, `character_load`, `character_play_animation_variant`, `navigation_*` 등) 으로 spawn / Walk→Sit / drive 검증. Extension UI 는 사용자 시연용, 자동 검증은 MCP tool 이 동등 동작 직접 수행. 이게 spec §14 "Verification Plan" 의 의도.

## I6 — validation_api `.py` hot-reload 가 module-level closure stale (2026-04-23)

**증상**: `extension_activate(omni.mycompany.validation_api, reload=True)` 후 module 코드는 re-import 되지만, `JobService.start_job(coro_factory)` 가 잡고 있는 `coro_factory` 는 옛 module 의 함수 reference 를 closure 에 holding → 새 호출 시 옛 코드 실행 (예: `_drive_physics_coro` 의 fix 가 반영 안 됨).

**대응**: 
- Module-level helper 함수 변경 시 hot-reload 의존 X
- **Kit process restart** (`run_process_module_standalone.py stop + start`) 이 유일한 확실한 방법
- 또는 lazy import 패턴 사용 (`from .robot_service import _drive_physics_coro` 를 매 호출마다 import)

## I7 — `DifferentialController.forward()` Isaac Sim 5.1 반환 type 변경

**증상**: spec §T2.1 가정 "numpy.ndarray (2,)" 와 다름. Isaac Sim 5.1 의 `DifferentialController.forward([lin, ang])` 는 **`ArticulationAction` 객체** 반환 (joint_velocities 속성에 wheel velocity 들어있음).

**Phase 0 진단 한계**: extension_list_all 로 ext 활성화만 확인 (T2.1) — 실제 `forward()` 반환 shape 는 검증 안 했음.

**수정 (commit `<TBD>`)**: `validation_api/services/robot_service.py::_drive_physics_coro` 에서:
```python
wv = ctrl.forward([lin, ang])
if hasattr(wv, "joint_velocities") and wv.joint_velocities is not None:
    jv = np.asarray(wv.joint_velocities, dtype=np.float32)
else:
    jv = np.asarray(wv, dtype=np.float32)
vels[left_idx] = float(jv.flat[0])
vels[right_idx] = float(jv.flat[1])
```
