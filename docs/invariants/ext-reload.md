<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Extension .py 수정 후 코드 반영 작업 시작 전 필수 숙지 -->
# Extension Reload — Invariants

Extension `.py` 수정 후 어떤 reload 경로를 쓰든 `sys.modules` cleanup 은 보장 안 됨.
`kkr-extensions/` 코드 수정 시 이 파일 Read.

## 핵심 결론 (L9 재재진단 + L16)

- **`.py` 수정 후 코드 반영을 확실히 하려면 Kit process restart**
  - `isaac_sim_restart` MCP tool, 또는
  - `scripts/run_process_module_standalone.py stop + start`
- omni.ext.plugin fswatcher (C++) 가 ext python 폴더를 자동 watch — 파일 저장 시
  `FS Change triggers reloading` + disable→enable 시퀀스를 실행하긴 함.
  **하지만 `_reload_enabled = False` (default) 가 fswatcher 경로에도 적용** —
  sys.modules cleanup 안 됨
- MCP `extension_activate(reload=True)` 도 sys.modules cleanup 안 함 (fswatcher 와 동일)
- 특히 module-level singleton (`_window = WindowService()`, `_router = APIRouter()` 등)
  패턴은 100% reload 실패

## 검증 패턴 (reload 성공 여부 확인)

코드에 hard-coded marker (예: 응답 dict 에 임시 필드 추가) 추가 → tool 호출 → marker
보이는지 확인:
- 보임 → reload 성공
- 안 보임 → reload 실패 → Kit process restart 필요

## ui.Window zombie cleanup 패턴 (L16)

fswatcher 자동 disable→enable 시 `on_shutdown` 의 `self._window.destroy()` 만으로는
`ui.Workspace` registry 에서 즉시 unregister 안 됨 (next update tick 에서 처리) →
다음 `on_shutdown` 이 같은 이름으로 새 `ui.Window` 생성 → registry 에 동명 entry
2개 → walker 가 stale OLD widget tree 반환 → MCP UI automation 의 widget path
호출이 callback 미발화.

표준 cleanup pattern (모든 신규/기존 Extension 의 `on_shutdown` 권장):

```python
# extension.py on_shutdown
if self._window is not None:
    self._window.visible = False  # Workspace 에서 deregister hint
    self._window.destroy()
    self._window = None

# ui_panel.py build() 시작
existing = ui.Workspace.get_window("<name>")
if existing is not None:
    existing.visible = False
    existing.destroy()
self._window = ui.Window("<name>", ...)
```

두 layer 모두 적용해야 효과적 — destroy 가 deferred 인 경우 build() sweep 가 backup.
완전 zero zombie 가 필요하면 build() 에서 `next_update_async()` 2회 yield 후 sweep —
현재는 invisible orphan 1개 남지만 walker 가 first visible 룰로 정상 NEW 만 picking
하므로 사용자 영향 없음.

## 증상 (zombie 잔존 시)

- kit log: `[Warning] [omni.ui_query.query] found 2 windows named "<name>". Using first
  visible window found`
- `extension_get_ui_tree` 가 `matched_windows: ["<name>", "<name>"]` 로 두 매치 보고
- Walker 가 OLD (visible) 를 walk → stale widget tree → MCP UI automation 호출
  callback 미발화
- 누적되면 메모리 leak (Kit 재시작까지)

## `branch/kit-app-template` source ↔ \_build hardlink

`branch/kit-app-template/source/apps/<app>.kit` 와
`branch/kit-app-template/_build/windows-x86_64/release/apps/<app>.kit` 는
premake 가 만든 hardlink (동일 inode). source 만 Edit 해도 _build 쪽이
자동 갱신되지만, 한 쪽 Edit 후 같은 세션에서 다른 쪽을 추가 Edit 하려고
하면 **`Edit` tool 이 "File has been modified since read" 로 실패** —
inode 가 동일해 메타데이터가 동시 갱신되기 때문.

권장 패턴:
- **source/apps/ 만 Edit** — \_build 쪽은 자동 동기화
- 검증: `stat <source>.kit <build>.kit` 의 Inode 비교 (동일하면 hardlink)
- 동일 .kit 을 양쪽 모두 수정해야 한다고 느끼면 hardlink 인지 먼저 확인

(이 hardlink 패턴은 `branch/usd-composer-webrtc-streaming/kit-app-template/`
에도 동일 적용)

## 관련 경계

- L9 / L16 사고 기록: `kkr-extensions/docs/lessons-learned.md`
- Extension 일반 규칙 (IExt / hot-reload / 한글 UI 금지): `kkr-extensions/docs/extension-basics.md`
- Window/UI automation sequence (panel race + dual-path drift): `docs/invariants/ui-invoke.md`
- MCP server import cache (별개 프로세스): `src/omniverse_kit_mcp/CLAUDE.md`
