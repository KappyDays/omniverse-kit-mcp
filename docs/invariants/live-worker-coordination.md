<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: parent/coordinator thread + live MCP worker thread coordination -->

# Live Worker Coordination — Invariants

Parent/worker operation is a common rule for projects. Root repo thread is parent /
Coordinator, `workspaces/<app>/instance-N` thread is a live MCP worker
Separate.

⚠️ Verification warning: this parent/worker workflow is a common project rule,
but live usage has only been verified with Codex threads so far. Non-Codex
hosts must follow the same contract and report adapter gaps.

This structure is not a pure token efficiency optimization. The purpose is to separate the live MCP environment,
Separation of authority/modification responsibility, dirty diff stability, and final judgment separation. Token cost is
Shorten it to Quiet Parent Contract.

## When to apply

- If actual Isaac Sim / USD Composer MCP tool verification is required, use worker.
- If the user asks to launch/open/start an Omniverse app, this is live MCP work:
  create or continue the matching `workspaces/<app>/instance-N` Codex thread and call
  `kit_app_start` there. Do not start the app from the repo-root parent thread.
- For Codex live MCP work, continue the active worker thread only when it is
  clearly the same delegated task, app, and instance. Start a fresh workspace
  thread for new tasks, ambiguous prior context, recovery boundaries, or
  stale-state boundaries.
- If only code/document/static test/diff cleanup is needed, parent handles it.
- A new worktree is not created unless the user specifies it.

## Root-thread launch prohibition

The parent thread must not use `scripts/run_process_module_standalone.py start` as
the normal answer to "start Isaac/Composer". That bypasses the workspace-local MCP
entry and can miss host-specific worker context. Use the workspace worker MCP
instead; reserve standalone process scripts for documented import-cache bypass,
recovery, or explicit low-level diagnosis. Composer paths are configured with
`USD_COMPOSER_KIT_EXE` / `USD_COMPOSER_KIT_FILE`; Isaac legacy path overrides
must not drive the Composer profile.

## Parent Responsibilities

- Owns work scope, dirty diff, static verification, and final decision.
- Only live MCP verification instructions and acceptance criteria are delegated to workers.
- If the worker discovers that modification is necessary, the parent modifies it and requests re-verification.
- Code / documents / static work that does not require MCP is completed in the parent.
- Only the milestone/result is retrieved without repeating relay of the entire worker log.
- User-facing reporting follows the Quiet Parent Contract.

## Worker Responsibilities

- Starting from `workspaces/<app>/instance-N`, enter the workspace-local MCP entry.
  Use it.
- Use first-class MCP tools first.
- The live-validation worker does not modify files by default.
- Live validation results and artifacts without continuously reporting long logs/intermediate states
  Focus on collecting.
- After changing any user-visible Stage state, finish with viewport visual
  acceptance per `visual-validation.md`: frame, capture with stats, inspect the
  PNG, and report the artifact path. Do not claim setup completion from prim/API
  assertions alone.
- Do not call `kit_app_restart` with routine setup. The basic order is
  attach/start/reload-first and the conditions for restart are:
  Follows `process-lifecycle.md`.
- After failure/abnormal operation, check and summarize Console WARN/ERROR.

## Worker startup sequence

1. Check MCP entry exposure: Codex is `codex mcp list`, other hosts are equivalent
   MCP listing.
2. Attach to an existing kit with `kit_app_start` or start if you do not have one.
3. Check responsiveness with `simulation_get_status` or `/health`.
4. If necessary, `stage_new`, `extension_clear_logs`, install, play, status,
   Perform bbox and viewport capture.
5. `kit_app_restart` has crash/hang, validation_api self-change,
   Change `extension.toml [dependencies]`, `extension_reload` failed, user
   Used only when requesting a fresh process.

## Quiet Parent Contract

Milestones that the Parent can report to the user:

- Worker creation and target workspace
- Kit attach/start result
- Live verification terminal results
- Console WARN/ERROR Summary
- artifacts such as bbox / viewport capture
- Blocker or parent modification required
- final summary

Parent can read and steer workers internally, but internal monitoring below
You should not relay state to the user:

-`read_thread` polling
- "Still waiting", "Confirming one more time", "No tool call yet",
  A heartbeat like “wait a little longer”
- Parent internal polling status, such as tool read failure / output size adjustment
- Repeated confirmation that there is no change in terminal status

If there is no response for a long time, a one-line summary every 3-5 minutes is allowed only when there is no terminal change.

## Related Boundaries

- Kit process lifecycle: `process-lifecycle.md`
- Extension reload: `ext-reload.md`
- Workspace entrypoints: `../../workspaces/README.md`
- Codex adapter notes: `../../AGENTS.md`
