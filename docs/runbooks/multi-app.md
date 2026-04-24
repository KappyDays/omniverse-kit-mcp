<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Multi-app / multi-instance 장애 대응 — port 충돌 / USD Composer 기동 실패 / 교차 감염 -->
# Multi-App 장애 대응

## 증상 1 — USD Composer instance start 시 `crashed` 즉시 반환

**진단**:
```bash
ls "/c/Users/kang/workspace/branch/kit-app-template/_build/windows-x86_64/release/kit/kit.exe"
ls "/c/Users/kang/workspace/branch/kit-app-template/_build/windows-x86_64/release/apps/kkr_usd_composer.kit"
```

둘 중 하나 없으면: USD Composer 빌드 손상.

**복구**:
```bash
cd /c/Users/kang/workspace/branch/kit-app-template
./repo.bat build --release
```
빌드 완료 후 재시도.

## 증상 1b — USD Composer crashed + `Failed to resolve extension dependencies`

**증상**: `log_tail` 에 `No versions of isaacsim.replicator.agent.core that
satisfies` 또는 유사한 Isaac-specific extension 이름.

**원인**: `ISAAC_SIM_EXTRA_EXT_IDS` 가 USD Composer profile 에 leak. Config
validator 에서 profile=isaac-sim 검사가 누락되면 발생.

**진단**:
```bash
.venv/Scripts/python.exe -c "
from isaacsim_mcp.config import AppConfig
import os
os.environ['ISAAC_MCP_APP_PROFILE']='usd-composer'
ac = AppConfig()
print('extra_ext_ids:', ac.isaac_sim_process.extra_ext_ids)
"
```

Expected for usd-composer: `()` (empty). If Isaac-specific IDs appear →
`docs/invariants/multi-app.md` 의 "ISAAC_SIM_EXTRA_EXT_IDS 는 Isaac-profile 전용"
section 의 validator 회귀 확인.

## 증상 2 — USD Composer 에서 `/robot/load` 가 503 이 아니라 404

**원인**: validation_api extension 이 USD Composer 에 로드 안 됨. kit 런치
command 에 `--ext-folder` / `--enable omni.mycompany.validation_api` 플래그가
빠졌거나, extension path 가 잘못됨.

**진단**:
```bash
# 방금 띄운 USD Composer 의 CommandLine 확인
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='kit.exe'\" | Where-Object { \$_.CommandLine -like '*port=8014*' } | Select-Object -ExpandProperty CommandLine"
```

CommandLine 에 `--ext-folder` 와 `--enable omni.mycompany.validation_api`
둘 다 있어야 함. 없으면 `src/isaacsim_mcp/modules/process_module.py::ProcessModule` start cmd 배열 빌드 회귀.

**복구**: stop + start 사이클 후 재진단. 여전히 문제면 Level C.

## 증상 3 — Isaac instance 2 기동 시 `Address already in use`

**원인**: 이전 kit 이 port 8012 를 잡고 있는데 `_is_process_alive` 가 감지
못 함 (CommandLine 에 `port=8012` 가 없는 kit — 예: 수동 GUI 실행 kit).

**진단**:
```bash
netstat -ano | findstr ":8012"
```

PID 확인 → 그 PID 가 무엇인지:
```bash
powershell.exe -NoProfile -Command "Get-Process -Id <PID> | Select-Object Id, ProcessName, StartTime, Path"
```

**복구**:
- 우리 MCP 가 띄운 게 아닌 외부 kit 이면 → 수동으로 Stop 또는 포기
- 우리 게 맞는데 식별 실패면 → `taskkill /F /PID <PID>` 수동 실행 후 재시도

## 증상 4 — Isaac + USD Composer 동시 기동 시 GPU OOM

**증상**: 두 번째 start 가 `still_loading` 반복 + log_tail 에
`CUDA out of memory` / `Failed to allocate` / `Vulkan device lost`.

**복구**:
- Scene content 를 empty 로 유지 (asset load 금지)
- 한 번에 하나씩만 사용 (Isaac 끝나면 stop, 그 다음 USD Composer)
- Long-term: GPU upgrade 또는 streaming mode 사용

## 증상 5 — hub.exe cleanup 이 다른 instance 를 깨뜨림

**증상**: Instance 2 stop 후 instance 1 의 asset listing (`/content/browse`)
이 `ClientLibraryError` / connection refused.

**원인**: `_cleanup_orphan_hub` 의 "다른 kit alive 면 skip" 가드 회귀.

**진단**:
```bash
Get-Process -Name hub -ErrorAction SilentlyContinue
netstat -ano | findstr :14090
```

hub.exe 가 없어졌으면 회귀 확정.

**복구**: Instance 1 도 restart — hub 가 자동 재생성됨. 코드 레벨 fix 는
`tests/unit/test_process_module_multi_app.py::test_hub_cleanup_skipped_when_other_kit_alive`
가 검증.

## 증상 6 — `~/.claude.json` 에 `isaacsim-mcp-*` entry 가 하나만 있음

**원인**: setup script 가 구 버전 (multi-app 이전) 로 실행됨.

**복구**: feature branch 에서:
```bash
cmd //c "setup\\setup-isaacsim-mcp.bat"
```
이후 `~/.claude.json` 검증 (Phase 5.2 Step 2 참조).

## 관련 경계

- Invariants: `docs/invariants/multi-app.md`
- Code SoT:
  - `src/isaacsim_mcp/modules/process_module.py`
  - `isaac_extension/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py`
- Live smoke:
  - `scripts/verify_multi_instance.py`
  - `scripts/verify_multi_app.py`
- 기존 장애: `docs/runbooks/kit-stdin-deadlock.md`, `cold-boot-timeout.md`,
  `hub-orphan.md`, `env-sub-config.md`
