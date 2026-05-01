<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Multi-app / multi-instance 아키텍처의 불변 규칙 — 새 profile 추가 시 필독 -->
# Multi-App × Multi-Instance — Invariants

이 MCP 서버는 한 host 에서 **여러 Kit 기반 app 인스턴스** 를 동시 제어한다.
현재 지원: **isaac-sim**, **usd-composer**. app 추가 / profile 수정 전 이 문서 Read.

## Port 할당 (contiguous per-profile window)

| Profile | Instance 1 | Instance 2 | Instance 3 |
|---------|-----------|-----------|-----------|
| `isaac-sim` | 8011 | 8012 | 8013 |
| `usd-composer` | 8014 | 8015 | 8016 |

파생 공식: `port = profile.default_ext_port + (instance_id - 1)`.

포트 충돌 방지 규칙:
- 새 profile 추가 시 `default_ext_port` 를 기존 profile 의 range 와 3-port
  간격 두고 할당 (kaolin → 8017 등)
- Instance 상한 3 은 `setup/setup_isaacsim_mcp.ps1` 의 `$InstanceCount` 에만
  명시. Code-level 제한 없음 — GPU 여유에 따라 늘릴 수 있음

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
포함 (isaacsim.sensors.rtx / omni.anim.* / isaacsim.replicator.agent.core).
USD Composer 에 주입하면 Kit boot 시 "Failed to resolve extension
dependencies" 로 crash. Config validator (`src/isaacsim_mcp/config.py::IsaacSimProcessConfig`) 가
profile=isaac-sim 에만 env 값 적용, 그 외는 profile 의 curated
extra_ext_ids 사용.

## 새 App Profile 추가 절차 (kaolin 등)

1. `src/isaacsim_mcp/types/profile.py` 에 `KitAppProfile` 추가 + `_PROFILES`
   dict 등록
2. `supported_module_groups` 에 해당 app 이 실제 지원하는 group 만 포함.
   지원 안 하는 group 은 extension 측 `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py` 의 guard 가 자동
   503 처리 → 추가 코드 변경 불필요
3. `setup/setup_isaacsim_mcp.ps1` 의 `$Profiles` 배열에 entry 추가
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

## 관련 경계

- Code SoT: `src/isaacsim_mcp/types/profile.py` (KitAppProfile + _PROFILES)
- ProcessModule launch: `src/isaacsim_mcp/modules/process_module.py::start`
- Extension guards: `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py`
- Setup registration: `setup/setup_isaacsim_mcp.ps1`
- 장애 대응: `docs/runbooks/multi-app.md`
