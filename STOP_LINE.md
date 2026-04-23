# STOP_LINE — 2026-04-23 10:25 (3차 업데이트)

## 트리거
**자율 자동화 차단 — `extension_ui_invoke` (MCP UI automation) 가 main thread 외 thread 에서 button callback 실행** → sync `omni.kit.commands.execute("CreatePayloadCommand", ...)` 호출 시에도 silent crash. 사용자 마우스 직접 click 만 OK.

## 진단 진척 (이전 STOP_LINE 후 사용자 직접 테스트 결과)

### 환경 issue 가설 → 기각
- 사용자 GUI drag&drop (Content panel → Stage panel/Viewport): F_Business_02, nova_carter 모두 정상 로드 (silent crash 없음)
- 사용자 마우스 직접 NavMesh Playground `Load Warehouse` click → 정상 + viewport 매끄러움
- 사용자 마우스 직접 `Spawn @ Random Walkable` click → status `Spawned 1 People` + Agents row 추가
  (단 `_sample_impl` 시그니처 버그로 sample 실패 → 수정됨; spawn prim 미생성은 sample 실패로 인한 것)
- 사용자 `Toggle Overlay` click → 정상

### 진짜 root cause
- `extension_ui_invoke` (omni.kit.ui_test 기반 click simulation) 가 button callback 을 **main thread 외 thread 에서 실행**
- 이 thread 환경에서 sync `omni.kit.commands.execute("CreatePayloadCommand", ...)` 또는 character/robot mesh 처리 시 → race → silent crash
- GUI drag&drop / 사용자 직접 mouse click 은 main thread → 정상 동작

### 영향 범위
- 본 프로젝트의 모든 MCP UI automation (`extension_ui_invoke` 사용) 가 character/robot mesh 처리 부분에 적용 시 silent crash
- spec §11 의 scenarios YAML (`extension_ui_invoke` 다수 사용) → 자동 검증 불가
- spec §14 의 14-step MCP automation → spawn 단계까지만 자동, 그 후 사용자 검증 필요

## 현재 코드 상태 (commit `c8f4683` + 추가 진단 + 사용자 제안)

### Phase 0~2 완료 (commit `1a54cef`, `8c88911`, `22600f2`)
모두 자동 검증 통과.

### Phase 3/4 코드 작성 완료 (commit `c8f4683`)
- people_controller.py: in-process character_service.load 호출
- robot_controller.py: in-process drive_physics 호출
- live 검증은 `extension_ui_invoke` 차단으로 미진행

### 본 STOP_LINE 시점 추가 변경 (uncommitted)
- `usd_loader.py`: `safe_load_usd_sync` 추가 (UI thread direct CreatePayloadCommand)
- `navmesh_sampler.py`: `sample_walkable_points_sync` 추가
- `ui_panel.py`:
  - `_on_load_warehouse` → sync 호출 (사용자 mouse click 으로 정상 검증됨)
  - `_on_spawn_random` → sync 호출 (사용자 mouse click 시 status OK 확인 — 단 `_sample_impl` 버그는 수정 후 재검증 필요)
  - `_bake_sync(create_volume)` 신설 + 두 버튼 분리:
    - `Bake (Stage)` — 기존 NavMeshVolume 활용 (warehouse 내장 우선)
    - `Bake (New)` — 신규 100m volume 생성 (fallback)
  - 사용자 제안 (warehouse 내장 NavMeshVolume 활용 분리) 적용

## 사용자 검증 필요 (자율 진행 불가)

NavMesh Playground window 가 띄워져 있음. **마우스로 직접 click**:

1. **Load Warehouse** click → ~20 s 후 viewport 에 warehouse
2. **Bake (Stage)** click → status 가 stage 의 NavMeshVolume 사용 (warehouse 내장이 있으면 더 정확) 또는 "No NavMeshVolume" warning. 후자면 **Bake (New)** 클릭
3. **Spawn @ Random Walkable** click (Type=People, count=1) → status `Spawned 1 People` + Agents row + viewport 에 character mesh 보여야 정상
4. People row 의 **Go** click (Phase 3 추가 검증) — 단 character_service in-process 호출 → 이전 silent crash 재현 가능. 결과 보고 필요

## 결정 요청

1. **자율 검증 우회 방식**:
   - (a) 모든 UI 동작을 사용자 마우스로 검증 (가장 안전, 시간 많이 소요)
   - (b) `extension_ui_invoke` 의 omni.kit.ui_test 대신 다른 UI automation API 조사 + 패치
   - (c) Extension 에 자체 REST endpoint 추가 → curl 호출 (FastAPI thread 라 동일 issue 가능)
2. **Phase 5 진행 결정**: scenarios YAML 자체는 mock test 로 검증 가능. SSIM baseline 은 사용자 마우스 spawn 후 viewport_capture 로 가능
3. **PR 결정**: Phase 0/1/2 + 코드 (Phase 3/4) 완료 분만 PR draft, live 검증 보류 명시 가능

## 관련 참조

- 이전 STOP_LINE: `git show e70bae1:STOP_LINE.md` / `git show c8f4683:STOP_LINE.md`
- issues: `docs/implementation_issues.md#i1`, `#i2`
- Phase 3/4 코드: `isaac_extension/omni.mycompany.navmesh_playground/omni/mycompany/navmesh_playground/{people,robot}_controller.py`
- 사용자 검증 결과 (이번 세션):
  - Load Warehouse OK (mouse click)
  - Spawn People status OK + Agents row 추가 (mouse click; 단 sample 버그로 prim 미생성)
  - Bake / Toggle Overlay 정상
