<!-- Parent: ../../CLAUDE.md (server repo root) -->
<!-- Scope: USD Composer profile workspace -->
# USD Composer Workspace

Workspace for USD scene authoring/DCC work using USD Composer.
Up to instance-1 (port 8114) / instance-2 (port 8115) can be operated simultaneously — CC or codex starts after `cd instance-{1,2}`.

## ⚠️ Capability constraints

USD Composer does not load robotics ext (`robot_*`, `sensor_attach_rtx_*`, `character_*`, `replicator_*`). Returns `CAPABILITY_NOT_SUPPORTED` when called — verbose: `../../docs/invariants/multi-app.md`.

## ⚠️ Required pull-doc before work

| work | Read first |
|---|---|
| USD Load (`stage_load_usd` / `stage_open`) | `../../docs/invariants/usd-load.md` |
| USD Composer startup/exit | `../../docs/invariants/process-lifecycle.md` |
| Parent ↔ live MCP worker coordination | `../../docs/invariants/live-worker-coordination.md` |
| `viewport_capture` / scene build | `../../docs/invariants/visual-validation.md` |
| Extension UI automation | `../../docs/invariants/ui-invoke.md` |
| Error diagnosis | `../../docs/tool-diagnostic-map.md` |

## Scenario commit rule

`scenarios/` YAML commits only when R1 is satisfied. Promote procedure: After passing the 4-item checklist of `../README.md`, move server `scenarios/` to `git mv`.

## Scratch cleanup

`scratch/` is gitignored — Temporary USD / Screenshot. Clean up after the session ends.

## Related Boundaries

- Server repo rule: `../../CLAUDE.md` (root)
- Multi-app / port matrix + Capability rule: `../../docs/invariants/multi-app.md`
- Workspace-wide scenario matrix + directory convention: `../README.md`
- Promote checklist Main text: `../README.md`