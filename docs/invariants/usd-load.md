<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: stage_load_usd / stage_open / robot_load / character_load 작업 시작 전 필수 숙지 -->
# USD Load — Invariants

`stage_load_usd` / `stage_open` / `robot_load` / `character_load` 호출 전 이 파일을
Read. 어느 한 조건이라도 깨지면 MDL resolver + carb log callback deadlock 으로 Kit
이벤트 루프 정지 → 모든 MCP tool 92 s timeout (실측 2026-04-20 hang 해결 후 baseline).

## 4 조건 (변경 금지 — 깨지면 hang 재발)

### 1. S3 URL 필수

허용 prefix:
- `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/...`
- `https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/...`
- `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/{ArchVis,DigitalTwin,Vegetation}/...`

`file:///` 로컬 캐시 **금지** (`isaac_course/cache_usd/` 재생성 금지).

카탈로그 SoT: `isaac_course/docs/asset_inventory.md` 진입점 + `isaac_course/docs/assets/*.md`.

### 2. `log_capture.start()` 호출 금지

- Extension `on_startup` 에서 `self._log_capture = None` 유지 (request-scoped refactor 전까지)
- MDL 로더 loop 가 carb thread 와 GIL 경합을 일으켰던 검증된 증상
- `extension_capture_logs` / `extension_clear_logs` MCP tool 은 현재 no-op

### 3. `ISAAC_SIM_EXTRA_EXT_IDS` 에 browser ext 금지

- `isaacsim.asset.browser` / `omni.kit.window.content_browser` 의 S3 crawl thread 가
  MDL resolver 와 경합하여 hang 확률 급증
- GUI Asset Browser 가 필요하면 수동 활성화 (해당 세션 후 비활성화)

### 4. 좀비 복구는 `cmd //c "taskkill /F /IM kit.exe /T"` 만 작동

- `powershell Stop-Process` 는 Access Denied 확정
- 편의 스크립트: `scripts/kill_kit_zombie.sh`

## `stage_open` vs `stage_load_usd`

- `stage_open(url)` — root stage 전체 교체 (scene 전환)
- `stage_load_usd(url, prim_path)` — 기존 stage 에 `/World/<name>` Payload 추가
  (multi-asset composition)

## 근본 원인 (재발 진단용)

`LogCaptureService` 의 carb log callback 이 등록된 상태에서 Kit 5.1 MDL resolver 가
S3 asset 의 Materials.usd 를 열면 `"Disabling base URL to resolve MDL identifier
'OmniPBR.mdl'"` 반복 → Python callback 이 carb thread 에 GIL 경합 → Kit main event
loop deadlock → 모든 MCP tool 92 s timeout.

## 해결 3 요소 (baseline — 변경 시 hang 재발)

1. Extension `on_startup` 에서 `self._log_capture = None`
   (NOT `get_log_capture_service().start()`)
2. `isaac_extension/omni.mycompany.validation_api/omni/mycompany/validation_api/services/stage_service.py::load_usd`
   는 `omni.kit.async_engine.run_coroutine(_main_loop_impl())` +
   `asyncio.wrap_future(future)` — FastAPI event loop ≠ Kit main event loop 이므로
   Kit main loop 에 명시적 schedule
3. `omni.kit.commands.execute("CreatePayloadCommand", instanceable=True, ...)` —
   GUI drag&drop scene_drop_delegate 와 동등 경로

코드 레시피 (독립 Extension 에서 S3 MDL-heavy asset 로드 시 복사할 방어 코드):
`isaac_extension/docs/usd-load-deadlock-recipe.md`

## 실측 (2026-04-20 hang 해결 후)

- Simple_Warehouse 2.4 s
- NovaCarter 3.1 s
- Biped_Setup 2.6 s
- SimReady cold 10~57 s
- Multi-asset composition OK

## 재발 시 진단 순서

1. Kit log `C:\Users\<you>\.nvidia-omniverse\logs\Kit\Isaac-Sim Full\5.1\kit_*.log`
   마지막 entry 가 `"Disabling base URL to resolve MDL identifier"` 반복 후 silent =
   deadlock 확정
2. `simulation_get_status` 가 92 s timeout → Kit main loop 차단
3. `cmd //c "taskkill /F /IM kit.exe /T"` (PowerShell `Stop-Process` 는 Access Denied)
4. `.venv/Scripts/python.exe scripts/run_process_module_standalone.py start` 로
   fresh restart

## 금지 사항 (재발 트리거)

- `log_capture.start()` 재활성
- `file:///` 로컬 캐시
- `ISAAC_SIM_EXTRA_EXT_IDS` 에 browser ext 추가
- **S3 load 실패 시 skip/fallback/placeholder** — 모두 금지. 근본 원인 분석 후 반드시 성공시킬 것

## 관련 경계

- 저수준 코드 위치 (Stage / USD 로드 프로토콜): `src/isaacsim_mcp/modules/CLAUDE.md`
- Asset URL 카탈로그 진입점: `isaac_course/docs/asset_inventory.md`
- 독립 Extension 방어 레시피: `isaac_extension/docs/usd-load-deadlock-recipe.md`
- LogCapture 비활성 결정 사고: `isaac_extension/docs/lessons-learned.md`
