<!-- Parent: ../../CLAUDE.md (server repo root) -->
<!-- Scope: Isaac Sim profile workspace — Where the user cds to start CC or codex -->
# Isaac Sim Workspace

Workspace for USD scene/scenario/robot demo with Isaac Sim 6.0.0.
Up to instance-1 (port 8111) / instance-2 (port 8112) can be operated simultaneously — CC or codex starts after `cd instance-{1,2}`.

## ⚠️ Required pull-doc before work

| work | Read first |
|---|---|
| USD Load (`stage_load_usd` / `robot_load` / `character_load` / `stage_open`) | `../../docs/invariants/usd-load.md` |
| Isaac Sim start/shutdown/hang | `../../docs/invariants/process-lifecycle.md` |
| Parent ↔ live MCP worker coordination | `../../docs/invariants/live-worker-coordination.md` |
| `viewport_capture` / scene build | `../../docs/invariants/visual-validation.md` |
| Extension UI automation (`extension_ui_invoke`) | `../../docs/invariants/ui-invoke.md` |
| Error diagnosis | `../../docs/tool-diagnostic-map.md` |

## Scenario commit rule

YAML of `scenarios/` is committed only when it meets R1 (actual NVIDIA Nucleus / Hub URL asset only). If not met, stored in `scratch/`. If server regression is warranted, pass the promote checklist item 4 of `../README.md` and then move server `scenarios/` to `git mv`.

## Scratch cleanup

`scratch/` is gitignored — temporary USD/screenshots/task notes. After the session ends, if it is not meaningful, clean it up.

## Related Boundaries

- Server repo rule: `../../CLAUDE.md` (root)
- Multi-app / port matrix: `../../docs/invariants/multi-app.md`
- Workspace-wide scenario matrix + directory convention: `../README.md`
- Promote checklist Main text: `../README.md`