<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: .env 변수가 무시되는 silent failure 진단 -->
# env sub-config silent failure (L14)

`.env` 의 `ISAAC_SIM_*` / `LAKEHOUSE_*` / `MCP_*` / `SCENARIO_*` 가 silently 무시되면
이 파일 진입.

## 증상 (2026-04-23 실측)

- `.env` 의 `ISAAC_SIM_STARTUP_TIMEOUT=120.0` 항상 무시 → default 240.0 사용
- `.env` 의 `ISAAC_SIM_EXTRA_EXT_IDS=[7개]` 항상 무시 → default 4개만 활성 →
  `omni.mycompany.navmesh_playground` 등 미등록
- 사용자 / 운영자가 `.env` 변경해도 효과 없는 silent failure
- 코드 / 변수명 모두 정확한데 동작 안 함

## 근본 원인

pydantic-settings v2 는 `default_factory` 로 만든 sub-`BaseSettings` 인스턴스에
**부모의 `env_file` 을 전파하지 않음**. `AppConfig(BaseSettings)` 가
`model_config = SettingsConfigDict(env_file=".env")` 를 가져도 sub-config
(`IsaacSimProcessConfig` 등) 가 `Field(default_factory=IsaacSimProcessConfig)` 로
인스턴스화될 때, 각 sub-config 는 독립 BaseSettings 인스턴스 → 부모의 `env_file`
전파받지 않음 → 자체 `env_file` 이 없으면 OS 환경변수만 참조.

## Fix 적용 위치

`src/isaacsim_mcp/config.py` (SoT). 모든 sub-`BaseSettings` 에 자체 `env_file=".env"`
명시:

```python
class IsaacSimProcessConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ISAAC_SIM_",
        env_file=".env",      # CRITICAL — sub-config 마다 명시 필수
        extra="ignore",
    )
    ...
```

대상 sub-config (전부 적용):
- `IsaacSimConfig`
- `IsaacSimProcessConfig`
- `LakehouseConfig`
- `MCPServerConfig`
- `ScenarioConfig`

## 검증 (PR 전 필수)

```bash
.venv/Scripts/python.exe -c "from isaacsim_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout, len(ac.isaac_sim_process.extra_ext_ids))"
```

→ `.env` 의 값 반영되어야 함 (예: 120.0 / 7).

영구 회귀 검출 (자동): `tests/integration/test_env_sub_config.py` (E14-1 / E14-2 /
E14-3 — AST 파싱으로 모든 sub-`BaseSettings` 가 `env_file=".env"` 가졌는지 검증).

## 재발 방지 (신규 sub-config 추가 시 체크리스트)

신규 `class XYZConfig(BaseSettings)` 추가 시 반드시:
1. `model_config = SettingsConfigDict(env_prefix="XYZ_", env_file=".env", extra="ignore")` 명시
2. test_env_sub_config.py E14-3 가 자동으로 검증함 — 추가 코드 불필요

## 관련 경계

- L14 사고 기록 원문: `isaac_extension/docs/lessons-learned.md`
- Config SoT: `src/isaacsim_mcp/config.py`
- Process 생애주기 invariants: `docs/invariants/process-lifecycle.md`
- 영구 회귀 테스트: `tests/integration/test_env_sub_config.py`
