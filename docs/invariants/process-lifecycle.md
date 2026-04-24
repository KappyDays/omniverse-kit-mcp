<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: isaac_sim_start / isaac_sim_stop / isaac_sim_restart 작업 시작 전 필수 숙지 -->
<!-- Multi-app context: 이 문서의 "kit.exe" 는 모든 app profile 에 동일하게 적용됨.
     Profile 별 launch 차이는 `docs/invariants/multi-app.md` 참조. -->
# Process Lifecycle — Invariants

이 MCP 서버의 모든 stage / viewport / character / robot / sensor / scenario tool 은
`kit.exe` 가 기동되어 `GET /validation/v1/health` 가 200 응답 시까지 무의미.
ProcessModule 호출 전 이 파일 Read.

## Tool 동작 요약

| Tool | 동작 | 정상 시간 |
|------|------|----------|
| `isaac_sim_start` | kit.exe 런치 (또는 alive process attach) + health polling (2 s interval, `startup_timeout` 까지) | warm boot 15-30 s · cold boot 13-30 s (stdin DEVNULL fix 후) |
| `isaac_sim_stop` | `taskkill /F /IM kit.exe /T` + orphan hub 정리 | ≤10 s |
| `isaac_sim_restart` | stop → `isaac_extension/.../__pycache__` clear → start | stop + start 합 |

## ⚠️ stdin=subprocess.DEVNULL 필수 (변경 금지 — DO-NOT-EDIT)

`src/isaacsim_mcp/modules/process_module.py::start` 의 `subprocess.Popen(...)` 가
`stdin=subprocess.DEVNULL` 명시 안 하면 MCP server 자식 kit.exe 가 Claude Code 의
MCP protocol stdin pipe 를 상속 → cold boot 중 stdin read 시 indefinite block →
전체 boot 정지. **240s timeout, 13s ready 검증 (L17)**. "extra_ext_ids race" 진단은
무효 — stdin pipe 가 실원인.

본문 / 재현 / 복구: `docs/runbooks/kit-stdin-deadlock.md`

## `isaac_sim_start` 결정 트리 (2026-04-23 redesign)

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

- `stdout` / `stderr` 는 `%TEMP%/isaacsim_mcp/kit_<epoch>.log` 로 리다이렉트
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

`src/isaacsim_mcp/modules/process_module.py::_prepare_launch_env` 가 isaac-sim.bat 의
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
.venv/Scripts/python.exe -c "from isaacsim_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout)"
```
→ `.env` 값 반영 확인. 누락 시 silent failure.

사고 + 재발 방지 체크리스트: `docs/runbooks/env-sub-config.md`

## Hang 확정 지표 (정확한 도구)

- **`isaac_sim_start` 응답** — `process_alive=true` 인데 반복 호출해도 ready 안 됨 +
  log_tail mtime 수 분째 정체
- **PowerShell** `Get-Process -Name kit -ErrorAction SilentlyContinue` —
  row 없음 = 죽음, row 있으면 alive
- **MCP `simulation_get_status`** — 응답 (duration_ms < 1000) = alive, refused = 죽음
- **`curl http://localhost:8011/validation/v1/health`** — 200 = alive
- `netstat -ano | grep ":8011" | grep LISTENING` 없음 = endpoint 미기동

**금지** (false negative — L7): `tasklist //FI "IMAGENAME eq kit.exe"` (git bash)
filter 처리 timing 문제로 alive Kit 도 빈 결과 반환.

## 관련 경계

- 코드 위치 SoT (ProcessModule hang recovery 4종 함정): `src/isaacsim_mcp/modules/process-ops.md`
- Standalone 테스트 스크립트: `scripts/run_process_module_standalone.py`
- DO-NOT-EDIT residual 본문 (재현 / 복구): `docs/runbooks/kit-stdin-deadlock.md`
- Cold boot timeout 분기 해석: `docs/runbooks/cold-boot-timeout.md`
- Hub orphan 수동 복구: `docs/runbooks/hub-orphan.md`
- Env sub-config 함정 본문: `docs/runbooks/env-sub-config.md`
