<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Multi-app / multi-instance 아키텍처의 불변 규칙 — 새 profile 추가 시 필독 -->
# Multi-App × Multi-Instance — Invariants

이 MCP 서버는 한 host 에서 **여러 Kit 기반 app 인스턴스** 를 동시 제어한다.
현재 지원: **isaac-sim**, **usd-composer**. app 추가 / profile 수정 전 이 문서 Read.

## Port 할당 (contiguous per-profile window)

| Profile | Instance 1 | Instance 2 |
|---------|-----------|-----------|
| `isaac-sim` | 8111 | 8112 |
| `usd-composer` | 8114 | 8115 |

파생 공식: `port = profile.default_ext_port + (instance_id - 1)`.

포트 충돌 방지 규칙:
- 새 profile 추가 시 `default_ext_port` 를 기존 profile 의 range 와 3-port
  간격 두고 할당 (kaolin → 8017 등)
- Instance 한도 2 — `src/omniverse_kit_mcp/config.py` 의 `instance_id` Field
  에 `ge=1, le=2` 가드. 사용자 결정 (2026-05-23) 으로 영구 한도 (확장 절차 없음)

## Process Identification (name scope 금지)

**금지**: `taskkill /IM kit.exe`, `Get-Process -Name kit` — host 의 모든
instance 매칭됨.

**필수**: PID 기반 (`taskkill /F /PID <self._process.pid> /T`) 또는
CommandLine 필터 (`ProcessModule._resolve_instance_pid` 가
`port=<N>` 문자열로 식별). `port=<N>` 은 kit 런치 시 `--/exts/...port=N`
플래그로 CommandLine 에 unique 하게 주입됨.

## Hub.exe 공유 daemon

`hub.exe` (port 14090) 는 모든 kit.exe 가 공유. `_cleanup_orphan_hub` 는
**호스트에 kit.exe 0 개** 일 때만 cleanup 수행. 조건부 skip 안 하면 한
instance 를 stop 할 때 다른 instance 의 asset resolution 이 끊긴다.

## Extension REST Bridge 중립성

`omni.mycompany.validation_api` 는 **app-agnostic**. Isaac / USD Composer
모두에서 로드된다. Isaac-특화 route 는 request-time 에 필요한 Kit ext 활성
여부를 probe 하여 없으면 HTTP 503 반환.

Guard function 은 `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py` 의
`require_*_stack()` — 새 Isaac-특화 route 추가 시 여기도 guard 등록.

## ISAAC_SIM_EXTRA_EXT_IDS 는 Isaac-profile 전용

`.env` 의 `ISAAC_SIM_EXTRA_EXT_IDS` 는 Isaac-specific extension id 만
포함 (isaacsim.sensors.experimental.rtx / isaacsim.sensors.experimental.physics /
isaacsim.ros2.bridge / isaacsim.replicator.agent.core).
USD Composer 에 주입하면 Kit boot 시 "Failed to resolve extension
dependencies" 로 crash. Config validator (`src/omniverse_kit_mcp/config.py::IsaacSimProcessConfig`) 가
profile=isaac-sim 에만 env 값 적용, 그 외는 profile 의 curated
extra_ext_ids 사용.

## 새 App Profile 추가 절차 (kaolin 등)

1. `src/omniverse_kit_mcp/types/profile.py` 에 `KitAppProfile` 추가 + `_PROFILES`
   dict 등록
2. `supported_module_groups` 에 해당 app 이 실제 지원하는 group 만 포함.
   지원 안 하는 group 은 extension 측 `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py` 의 guard 가 자동
   503 처리 → 추가 코드 변경 불필요
3. `setup/setup_omniverse_kit_mcp.ps1` 의 `$Profiles` 배열에 entry 추가
4. `tests/unit/test_config_multi_app.py` 에 profile 별 port / supported
   group / kit_exe 검증 테스트 추가
5. `scripts/verify_multi_app.py` 를 확장 (optional — 새 profile smoke)

## MCP Tool Surface Invariance

Profile 이 늘어나도 `EXPECTED_MODULE_TOOLS` frozenset 은 변하지 않는다.
- 공통 tool 은 profile 무관 등록
- 지원 안 하는 capability 는 runtime 에 tool 이 `CAPABILITY_NOT_SUPPORTED`
  error_code 반환 (UI 에서 graceful)
- Tool 이름 기반 profile 분기 (예: `isaacsim_robot_load`) 금지 —
  frozenset 관리 부담 + client 가 profile 별로 다른 tool 이름을 알아야 함

## `.kit` ext folder 절대경로 — repo / 디렉토리 rename 시 필수 갱신

`branch/` 의 외부 Kit app build (`isaac-sim-standalone-*.bat`,
`branch/kit-app-template/_build/.../release/*.kit.bat`,
`branch/usd-composer-webrtc-streaming/.../release/*.kit.bat`) 는 자기 layout
밖의 `omniverse-kit-mcp/kkr-extensions/` 를 ext folder 로 흡수하기 위해
`.kit` 파일의 `[settings.app.exts.folders]` `'++'` 리스트에 **절대경로** 를
하드코딩한다. (상대경로는 .kit 위치별 깊이가 달라 layout-fragile).

작업 디렉토리 rename / repo move 시 이 절대경로가 stale 되면 `omni.mycompany.*`
extension 이 ext folder 에서 안 보이고 dependency solver 가 즉시 fail —
`.bat` 직접 실행 3 초만에 종료. 진단·복구: `docs/runbooks/kit-dep-solver-fail.md`.

### 검출 절차 (rename / move 직후 필수)

```bash
# 1) 현재 트리 전체에서 .kit 파일의 ext folder 절대경로 grep
grep -rn '"<workspace>/' --include='*.kit' <workspace>/

# 2) 매치된 모든 경로의 실제 디렉토리 존재 + 비어있지 않은지 확인
#    (rename 후 옛 경로는 빈 폴더만 잔존하는 케이스 흔함)
```

### 대상 파일 목록 (2026-05-04 현재)

- `branch/isaac-sim-standalone-6.0.0-windows-x86_64/apps/isaacsim.exp.full.kit`
- `branch/kit-app-template/source/apps/kkr_usd_composer.kit`
  (`_build/windows-x86_64/release/apps/kkr_usd_composer.kit` 와 hardlink — source 만 수정해도 양쪽 갱신)
- `branch/usd-composer-webrtc-streaming/kit-app-template/source/apps/kkr_usd_composer.kit`
  (동일 hardlink 패턴)

세 파일 모두 `[settings.app.exts.folders]` `'++'` 리스트의 마지막 항목이
`"<repo>/kkr-extensions"` 로 통일되어 있어야 함.

## 관련 경계

- Code SoT: `src/omniverse_kit_mcp/types/profile.py` (KitAppProfile + _PROFILES)
- ProcessModule launch: `src/omniverse_kit_mcp/modules/process_module.py::start`
- Extension guards: `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py`
- Setup registration: `setup/setup_omniverse_kit_mcp.ps1`
- Dependency solver fail 진단: `docs/runbooks/kit-dep-solver-fail.md`
- 장애 대응: `docs/runbooks/multi-app.md`
