<!-- Parent: ../../CLAUDE.md (server repo root) -->
<!-- Scope: USD Composer profile workspace -->
# USD Composer Workspace

USD Composer 로 USD scene authoring / DCC 작업하는 워크스페이스.
instance-1 (port 8014) / instance-2 (port 8015) 까지 동시 가동 가능 — `cd instance-{1,2}` 후 CC 시작.

## ⚠️ Capability 제약

USD Composer 는 robotics ext (`robot_*`, `sensor_attach_rtx_*`, `character_*`, `replicator_*`) 를 로드하지 않는다. 호출 시 `CAPABILITY_NOT_SUPPORTED` 반환 — 상세: `../../docs/invariants/multi-app.md`.

## ⚠️ 작업 전 필수 pull-doc

| 작업 | 먼저 Read |
|---|---|
| USD 로드 (`stage_load_usd` / `stage_open`) | `../../docs/invariants/usd-load.md` |
| USD Composer 기동 / 종료 | `../../docs/invariants/process-lifecycle.md` |
| `viewport_capture` / scene build | `../../docs/invariants/visual-validation.md` |
| Extension UI automation | `../../docs/invariants/ui-invoke.md` |
| 에러 진단 | `../../docs/tool-diagnostic-map.md` |

## Scenario commit 룰

`scenarios/` YAML 은 R1 충족 시에만 commit. promote 절차: spec § 8 4 항목 통과 후 `git mv` 로 server `scenarios/` 이동.

## Scratch 정리

`scratch/` 는 gitignored — 임시 USD / 스크린샷. 세션 종료 후 정리.

## 관련 경계

- Server repo 룰: `../../CLAUDE.md` (root)
- Multi-app / port 매트릭스 + Capability 규칙: `../../docs/invariants/multi-app.md`
- 워크스페이스 전체 시나리오 매트릭스 + 디렉토리 규약: `../README.md`
- Promote checklist 본문: `../../docs/superpowers/specs/2026-05-04-workspace-split-design.md` § 8
