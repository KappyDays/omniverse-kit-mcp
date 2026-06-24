---
name: omniverse-mcp-tool-upgrade
description: Invoke after or during a Claude Code or Codex session that performed omniverse work, to retrospectively analyze that session's work (conversation — MCP tools called, workarounds, repeated friction — plus git/session range), identify where MCP tools were missing or insufficient, then add new or upgrade existing MCP tools (8-place edit for new tools), verify static/stdio/live layers honestly, apply public hygiene gates before public-bound handoff, and sync tool-only docs. Autonomous with 3 distributed self-reviews (necessity, adversarial-correctness, integration). Input is the session's actual performed work, not an external task spec. Not for executing omniverse tasks, broad CLAUDE.md sync (use omniverse-docs-sweep), Kit extension catalog sync (omniverse-kit-extension-catalog-sync), or asset URL/inventory (omniverse-asset-inventory-sync).
user-invocable: true
disable-model-invocation: true
metadata:
  version: "1.0.0"
---

# omniverse-mcp-tool-upgrade: Session-Retrospective MCP Surface Upgrade

Prefix your first line with 🔧 inline.

**Goal**: **Detailed analysis of the omniverse tasks (implementation content, called MCP tool, bypass/manual steps, repetitive friction) performed in this Claude Code / Codex session**, identify gaps in the MCP surface, and — if **new tool addition or existing tool upgrade** is required — autonomously complete the invariant-defined implementation set (currently 8 places for new tools) + registration/drift verification + tool-specific docs sync. **The input is the actual task of the session (conversation + working tree + committed session range), not a task specification given externally**. The SoT of the procedure is an existing invariant document, and this skill is only *pointed to* (no hard-code).

## When to Use

**Session work review is triggered.** User says "Please analyze the omniverse work of this session and upgrade the MCP", "Make what was inconvenient / bypassed while working just now into an MCP tool", "Reinforce MCP functions that were lacking in this session", "Existing tool needs to be upgraded", etc. **Skip** for:
- Re-execution/visual verification of omniverse tasks being analyzed (this skill only extends to the MCP surface)
- Work already possible with existing tools (early-exit when discovered in Phase 1)
- Extensive CLAUDE.md layer synchronization → `omniverse-docs-sweep`
- Kit Extension catalog update → `omniverse-kit-extension-catalog-sync`
- USD asset URL / inventory → `omniverse-asset-inventory-sync`

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | No hard-coding of procedures — the SoT of the implementation locations/research/module procedures must be documented in each invariant. skill just points |
| I2 | Tool addition is prohibited during reconstruction (`docs/invariants/mcp-tool-add.md` §Prohibited during reconstruction) — MCP surface is immutable |
| I3 | If you do not pass self-review ②/③, STOP + report. green camouflage prohibited |
| I4 | import-cache + ext-reload True — same-host live REST behavior cannot be proven from the stale MCP host. In-session verification separates static registration/drift, fresh workspace-local MCP stdio surface/result-shape smoke, and behavioral live REST only after MCP host restart + ext reload (`docs/invariants/ext-reload.md`) |
| I5 | No “I wish there was” gap implementation (Review ①) — Only directly experienced/expected minute-by-minute pain |
| I6 | In case of implementation/verification failure, the drift-fail tree is prevented from being neglected by partial modification in the invariant-defined locations — the gap is left-clean or reverted. Prohibit half-state exit |

Breaking any → STOP and report.

## Required Read upon entry (autonomous mode — do not autoload sub-CLAUDE.md)

- `AGENTS.md` + root `CLAUDE.md` — Codex/Claude entry routing; do not rely on auto-loaded nested memory
- `docs/references/CLAUDE.md` — research flow steps 0 to 6 (duplicate check → catalog → hint → API → example → source → document)
- `docs/invariants/mcp-tool-add.md` — Simultaneously modify the invariant-defined new-tool locations (currently 8) + verify_mcp_sync + drift
- `docs/invariants/module-add.md` — new module/scenario action
- `docs/invariants/ext-reload.md` — reload after modifying extension `.py` (assuming verification of P4 behavior)
- `docs/tool-diagnostic-map.md` — Diagnostic reverse index
- (**When public-bound code/docs/history will be committed, pushed, or summarized**) `docs/invariants/public-repo-hygiene.md`
- (**Only when hygiene reports already-public findings or history rewrite is considered**) `docs/runbooks/public-history-leak.md`
- (**When implementing tools that synchronously edit/traverse/render-query the live stage — including read/traverse**) `docs/invariants/usd-load.md` + `kkr-extensions/docs/usd-load-deadlock-recipe.md` — deadlock-safe baseline: Synchronous MDL stage edit/traverse/render-query causes freeze (deadlock). Follow the deadlock-safe pattern in that document.

## Workflow

All Python invocations use `.venv/Scripts/python.exe`.

### Phase 1 — Session work analysis + research (once per session)

1. **Session task analysis (hybrid input — same model as `omniverse-docs-sweep`)**:
   - (a) **conversation (primary)**: Omniverse tasks performed this session — MCP tools called, **circumvention/manual steps** used, **repeated friction**, “I wish I had this tool” moments, points where the limitations of existing tools were encountered. The retry/bypass/manual steps are mainly shown here.
   - (b) **git (corroboration)**: omniverse-related code/extension/scenario changes. **uncommitted If you only look at `git diff HEAD`, you will miss it** — Since this project frequently commits during sessions, `git log --oneline <session-base>..HEAD` **includes work committed during sessions** (estimated when the conversation starts when the base is unknown). If conversation is poor/compacted, git takes the lead.
→ Extract each friction point as a **gap candidate** (what existing tools were lacking / did not exist at all). **If you can't find the work/friction, don't make up a gap and STOP (lack of input — Stop Conditions).**
2. Search `docs/tool-catalog.md` for each gap candidate (research step 0). **If covered sufficiently with the existing tool**, there is no gap (friction may have been a simple usage issue → removed).
3. Remaining gap **Tentative classification** (confirmed after step 4 research):
   - `(a)` **New MCP tool** (Kit command/API wrap) → `docs/invariants/mcp-tool-add.md` invariant-defined locations
   - `(b)` **Upgrade existing tool** (extend signature, add parameters, enhance returns, or expose missing result-shape/diagnostic/orchestration fields) → Modify service/client/module/tool functions of the tool (e.g., strengthen `viewport_capture` warmup/stats, expose `scenario_*` retry/failure/live-checklist/public-report fields). Existing tools are not "covered sufficiently" when their return shape blocks planning, live checklist, retry/failure summary, or public-safe reporting. When frozenset is unchanged, catalog regen only; when changed, the new-tool location set applies.
   - `(c)` new module/scenario action → `docs/invariants/module-add.md`
   - `(d)` MCP resource → `src/omniverse_kit_mcp/mcp/resources.py` + `tests/unit/test_resources_paths.py`
   - `(e)` outside MCP area = validation_api cannot be reached in-process (e.g. host app `.kit` needs to be rebuilt) → Blocker reporting only. **"Difficult" ≠ "Out of scope"** (OS-input types that can be wrapped with carb.input are (a)). **(e) Confirmation only after step 4 research (steps 1 to 4) — Confirmation of non-discovery of in-process path. Unresearched (e) classification prohibited (prevention of false blockers).**
4. Execute research flow (`docs/references/CLAUDE.md` step 1~6) for each gap → Confirm ext/API to be wrapped. When in-process path is discovered through research, provisional (e) → (a)/(b) reclassification; (e) Confirmed only when route absence is confirmed.
5. Output: **Prioritized gap list** (based on pain experienced in minutes + bypass cost during this session).> **🔍 Self-review ① — Necessity/Reuse** (*Before* writing code. Hat: User/Waste Prevention)
> - Was this gap an actual minute-by-minute friction in this session, or was it simply a usage issue/"nice to have" (I5)?
> - Was it possible to bypass it with the existing tool combination (`kit_command_execute` / `extension_search` / `window_menu_trigger`)?
> - Is there already an equivalent tool for `tool-catalog.md` (recheck step 2)?
> Removal of gaps that did not pass. Record pass/fail from each perspective in TodoWrite.

### Phase 2~5 — Repeat for each gap (in order of priority)

- **P2 design**: name / signature / params / return `@dataclass(slots=True, frozen=True)` / invariant location mapping (or module-add·resource path) / mock operation specification. For existing-tool result-shape upgrades, explicitly record: current response contract, additive/backward-compatible fields, caller/report consumers, mock fidelity, golden/unit tests, docs/catalog impact, and whether public-safe reporting needs `redact_local_paths`.
- **P3 Implementation**: Inline execution of `docs/invariants/mcp-tool-add.md` in all required places (classification (c) side `module-add.md`, (d) side resource procedure). Type boundary: Internal dataclass, **MCP server Pydantic prohibited**. App-specific ext surface reflects `ISAAC_MCP_APP_PROFILE` dimension (research step1 `apps`). **The location set includes EXPECTED frozenset + tool metadata/profile registry + tool group caveat — Must be completed before P4 because the drift check of P4-(i) verify_mcp_sync requires frozenset and metadata matching.**

  > **🔍 Self-review ② — Adversarial correctness** (immediately after implementation, *before* verification. Hat: attacker)
  > - Is the selected Kit API real + signature? — Did you confirm it with the actual source (`standalone_examples/` · ext source) or is it just a guess?
  > -What about side-effects? (Example: Doesn't `CreateConveyorBelt({})` create a default prim or pollute the stage?)
  > - R1 false-positive guard: doesn't mock always return success? Mock fidelity cannot be confirmed live within the session → determined based on the **documented contract** of the extension REST endpoint (live confirmation is P4-(ii)).
  > - deadlock-safe: Doesn't the new behavior synchronously edit/traverse/render-query the live (MDL) stage? Did you follow the deadlock-safe baseline of `docs/invariants/usd-load.md` (sync write → freeze landmine)?
  > If you do not pass, STOP (I3). TodoWrite pass/fail.

- **P4 Verification — Three Layer Separation**:
  - **(i) static registration/drift (required gate)**: `.venv/Scripts/python.exe scripts/verify_mcp_sync.py` — Reimport code to fresh subprocess → catalog regen + drift pytest. Green can be checked regardless of import-cache.
  - **(ii) workspace-local MCP stdio smoke (non-mutating surface/result-shape checks)**: use `workspaces/<app>/instance-N/.mcp.json` for `list_tools`, `mcp_runtime_info`, and non-mutating calls such as `scenario_plan` / dry-run result-shape checks. Repo-root standalone/mock checks are useful but do not satisfy this layer.
  - **(iii) live stage/REST verification (behavioral)**: worker thread only, scratch/test stage only, after MCP host restart + extension reload. Stage-mutating robot/sensor/viewport behavior must not be claimed from layer (i) or standalone mock alone.
- **P4b Public Push Gate (when public-bound)**: run `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py` (or `--base <base> --head HEAD`, `--today`, `--date`, plus `--redact-samples` for copied output). Read `push-decision` / `push_decision.normal_push_allowed`; if false, stop normal push/handoff and report `status`, `requires_user_approval`, and `next_action`.
- **P5 docs (tool only)**: tool-catalog regen is included in P4-(i) `verify_mcp_sync` (group caveat·frozenset·metadata has already been completed in P3). P5 unique task = Check current Pull-First docs routing (`AGENTS.md`, root `CLAUDE.md`, relevant local `CLAUDE.md`, tool/group caveat) for additional updates. Extensive CLAUDE.md layer synchronization causes `omniverse-docs-sweep` handoff. Public artifacts should prefer `scenario_last_report(report_format="markdown", redact_local_paths=true)` and `review_public_hygiene.py --redact-samples`; hashes/counts/ports/redacted placeholders are allowed, local paths, worker/thread IDs, PIDs, and generated cache paths are not.

### end

Once P2~5 iterations of all gaps are completed, once before declaring completion:

> **🔍 Self-review ③ — Consistency/Completeness** (*Before* declaration of completion. Hat: Maintainer)
> - `mcp-tool-add.md` All required places? `verify_mcp_sync` green + drift pass? `git status` created file unchanged?
> - Is there any type boundary violation (MCP server Pydantic is prohibited)? Is group naming consistent?
> - Restart/reload honesty: no spoofing of "live called". “Available after registration/drift green + (host restart + ext reload)”. Didn't you hide that standalone is via mock (I4)?
> - If public-bound: did `review_public_hygiene.py` report `normal_push_allowed=true`, or was the stop action reported honestly?
> - clean tree: Are there any remaining parts of the failed gap (I6)?
> If you do not pass, STOP (I3). TodoWrite pass/fail.

## Stop Conditions

STOP and report on any:
- Phase 1: conversation · git No omniverse work/friction to analyze anywhere → **STOP "Not enough session work to analyze"** (work may be in another session or uncommitted/unrecorded/compact lost). **Distinguished from “no upgrade required” (no gap after analysis)** — Prohibition of fabricating gap without basis (I5). Not an error.
- Phase 1: All gap candidates are covered by existing tools (including simple usage issues) → **early-exit ("No upgrade required")** — Not an error.
- Phase 1: All gaps are outside the (e) MCP area → Report structural blocker list — not an error.
- Self-review ②/③ Not passed → STOP + report (I3).
- P4 (i) verify_mcp_sync / drift fail → corresponding gap leave-clean or revert (I6), STOP + report.
- Public hygiene reports `normal_push_allowed=false` → STOP normal push/handoff; follow `next_action`. If findings are already public, do not rewrite/force-push without explicit user approval and a `docs/runbooks/public-history-leak.md` plan.
- Violation of I1–I6 → STOP.

## Never Do

- ❌ Hard-code procedures into skills (SoT in implementation-location/research/module invariants)
- ❌ Re-execution/visual verification of omniverse tasks to be analyzed (out of scope)
- ❌ Implementation of the “I wish there was” gap (Review ①·I5)
- ❌ Fabrication of gap without basis in input (conversation·git) — If input is insufficient, stop implementing instead of implementing
- ❌ Pydantic (type boundary) in MCP server code
- ❌ Abandon drift-fail tree by modifying only part of the invariant-defined location set (I6)
- ❌ Passing standalone (mock) is reported as verification of actual endpoint behavior (I4)
- ❌ Extensive CLAUDE.md synchronization (→ docs-sweep), catalog/asset area invasion
- ❌ Add tool during reconstruction (I2)
- ❌ Re-surface public-inappropriate evidence in sign-off/artifacts: redact local paths, worker/thread IDs, PIDs, and generated cache/reference paths
- ❌ Rewrite history or force-push for public findings without explicit user approval and runbook preparation

## Sign-off

### Standard (happy path)

```
🔧 omniverse-mcp-tool-upgrade complete

Session work summary: <Omniverse work performed in this session>
Gaps (derived from session friction, in priority order):
- [new] <tool> (a) — <ext/API to wrap> ← friction: <what was missing>
- [upgrade] <existing tool> (b) — <added coverage> ← friction: <previous limitation>
- [reuse] <existing tool> — <friction was only usage guidance>
- [blocker(e)] <capability> — <unreachable reason>

Implementation result (by gap):
- <tool>: required touch points updated / self-review ①✓ ②✓ ③✓

validation:
- verify_mcp_sync.py (registration/drift): OK
- tool-catalog.md regen: synced
- workspace-local MCP stdio smoke: <OK/not run + reason>
- public hygiene: <command/range> -> push_decision=<status>, normal_push_allowed=<true|false>
- ⚠️ behavior (real REST) validation: MCP host restart + ext reload is required before this is possible (not run in-session)

docs:
- Pull-First docs routing / group caveat / EXPECTED frozenset / tool metadata updated

Next:
1. MCP host (Claude Code / Codex CLI) restart → register the new tool live
2. extension reload (`docs/invariants/ext-reload.md`) → new REST endpoint live
3. then use the new tool for follow-up work / broad docs via /omniverse-docs-sweep
```

### Variant — Insufficient input (unable to analyze)

```
🔧 omniverse-mcp-tool-upgrade — not enough session work to analyze
No Omniverse work/friction was found in this session conversation or git state.
- possible causes: work was in another session, uncommitted/unrecorded, or lost during context compaction
- action: rerun from the session that did the work, or specify `git log <base>..HEAD` as the target commit range
```

### Variant — Early-exit (no upgrade required)

```
🔧 omniverse-mcp-tool-upgrade — upgrade not required
all capabilities are covered by existing tools:
- <capability> → <existing tool>
the original task can proceed directly.
```

### Variant — Blocker (all outside (e) area)

```
🔧 omniverse-mcp-tool-upgrade — structural blocker
MCP in-process cannot be reached in-process:
- <capability> — <reason (for example, host app .kit rebuild required)>
recommendation: <alternative (host app build change / separate approach)>
```

### Variant — Verification fail (P4 (i) stop)

```
🔧 omniverse-mcp-tool-upgrade (validation fail — revert or leave clean for that gap)
- <tool>: verify_mcp_sync / drift fail — <details>
- action: <revert or partial completion> (I6 — do not leave a drift-failing tree)
Action required: <cause> fix it, then rerun.
```

## References (background only — do not read inline)

- `.claude/skills/omniverse-docs-sweep/SKILL.md`, `.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md` — isomorphic skill structure patterns reference

(For SoT procedure documents, see “Required Reading Upon Entry” above.)

Answer in the same language as the question.
