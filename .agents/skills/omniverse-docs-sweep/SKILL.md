---
name: omniverse-docs-sweep
description: "Invoke during a working session to sync project docs (CLAUDE.md hierarchy + invariants/runbooks/pull-doc table) with work just completed. Hybrid input — working tree diff + committed session range/date + conversation. Auto-edits L1 (Pull-First routing together-missing docs) + L2 (tactical: counter·pointer·table item·line cap), reports L3 (permanent rule·new directory·new sub-CLAUDE.md·lessons-learned permanent rules) candidates as dry-run for user approval. Skip only when working tree, selected session range, and conversation input are all empty. Not for: manually editing generated docs (tool-catalog.md, phase-*-validation-report.md, references/testbed-snapshot/**), other skills' domains (extensions.json/extensions-catalog.md, docs/assets/isaac/assets/*.md/asset_inventory.md)."
metadata:
  version: "1.0.0"
---

# omniverse-docs-sweep: Project Documentation Sweep

Prefix your first line with 🧹 inline.

**Goal**: Automatically synchronize the current Pull-First documentation hierarchy (root `CLAUDE.md` required pull-doc table, `docs/CLAUDE.md`, sub-`CLAUDE.md`, `docs/invariants/`, `docs/runbooks/`, counters/pointers/table entries) by analyzing the working tree, committed session range/date, and conversation decisions of the previous task. Permanent rules and new document candidates are only reported in dry-run (silent automatic addition is prohibited). Treat the repo docs hierarchy as SoT and do not hard-code propagation rules in the skill.

## When to Use

User says "docs sweep", "update document", "synchronize docs", "clean up CLAUDE.md", etc. **Skip** for:
- Fix typos in a single doc (Direct Edit is cheaper)
- Kit Extension catalog update → `omniverse-kit-extension-catalog-sync`
- USD asset URL / inventory → `omniverse-asset-inventory-sync`
- When working tree, selected committed session range/date, and conversation input are all empty (automatic graceful shutdown — no error)

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | Auto-gen / immutable history / external sync manual editing prohibited — `docs/tool-catalog.md` (auto-gen via `scripts/generate_tool_catalog.py`), `docs/phase-*-validation-report.md` (immutable history), `docs/references/testbed-snapshot/**` (external sync via `scripts/sync_testbed_snapshot.py`), and generated local references under `docs/references/extensions*`, `docs/references/app-specific/`, `docs/references/official-assets/`. If `scripts/verify_mcp_sync.py` regenerates `docs/tool-catalog.md` as part of relevant MCP/tool work, include that generated change; otherwise suggest rerunning the relevant sync script instead of manual edits. |
| I2 | Do not invade other skill areas — `docs/references/extensions.json` / `extensions-catalog.md` (`omniverse-kit-extension-catalog-sync`), `docs/assets/isaac/assets/*.md` / `asset_inventory.md` (`omniverse-asset-inventory-sync`). |
| I3 | L3 (permanent rule·new directory·new sub-CLAUDE.md·`lessons-learned.md` permanent rule·routing self-modification·delete rather than stale) is dry-run only — no editing without user approval. Reported only as a sign-off candidate list. |
| I4 | Pre-stage verification gate — Step 9 (`git add`) is executed only when `pytest tests/unit/test_doc_integrity.py -q` + relevant unit/static checks + `scripts/verify_mcp_sync.py` + public hygiene gate in Step 8 are all green. If any one fails, no stage + working tree changes remain (auto-revert prohibited). |
| I5 | Pull-First docs hierarchy is SoT — prohibit hard-coded propagation rules in skills. Read root `CLAUDE.md` required pull-doc table, `docs/CLAUDE.md`, relevant invariants/runbooks, and local `CLAUDE.md` path walk every time. STOP only when those current routing docs cannot be interpreted. |
| I6 | DO-NOT-EDIT Protected area absolutely prohibited from editing — `<!-- DO-NOT-EDIT-START -->` … `<!-- DO-NOT-EDIT-END -->` All lines inside a block + inline `<!-- ⛔ DO-NOT-EDIT ... -->` Marked rows (automatically verified G1-G7 guards). |
| I7 | No history rewrite / force-push from this skill. If public hygiene reports already-public findings, route to `docs/runbooks/public-history-leak.md` as a dry-run/remediation candidate and require explicit user approval before any rewrite. |

Breaking any → STOP and report.

## Required Read upon entry

- `AGENTS.md` + root `CLAUDE.md` — Codex/Claude entry routing and required pull-doc table
- `docs/CLAUDE.md` — docs directory map and generated-doc rules
- `docs/invariants/public-repo-hygiene.md` — required before public-bound staging/push review
- `docs/runbooks/public-history-leak.md` — only when hygiene reports already-public findings or rewrite is considered
- Every applicable local `CLAUDE.md` on the path of files being edited

## Workflow

All Python invocations use `.venv/Scripts/python.exe` (Windows; bypasses `uv run` lock contention with multi-instance MCP servers).

### Step 1 — Collect input (Hybrid: git state + conversation)

**Input (a) — git state**:

```bash
git diff HEAD --name-status
git diff HEAD
git status --porcelain
git log --oneline <session-base>..HEAD
git diff --name-status <session-base>..HEAD
```

If `<session-base>` is unknown, use the user-provided base/date when available, otherwise estimate from the session start or use `--since` / `--date` history inspection. A clean working tree is not no-op evidence when this session already committed or rewrote history.

**Input (b) — Current conversation (since last commit)**: Scans the agent's session conversation history back to the boundary anchor *"since last commit"*. The extraction target is limited to *decisions/insights* that occurred during the session (all utterances If there is no conversation within the boundary, only (a) is used.

**Input (c) — Optional slash argument**: User can add and highlight (b) in free text when called (e.g. `/omniverse-docs-sweep "Phase H completed + stdin DEVNULL invariant made explicit"`).

- (a) working tree + selected committed range/date + (b) are all empty → normal shutdown ("nothing to sweep" sign-off variant).
- Not empty → list of changed files + line-by-line diff + (b) preservation of extraction results, continued.

### Step 2 — L1 Mapping (Pull-First Docs Routing)

Read root `CLAUDE.md` "Required pull-doc before work" table, `docs/CLAUDE.md`, and every applicable local `CLAUDE.md` for the changed paths. Match Step 1 files and conversation decisions to the current Pull-First routing docs to extract *candidate docs that need to be updated together*. **STOP** (I5 — skill stale signal) only if the current routing docs cannot be interpreted. Never hard-code propagation rules inside a skill.

Output: `{changed file: [files to update together]}` mapping.

### Step 3 — Derive L2 tactical candidates

- **(3a) Counter**:
  - Number of tools: Add up `grep -c '@mcp.tool()' src/omniverse_kit_mcp/tools/*.py` → Check the values ​​of root `CLAUDE.md` / `README.md`
  - test number: `pytest --collect-only -q` last line
  - Number of lines: `wc -l` in each CLAUDE.md / invariants / runbooks
- **(3b) Pointer**: Extract cross-refs (`docs/...`, `../...`) of all sub-CLAUDE.md / invariants / runbooks → Verify file existence. Among broken pointers, only *simple rename / path drift* are candidates (along with semantic transformation is L3).
- **(3c) Missing table entry**: Verify whether the new file in Step 1 is missing in the sub-CLAUDE.md "File Structure" table / root CLAUDE.md "Document Map" table / pull-doc table.
- **(3d) Result-shape path clarity**: When docs mention diagnostics, fallback, scenario, or public-report fields, prefer exact JSON paths (`data.diagnostics.fallback_tool_order`, `data.checks.probe.evidence...`, `diagnostic_next_actions[]`) and only keep claims backed by tests, generated catalog output, or explicit live evidence from the session.

Record each candidate as `{file, before, after, reason}`.

### Step 4 — Identify L3 candidates

Comprehensive conversation extraction results + git commit msg + git status signals from Step 1 (b) (not applied, candidate only):
- Permanence intent keywords (extracted from Step 1 (b) + same search in commit msg): “Always from now on”, “Never
- New directory untracked (`git status --porcelain | grep '^?? .*/$'`)
- New sub-CLAUDE.md untracked
- Attempt to add permanent rule to `lessons-learned.md` detected (meta rule violation — incident log only)
- Detection of possible violation of root CLAUDE.md meta rule `deletions are limited to stale content`
- root `CLAUDE.md` required pull-doc table / `docs/CLAUDE.md` map self-modifying candidate

Preserve candidates in the “L3 candidates” section of Sign-off.

### Step 5 — Self-review A (automatic gate)

As a result of applying *in-memory* each L1+L2 candidate:
- **Linecap**: root `CLAUDE.md` ≤150 / sub-CLAUDE.md ≤150 / `docs/invariants/*.md` ≤200 / `docs/runbooks/*.md` ≤300 — Discard candidates if any one is exceeded
- **Routing Residual**: Are all docs requested by Pull-First L1 mapping included in the candidates?
- **Broken pointer**: Checks whether there are *new* broken cross-refs after applying the candidate.
- **DO-NOT-EDIT invasion**: Candidate's edit line range is `<!-- DO-NOT-EDIT-START -->` … Does it overlap with a `<!-- DO-NOT-EDIT-END -->` marker row inside a block or inline with `<!-- ⛔ DO-NOT-EDIT ... -->` — discard if overlap (I6)

Record discarded candidates with reasons in the Sign-off “Discarded — Self-review A” section.

### Step 6 — Self-review B (LLM)Step 5 Re-read the passing candidates:
- **Duplicate**: Is there already an item with the same meaning?
- **Meta Rule Violation**:
  - Add permanent rule to `lessons-learned.md`? (root CLAUDE.md meta — incident log only)
  - Add cross-cutting rule to sub-CLAUDE.md? (sub is for directory-specific rules only)
  - Deletion that is not stale-specific?
- **Tone Match**: Is this the same markdown pattern as the existing line? Korean/English tone matching?

Record discarded candidates with reasons in the Sign-off “Discarded — Self-review B” section.

### Step 7 — Apply L1+L2

Actual editing of each passing candidate with `Edit` tool. If there are multiple candidates in one file, the changes are combined and processed into 1 Edit call, if possible. **Does not apply to L3 candidates** — Sign-off reporting only. Do not hand-edit generated docs; when a tool docstring or tool metadata change makes `scripts/verify_mcp_sync.py` regenerate `docs/tool-catalog.md`, include the generated diff as sync evidence instead.

### Step 8 — Post-verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_doc_integrity.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_doc_references.py -q  # when MCP usage guide, artifact anchors, scenario routing, or documented command lines changed
.venv/Scripts/python.exe -m pytest tests/unit/ -q
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base <session-base> --head HEAD --redact-samples
git diff --check
```

Use the default guard for current-tree + pending-history review, and use the range/date hygiene command when the session has committed work, pushed work, or a user-provided base/date. `--skip-history` is allowed only as an extra current-tree-only diagnostic, never as the public push gate. All green and `normal_push_allowed=true` → Proceed to Step 9. Even one fails or hygiene says `normal_push_allowed=false` → Step 9 skip + Sign-off "Verification fail / public hygiene action required" variant. **Changes remain in the working tree — no auto-revert** (risk of user in-progress task conflict).

### Step 9 — Auto-stage + Sign-off

```bash
git add <changed files>
```

Never call `git commit` / `git push` from this skill (Auto-stage only — parent workflow/user commits as a semantic unit). Stage only when Step 8 is green and public hygiene allows a normal push. And the Sign-off output below.

## Stop Conditions

STOP and report on any:
- Step 1: working tree + selected committed range/date + conversation input are all empty → Normal shutdown ("nothing to sweep") — not an error
- Step 2: Pull-First routing docs cannot be interpreted → STOP (root/docs CLAUDE schema modification suspected, skill code modification may be necessary)
- Step 5: Discard all L1+L2 candidates as line cap/DO-NOT-EDIT violation/routing remainder → STOP + report (human judgment required — transfer/split/compress)
- Step 6: All candidates are discarded for violating meta rules → STOP + Report
- Step 8: Post-verification fail or public hygiene `normal_push_allowed=false` → Step 9 skip + report `next_action`
- Public hygiene reports already-public findings → STOP; do not rewrite/force-push; prepare dry-run remediation plan from `docs/runbooks/public-history-leak.md`
- I1–I7 violation → STOP

## Never Do

- ❌ Manual-edit auto-generated (`docs/tool-catalog.md`) / immutable history (`docs/phase-*-validation-report.md`) / edit testbed-snapshot or generated reference caches
- ❌ Edit other skill areas (`docs/references/extensions.json` / `extensions-catalog.md`, `docs/assets/isaac/assets/*.md` / `asset_inventory.md`)
- ❌ L3 candidate silent automatic application — always with dry-run report
- ❌ If Step 8 fails, `git add` (does not stage)
- ❌ Step 8 auto-revert changes after fail (risk of damage to user’s in-progress work)
- ❌ `git commit` / `git push` (Auto-stage only)
- ❌ History rewrite / force-push (route to public-history runbook and require explicit user approval)
- ❌ root `CLAUDE.md` pull-doc table or `docs/CLAUDE.md` map self-correction (routing changes are L3)
- ❌ Add permanent rule `lessons-learned.md` (incident log only)
- ❌ Delete, not limited to stale
- ❌ DO-NOT-EDIT Inside protected block / inline `⛔ DO-NOT-EDIT` Edit marker row (G1-G7 guards)

## Sign-off

### Standard (happy path)

```
🧹 omniverse-docs-sweep complete

L1+L2 applied (auto-edit, staged):
- <file>: <change summary>
-...L3 candidates (dry-run, not applied — processed in next call upon user approval):
- [1] <Candidate Type>: <Target Location>
       Rationale: <commit msg / conversation keyword / git status signal>
-...

Discarded (discard simulation — debugging transparency):
- <file>: <Reason for discard — line cap / routing residual / DO-NOT-EDIT infringement / meta rule / duplication> [Self-review A|B]
-...

Verification (Step 8):
- pytest tests/unit/test_doc_integrity.py: <N> passed
- pytest tests/unit/: <N> passed
- scripts/verify_mcp_sync.py: OK
- review_public_hygiene.py: push_decision=<status>, normal_push_allowed=<true|false>
- git diff --check: OK
- Cap: root <X>/150, sub max <X>/150, invariants max <X>/200, runbooks max <X>/300

Staged (commit/push pending — only when normal_push_allowed=true):
- M <file>
-...

Next: parent workflow/user may commit as a semantic unit. L3 candidate processing is instructed as “Apply L3 1 time” / “Ignore L3”.
```

### Variant — No-op (Step 1 stop)

```
🧹 omniverse-docs-sweep complete — nothing to sweep
working tree/session range/conversation: empty
```

### Variant — Post-verification fail (Step 8 stop)

```
🧹 omniverse-docs-sweep complete (post-verification fail — does not stage)

L1+L2 applied:
- ... (Changes remain in the working tree — no auto-revert)

Verification fail / public hygiene action required:
- <item that failed among pytest / verify_mcp_sync / review_public_hygiene / git diff --check> (<actual measurement vs cap / drift content / push_decision next_action>)

Action required: <Summary of causes> — Called again after user processing (migration / compression / division / drift correction).
```

## Required References

- `AGENTS.md` + root `CLAUDE.md` — Pull-First routing, required pull-doc table, meta rules (line hardcap, migration/delete rules, lessons-learned incident log), and DO-NOT-EDIT protection G1-G7
- `docs/CLAUDE.md` — Role of each file in docs directory + update rules
- `docs/invariants/public-repo-hygiene.md` — public-safe current-tree/session-history gate
- `docs/runbooks/public-history-leak.md` — only when already-public findings appear
- `tests/unit/test_doc_integrity.py` — line cap / cross-ref / G1-G7 guard
- `scripts/verify_mcp_sync.py` — MCP catalog drift guard
- `.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md` — isomorphic patterns reference
- `.claude/skills/omniverse-asset-inventory-sync/SKILL.md` — isomorphic patterns reference

Answer in the same language as the question.
