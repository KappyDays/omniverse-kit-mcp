# Live E2E Verification — omniverse-kit-mcp P1 Upgrade (self-contained goal)

> **사용법**: 새 세션을 **`workspaces/isaac/instance-1/`에서 시작**한 뒤 `/goal @live_e2e_prompt.md 전부 완료해줘`.
> 당신의 목표는 아래 P1 업그레이드 항목들을 **라이브 Isaac Sim에서 검증**하고 각 항목 PASS/FAIL을
> 근거와 함께 보고/완료하는 것이다. 이 파일 하나로 충분하다 — 추가 맥락 없이 진행하라.

---

## ⛔ 0. PREFLIGHT — 시작 전 반드시 확인 (실패 시 STOP하고 사용자에게 안내)

이 검증은 이 프로젝트의 **Isaac MCP 서버 + 라이브 kit.exe(GPU)** 가 필요하다. 코드/단위테스트는 이미
통과했으나 **MCP import-cache 제약** 때문에 라이브 미검증이다. 다음을 순서대로 확인하라:

1. **세션 위치**: 이 세션은 `workspaces/isaac/instance-1/`에서 시작돼야 한다 — 그곳 `.mcp.json`이
   `uv --directory ../../.. run --no-sync omniverse-kit-mcp`로 **이 repo 최신 코드의 MCP 서버를 spawn**한다.
   repo 루트엔 `.mcp.json`이 없어 루트에서 시작하면 Isaac 도구가 전혀 없다.
2. **MCP 도구 존재 확인** (가장 중요): 당신의 도구 목록에 `kit_app_start`, `extension_reload`,
   `viewport_set_camera_lookat` 가 **모두** 있는가?
   - **하나라도 없으면 즉시 STOP**하고 사용자에게 이렇게 안내한 뒤 종료하라:
     > "Isaac MCP 도구(또는 신규 도구 extension_reload / viewport_set_camera_lookat)가 안 보입니다.
     > (a) `cd workspaces/isaac/instance-1` 위치에서 Claude Code를 시작했는지 확인하고 세션을 재시작하세요.
     > (b) 그래도 신규 두 도구가 안 보이면 MCP 서버가 stale wheel로 설치된 것 — repo 루트에서
     > `uv sync` (또는 `uv pip install -e .`) 실행 후 세션 재시작."
   - (`extension_reload` / `viewport_set_camera_lookat`는 이번 업그레이드 **신규** 도구라, 최신 코드로
     spawn된 서버에서만 보인다. 보이면 OK.)
3. **필독 (작업 전)**: `docs/invariants/usd-load.md`, `docs/invariants/process-lifecycle.md`
   (stage 로드/기동·deadlock 방어 규칙). 실패 진단: `docs/tool-diagnostic-map.md`.
   전체 설계/근거: `docs/superpowers/specs/2026-05-26-mcp-upgrade-p1-design.md`.

---

## 1. 셋업

1. `kit_app_start` (isaac-sim, instance 1).
   - 이미 **옛 코드**로 kit이 떠 있으면 반드시 `kit_app_restart` — validation_api의 새 REST
     엔드포인트(`/extension/reload_clean`, `/viewport/set_camera_lookat`, capture stats)는 kit 재기동
     후에만 라이브 반영된다. kit.exe는 `--ext-folder <repo>/kkr-extensions`로 이 repo의 validation_api를 로드.
   - cold boot는 GPU 셰이더 캐시 재빌드로 수 분 걸릴 수 있다. `still_loading` 응답이면 `kit_app_start`를
     다시 호출하며 폴링(재spawn 아님). 상세: `process-lifecycle.md`.
2. `simulation_get_status`로 health 확인.

---

## 2. 검증 체크리스트 (각 PASS 기준 충족까지 수행)

### ① extension_reload — Kit 재시작 없이 .py 반영 (의견 #1)

1. 데모 extension 활성화: `extension_activate("omni.mycompany.ui_demo")`.
2. ui_demo의 메인 소스(`kkr-extensions/omni.mycompany.ui_demo/` 트리의 `extension.py` — 패키지 경로는
   `omni/mycompany/ui_demo/extension.py`)의 `on_startup`에 **마커** 한 줄 추가:
   `carb.log_warn("E2E_RELOAD_MARKER_v1")` (Edit 도구로).
3. `extension_reload("omni.mycompany.ui_demo")` 호출.
4. **기대**: 응답 `{ok:true, reloaded:true, modules_purged>=1}` + 마커가 **kit_app_restart 없이** 반영.
   확인: `extension_capture_logs(ext_id="omni.mycompany.ui_demo")`에 `E2E_RELOAD_MARKER_v1`가 보이거나,
   재호출 시 on_startup 재실행 로그. (reload는 disable→enable이므로 on_startup이 다시 돈다.)
5. **self-reload 가드**: `extension_reload("omni.mycompany.validation_api")` → **HTTP 400**이어야 함
   (self-reload unsupported). 200이면 FAIL.
- **PASS**: 마커가 restart 없이 반영 + validation_api self-reload가 400.

### ② ISAAC_SIM_EXTRA_EXT_FOLDERS — out-of-tree extension 등록 (의견 #1) — 선택

1. `office_mcp/exts/`가 존재하는지 먼저 확인(`ls`). 없으면 **SKIP**으로 보고하고 ④로.
2. 있으면: `workspaces/isaac/instance-1/.mcp.json`의 `env`에
   `"ISAAC_SIM_EXTRA_EXT_FOLDERS": "[\"C:/Users/<you>/workspace/omniverse-kit-mcp/office_mcp/exts\"]"` 추가 →
   세션 재시작(서버가 env 재로드) → `kit_app_restart`.
3. **기대**: `office_mcp/exts/` 하위 extension(예: `omni.office_mcp.network_demo`)을 런타임 add_path 없이
   `extension_activate(...)`로 enable 가능.
- **PASS**: out-of-tree extension이 `--ext-folder`로 등록되어 enable됨. (자산 없으면 SKIP.)

### ④ stage 교체 play-guard — play 중 stage_new 92s hang 방지 (의견 #2)

1. `simulation_play` → `simulation_get_status`로 `is_playing:true` 확인.
2. `stage_new` 호출.
3. **기대**: **수 초 내 정상 반환**(92s timeout/hang 없음). 이후 `simulation_get_status`가
   `is_stopped:true` (가드가 자동 `simulation_stop` 선행).
- **PASS**: hang 없이 즉시 반환 + 자동 stop. (FAIL = 90초+ 멈춤 → `usd-load.md` 재발 진단 순서로 복구.)

### ⑤ viewport_capture warmup_frames + return_stats — cold-RTX black 자동판정 (의견 #3)

1. `viewport_capture(return_stats=true, warmup_frames=8)` (씬이 비어 있어도 됨).
2. **기대**: 응답에 `pixel_mean`(채널별 평균 리스트), `pixel_variance`, `warmup_frames_used:8` 포함.
   검은 프레임이면 `pixel_mean`≈0, 렌더 살아있으면 >0.
3. 교차확인: `simulation_play` 후 다시 캡처 → mean/variance 변화(렌더 갱신).
- **PASS**: stats 3종 필드 존재 + black/비-black이 mean으로 구분.

### ⑥ viewport_set_camera_lookat — deadlock-safe 카메라 이동 (의견 #3)

1. 콘텐츠가 있는 씬 준비: 간단히 `stage_create_prim`로 `/World/TestCube`(Cube) 1개 생성.
   (엄밀 검증은 아래 "MDL 옵션".)
2. `viewport_set_camera_lookat(eye=[5,5,5], target=[0,0,0])`.
3. **기대**: **수 초 내 반환**(office 세션의 92s deadlock 재발 없음), 응답에 `camera_path`(예
   `/OmniverseKit_Persp`). 이어 `viewport_capture(return_stats=true)`로 **앵글이 바뀐** 화면 확인.
- **PASS**: deadlock 없이 카메라 이동 + 캡처가 새 시점 반영.
- **MDL 옵션(권장, 엄밀)**: `usd-load.md` + `kkr-extensions/docs/usd-load-deadlock-recipe.md`대로
  office.usd를 fresh stage + CreatePayloadCommand 경로로 로드한 뒤 ⑥을 수행 → REST 동기 xformOp write가
  MDL 스테이지에서도 deadlock-free임을 확인. (자산/시간 여유 있을 때만.)

---

## 3. 완료 기준 (이 goal이 "done"인 조건)

- **①, ④, ⑤, ⑥** 각각 PASS로 확인되거나, FAIL이면 **증상 + 원인 진단 + Kit 로그 마지막 줄**까지 보고.
- **②**는 `office_mcp/exts/` 있으면 수행, 없으면 SKIP(사유 명시).
- 아래 형식으로 **종합 보고**하면 목표 완료:
```
① extension_reload: PASS/FAIL — <마커 반영 + 400 확인>
② extra_ext_folders: PASS/FAIL/SKIP — <근거>
④ play-guard: PASS/FAIL — <stage_new 반환 시간>
⑤ capture stats: PASS/FAIL — <pixel_mean 값 + 필드 존재>
⑥ camera_lookat: PASS/FAIL — <반환 시간 + 재프레이밍 확인>
```
- FAIL이 있어도 "진단과 함께 보고 완료"면 목표 충족 — 추측으로 PASS 단정 금지(정직 우선).
- 92s hang류 발생 시: `cmd //c "taskkill /F /IM kit.exe /T"`로 복구 후 원인 보고(`usd-load.md` 참조).

---

## 4. 정리 (검증 후)

- ① 마커 추가한 `extension.py` 원복: `git checkout -- <그 파일 경로>`.
- ② `.mcp.json`/`.env` 변경했으면 원복 여부 결정.
- 필요 시 `kit_app_stop`.

---

## 부록 — 검증 대상의 출처 (이미 `main`에 병합됨)

- `feat(extension): extension_reload …` + `feat(validation_api): /extension/reload_clean …` → **①**
- `feat(config): ISAAC_SIM_EXTRA_EXT_FOLDERS …` → **②**
- `feat(simulation): auto-stop timeline before stage swap …` → **④**
- `feat(viewport): viewport_capture warmup_frames + return_stats …` → **⑤**
- `feat(viewport): viewport_set_camera_lookat …` → **⑥**

③(deadlock-recipe 수정)·⑦(visual-validation 워크플로)·⑧(scene-reexport-lock 런북)은 문서/로직 변경이라
라이브 E2E 대상이 아님(코드 리뷰/단위로 충분).

> 이 파일은 repo 루트와 `workspaces/isaac/instance-1/`에 동일 사본으로 존재한다 (어느 위치에서 열어도
> `@live_e2e_prompt.md`가 resolve되도록). 둘은 동일하다.
