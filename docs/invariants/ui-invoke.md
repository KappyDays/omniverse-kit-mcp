<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: extension_ui_invoke / window_ui_show 사용 작업 시작 전 필수 숙지 -->
# UI Invoke — Invariants

`extension_ui_invoke` 는 panel layout race + controller 코드 경로 분리 두 함정이
있다. UI automation 작업 전 이 파일 Read.

## panel layout race (L15)

`omni.kit.ui_test.input.emulate_mouse:49` 가 `pos.x / window_width` 호출.
`window_width = ui.Workspace.get_main_window_width()` 가 panel 생성 직후
(또는 `extension_activate(reload=True)` 직후) 1~10 프레임 동안 0 반환 →
`ZeroDivisionError`. OS 윈도우 자체는 정상 (3864×2100, `window_list` 확인됨).

## 안전 호출 sequence

```
extension_activate(ext_id, reload=True)
  → window_ui_show(panel_name, focus=true, settle_frames=10)  # 자동 처리됨
  → extension_ui_invoke(widget_path)
```

## 자동 방어 (현재 적용됨)

`isaac_extension/omni.mycompany.validation_api/omni/mycompany/validation_api/services/ui_service.py::ui_invoke`
가:
1. widget_path 의 window 부분을
   `isaac_extension/omni.mycompany.validation_api/omni/mycompany/validation_api/services/ui_service.py::_auto_show_window`
   로 자동 호출 (settle_frames=10)
2. `isaac_extension/omni.mycompany.validation_api/omni/mycompany/validation_api/services/ui_service.py::_install_ui_test_dimensions_patch`
   가 `omni.kit.ui_test.input.emulate_mouse` 를 monkey-patch — workspace dimensions=0
   시 OS app-window dimensions 으로 대체

두 layer 모두 적용 — 한 쪽만으로도 fix 되지만 함께 적용하면 future timing 변화에
robust.

## L8 무효화 (재진단 결과)

이전 "ext_ui_invoke binding stale → 사용자 마우스 직접 click 만 안정" 진단은 무효 —
실제 원인은 layout race. **Claude 도 위 sequence 로 클릭 가능**.

## ⚠️ MCP 직접 호출 ≠ UI 버튼 검증 (L13)

Extension UI 버튼의 동작 검증을 MCP 직접 호출 (예: `character_load`,
`character_play_animation_variant`) 로 대체하면 controller 코드 경로의 버그를 못
잡음. 사용자가 UI 버튼 클릭 시:
- `_on_spawn_random` → `safe_spawn_character_sync` (자체 구현) → `_walk_then_sit`
  (controller code) — 다른 경로 사용

검증 결과 분리:
- MCP 검증 PASS, UI 클릭 fail — controller 의 dual-path drift 가능

**Extension UI 버튼 동작은 반드시 사용자처럼 button click 으로 실측**.
MCP 등가 호출은 동작 가능성 확인일 뿐 검증 아님.

## controller dual-path drift 방지

controller / usd_loader 가 validation_api singleton 을 사용하는 경우:
- 사용 메서드명 + 시그니처 + 응답 dict key 를 service 코드 SoT 와 직접 매칭
- 예: `vr._job.get_status` (sync) vs `vr._job.status` (X)
- `_ANIM_GRAPH_SUFFIX` 도 character_service.py SoT 따라가기

AgentRecord 처럼 path 가 두 종류 (parent payload vs SkelRoot) 인 경우:
- 별도 필드 (`prim_path` + `skel_root_path`) 로 분리
- 단일 필드 재사용은 delete vs animation API 충돌 발생

## 관련 경계

- L13 / L15 사고 기록: `isaac_extension/docs/lessons-learned.md`
- Window / Extension domain 분리: `src/isaacsim_mcp/modules/CLAUDE.md`
- Extension reload (UI panel zombie 와 같은 layer): `docs/invariants/ext-reload.md`
- Validation_api reuse pattern (싱글턴 in-process import): `isaac_extension/docs/validation_api-reuse.md`
