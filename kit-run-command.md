<!-- SoT: src/omniverse_kit_mcp/modules/process_module.py::ProcessModule.start + types/profile.py + .env -->
<!-- 이 문서는 MCP `kit_app_start` tool 이 spawn 하는 실제 커맨드의 사람이 재현 가능한 형태이다. -->
<!-- profile / .env 가 변경되면 이 문서도 함께 갱신할 것. -->

# Kit Run Command — Isaac Sim & USD Composer

MCP `kit_app_start` 가 `subprocess.Popen` 으로 띄우는 실제 커맨드를 사람이 그대로 재현할 수 있는 형태로 정리한다. ProcessModule 우회 디버깅(MCP server 미경유 직접 기동) 시 사용.

## 공통 규약

| 항목 | 값 | 비고 |
|------|-----|------|
| `--ext-folder` | `<repo>/kkr-extensions` | 모든 profile 동일 |
| `--enable` (REST bridge) | `omni.mycompany.validation_api` | 항상 1 차 enable |
| Extension REST port flag | `--/exts/omni.services.transport.server.http/port=<PORT>` | port range fallback 차단용 강제 바인딩 |
| `stdin` | **`DEVNULL` 필수** | MCP stdio 상속 시 cold boot hang. PowerShell 직접 실행도 `< NUL` 권장 |
| `stdout` / `stderr` | `%TEMP%/omniverse_kit_mcp/kit_<epoch>.log` | OS pipe 버퍼 포화 → kit hang 방지 |

## Port 매트릭스 (instance_id → ext_port)

| Profile | Instance 1 | Instance 2 |
|---------|-----------|-----------|
| `isaac-sim` | 8111 | 8112 |
| `usd-composer` | 8114 | 8115 |

Health URL: `http://127.0.0.1:<PORT>/validation/v1/health`

---

## MCP-safe manual launchers

권장 수동 실행 진입점은 repo 원본 `setup/launchers/*_mcp.*` 를 각 앱 폴더에 복사한 파일이다.

| App | Installed launcher | Ports |
|---|---|---|
| Isaac Sim | `<isaac-sim-root>/isaac-sim_mcp.bat` | 8111 → 8112 |
| USD Composer | `<usd-composer-root>/kkr_usd_composer_mcp.kit.bat` | 8114 → 8115 |

두 launcher 모두 `--dry-run`, `--instance 1|2`, `--port <PORT>` 를 지원하고, 선택한 port 를 `--/exts/omni.services.transport.server.http/port=<PORT>` 와 `allow_port_range=false` 로 Kit 에 전달한다.

```powershell
& "<usd-composer-root>/kkr_usd_composer_mcp.kit.bat" --dry-run
& "<usd-composer-root>/kkr_usd_composer_mcp.kit.bat" --instance 2
```

---

## Isaac Sim

### 경로

- `kit.exe`: `<isaac-sim-root>/kit/kit.exe`
- `.kit`: `<isaac-sim-root>/apps/isaacsim.exp.full.kit`

### Extension enable 리스트

`.env` 의 `ISAAC_SIM_EXTRA_EXT_IDS` 가 적용 (profile default 를 override). 현재 `.env` 값:

```
omni.anim.graph.bundle
omni.anim.navigation.bundle
isaacsim.replicator.agent.core
omni.kit.ui_test
isaacsim.sensors.rtx
omni.graph.action
omni.replicator.core
omni.mycompany.navmesh_playground
```

### ROS 환경 변수 (필수 — silent fail 방지)

`isaac-sim.bat` + `setup_ros_env.bat` 동등 — 누락 시 ROS2 bridge dlopen 의존 ext 가 silent fail → kit 이벤트 루프 정지 → /health 미응답.

| 변수 | 값 |
|------|-----|
| `ROS_DISTRO` | `humble` |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` |
| `PATH` | 기존 `PATH` + `;<isaac-sim-root>/exts/isaacsim.ros2.bridge/humble/lib` |

### 커맨드 (instance 1, port 8111)

PowerShell:

```powershell
$env:ROS_DISTRO = "humble"
$env:RMW_IMPLEMENTATION = "rmw_fastrtps_cpp"
$env:PATH = "$env:PATH;<isaac-sim-root>/exts/isaacsim.ros2.bridge/humble/lib"

& "<isaac-sim-root>/kit/kit.exe" `
  "<isaac-sim-root>/apps/isaacsim.exp.full.kit" `
  --ext-folder "<repo>/kkr-extensions" `
  --enable omni.mycompany.validation_api `
  --/exts/omni.services.transport.server.http/port=8111 `
  --enable omni.anim.graph.bundle `
  --enable omni.anim.navigation.bundle `
  --enable isaacsim.replicator.agent.core `
  --enable omni.kit.ui_test `
  --enable isaacsim.sensors.rtx `
  --enable omni.graph.action `
  --enable omni.replicator.core `
  --enable omni.mycompany.navmesh_playground `
  *> "$env:TEMP/omniverse_kit_mcp/kit_isaac_$(Get-Date -UFormat %s).log" `
  < $null
```

bash (Git Bash):

```bash
export ROS_DISTRO=humble
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export PATH="$PATH:<isaac-sim-root>/exts/isaacsim.ros2.bridge/humble/lib"

"<isaac-sim-root>/kit/kit.exe" \
  "<isaac-sim-root>/apps/isaacsim.exp.full.kit" \
  --ext-folder "<repo>/kkr-extensions" \
  --enable omni.mycompany.validation_api \
  --/exts/omni.services.transport.server.http/port=8111 \
  --enable omni.anim.graph.bundle \
  --enable omni.anim.navigation.bundle \
  --enable isaacsim.replicator.agent.core \
  --enable omni.kit.ui_test \
  --enable isaacsim.sensors.rtx \
  --enable omni.graph.action \
  --enable omni.replicator.core \
  --enable omni.mycompany.navmesh_playground \
  > /tmp/kit_isaac.log 2>&1 < /dev/null &
```

### 다른 instance

`port=8111` 부분만 `8112` (instance 2) 로 교체.

---

## USD Composer

### 경로

- `kit.exe`: `<usd-composer-root>/kit/kit.exe`
- `.kit`: `<usd-composer-root>/apps/kkr_usd_composer.kit`

### Extension enable 리스트

profile 기본값이 비어있다 (`extra_ext_ids=()`). `validation_api` 만 enable. `ISAAC_SIM_EXTRA_EXT_IDS` 는 USD Composer 에 적용되지 않음 (`config.py::_resolve_profile_and_derived_fields` 가 isaac-sim profile 에만 env override 허용 — Isaac-only ext 주입 시 dependency resolve 실패로 crash).

### ROS 환경 변수

**불필요**. `_prepare_launch_env` 가 `ROS_DISTRO` / `RMW_IMPLEMENTATION` 을 명시적으로 env 에서 제거. 부모 셸에 ROS env 가 설정돼 있으면 unset 후 실행할 것.

### 커맨드 (instance 1, port 8114)

PowerShell:

```powershell
Remove-Item Env:ROS_DISTRO -ErrorAction SilentlyContinue
Remove-Item Env:RMW_IMPLEMENTATION -ErrorAction SilentlyContinue

& "<usd-composer-root>/kit/kit.exe" `
  "<usd-composer-root>/apps/kkr_usd_composer.kit" `
  --ext-folder "<repo>/kkr-extensions" `
  --enable omni.mycompany.validation_api `
  --/exts/omni.services.transport.server.http/port=8114 `
  *> "$env:TEMP/omniverse_kit_mcp/kit_usdcomposer_$(Get-Date -UFormat %s).log" `
  < $null
```

bash (Git Bash):

```bash
unset ROS_DISTRO
unset RMW_IMPLEMENTATION

"<usd-composer-root>/kit/kit.exe" \
  "<usd-composer-root>/apps/kkr_usd_composer.kit" \
  --ext-folder "<repo>/kkr-extensions" \
  --enable omni.mycompany.validation_api \
  --/exts/omni.services.transport.server.http/port=8114 \
  > /tmp/kit_usdcomposer.log 2>&1 < /dev/null &
```

### 다른 instance

`port=8114` 부분만 `8115` (instance 2) 로 교체.

---

## 종료 / 정리

```powershell
# 특정 instance 만 (port 로 식별 — 다른 instance 영향 없음)
$pid = Get-CimInstance Win32_Process -Filter "Name='kit.exe'" |
       Where-Object { $_.CommandLine -like "*port=8111*" } |
       Select-Object -First 1 -ExpandProperty ProcessId
taskkill /F /PID $pid /T

# 전체 종료 후 hub orphan 까지 정리 (host 의 모든 kit.exe 가 죽었을 때만 실행)
taskkill /F /IM hub.exe /T
Remove-Item "$env:TEMP/hub-*.lock", "$env:TEMP/hub-*.config.json" -ErrorAction SilentlyContinue
```

## 검증

기동 후 health 확인:

```powershell
curl http://127.0.0.1:8111/validation/v1/health   # Isaac Sim instance 1
curl http://127.0.0.1:8114/validation/v1/health   # USD Composer instance 1
```

200 응답 = ready. cold boot 는 stdin DEVNULL fix 후 13–30s, GPU 셰이더 캐시 재빌드 시 5–10 분.

## 관련 문서

- ProcessModule SoT: `src/omniverse_kit_mcp/modules/process_module.py`
- Profile SoT: `src/omniverse_kit_mcp/types/profile.py`
- Lifecycle invariants: `docs/invariants/process-lifecycle.md`
- Multi-app invariants: `docs/invariants/multi-app.md`
- stdin deadlock runbook: `docs/runbooks/kit-stdin-deadlock.md`
- Hub orphan runbook: `docs/runbooks/hub-orphan.md`

---

## Auto-attach 설정 (사용자 직접 기동 시 MCP attach 가능)

`.kit` 파일에 dependency / ext-folder / port 를 영구 박아 두어, **사용자가 평소 방식 (단축키, `isaac-sim.bat`, `repo.bat launch`) 으로 띄워도 MCP 가 attach 가능**하도록 설정. 이 설정 후에는 `--enable` / `--ext-folder` / `--/exts/...port=N` CLI 인자가 불필요.

### Isaac Sim — `branch/isaac-sim-standalone-5.1.0-windows-x86_64/apps/isaacsim.exp.full.kit`

- `[dependencies]` 끝에 9 개 추가 (validation_api + 8 개 character/sensor/replicator/omnigraph 의존성)
  - `omni.mycompany.validation_api`, `omni.anim.graph.bundle`, `omni.anim.navigation.bundle`, `isaacsim.replicator.agent.core`, `omni.kit.ui_test`, `isaacsim.sensors.rtx`, `omni.graph.action`, `omni.replicator.core`, `omni.mycompany.navmesh_playground`
- `[settings]` 에 `exts."omni.services.transport.server.http".port = 8111`
- `[settings.app.exts.folders] '++'` 배열에 `"<repo>/kkr-extensions"` 추가

### USD Composer — `branch/kit-app-template/source/apps/kkr_usd_composer.kit` (build artifact 자동 동기화)

- `[dependencies]` 끝에 `omni.mycompany.validation_api` 1 개만 추가 (USD Composer 는 common tool 만 지원)
- `[settings.exts]` 에 `"omni.services.transport.server.http".port = 8114` (Isaac Sim 과 충돌 회피)
- `[settings.app.exts.folders] '++'` 배열에 `"<repo>/kkr-extensions"` 추가

### 가설 검증 — browser ext 무해성 (2026-04-25 자동 검증)

과거 `docs/invariants/usd-load.md` 의 "browser ext 금지" 항목은 2026-04-20 시점 가설. 자동 검증으로 무효화 확인 후 invariants 에서 제거:

| 검증 항목 | 결과 |
|---|---|
| `extension.py:36` 의 `self._log_capture = None` (carb log hook 미등록) | 코드 확인 OK — deadlock 핵심 조건 미충족 |
| USD Composer (`content_browser` default 활성) 에서 warehouse MDL-heavy load | **PASS** — 17.5s, hang 없음 |
| Isaac Sim 동일 load (회귀 검증) | **PASS** — 54.8s (동시 instance + cold cache 환경) |

→ deadlock 의 진짜 인과는 **carb log hook 등록 + MDL resolver 결합**. log hook 이 disable 된 현재는 browser ext 활성 여부 무관. lessons-learned 에 사고 기록 보존.

### 검증

수정 후 사용자가 직접 두 앱을 다시 띄우고:

```powershell
curl http://127.0.0.1:8111/validation/v1/health   # Isaac Sim
curl http://127.0.0.1:8114/validation/v1/health   # USD Composer
```

두 응답 모두 200 → MCP `kit_app_start` (instance_id=1, profile=isaac-sim / usd-composer) 호출 시 `status=ready` (idempotent attach).

### 주의

- **ext-folder 가 절대경로** (`<repo>/kkr-extensions`) → 프로젝트를 옮기면 `.kit` 도 함께 갱신
- **Isaac Sim `.kit` 은 NVIDIA release 시 덮어쓸 수 있음** — major upgrade 후 위 변경 다시 적용
- **USD Composer source `.kit` 만 수정**: `_build/.../apps/` 산출물도 자동 sync 됨 확인. `repo.bat build` 재실행이 필요 없음
- ROS env (`ROS_DISTRO=humble` 등) 는 `.kit` 에서 set 불가 → Isaac Sim 은 항상 `isaac-sim.bat` 으로 띄울 것 (자동 set). USD Composer 는 ROS 불필요
