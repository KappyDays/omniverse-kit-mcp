<!-- Parent: CLAUDE.md -->
<!-- Scope: ProcessModule 운영 매뉴얼 — 기동 장애 / 환경 설정 시 참조 -->

# ProcessModule — 운영 매뉴얼

kit.exe 기동/종료 관련 운영 자료. 정상 개발 흐름에서는 읽을 필요 없음.
아래 상황에서만 참조:
- `kit_app_start` 가 `still_loading` / `crashed` 반환 시
- kit.exe hang / zombie 의심 시
- `.env` 환경변수 미반영 시

작업 전 필수 숙지: `../../../docs/invariants/process-lifecycle.md`. 장애별 진단
절차: `../../../docs/runbooks/` (kit-stdin-deadlock / cold-boot-timeout /
hub-orphan / env-sub-config).

## ProcessModule stdin/stdout/stderr 규약 (변경 금지)

- **`stdin=subprocess.DEVNULL` 필수** (2026-04-24 root cause 확정 — `../../../docs/runbooks/kit-stdin-deadlock.md` 필독). MCP server 는 MCP host (Claude Code / Codex CLI) 의 stdio 자식 → 그 stdin 은 MCP protocol pipe. ProcessModule 이 `subprocess.Popen` 에 `stdin` 명시 안 하면 자식 kit.exe 가 그 pipe 를 상속 → cold boot 중 stdin read 시 block → 전체 boot 정지 (~85 ms 시점, ext registration 직후). bash 에서 standalone 실행은 TTY stdin 이라 안전 — 이 차이 때문에 standalone 은 통과 / MCP 는 hang 의 false negative 가 발생함
- `stdout` / `stderr` 는 **`%TEMP%/omniverse_kit_mcp/kit_<epoch>.log`** 로 리다이렉트. **stdout/stderr 에 `subprocess.DEVNULL` 금지** — Windows OS pipe 버퍼 포화 시 kit.exe 초기화 정지 (stdin 와 정반대)
- `startup_timeout` 기본 120 s (사용자 확정 2026-04-23). 의도: **cold boot 끝까지 기다리지 말고 빠르게 진단 정보 반환**. Cold boot (GPU 셰이더 캐시 재빌드) 가 5-10 분 걸려도 timeout 후 `status=still_loading` + `process_alive=true` 반환 → caller 가 `kit_app_start` 재호출하면 spawn 없이 폴링만 이어감 (Branch 2). **stdin fix 후 cold boot 는 보통 13-30 초** — 5-10분 케이스는 transient (hub orphan / pycache 손상) 의심
- `ProcessModule.start()` 반환 dict 의 `startup_log` + `log_tail` 필드가 실패 원인 파악용
- `start()` 는 매 기동 시 `_sweep_old_logs()` 로 7 일 이전 `kit_*.log` 자동 삭제

## ProcessModule.start() 결정 트리 (2026-04-23 redesign)

```
process alive?
├─ NO  → spawn fresh + poll health (startup_timeout 초)
└─ YES → health responding?
         ├─ YES → return status=ready (idempotent)
         └─ NO  → poll health WITHOUT respawn (startup_timeout 초)
                  (cold boot 진행 중일 수 있어 강제로 죽이지 않음)
```

Timeout 응답 (`startup_timeout` 도달 시):
- `process_alive=true` → `{status: "still_loading", log_tail: [...], pid}` — caller 재호출로 Branch 2 폴링 이어감
- `process_alive=false` → `{status: "crashed", log_tail: [...]}` — 즉시 진단 (commonly: ext 누락 / MDL deadlock / GPU driver)

Orphan kit.exe 강제 회수가 필요하면 `kit_app_stop` + `kit_app_start` 명시적 호출 (옛 "auto force-kill" 의 안전한 대체). Log tail 해석 절차: `../../../docs/runbooks/cold-boot-timeout.md`.

## ProcessModule hang recovery (GUI X-close 후 재기동 실패)

**증상**: `kit_app_start` 응답이 `still_loading` 으로 반복 (process_alive=true 인데 health 영원히 무응답) — orphan 또는 진짜 hang.

**원인 (4 중, 발견 빈도 순)**:
1. **stdin pipe inheritance** (2026-04-24 확정, 가장 흔하고 위험): MCP server (`omniverse-kit-mcp`) 가 MCP host (Claude Code / Codex CLI) 의 stdio 자식 → `subprocess.Popen(...)` 에 `stdin` 명시 안 하면 자식 kit.exe 가 MCP protocol pipe 을 stdin 으로 상속 → cold boot 중 stdin read 시도 시 block → 전체 boot 정지. 증상: alive + CPU ~0 + WS ~60MB + internal log mtime ~85ms 시점 정체. **`subprocess.Popen(stdin=subprocess.DEVNULL, ...)` 명시 필수** (현재 ProcessModule 적용 완료). bash 에서 standalone script 로 실행하면 stdin=TTY 라 안전 — 이 차이가 false negative 의 흔한 원인 ("standalone 으로는 되는데 MCP 로는 hang" → stdin DEVNULL 누락 의심)
2. **ROS env 누락**: `ProcessModule` 이 `subprocess.Popen(env=)` 미지정 시 `ROS_DISTRO` / `RMW_IMPLEMENTATION` / `PATH` (`ros2.bridge/humble/lib`) 가 빠짐 → ROS2 bridge 의존 Kit extension 이 startup 훅에서 silent fail → kit.exe 이벤트 루프 정지. **2026-04-19 `_prepare_launch_env()` 도입으로 자동 회피됨** (`../../../docs/invariants/process-lifecycle.md`). 재발 시 startup_log 의 ROS env 라인 확인
3. **MDL resolver deadlock**: `LogCaptureService` 가 활성 + S3 MDL-heavy asset 로드 시 carb log callback 가 GIL 경합으로 main loop 정지. log_tail 마지막이 `"Disabling base URL to resolve MDL identifier"` 반복 후 침묵. 회피: `../../../docs/invariants/usd-load.md` 의 3 요소 baseline 유지
4. **Hub orphan**: `omni.client` 가 `hub.exe` 를 `--mode=shared` 로 spawn → kit process tree 와 분리된 daemon → kit 종료해도 port 14090 orphan 잔존. 시간 경과 시 accept loop broken 되어 `netstat` 은 LISTENING 이지만 새 connection 은 `10061 refused` → 다음 kit 의 OmniHub init 실패, startup_log 에 `"Hub failed to launch: child exited with exit code: 1"` 반복. `ProcessModule._cleanup_orphan_hub()` 가 `stop/start` 양쪽에서 `taskkill /F /IM hub.exe /T` + `%TEMP%/hub-*.{lock,config.json}` 제거 자동 수행. 수동 회복: `../../../docs/runbooks/hub-orphan.md`

**복구 절차**:
1. `kit_app_start` 응답의 `log_tail` 확인 → MDL deadlock 시그니처 또는 ext 로드 실패 확인
2. 진짜 hang 으로 판정되면 강제 종료: `cmd //c "taskkill /F /IM kit.exe /T"` (실측: 유일하게 성공. PowerShell `Stop-Process` / `taskkill /F /PID <pid>` 은 "Access is denied"). 편의 스크립트: `../../../scripts/kill_kit_zombie.sh`
3. Minimal ext 직접 런치 (cold boot 우회로 빠른 health 확인):
   ```bash
   nohup "C:/.../kit/kit.exe" "C:/.../apps/isaacsim.exp.full.kit" \
     --ext-folder "C:/.../omniverse-kit-mcp/kkr-extensions" \
     --enable omni.mycompany.validation_api \
     > "$LOG" 2>&1 &
   ```
   이후 MCP `kit_app_start` 가 alive 감지 + health 폴링하여 ready 응답
4. Character / Navigation / UI automation 필요 시: minimal endpoint 확인 후 `kit_app_restart` 로 `.env` full ext-list 재기동

**Hang 확정 지표** (정확한 도구):
- **`kit_app_start` 응답** — `process_alive=true` 인데 반복 호출해도 ready 안 됨 + log_tail mtime 수 분째 정체
- **PowerShell `Get-Process -Name kit -ErrorAction SilentlyContinue`** — row 없음 = 죽음, row 있으면 alive (CPU 고정 + WorkingSet 정체면 hang 의심)
- **MCP `simulation_get_status`** — 응답 (duration_ms < 1000) = alive, connection refused = 죽음
- **`curl http://localhost:8011/validation/v1/health`** — 200 응답 = alive
- `netstat -ano | grep ":8011" | grep LISTENING` 없음 = endpoint 미기동
- `%TEMP%/omniverse_kit_mcp/kit_<epoch>.log` mtime 수 분째 정체

**금지** (false negative 발생): `tasklist //FI "IMAGENAME eq kit.exe"` (git bash 호출). filter 처리 timing 문제로 alive Kit 도 빈 결과 반환. 2026-04-23 사용자 검증 + I3 (`../../../docs/implementation_issues.md`).

## `.env` ↔ sub-config 함정 (2026-04-23 발견)

pydantic-settings v2 는 `default_factory` 로 만든 sub-`BaseSettings` 인스턴스에 **부모의 `env_file` 을 전파하지 않음**. 모든 sub-config (`IsaacSimConfig`, `IsaacSimProcessConfig`, `LakehouseConfig`, `MCPServerConfig`, `ScenarioConfig`) 가 자체 `model_config = SettingsConfigDict(env_prefix=..., env_file=".env", extra="ignore")` 를 가져야 함. 누락 시 OS 환경변수만 참조 → `.env` silently 무시.

**증상 (실측)**:
- `.env` 의 `ISAAC_SIM_STARTUP_TIMEOUT=120.0` 무시 → 항상 default 240.0 사용
- `.env` 의 `ISAAC_SIM_EXTRA_EXT_IDS=[7개]` 무시 → 항상 default 4개만 활성 → `omni.mycompany.navmesh_playground` 등 미등록

**검증**:
```bash
.venv/Scripts/python.exe -c "from omniverse_kit_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout, len(ac.isaac_sim_process.extra_ext_ids))"
```
→ `.env` 값 반영되어야 함. 사고 기록 + 재발 방지 체크리스트: `../../../docs/runbooks/env-sub-config.md`.

## Isaac Sim Standalone 경로 (ProcessModule 기본값)

```
C:\Users\<you>\workspace\branch\isaac-sim-standalone-5.1.0-windows-x86_64\
  ├── kit\kit.exe
  └── apps\isaacsim.exp.full.kit
```

다른 사용자는 `.env` 에 `ISAAC_SIM_KIT_EXE` + `ISAAC_SIM_KIT_FILE` override (README §"Isaac Sim Setup" 참조).

## 관련 경계

- 코드 SoT: `process_module.py::start` / `process_module.py::_cleanup_orphan_hub`
- Process lifecycle invariants (작업 전 필수): `../../../docs/invariants/process-lifecycle.md`
- stdin pipe deadlock (L17): `../../../docs/runbooks/kit-stdin-deadlock.md`
- Cold boot timeout 분기: `../../../docs/runbooks/cold-boot-timeout.md`
- Hub orphan 복구: `../../../docs/runbooks/hub-orphan.md`
- Env sub-config 함정 (L14): `../../../docs/runbooks/env-sub-config.md`
- 모듈 책임 매트릭스 + Character 제약: `CLAUDE.md` (sibling)
- Integration Facts (15 도메인): `integration-facts.md` (sibling)
- Standalone 테스트 스크립트: `../../../scripts/run_process_module_standalone.py`
