# Workspaces — omniverse-kit-mcp Consumer Workspaces

이 디렉토리는 omniverse-kit-mcp server 를 **사용** 하기 위한 워크스페이스. server 코드 / docs / tests 는 `../` (repo root) 참조.

## 사용 패턴

각 instance 폴더 = 1 MCP host 세션 (Claude Code 또는 codex) = 1 MCP entry 로드 (~150 tool 이름). 멀티 앱 시나리오는 호스트 창 2 개 동시 운영.

```
cd workspaces/isaac/instance-1   # Isaac Sim instance 1 (port 8011)
claude                            # Claude Code 진입
.\launch-codex.bat                # Codex CLI 진입 (대안)
```

## 첫 사용

`.mcp.json` 은 4 개 instance 폴더에 commit 되어 있다 (`uv --directory ../../..` 상대경로 — host working dir = instance 폴더 → repo root). clone 직후 추가 setup 없이 바로 `cd` + `claude` (또는 `.\launch-codex.bat`) 가능. uv / Isaac Sim / USD Composer 자체 설치만 별도 — `../setup/CLAUDE.md`. Codex CLI 자체 설치 (`npm install -g @openai/codex`) 는 `../README.md` Wiring 섹션.

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
- `{profile}/instance-{N}/.codex/config.toml` + `.\launch-codex.bat` — committed. Codex CLI 진입점 (workspace 별 1 MCP entry)

## 확장

instance-3 / cross-app `mixed/` / 신규 profile 추가 절차: `../docs/superpowers/specs/2026-05-04-workspace-split-design.md` § 14.

## Promote work scenario → server regression

상세: spec § 8 (4 항목 체크리스트 + `git mv`).
