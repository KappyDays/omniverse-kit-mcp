<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Historical incident log — 사고 맥락 / 재현 증거 추적용. 영구 규칙은 docs/invariants/ 에 편입 -->

# Lessons Learned — Historical Incident Log

**본 파일의 역할이 바뀌었다** (2026-04-24 Pull-First restructure):
- 과거에는 "새 작업 전 필독" 이었으나, **영구 규칙 (L14/L15/L16/L17 등) 은 `../../docs/invariants/*.md` 와 `../../docs/runbooks/*.md` 로 편입 완료**
- 새 작업 시작 시 필독 → invariants/ pull-doc 을 Read. 루트 `../../CLAUDE.md` 의 "작업 전 필수 pull-doc" 표가 진입점
- 이 파일은 **사고 맥락 추적 / 재현 증거 / 잘못된 진단 회피 기록** 용 historical log. 재발 시 상세 증상·재현 절차를 찾을 때 참조
- 새 영구 규칙은 여기에 추가하지 말고 `docs/invariants/` 에 신규 pull-doc 작성 (작업 전 로드 대상)

엔트리 형식 (historical entries):
- **원인** — 무엇이 잘못됐는가 (1-2 문장)
- **증상** — 어떻게 드러나는가
- **재발 방지** — 다음엔 어떻게 할 것인가 (구체적 절차) — 영구 규칙화된 항목은 invariants/ 포인터 추가

---

## 2026-04-24 — ProcessModule cold boot hang root cause

### L17. `subprocess.Popen` 의 `stdin` 명시 누락 = MCP server 자식 프로세스에서 boot 정지

- **원인**: `src/omniverse_kit_mcp/modules/process_module.py::start()` 의 `subprocess.Popen(...)` 가 `stdin` 인자 미지정. MCP server (`omniverse-kit-mcp`) 는 Claude Code 의 stdio 자식이라 그 stdin = MCP protocol 양방향 pipe. 자식 kit.exe 가 그 pipe stdin 을 상속 → cold boot 어느 init 단계에서 stdin read 시도 → MCP pipe 에서 indefinite block → 그 thread + join 대기 thread 들 모두 정지 → 전체 boot 멈춤.
- **증상 (실측 2026-04-23 두 번 hang, 2026-04-24 root cause 확정)**:
  - `isaac_sim_start` 응답 `status=timeout` (240s 후) 또는 `status=still_loading`
  - PowerShell `Get-Process kit`: alive (PID 정상), CPU < 5s (5분 idle), WS ~60MB (boot 시작도 못함)
  - internal kit log (`%LocalAppData%/../.nvidia-omniverse/logs/Kit/Isaac-Sim Full/5.1/kit_*.log`) mtime 이 **~85-91ms 시점 정체** (마지막 line 보통 `[ext: omni.kit.loop-isaac] registered`)
  - `bash` 에서 `scripts/run_process_module_standalone.py start` 로 같은 코드 / 같은 .env 호출하면 **15초만에 정상 ready** — false negative 위험
- **잘못된 진단 회피** (2026-04-23 의 mistake):
  - "extra_ext_ids 7-8개 race", "GPU 셰이더 캐시 cold", "user.config corruption" 등은 모두 상관관계만 있고 인과관계 없음
  - ext 갯수 / dependency 변경은 stdin race 의 timing 만 바꿈 — 진짜 원인 가린다
  - 다음 hang 발생 시 **반드시 stdin 명시 여부 첫 번째로 확인** (코드 수정 시 누락 의심)
- **재발 방지 (코드 baseline)**:
  ```python
  self._process = subprocess.Popen(
      cmd,
      stdin=subprocess.DEVNULL,  # CRITICAL — 절대 누락 금지
      stdout=self._stdout_handle,
      stderr=subprocess.STDOUT,
      env=env,
      ...
  )
  ```
  - 다른 `subprocess.Popen` 호출도 자식이 input 안 받으면 동일하게 `stdin=DEVNULL` 명시 (default = inherit 이라 silent leak)
  - 재현 검증 (Fix 회귀 방지): `python -c "import subprocess; p=subprocess.Popen(['.venv/Scripts/python.exe','scripts/run_process_module_standalone.py','start'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True); print(p.communicate(input='', timeout=300))"` → ~13s ready 여야 PASS, 240s timeout 면 stdin DEVNULL 누락
- **상세**: 루트 `CLAUDE.md §"kit.exe cold boot hang — stdin pipe deadlock"` 와 `src/omniverse_kit_mcp/modules/CLAUDE.md §"ProcessModule hang recovery"` 1번

---

## 2026-04-23 — NavMesh Playground (Phase J) 구현 세션

### L15. `ext_ui_invoke` "float division by zero" 의 진짜 원인 = 패널 layout 미초기화

- **원인**: `omni.kit.ui_test.input.emulate_mouse:49` 가 `pos.x / window_width` 호출. `window_width = ui.Workspace.get_main_window_width()` 가 **panel 생성 직후 (또는 `extension_activate(reload=True)` 직후)** 1~10 프레임 동안 0 반환 → `ZeroDivisionError`. OS 윈도우는 정상 (3864×2100, `window_list` 확인).
- **증상 (실측 2026-04-23)**:
  - 첫 `ext_ui_invoke` 실패: HTTP 500 "float division by zero"
  - 동일 path 재호출도 실패 (workspace 가 settle 안 함)
  - `window_ui_show(name, focus=true, settle_frames=10)` 호출 후 → 모든 ext_ui_invoke 성공
- **진짜 회피**: 호출 sequence
  ```
  window_ui_show(panel, focus=true, settle_frames=10)
    → ext_ui_invoke(widget_path)  # 이제 정상
  ```
- **재발 방지 (코드)**:
  - `validation_api/services/ui_service.py::ui_invoke` 가 widget_path 의 window 부분 자동으로 `_auto_show_window(name, settle_frames=10)` 호출 (auto-settle)
  - 추가 방어책: `_install_ui_test_dimensions_patch()` 가 `omni.kit.ui_test.input.emulate_mouse` 를 monkey-patch — workspace dimensions=0 시 OS app-window dimensions 으로 대체 (legacy normalised channel; 절대 좌표는 영향 없음)
  - 두 layer 모두 적용 — 어느 한 쪽만으로도 충분히 fix 되지만 같이 적용하면 future timing 변화에도 robust
- **L8 갱신**: 이전에 "ext_ui_invoke binding stale" 이라 진단했으나, 실제는 layout race 였음. L8 의 "사용자 마우스 직접 click 만 안정" 은 무효 — Claude 도 위 sequence 로 클릭 가능.

### L14. pydantic-settings v2 sub-config 가 부모 `env_file` 을 안 받음

- **원인**: `AppConfig(BaseSettings)` 가 `model_config = SettingsConfigDict(env_file=".env")` 를 갖고, sub-config (`IsaacSimProcessConfig` 등) 가 `Field(default_factory=IsaacSimProcessConfig)` 로 인스턴스화될 때, **각 sub-config 는 독립 BaseSettings 인스턴스**여서 부모의 `env_file` 을 전파받지 않음. 자체 `env_file` 이 없으면 OS 환경변수만 참조.
- **증상 (실측 2026-04-23)**:
  - `.env` 의 `ISAAC_SIM_STARTUP_TIMEOUT=120.0` 항상 무시 → default 240.0 사용
  - `.env` 의 `ISAAC_SIM_EXTRA_EXT_IDS=[7개]` 항상 무시 → default 4개만 → navmesh_playground 등 미활성
  - 사용자 / 운영자가 `.env` 변경해도 효과 없는 silent failure
- **재발 방지**:
  - 모든 sub-`BaseSettings` 에 `env_file=".env"` 명시 (config.py 가 SoT)
  - 신규 sub-config 추가 시 동일 패턴 (env_prefix + env_file + extra="ignore")
  - 검증 명령 (PR 전 필수):
    ```bash
    .venv/Scripts/python.exe -c "from omniverse_kit_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout)"
    ```
    → `.env` 값 반영 확인

### L13. Extension UI 검증을 MCP 직접 호출로 대체하면 controller 코드 경로의 버그 못 잡음

- **원인**: navmesh_playground 의 spawn/Go/Sit 동작을 MCP `character_load` / `character_play_animation_variant` 직접 호출로 검증 → 통과. 하지만 사용자가 Extension UI 버튼 클릭 시 `_on_spawn_random` → `safe_spawn_character_sync` (자체 구현) → `_walk_then_sit` (controller code) 의 **다른 경로** 사용. 6 가지 버그 누적 (AnimGraph 잘못된 path suffix, JobService method name 오류, SkelRoot vs parent prim path 혼동 등).
- **증상**: MCP 검증 결과 = "all PASSED", 사용자 UI 클릭 결과 = "Animation graph not assigned valid skeleton" + "Type mismatch (Action, Walk variables)" + "Unsupported type: list" + "JobService has no attribute status".
- **재발 방지**:
  - Extension UI 버튼 동작은 **반드시 사용자처럼 button click 으로 실측**. MCP 등가 호출은 동작 가능성 확인일 뿐 검증 아님.
  - controller / usd_loader 가 validation_api singleton 을 사용하는 경우, 사용 메서드명 + 시그니처 + 응답 dict key 를 **service 코드 SoT 와 직접 매칭**하여 dual-path drift 방지. 예: `vr._job.get_status` (sync) vs `vr._job.status` (X). `_ANIM_GRAPH_SUFFIX` 도 character_service.py SoT 따라가기.
  - AgentRecord 처럼 path 가 두 종류 (parent payload vs SkelRoot) 인 경우 별도 필드 (`prim_path` + `skel_root_path`) 로 분리 — 단일 필드 재사용은 delete vs animation API 충돌 발생.

### L7. `tasklist //FI "IMAGENAME eq kit.exe"` (git bash) 가 false negative

- **원인**: git bash 의 `tasklist //FI` 호출이 timing/filter 처리 buggy. alive Kit 도 빈 결과 반환.
- **증상**: 본 세션 중 "silent crash" 진단 8+회 모두 잘못. Kit 은 살아있었음 (PowerShell `Get-Process -Name kit` + MCP `simulation_get_status` 200 응답으로 확정).
- **재발 방지**: Kit alive 판단은 다음 도구로만:
  - **PowerShell** `Get-Process -Name kit -ErrorAction SilentlyContinue`
  - **MCP** `simulation_get_status` (응답 ≤ 1s = alive)
  - **`curl http://localhost:8011/validation/v1/health`** (200 = alive)
  - 절대 `tasklist //FI` (git bash) 사용 금지. `src/omniverse_kit_mcp/modules/CLAUDE.md §"ProcessModule hang recovery"` 에 정정.

### L8. `extension_ui_invoke` callback 호출 inconsistency (hot-reload 후)

- **원인**: `omni.kit.ui_test.click` 의 mouse event simulation 이 hot-reload 누적 시 stale button widget reference 가리킴 (이전 panel instance 의 closure).
- **증상**: ext_ui_invoke 응답 OK + post_state 정상이지만 button callback 자체 호출 안 됨 (carb.log_warn 로그 없음, prim 미생성). 사용자 마우스 직접 click 만 안정.
- **재발 방지**: 자율 검증은 **MCP 직접 동작** (`stage_load_usd`, `character_load`, `navigation_*` 등) 으로 동등 결과 만들기 (spec §14 의도). Extension UI button 은 사용자 시연용. spec 의 scenarios YAML 에 `extension_ui_invoke` 다수 사용 시 자동 검증 차단됨 — 필요 시 동등 MCP action 으로 재작성.

### L9. Extension `.py` hot-reload — fswatcher 는 disable→enable 만, sys.modules cleanup 신뢰 불가

- **원인 (재재진단 2026-04-23 실증)**: omni.ext.plugin (C++) fswatcher 가 ext python 폴더를 자동 watch — 파일 저장 시 kit log `FS Change triggers reloading: <path>` + `Processing ext disable request` + `on_shutdown` + `enable` + `on_startup` 시퀀스 발생. **하지만 sys.modules cleanup 은 보장 안 됨** — `_reload_enabled = False` (omni/ext/_impl/_internal.py:152 default) 가 fswatcher 경로에도 적용되는 것으로 추정.
- **실증 (validation_api 에서 hard-coded `_reload_marker` 응답 필드 추가 후 검증)**: 코드 수정 → 파일 저장 → fswatcher reload 시퀀스 정확 발생 → 그러나 응답에 marker 필드 안 나타남 = **새 코드가 import 되지 않음**. 즉 disable→enable 은 일어나지만 `from .rest_router import router` 가 cached 옛 module 리턴.
- **이전 (2026-04-23 오전) 잘못된 결론**: "fswatcher 가 자동 reload — MCP toggle 불필요" 라고 정정한 것은 navmesh_playground 의 `ui.Button` 라벨 변경이 화면에 반영된 것을 보고 추론. 실은 ui_panel 의 build() 가 `ui.Workspace.get_window()` zombie sweep 코드 (L16) 와 함께 새로 호출되면서 *우연히* 새 ui_panel module 이 일부 cleanup 됐거나, 더 정확히는 reload 자체가 partial 동작.
- **신뢰 가능한 결론** (변경 금지):
  - **Extension `.py` 수정 후 코드 반영을 확실히 하려면 Kit process restart** (`isaac_sim_restart` 또는 `scripts/run_process_module_standalone.py stop + start`)
  - fswatcher reload 가 일부 변경에는 작동할 수 있으나 신뢰 못 함 — 항상 검증 필요. validation_api 처럼 module-level singleton (`_window = WindowService()`) 패턴은 100% reload 실패
  - MCP `extension_activate(ext_id, reload=True)` 도 sys.modules cleanup 안 함 — fswatcher 와 동일 한계
  - **변경 검증 패턴**: 코드에 hard-coded marker (예: 응답 필드 추가) 하고 호출 → marker 안 보이면 reload 실패 → Kit restart

### L16. fswatcher 자동 reload + ui.Window orphan zombie

- **원인**: omni.ext.plugin fswatcher 가 .py 저장 시 자동 disable→enable. `on_shutdown` 의 `self._window.destroy()` 호출만으로는 `ui.Workspace` 의 window registry 에서 즉시 unregister 되지 않고 **next update tick 에서 처리됨**. 다음 `on_startup` 이 같은 tick 내에 동일 이름으로 새 `ui.Window` 생성 → registry 에 동명 entry 2개 (OLD-being-destroyed + NEW).
- **증상**:
  - kit log: `[Warning] [omni.ui_query.query] found 2 windows named "<name>". Using first visible window found`
  - `extension_get_ui_tree` 가 `matched_windows: ["<name>", "<name>"]` 로 두 매치 보고
  - Walker 가 OLD (visible) 를 walk 하면 stale widget tree 반환 → MCP UI automation 이 옛 widget path 호출 → callback 미발화
  - 누적되면 메모리 leak (Kit 재시작까지)
- **재발 방지** (`navmesh_playground/extension.py` + `ui_panel.py` 적용 패턴):
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
  - 두 layer 모두 적용해야 효과적 — destroy 가 deferred 인 경우 build() sweep 가 backup
  - 완전 zero zombie 가 필요하면 build() 에서 next_update_async() 2회 yield 후 sweep — 현재는 invisible orphan 1개 남지만 walker 가 first visible 룰로 정상 NEW 만 picking 하므로 사용자 영향 없음
  - **모든 신규/기존 Extension 의 on_shutdown 에 `visible=False; destroy(); =None` 패턴 표준화 권장**

### L10. `DifferentialController.forward()` Isaac Sim 5.1 type 변경

- **원인**: spec §T2.1 가정 "numpy.ndarray (2,) 또는 list[2]" 와 다름. Kit 5.1 의 `DifferentialController.forward([lin, ang])` 는 **`ArticulationAction` 객체** 반환 (joint_velocities 속성에 wheel velocity).
- **증상**: `TypeError: 'ArticulationAction' object is not subscriptable` (subscript `wv[0]` 시도 시).
- **재발 방지**: Kit SDK API 반환 type 은 Phase 0 의 단순 `extension_list_all` enabled 확인만으로 부족. 실제 `forward()` 호출하여 type 확인 필요. 본 ext 의 `_drive_physics_coro` 가 양쪽 호환:
  ```python
  wv = ctrl.forward([lin, ang])
  if hasattr(wv, "joint_velocities") and wv.joint_velocities is not None:
      jv = np.asarray(wv.joint_velocities, dtype=np.float32)
  else:
      jv = np.asarray(wv, dtype=np.float32)
  ```

### L11. CreatePayloadCommand 가 nested parent 미생성 시 silent fail

- **원인**: `CreatePayloadCommand(path_to="/World/People/People_01")` 호출 시 `/World/People` Xform 이 존재하지 않으면 silent fail. prim 생성 안 됨, 에러 raise 안 됨.
- **증상**: callback log 가 "safe_load_usd_sync OK" 출력하지만 stage 에 prim 미존재. validation 강화 (`prim.GetTypeName()` 비어있으면 raise) 로 다음에는 잡힘.
- **재발 방지**:
  - `_ensure_parent_xform(stage, prim_path)` 로 nested intermediate Xform 자동 생성
  - 또는 단순 1단계 path 사용 (`/World/People_01` 대신 `/World/People/People_01`) — 사용자 통찰 (Load Warehouse 와 동일 패턴)
  - prim validity 확인 시 `IsValid()` 만 으로 부족 — `GetTypeName()` 도 검증

### L12. `stage_capture_snapshot` glob `*` 가 `/` 매치 안 함

- **원인**: glob 의 `*` 는 path separator (`/`) 를 cross 하지 않음.
- **증상**: `include_prim_patterns=["/World/People*"]` 가 `/World/People/People_01` 미매치.
- **재발 방지**: `["/World/People/*"]` (1단계 children) 또는 `stage_assert_prim_exists(prim_path=...)` 로 정확 명시.

---

## 2026-04-22 — isaac_tutorial 최초 구현 세션

### L1. Service signature 를 plan 단계의 가정으로 호출

**원인**: `validation_api.services.*` 메서드 시그니처를 직접 확인하지 않고, "보통 이런 kwarg 쓰겠지" 로 호출 코드 작성. 실제로는 대부분 메서드가 단일 `request: dict` 인자 + Pydantic `ConfigDict(extra="forbid")` 라 낯선 키 하나가 즉시 TypeError.

**증상**:
- `StageService.load_usd() got an unexpected keyword argument 'url'`
- `TypeError: RobotService.__init__() missing 1 required positional argument: 'job_service'`

둘 다 live Kit 에서만 터짐. pytest 는 MagicMock 이 모든 signature 를 허용하므로 감지 못 함.

**재발 방지**:
1. 호출 전 해당 `services/<name>_service.py` 에 `grep "async def\|def "` 로 시그니처 확인
2. 요청이 dict 이면 `models/<name>.py` 에서 `class ...RequestModel` 찾아 필드 이름 확인
3. 반환 확인은 `grep "return {"` 로 dict 키 확인
4. 테스트에서도 **positional dict 인자 + 정확한 키** 를 assert (`call_args.args[0] == {...}` 형태)

### L2. Service 인스턴스를 직접 만들려고 시도

**원인**: `RobotService()`, `CharacterService()` 처럼 arg 없이 인스턴스화. 실제로는 `RobotService(job_service)`, `CharacterService(job_service, stage_service)` 의존성 체인.

**증상**: `TypeError: RobotService.__init__() missing 1 required positional argument: 'job_service'` (live Kit 에서만)

**재발 방지**:
- validation_api 재사용 시 **절대 직접 인스턴스화하지 말 것**
- `from omni.mycompany.validation_api import rest_router as vr` 후 `vr._stage`, `vr._robot`, `vr._character`, `vr._job` 등 모듈 레벨 싱글턴 사용
- 상세: `validation_api-reuse.md` 의 "rest_router 싱글턴 import" 절

### L3. Kit 107 omni.ui font atlas 는 CJK glyph 없음

**원인**: UI label / tooltip / status 에 한글 삽입. Kit 107 `omni.ui` font atlas 는 kit.exe 기동 시 ASCII + Latin glyph 만 로드, Extension `on_startup` 시점에는 font 교체 경로 없음.

**증상**: 한글이 모두 mojibake (□□□ / 깨진 사각형) 로 렌더링. 기능은 동작하나 학생에게 읽히지 않음.

**재발 방지**:
- **모든 UI 문자열 영어 전용**. label, tooltip, status_label 텍스트, notification 메시지 전부
- 특수문자도 주의: `✓` / `✗` / `→` / `×` / `÷` 중 일부는 Latin 에 있지만 보수적으로 `[OK]` / `[FAIL]` / `->` / `x` / `/` 사용
- 한글은 docstring / code comment / git commit message 에서만 허용 (Kit Console 출력은 OK, UI 위젯 아님)
- 실측: `grep "[가-힣]" kkr-extensions/omni.mycompany.<ext>/` 로 runtime 문자열만 남기고 검수

### L4. omni.ui 위젯은 pytest 에서 단위 검증 불가

**원인**: UI 패널 (env_setup_panel, steps_panel, main_window) 에 pytest 테스트 작성 시도. `omni.ui` 는 conftest.py 에서 stub 된 빈 ModuleType — 위젯 실제 동작 시뮬레이션 안 됨.

**증상**: UI 관련 `assert btn.text == "..."` 같은 테스트가 "테스트는 통과하지만 실 동작 모름" 상태. 또는 stub 한계로 아예 import 실패.

**재발 방지**:
- `omni.ui` 를 쓰는 코드는 **actions / state / services 로직과 분리**해서, 로직 부분만 pytest 로 검증
- UI 부분은 **live Kit + 수동 QA_CHECKLIST** 로 검증 (`isaac_tutorial/QA_CHECKLIST.md` 참고 템플릿)
- conftest.py 의 stub 은 "import 되게만 하는" 수준 — 위젯 동작 검증 용도 아님을 코멘트로 명시

### L5. 신규 Extension 은 독립 구조 (정책)

**원인**: 초기 `isaac_tutorial` 설계 시 "validation_api services in-process import" 를 기본 패턴으로 제안. 하지만 이건 tutorial_ext 의 특수 상황 (heavy orchestration — office load, sit_on_prim, NavMesh navigate 재사용 필요) 때문.

**증상**: 모든 신규 Extension 이 이 패턴 따라가면 의존 그래프 증가, 학생 배포 2-Extension 필수, validation_api 업데이트가 downstream 깨뜨릴 위험.

**재발 방지 (정책)**:
- 신규 Extension 은 **Kit SDK 직접 호출 (독립 구조)** 기본
- S3 MDL-heavy asset 로드 필요 시 `usd-load-deadlock-recipe.md` 의 방어 코드 **복사** (import 아닌)
- 이미 만들어진 Extension (tutorial 등) 만 validation_api 재사용 허용
- 새 Extension 시작 시 `extension-basics.md` 의 "신규 독립 Extension 스켈레톤" 템플릿 복붙

### L6. 대형 단일 CLAUDE.md 는 유지보수 안 됨

**원인**: `kkr-extensions/CLAUDE.md` 가 단일 파일에 validation_api 내부 구현 + 도메인 함정 + Extension 공통 규칙 + tutorial_ext 섹션을 모두 담아 275+ line 비대해짐.

**증상**:
- 새 Extension 만드는 사람이 "뭘 읽어야 하는지" 판단 어려움 (validation_api 무관한 내용까지 다 읽게 됨)
- Lessons learned 를 기록할 위치 부재
- 토픽이 서로 섞여 검색성 저하

**재발 방지**:
- `kkr-extensions/CLAUDE.md` 를 **nav hub** 로만 운영 (Extension 목록 + 정책 + docs/* 포인터)
- 토픽별로 `kkr-extensions/docs/` 아래 분리 (extension-basics / kit-sdk-pitfalls / usd-load-deadlock-recipe / validation_api-reuse / lessons-learned)
- 새 Extension 은 **CLAUDE.md 파일 자체를 두지 말 것** — 공통 내용은 docs/, 개별 QA 는 각 Extension 폴더 내 QA_CHECKLIST.md 로 국한

---

## 엔트리 추가 방법

새 실수를 겪었으면:

1. 이 파일 최상단 (가장 최근 세션) 에 섹션 추가 (날짜 + 세션 타이틀 H2)
2. 각 실수당 `### L<번호>. 제목` + **원인 / 증상 / 재발 방지** 3 필드
3. 가능하면 구체적 파일 경로 / 증상 로그 / 방지 절차 스크립트 포함
4. Commit message 에 `docs(lessons): ...` prefix
