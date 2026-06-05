<!-- Parent: ../../CLAUDE.md (server repo root) -->
<!-- Scope: Isaac Sim profile workspace — 사용자가 cd 해서 CC 또는 codex 시작하는 곳 -->
# Isaac Sim Workspace

Isaac Sim 5.1 으로 USD scene / 시나리오 / robot demo 작업하는 워크스페이스.
instance-1 (port 8011) / instance-2 (port 8012) 까지 동시 가동 가능 — `cd instance-{1,2}` 후 CC 또는 codex 시작.

## ⚠️ 작업 전 필수 pull-doc

| 작업 | 먼저 Read |
|---|---|
| USD 로드 (`stage_load_usd` / `robot_load` / `character_load` / `stage_open`) | `../../docs/invariants/usd-load.md` |
| Isaac Sim 기동 / 종료 / hang | `../../docs/invariants/process-lifecycle.md` |
| `viewport_capture` / scene build | `../../docs/invariants/visual-validation.md` |
| Extension UI automation (`extension_ui_invoke`) | `../../docs/invariants/ui-invoke.md` |
| 에러 진단 | `../../docs/tool-diagnostic-map.md` |

## Scenario commit 룰

`scenarios/` 의 YAML 은 R1 (실 NVIDIA Nucleus / Hub URL asset 만) 충족 시에만 commit. 미충족이면 `scratch/` 에 보관. server 회귀로 박을 만하면 promote checklist (`../../docs/superpowers/specs/2026-05-04-workspace-split-design.md` § 8) 4 항목 통과 후 `git mv` 로 server `scenarios/` 이동.

## Scratch 정리

`scratch/` 는 gitignored — 임시 USD / 스크린샷 / 작업 메모. 세션 종료 후 의미 없으면 정리.

## 관련 경계

- Server repo 룰: `../../CLAUDE.md` (root)
- Multi-app / port 매트릭스: `../../docs/invariants/multi-app.md`
- 워크스페이스 전체 시나리오 매트릭스 + 디렉토리 규약: `../README.md`
- Promote checklist 본문: `../../docs/superpowers/specs/2026-05-04-workspace-split-design.md` § 8
