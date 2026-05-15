<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: kit_app_start / kit_app_stop / kit_app_restart 작업 시작 전 필수 숙지 -->
<!-- Multi-app context: 이 문서의 "kit.exe" 는 모든 app profile 에 동일하게 적용됨.
     Profile 별 launch 차이는 `docs/invariants/multi-app.md` 참조. -->
# Process Lifecycle — Invariants

이 MCP 서버의 모든 stage / viewport / character / robot / sensor / scenario tool 은
`kit.exe` 가 기동되어 `GET /validation/v1/health` 가 200 응답 시까지 무의미.
ProcessModule 호출 전 이 파일 Read.

## Tool 동작 요약

| Tool | 동작 | 정상 시간 |
|------|------|----------|
| `kit_app_start` | kit.exe 런치 (또는 alive process attach) + health polling (2 s interval, `startup_timeout` 까지) | warm boot 15-30 s · cold boot 13-30 s (stdin DEVNULL fix 후) |
| `kit_app_stop` | `taskkill /F /IM kit.exe /T` + orphan hub 정리 | ≤10 s |
| `kit_app_restart` | stop → `kkr-extensions/.../__pycache__` clear → start | stop + start 합 |

## ⚠️ stdin=subprocess.DEVNULL 필수 (변경 금지 — DO-NOT-EDIT)

`src/omniverse_kit_mcp/modules/process_module.py::start` 의 `subprocess.Popen(...)` 가
`stdin=subprocess.DEVNULL` 명시 안 하면 MCP server 자식 kit.exe 가 MCP host (Claude Code / Codex CLI) 의
MCP protocol stdin pipe 를 상속 → cold boot 중 stdin read 시 indefinite block →
전체 boot 정지. **240s timeout, 13s ready 검증 (L17)**. "extra_ext_ids race" 진단은
무효 — stdin pipe 가 실원인.

본문 / 재현 / 복구: `docs/runbooks/kit-stdin-deadlock.md`

## `kit_app_start` 결정 트리 (2026-04-23 redesign)

```
process alive?
├─ NO  → spawn fresh + poll health (startup_timeout 초)
└─ YES → health responding?
         ├─ YES → return status=ready (idempotent)
         └─ NO  → poll health WITHOUT respawn (startup_timeout 초)
                  (cold boot 진행 중일 수 있어 강제로 죽이지 않음)
```

## Timeout 응답 (`startup_timeout` 만료 시)

- `process_alive=true` → `{status: "still_loading", log_tail: [...], pid}` —
  caller 재호출로 spawn 없이 폴링 이어감
- `process_alive=false` → `{status: "crashed", log_tail: [...]}` —
  즉시 진단 (commonly: ext 누락 / MDL deadlock / GPU driver)

응답 분기 / log_tail 해석 패턴: `docs/runbooks/cold-boot-timeout.md`

## stdout/stderr 규약 (변경 금지)

- `stdout` / `stderr` 는 `%TEMP%/omniverse_kit_mcp/kit_<epoch>.log` 로 리다이렉트
- **`subprocess.DEVNULL` 금지** (stdin 과 정반대) — Windows OS pipe 버퍼 포화 시
  kit.exe 초기화 정지
- `start()` 는 매 기동 시 `_sweep_old_logs()` 로 7일 이전 `kit_*.log` 자동 삭제
- `startup_log` + `log_tail` 필드가 실패 원인 파악용

## startup_timeout 기본값

- 기본 120 s (사용자 확정 2026-04-23). 의도: 빠른 진단 정보 반환
- Cold boot (GPU 셰이더 캐시 재빌드) 가 5-10 분 걸려도 timeout 후 `still_loading` +
  `process_alive=true` 반환 → 재호출하면 Branch 2 폴링 이어감
- stdin fix 후 cold boot 는 보통 13-30 초 — 5-10분 케이스는 transient
  (hub orphan / pycache 손상) 의심

## ROS env 자동 setup (silent fail 방지)

`src/omniverse_kit_mcp/modules/process_module.py::_prepare_launch_env` 가 isaac-sim.bat 의
ROS env setup 을 Python 으로 재현 — 생략 시 ROS2 bridge 의존 ext silent fail →
kit.exe 이벤트 루프 정지 → `/health` 미응답.

## OmniHub orphan 주의

kit.exe 는 `hub.exe` 를 `--mode=shared` daemon 으로 분리 spawn → `taskkill /T` 가
kit tree 에 닿지 않아 hub 가 port 14090 orphan 잔존. 수 시간 경과 시 accept loop
broken → 다음 기동 `"Hub failed to launch: exit code 1"`.

자동 처리: `ProcessModule._cleanup_orphan_hub()` 가 `stop/start` 양쪽에서 자동
실행. 수동 복구 절차: `docs/runbooks/hub-orphan.md`

## `.env` ↔ sub-config 전파 (L14)

pydantic-settings v2 는 `default_factory` sub-`BaseSettings` 에 부모의 `env_file` 을
전파하지 않음. 모든 sub-config (`IsaacSimConfig`, `IsaacSimProcessConfig`,
`LakehouseConfig`, `MCPServerConfig`, `ScenarioConfig`) 가 자체 `env_file=".env"`
보유 필수.

검증 명령:
```bash
.venv/Scripts/python.exe -c "from omniverse_kit_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout)"
```
→ `.env` 값 반영 확인. 누락 시 silent failure.

사고 + 재발 방지 체크리스트: `docs/runbooks/env-sub-config.md`

## External instance check (destructive 작업 전 필수)

`kit_app_stop` 은 **THIS MCP server 가 spawn 한 kit.exe 만** 종료. 사용자가 GUI
실행한 standalone Isaac Sim, 다른 MCP server (multi-instance / multi-app) 는 별도
프로세스로 살아있을 수 있음 — Kit 은 종료 시 carb persistent settings (예:
`%LOCALAPPDATA%\ov\data\Kit\<app>\<ver>\user.config.json`) 을 메모리에서 덮어쓰기
때문에 **외부 인스턴스가 살아있는 채로 config 편집 시 변경분이 셧다운에 사라짐**.

### 점검 절차

destructive 작업 전 `process_list_kit_instances` MCP tool 호출:

```
process_list_kit_instances → instances[].is_this_mcp_instance == false 인 row 가
있으면 외부 인스턴스 — 사용자에게 종료 요청 후 작업 진행
```

### Destructive 작업 정의 (외부 인스턴스 영향 받음)

- Kit `user.config.json` / `*.toml` 편집 (carb persistent settings)
- `%LOCALAPPDATA%\ov\data\Kit\<app>` 캐시 / extension data 삭제
- `extension_activate(reload=True)` 같은 강제 reload (다른 인스턴스에는 무영향이나
  파일 충돌 가능)
- `omniverse.toml` / `hub.toml` 등 omniverse 공통 config 편집

### 영향 없는 (안전한) 작업

- `__pycache__` 삭제 (`kit_app_restart` 가 자동 — ext_folder 한정)
- `kit.exe stdout/stderr 로그 sweep` (`_sweep_old_logs`, 7일 이전)
- `simulation_*` / `stage_*` / `viewport_*` (Extension REST 경유 — 다른 인스턴스
  REST 와 격리)

## Hang 확정 지표 (정확한 도구)

- **`kit_app_start` 응답** — `process_alive=true` 인데 반복 호출해도 ready 안 됨 +
  log_tail mtime 수 분째 정체
- **PowerShell** `Get-Process -Name kit -ErrorAction SilentlyContinue` —
  row 없음 = 죽음, row 있으면 alive
- **MCP `simulation_get_status`** — 응답 (duration_ms < 1000) = alive, refused = 죽음
- **`curl http://localhost:8011/validation/v1/health`** — 200 = alive
- `netstat -ano | grep ":8011" | grep LISTENING` 없음 = endpoint 미기동

**금지** (false negative — L7): `tasklist //FI "IMAGENAME eq kit.exe"` (git bash)
filter 처리 timing 문제로 alive Kit 도 빈 결과 반환.

## `.bat` wrapper PID ≠ kit.exe PID (false-positive EXITED 회피)

수동 진단 (PowerShell) 에서 `branch/` 의 외부 Kit `.bat` 을 백그라운드로 띄울 때:

```powershell
$proc = Start-Process -FilePath $bat `
    -RedirectStandardOutput $log -RedirectStandardError $err `
    -PassThru -WindowStyle Hidden
# $proc.Id 는 .bat 호스트 cmd.exe / 또는 .bat 자체의 PID — kit.exe 의 PID 가 아님
```

`.bat` 은 내부에서 `call "%~dp0kit\kit.exe" ...` 으로 자식 kit.exe 를 spawn 하고
대기. 호스트 wrapper 는 자식 종료를 따라 함께 종료되므로 kit.exe 가 살아있는 동안은
wrapper PID 도 살아있다 — **그러나 일부 케이스 (cmd.exe wrapper 가 즉시 detach,
또는 kit.exe 가 fastShutdown 후 wrapper 만 잔존하다 즉시 종료) 에서는 wrapper PID 가
먼저 사라져 false-positive `EXITED` 보고**.

생사 확인 권장 도구:

```powershell
# 자식 kit.exe 자체 확인 (multi-instance host 면 PID 비교 필요)
Get-Process -Name kit -ErrorAction SilentlyContinue

# 부모 wrapper PID 의 자식 process 트리
Get-CimInstance Win32_Process -Filter "ParentProcessId=<wrapperPID>" |
    Select-Object ProcessId, Name, CommandLine
```

(Multi-app / multi-instance 에서 `Get-Process -Name kit` 는 host 의 모든 kit.exe
매칭 — `port=<N>` 으로 식별. 본문 §"Process Identification (name scope 금지)" 참조 —
[`multi-app.md`](multi-app.md))

## 관련 경계

- 코드 위치 SoT (ProcessModule hang recovery 4종 함정): `src/omniverse_kit_mcp/modules/process-ops.md`
- Standalone 테스트 스크립트: `scripts/run_process_module_standalone.py`
- DO-NOT-EDIT residual 본문 (재현 / 복구): `docs/runbooks/kit-stdin-deadlock.md`
- Cold boot timeout 분기 해석: `docs/runbooks/cold-boot-timeout.md`
- Hub orphan 수동 복구: `docs/runbooks/hub-orphan.md`
- Env sub-config 함정 본문: `docs/runbooks/env-sub-config.md`
