# Live E2E Verification — omniverse-kit-mcp P1 Upgrade

> **이 파일 하나만으로 새 세션에서 실행 가능하도록 작성됨.** 당신은 omniverse-kit-mcp 프로젝트의
> P1 업그레이드(아래 항목)를 **라이브 Isaac Sim에서 검증**하는 역할이다. 코드/단위테스트는 이미
> 통과했으나, MCP import-cache 제약 때문에 **라이브 E2E는 미검증** 상태다. 이 프롬프트의 체크리스트를
> 순서대로 수행하고, 각 항목 pass/fail을 보고하라.

---

## 0. 가장 중요한 전제 (import-cache) — 안 지키면 전부 헛수고

이 업그레이드는 (a) **새 MCP 도구 2개**, (b) **validation_api Extension의 새 REST 엔드포인트**, (c)
**기존 도구 파라미터 확장**을 포함한다. 둘 다 캐시 때문에 "그냥 호출"하면 옛 코드가 돈다:

1. **새 MCP 도구는 "이 repo에서 새로 spawn된 MCP 서버" 세션에서만 보인다.**
   - 이 세션을 **`workspaces/isaac/instance-1/` 폴더에서 열어라.** 그 안의 `.mcp.json`이
     `uv --directory ../../.. run omniverse-kit-mcp`로 **이 repo의 최신 코드로 서버를 spawn**한다.
   - 첫 확인: 당신의 MCP 도구 목록에 **`extension_reload`** 와 **`viewport_set_camera_lookat`** 가
     있는가? 없으면 MCP 서버가 stale → **세션을 재시작**(또는 MCP 서버 재시작)하라. 있을 때까지 진행 금지.

2. **validation_api의 새 REST는 `kit_app_restart` 후에만 라이브 반영된다.**
   - Kit이 옛 코드로 이미 떠 있으면 반드시 `kit_app_restart`. 안 떠 있으면 `kit_app_start`.
   - kit.exe는 `--ext-folder <repo>/kkr-extensions`로 기동되어 **이 repo의 validation_api**를 로드한다.

> 작업 전 필독: `docs/invariants/usd-load.md`, `docs/invariants/process-lifecycle.md` (stage 로드/기동
> 규칙·deadlock 방어). 실패 진단은 `docs/tool-diagnostic-map.md`.
> 전체 설계/근거: `docs/superpowers/specs/2026-05-26-mcp-upgrade-p1-design.md` + plan 동명 파일.

---

## 1. 셋업

1. (위 0-1) 새 도구 2개가 도구 목록에 있는지 확인.
2. `kit_app_start` (instance 1, isaac-sim profile). 이미 옛 코드로 떠 있으면 `kit_app_restart`.
   - cold boot는 수 분 걸릴 수 있음 — `process-lifecycle.md`의 still_loading 처리 참고.
3. `simulation_get_status`로 살아있는지 확인.

---

## 2. 검증 체크리스트 (항목별 action → 기대 → pass 기준)

### ① extension_reload — Kit 재시작 없이 .py 반영 (의견 #1)

1. 테스트용 데모 extension 활성화: `extension_activate("omni.mycompany.ui_demo")`.
2. `kkr-extensions/omni.mycompany.ui_demo/omni/mycompany/ui_demo/extension.py`(또는 그 패키지의 .py)에
   **눈에 띄는 마커**를 추가 — 예: `on_startup`에 `carb.log_warn("E2E_RELOAD_MARKER_v1")` 한 줄.
3. `extension_reload("omni.mycompany.ui_demo")` 호출.
4. **기대**: 응답 `{ok:true, reloaded:true, modules_purged:>=1}`. 그리고 마커가 실제로 반영됨 —
   `extension_capture_logs(ext_id="omni.mycompany.ui_demo")`에서 `E2E_RELOAD_MARKER_v1`가 보이거나,
   UI 변경이라면 `extension_get_ui_tree`로 새 위젯/라벨 확인. **`kit_app_restart` 없이** 반영돼야 함.
5. **self-reload 가드**: `extension_reload("omni.mycompany.validation_api")` → **HTTP 400**(self-reload
   unsupported) 반환해야 함. 200이면 FAIL.
- **PASS**: 마커가 restart 없이 반영 + validation_api self-reload가 400.

### ② ISAAC_SIM_EXTRA_EXT_FOLDERS — out-of-tree extension 등록 (의견 #1, 선택/고급)

1. `workspaces/isaac/instance-1/.mcp.json`의 `env`에 (또는 repo `.env`에)
   `"ISAAC_SIM_EXTRA_EXT_FOLDERS": "[\"C:/Users/<you>/workspace/omniverse-kit-mcp/office_mcp/exts\"]"` 추가.
2. 세션 재시작(서버가 env 다시 읽도록) → `kit_app_restart`.
3. **기대**: `office_mcp/exts/` 하위 extension(예: `omni.office_mcp.network_demo`)을 런타임
   `add_path` 없이 `extension_activate(...)`로 바로 enable 가능.
- **PASS**: out-of-tree extension이 launch 시 `--ext-folder`로 등록되어 enable됨.
- (office_mcp/exts가 없으면 이 항목은 skip하고 그렇게 보고.)

### ④ stage 교체 play-guard — play 중 stage_new 92s hang 방지 (의견 #2)

1. `simulation_play` → `simulation_get_status`로 `is_playing:true` 확인.
2. `stage_new` 호출.
3. **기대**: **수 초 내 정상 반환**(92s timeout/hang 없음). 이후 `simulation_get_status`가 `is_stopped:true`
   (가드가 자동 `simulation_stop` 선행).
- **PASS**: hang 없이 즉시 반환 + 자동 stop 확인. (FAIL = 90초+ 멈춤.)

### ⑤ viewport_capture warmup_frames + return_stats — cold-RTX black 자동판정 (의견 #3)

1. (씬이 비어 있어도 됨) `viewport_capture(return_stats=true, warmup_frames=8)`.
2. **기대**: 응답에 `pixel_mean`(채널별 평균 리스트), `pixel_variance`, `warmup_frames_used:8` 포함.
   검은 프레임이면 `pixel_mean`가 0에 가깝고, 렌더가 살아있으면 >0.
3. 교차 확인: `simulation_play` 후 다시 캡처 → mean/variance가 달라지는지(렌더 갱신).
- **PASS**: stats 3종 필드가 응답에 존재 + black/비-black이 mean으로 구분됨.

### ⑥ viewport_set_camera_lookat — deadlock-safe 카메라 이동 (의견 #3)

1. 콘텐츠가 있는 씬 준비 — 간단히는 `stage_create_prim`로 Cube 1개 + 조명. **엄밀한 검증**은
   MDL-heavy 씬(office.usd 등)을 deadlock-recipe로 로드한 상태에서(아래 주의) 카메라를 옮기는 것.
2. `viewport_set_camera_lookat(eye=[5,5,5], target=[0,0,0])`.
3. **기대**: **수 초 내 반환**(office 세션의 92s deadlock 재발 없음), 응답에 `camera_path`(예:
   `/OmniverseKit_Persp`). 이어서 `viewport_capture`(return_stats=true)로 **앵글이 바뀐** 화면 확인.
- **PASS**: deadlock 없이 카메라 이동 + 캡처가 새 시점 반영. (FAIL = 90초+ 멈춤.)
- **MDL 엄밀 테스트(권장)**: `usd-load.md`/`usd-load-deadlock-recipe.md`대로 office.usd를 로드한 뒤
  ⑥을 수행해 REST 경로 동기 xformOp write가 MDL 스테이지에서도 안전함을 확인.

---

## 3. 보고 형식

각 항목을 다음으로 보고:
```
① extension_reload: PASS/FAIL — <근거: 마커 반영 여부 + 400 확인>
② extra_ext_folders: PASS/FAIL/SKIP — <근거>
④ play-guard: PASS/FAIL — <stage_new 반환 시간>
⑤ capture stats: PASS/FAIL — <pixel_mean 값 + 필드 존재>
⑥ camera_lookat: PASS/FAIL — <반환 시간 + 재프레이밍 확인>
```
FAIL 시: 증상 + Kit 로그 마지막 줄(`C:\Users\<you>\.nvidia-omniverse\logs\Kit\...`) + 어느 단계에서
막혔는지. 92s hang류면 `usd-load.md` "재발 시 진단 순서" 따라 `taskkill /F /IM kit.exe /T`로 복구.

---

## 4. 정리

- ① 마커 추가했던 `extension.py` 원복(git checkout 또는 마커 라인 삭제).
- ② .mcp.json/.env 변경했으면 원복 여부 결정.
- 필요 시 `kit_app_stop`.

---

## 부록 — 검증 대상 변경의 출처 (커밋)

`main` 브랜치(이미 병합됨)에 포함:
- `feat(extension): extension_reload …` / `feat(validation_api): /extension/reload_clean …` → ①
- `feat(config): ISAAC_SIM_EXTRA_EXT_FOLDERS …` → ②
- `feat(simulation): auto-stop timeline before stage swap …` → ④
- `feat(viewport): viewport_capture warmup_frames + return_stats …` → ⑤
- `feat(viewport): viewport_set_camera_lookat …` → ⑥

(③ deadlock-recipe 수정, ⑦ visual-validation 워크플로, ⑧ scene-reexport-lock 런북은 문서/로직 변경이라
라이브 E2E 대상 아님 — 코드 리뷰/단위로 충분.)
