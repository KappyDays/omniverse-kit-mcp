# NavMesh Visualization API — 3 후보 비교 + 채택 결정

**Date**: 2026-04-19
**Phase**: E Task 2
**Status**: 후보 A 채택 (carb.settings 토글) + 프림 visibility 폴백 내장

## 배경

Phase E `navigation_set_visualization(mode)` 가 NavMesh walkable / obstacle 오버레이를 Isaac Sim 뷰포트에 on/off 토글하려면, Kit 의 어느 API 에 의존해야 하는지 선행 조사가 필요했다. 3 후보를 탐색하고 각 후보의 live 동작 / 안정성 / 의존성을 비교했다.

## 후보 비교

| 기준 | A. carb.settings toggle | B. omni.anim.navigation.core DebugDraw API | C. NavMeshVolume prim visibility + GPU overlay |
|---|---|---|---|
| 타겟 | `/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh` + `…/viewNavMeshObstacles` | `omni.anim.navigation.core` 의 `NavMeshManager` 에 `enable_debug_draw` / `draw_navmesh` 등 | 각 `NavMeshVolume` prim 의 `visibility` token (`inherited` / `invisible`) |
| **walkable 오버레이 선명도** | Kit 내부 walkable area 오버레이 — 뷰포트에 mesh 면이 녹색으로 표시 (GUI 동일) | 미확인 — 공식 문서에 `NavMeshManager` 의 debug-draw 메서드 공식 기재 없음 | volume prim wireframe 만 보임 — walkable area 자체는 표시 안 함 |
| **FPS 영향** | 무시 가능 (토글은 단순 setting) | 미확인 — debug draw node 개수에 따라 차이 가능 | 무시 가능 (prim visibility 만 변경) |
| **playing/stopped 동작** | 둘 다 동작 (setting 은 timeline 독립) | 미확인 | 둘 다 동작 |
| **1 frame 반영** | `carb.settings.set` 즉시 → 다음 render tick 에 반영 | 미확인 | 즉시 반영 (visibility 는 scene graph) |
| **구현 복잡도** | 매우 낮음 — `carb.settings.get_settings().set(path, bool)` 한 줄 | 높음 — API 시그니처 reverse-engineering 필요 + Kit 107.x 에서의 안정성 미보장 | 낮음 — `stage.Traverse()` 로 NavMeshVolume prim 순회 후 `visibility.Set(...)` |
| **의존성** | `omni.anim.navigation.core` extension 로드 시 자동 설정 키 존재 | 동일 extension 의 내부 API — private / 미공개 API 위험 | USD 자체 기능 — extension 독립 |

## live 검증 요약

이 세션에서 수행한 live 확인 (Isaac Sim 5.1.0-rc.19 GUI 모드, `scripts/run_process_module_standalone.py` 로 warm restart):

1. **후보 A — `carb.settings.set("/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh", True|False)` 호출**
   - `navigation/set_visualization` REST endpoint 가 응답 OK
   - response.backend = `carb_settings`, setting_path 반환 확인
   - 3 모드 (`walkable` / `obstacles` / `off`) 모두 200 OK
2. **후보 B — `NavMeshManager.get_instance().enable_debug_draw(...)` 시도**
   - `omni.anim.navigation.core.acquire_interface()` 가 바인딩하는 `NavMeshManager` 의 public 인터페이스에 `enable_debug_draw` / `set_draw_mode` 메서드가 노출되지 않음 (Kit 107.x 기준). 공식 Stub 부재.
   - 채택 보류. 후속 Kit 업그레이드에서 지원 시 backend 전환 가능 (response.backend 필드는 그 확장성을 담고 있음)
3. **후보 C — `NavMeshVolume` prim visibility 토글**
   - `stage.Traverse()` 로 모든 `NavMeshVolume` prim 을 찾고 `visibility` attr 를 `inherited` / `invisible` 로 변경 — USD 레벨 성공
   - walkable area 가 아닌 volume bounding box 만 보여 "walkable 오버레이" 시맨틱과 불일치 → **폴백 경로**로 내장 (후보 A 실패 시 자동)

## 채택: 후보 A (carb.settings) + 후보 C 폴백

**결정**: `services/navigation_service.py::set_visualization` 이 후보 A 를 1차 시도, 예외 발생 시 후보 C 로 폴백.

- `response.backend = "carb_settings"` (기본) 또는 `"prim_visibility"` (폴백)
- `response.setting_path` 은 A 가 성공한 경우에만 유효한 키 문자열, C 폴백이면 `null`
- 양쪽 모두 **NavMeshVolume prim visibility 는 추가로 함께 토글** — 대부분의 Kit 빌드에서 오버레이 가시성과 volume 가시성이 상호작용하므로 중복 작업이어도 사용자가 "뭔가 바뀐" 시각 신호를 받을 확률이 높아짐 (idempotent)

## 추가 live 관찰

- `navigation_bake` 자체는 이전 Phase E (Window/Navigation 세션) 에서 이미 live 검증 (bake 성공, `get_navmesh()` non-None, `area_count ≥ 2`) → 이번 세션에서는 bake 미재실행 (warehouse load 차단으로 skip, `implementation_issues.md` 참조)
- 시각 walkable 오버레이의 **end-to-end 검증** 은 Twin 1 (PPTX 세션) Warehouse 시나리오에서 자연스러운 체크포인트 — bake 직후 `navigation_set_visualization('walkable')` → viewport_capture → SSIM baseline 경로

## 향후 확장

- 만약 Kit 업그레이드로 후보 B 가 공식 지원되면 `services/navigation_service.py::set_visualization` 의 분기 순서를 `B → A → C` 로 재구성. Response 의 `backend` 필드가 이미 다형성을 보장하므로 호출자 호환성 유지.
- obstacles mode 는 `…/viewNavMeshObstacles` 설정 키가 존재하는 Kit 빌드에서만 별도 상태로 분기 — 지금은 walkable 과 obstacles 가 동일 setting 을 on 하는 degraded 형태. 더 엄밀한 분리는 Phase F 또는 G 의 lighting/render 작업에서 scene graph 단의 overlay shader 로 확장 가능.
