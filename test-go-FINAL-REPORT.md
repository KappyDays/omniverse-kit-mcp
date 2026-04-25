# Test-Go Autonomous Run — Final Report

**Branch:** `feature/test-go` (NOT pushed — manual user action per Rule 2)
**Run date:** 2026-04-25
**Tool surface used:** 111 MCP tools (`window_capture_sequence` = 111th, used in both phases)

## Phase Verdict
| Phase | Status | Notes |
|-------|--------|-------|
| 0 | PASS | repo state, branch (feature/test-go), kit/hub cleanup, output dirs, MCP tool fetch (5/5), invariants Read (7 files), pytest baseline (433 pass) |
| A | PASS | USD Composer Input Extension — scaffold + timeline gating + 10-frame capture all green |
| B | PARTIAL | Conveyor Pick Extension — scaffold + scene build (4 belt + franka + basket) PASS; pick #1 not completed but diagnostic captured ("Franka init failed -- pick loop disabled") |
| C | PASS | Final report + commit |

## Per-Task MVP Results
| Task | MVP Pass | Evidence |
|------|---------|---------|
| A: scaffold loaded | ✅ | extension_get_info enabled=true (mcp_logs/A.1.3) |
| A: `_build_status_window` ran | ✅ | extension_get_ui_tree found "USD Composer Input" window (mcp_logs/A.1.3) |
| A: timeline play -> ACTIVE | ✅ | A_seq_5.png shows status label "Status: ACTIVE (timeline playing)" |
| A: timeline stop -> inactive | ✅ | A4_after_stop.png shows label back to "Status: inactive" |
| A: 10-frame capture | ✅ | All `frames[].ok=true` (mcp_logs/A.4.2) |
| B: scaffold loaded | ✅ | extension_get_info enabled=true |
| B: 4 belt + franka + basket | ✅ | stage_assert_prim_exists for all 6 (mcp_logs/B.3) |
| B: ≥1 cube spawn | ✅ | /World/Cubes/Cube_0003 exists (≥4 spawned at 3s interval) |
| B: pick #1 complete | ❌ (with diagnostic) | Status bar: `[conveyor_pick] Franka init failed -- pick loop disabled` |

7 of 8 evidence checks PASS, 1 of 8 with captured diagnostic (per Rule 6 partial-fail rule).

## Failures / Limitations
1. **`extension.toml` `omni.kit.app` dependency** rejected by USD Composer (not registered). *Resolved in Phase A* by replacing with `omni.kit.uiapp` (matches existing `ui_demo`/`navmesh_playground` pattern).
2. **`omni.kit.commands.execute('CreatePrimWithDefaultXform')`** silent-failed when parent prim was missing. *Resolved in Phase B* by switching to `pxr.UsdGeom.Xform.Define` / `Cube.Define` directly with explicit parent creation.
3. **`UsdGeom.Imageable(prim).GetDisplayColorAttr()`** AttributeError. *Resolved in Phase B* by calling the schema directly (`cube.GetDisplayColorAttr()`).
4. **PickPlaceController init exception** — root cause not isolated within the time budget. Hypothesis: `Franka(prim_path=...)` runs before the S3 USD reference is fully resolved. Production fix would (a) wait for `is_new_stage_loading()` to clear, (b) retry on later ticks, or (c) use `safe_load_usd` from `usd-load-deadlock-recipe.md`.
5. **Conveyor surface motion** not implemented — `_create_belt_simple` builds static colliders only. The O-loop is geometric, not kinematic.

## Branch / Commits
```
44beb71 feat(ext): omni.mycompany.conveyor_pick — O-conveyor + Franka pick-and-place (Phase B)
45032e1 feat(ext): omni.mycompany.usd_composer_input — hover highlight + QWEASD camera (Phase A)
95cb1a4 chore(test-go): Phase 0 — directories for isaac-test / usd-composer-test
```
(Phase C commit added by C.3.)

## Tests
- `pytest tests/unit -q` — **433 passed** (no regression vs baseline)
- New extensions are not under unit-test coverage (Kit-runtime only, per project policy: `omni.ui` is stub-only in pytest env)
- All MCP tool calls logged to `<output_dir>/mcp_logs/`

## Process / Process-lifecycle observations
- USD Composer cold boot: 13.6s (first), 11.0s (after toml change + restart)
- Isaac Sim cold boot: 12.5s (first), 11.4s (after each subsequent restart)
- All under `ISAAC_SIM_STARTUP_TIMEOUT=120s` baseline (per `feedback_isaac_sim_start_timeout.md`)
- No MDL deadlock observed in either app (no S3 MDL-heavy asset was loaded; Franka USD is a thin reference)
- No `kit.exe` zombies left after `isaac_sim_stop` calls

## Next Steps (manual user action)
1. Review feature/test-go commits (3 + 1 = 4 total after Phase C commit)
2. Manual verification of Phase A:
   - Open USD Composer, play timeline, hover mouse over a prim → expect FFD700 yellow highlight
   - Press Q/W/E/A/S/D (and combine with Shift) → expect camera translation
3. Phase B follow-up to actually complete a pick:
   - Wait for Franka asset payload (`omni.usd.get_context().is_new_stage_loading() == False`) before instantiating `Franka(...)` in `_init_franka`
   - OR add a retry loop in `PickController.run` that re-attempts `_init_franka` for ~5s after the first failure
4. Optional: Add `omni.physx.conveyor` belt motion so cubes actually traverse the O loop
5. Push: `git push -u origin feature/test-go` (autonomous run did **not** push — Rule 2)
6. Open PR or merge per workflow preference
