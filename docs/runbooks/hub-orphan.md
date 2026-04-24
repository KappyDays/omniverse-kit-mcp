<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: OmniHub orphan port 14090 잔존 진단 / 복구 -->
# OmniHub orphan port 14090 (수동 복구)

`omni.client` 가 spawn 한 `hub.exe` daemon 이 orphan 잔존하여 다음 kit 기동 시
`"Hub failed to launch: child exited with exit code: 1"` 발생 시 진입.

## 증상

- `isaac_sim_start` 의 startup_log 에 `"Hub failed to launch: child exited with exit
  code: 1"` 반복
- `netstat -ano | findstr :14090` 결과 LISTENING 이지만 새 connection 은 `10061
  refused`
- kit.exe 종료 후에도 `Get-Process -Name hub -ErrorAction SilentlyContinue` 가 row 반환
- `%TEMP%/hub-*.lock` / `hub-*.config.json` 파일 잔존

## 근본 원인

`omni.client` 가 `hub.exe` 를 `--mode=shared` 로 spawn — kit process tree 와 분리된
daemon. kit 종료해도 port 14090 orphan 잔존. 시간 경과 시 accept loop broken →
새 connection refuse → 다음 kit 의 OmniHub init 실패.

## 자동 복구 (현재 적용됨)

`src/isaacsim_mcp/modules/process_module.py::_cleanup_orphan_hub` 가
`stop` / `start` 양쪽에서 자동 수행:
- `taskkill /F /IM hub.exe /T`
- `%TEMP%/hub-*.lock` / `hub-*.config.json` 파일 제거

## 수동 복구 (자동 fail 시)

1. **Hub process 강제 종료**:
   ```bash
   cmd //c "taskkill /F /IM hub.exe /T"
   ```
   (PowerShell `Stop-Process` 는 Access Denied 가능)

2. **Lock / config 파일 정리**:
   ```bash
   rm -f /c/Users/$USER/AppData/Local/Temp/hub-*.lock /c/Users/$USER/AppData/Local/Temp/hub-*.config.json
   ```

3. **kit 재기동**:
   ```bash
   .venv/Scripts/python.exe scripts/run_process_module_standalone.py start
   ```

## 진단 도구

- `Get-Process -Name hub -ErrorAction SilentlyContinue` (PowerShell) — alive 확인
- `netstat -ano | findstr :14090` — LISTENING 확인
- `ls /c/Users/$USER/AppData/Local/Temp/hub-*` — lock/config 파일 확인

## 관련 경계

- 자동 복구 코드: `src/isaacsim_mcp/modules/process_module.py::_cleanup_orphan_hub`
- ProcessModule hang recovery 4종 함정 중 #4: `src/isaacsim_mcp/modules/process-ops.md`
- Process 생애주기 invariants: `docs/invariants/process-lifecycle.md`
- Cold boot timeout 분기: `docs/runbooks/cold-boot-timeout.md`
