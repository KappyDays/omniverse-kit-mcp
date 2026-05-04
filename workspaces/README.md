# Workspaces — omniverse-kit-mcp Consumer Workspaces

이 디렉토리는 omniverse-kit-mcp server 를 **사용** 하기 위한 워크스페이스. server 코드 / docs / tests 는 `../` (repo root) 참조.

## 사용 패턴

각 instance 폴더 = 1 개 CC 세션 = 1 MCP entry 로드 (~150 tool 이름). 멀티 앱 시나리오는 CC 창 2 개 동시 운영.

```
cd workspaces/isaac/instance-1   # Isaac Sim instance 1 (port 8011)
claude
```

## 첫 사용

`.mcp.json` 은 4 개 instance 폴더에 commit 되어 있다 (`uv --directory ../../..` 상대경로 — CC working dir = instance 폴더 → repo root). clone 직후 추가 setup 없이 바로 `cd` + `claude` 가능. uv / Isaac Sim / USD Composer 자체 설치만 별도 — `../setup/CLAUDE.md`.

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
- `{profile}/instance-{N}/.mcp.json` — committed. `uv --directory ../../..` 상대경로. CC 진입점

## 확장

instance-3 / cross-app `mixed/` / 신규 profile 추가 절차: `../docs/superpowers/specs/2026-05-04-workspace-split-design.md` § 14.

## Promote work scenario → server regression

상세: spec § 8 (4 항목 체크리스트 + `git mv`).
