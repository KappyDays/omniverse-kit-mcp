# Workspaces — omniverse-kit-mcp Consumer Workspaces

이 디렉토리는 omniverse-kit-mcp server 를 **사용** 하기 위한 워크스페이스. server 코드 / docs / tests 는 `../` (repo root) 참조.

## 사용 패턴

각 instance 폴더 = 1 MCP host 세션 (Claude Code 또는 codex) = 해당 app/instance 의 Kit MCP entry 제공 (~150 tool 이름). Codex 전역 MCP entry 가 있으면 함께 표시될 수 있다. 멀티 앱 시나리오는 호스트 창 2 개 동시 운영.

```
cd workspaces/isaac/instance-1   # Isaac Sim instance 1 (port 8111)
claude                            # Claude Code 진입
codex                             # Codex CLI 진입
```

## 첫 사용

`.mcp.json` 과 `.codex/config.toml` 은 4 개 instance 폴더에 commit 되어 있다 (`uv --directory ../../..` 상대경로 — host working dir = instance 폴더 → repo root). clone 직후 추가 setup 없이 바로 `cd` + `claude` 또는 `codex` 가능. uv / Isaac Sim / USD Composer 자체 설치만 별도 — `../setup/CLAUDE.md`. Codex CLI 자체 설치 (`npm install -g @openai/codex`) 는 `../README.md` Wiring 섹션.

CodeGraph 같은 코드 탐색 MCP 는 user/global Codex config 에 둔다. 이
workspace-local `.codex/config.toml` 들에는 Kit MCP entry 1 개만 유지해야
하며, `tests/unit/test_codex_entrypoint_sync.py` 가 sibling `.mcp.json` 과의
1:1 mirror 를 검증한다. CodeGraph 를 쓰려면 repo root 에서
`codegraph init -i` 로 `.codegraph/` 를 만들고, workspace 폴더의
`codex mcp list` 에서 global `codegraph` 와 workspace Kit MCP 가 함께
보이는지만 확인한다.

## 시나리오 → 폴더 매트릭스

| 시나리오 | CC 창 | 진입 폴더 |
|---|---|---|
| isaac × 1 | 1 | `isaac/instance-1/` |
| composer × 1 | 1 | `usd-composer/instance-1/` |
| isaac + composer | 2 동시 | `isaac/instance-1/` + `usd-composer/instance-1/` |
| isaac × 2 | 2 동시 | `isaac/instance-1/` + `isaac/instance-2/` |
| composer × 2 | 2 동시 | `usd-composer/instance-1/` + `usd-composer/instance-2/` |

## 디렉토리 규약

- `{profile}/CLAUDE.md` — profile 별 작업 룰 + pull-doc 표 (server `docs/` 상대경로 참조)
- `{profile}/scenarios/` — work-only YAML. R1 충족 시 commit 가능
- `{profile}/scratch/` — gitignored. 임시 USD / 스크린샷
- `{profile}/instance-{N}/.mcp.json` — committed. `uv --directory ../../..` 상대경로. CC (Claude Code) 진입점
- `{profile}/instance-{N}/.codex/config.toml` — committed. Codex CLI 진입점 (workspace 별 Kit MCP entry)

## 확장

신규 profile 추가 절차는 `../docs/invariants/multi-app.md` 의 "새 App Profile
추가 절차" 를 따른다. 새 profile 을 추가하면 해당 profile 폴더, instance
`.mcp.json`, `.codex/config.toml`, profile `CLAUDE.md`, setup 등록, config/test
가 함께 움직여야 한다.

## Promote work scenario → server regression

work-only scenario 를 server regression 으로 승격할 때는 아래 4 항목을 통과한
뒤 `git mv` 로 server `scenarios/` 아래로 이동한다.

1. 실 NVIDIA / Hub asset 만 사용한다. primitive 대체 검증은 승격 금지.
2. `scenario_validate` 또는 동등한 live 검증이 통과한다.
3. 캡처가 필요한 시나리오는 `viewport_capture` 결과를 시각 확인한다.
4. app/profile 고유 전제는 YAML 또는 인접 README 에 명시한다.
