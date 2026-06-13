---
name: omniverse-docs-sweep
description: "Invoke during a working session to sync project docs (CLAUDE.md hierarchy + invariants/runbooks/pull-doc table) with the work just completed. Hybrid input — decisions in git diff HEAD + conversation. Auto-edits L1 (change propagation matrix together - missing modifications) + L2 (tactical: counter·pointer·table item·line cap), reports L3 (permanent rule·new directory·new sub-CLAUDE.md·lessons-learned permanent rules) candidates as dry-run for user approval. Skip if no diff. Not for: auto-generated docs (tool-catalog.md, phase-*-validation-report.md, references/testbed-snapshot/**), other skills' domains (extensions.json/extensions-catalog.md, docs/assets/isaac/assets/*.md/asset_inventory.md)."
user-invocable: true
disable-model-invocation: true
metadata:
  version: "1.0.0"
---

# omniverse-docs-sweep: Project Documentation Sweep

Prefix your first line with 🧹 inline.

**Goal**: Automatically synchronize root CLAUDE.md "change propagation matrix" + sub-CLAUDE.md / `docs/invariants/` / `docs/runbooks/` / counter/pointer / table entries by analyzing `git diff HEAD` + conversation decisions of the previous task. Permanent rules and new document candidates are only reported in dry-run (silent automatic addition is prohibited). Set the matrix as SoT and do not hard-code the rules in the skill.

## When to Use

User says "docs sweep", "update document", "synchronize docs", "clean up CLAUDE.md", etc. **Skip** for:
- Fix typos in a single doc (Direct Edit is cheaper)
- Kit Extension catalog update → `omniverse-kit-extension-catalog-sync`
- USD asset URL / inventory → `omniverse-asset-inventory-sync`
- When `git diff HEAD` is empty (automatic graceful shutdown — no error)

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | Auto-gen / immutable history / external sync editing prohibited — `docs/tool-catalog.md` (auto-gen via `scripts/generate_tool_catalog.py`), `docs/phase-*-validation-report.md` (immutable history), `docs/references/testbed-snapshot/**` (external sync via `scripts/sync_testbed_snapshot.py`). When drift is found, it only *suggests re-executing the relevant sync script*. |
| I2 | Do not invade other skill areas — `docs/references/extensions.json` / `extensions-catalog.md` (`omniverse-kit-extension-catalog-sync`), `docs/assets/isaac/assets/*.md` / `asset_inventory.md` (`omniverse-asset-inventory-sync`). |
| I3 | L3 (permanent rule·new directory·new sub-CLAUDE.md·`lessons-learned.md` permanent rule·matrix self-modification·delete rather than stale) is dry-run only — no editing without user approval. Reported only as a sign-off candidate list. |
| I4 | Pre-stage verification gate — Step 9 (`git add`) is executed only when `pytest tests/unit/test_doc_integrity.py -q` + `pytest tests/unit/ -q` + `scripts/verify_mcp_sync.py` in Step 8 are all green. If any one fails, no stage + working tree changes remain (auto-revert prohibited). |
| I5 | Matrix is ​​SoT — Prohibit hard-code change propagation rules into skills. root `CLAUDE.md` Parse the "Change Propagation Matrix" table every time. STOP (skill stale signal) when parse fails. |
| I6 | DO-NOT-EDIT Protected area absolutely prohibited from editing — `<!-- DO-NOT-EDIT-START -->` … `<!-- DO-NOT-EDIT-END -->` All lines inside a block + inline `<!-- ⛔ DO-NOT-EDIT ... -->` Marked rows (automatically verified G1-G7 guards). |

Breaking any → STOP and report.

## Workflow

All Python invocations use `.venv/Scripts/python.exe` (Windows; bypasses `uv run` lock contention with multi-instance MCP servers).

### Step 1 — Collect input (Hybrid: git state + conversation)

**Input (a) — git state**:

```bash
git diff HEAD --name-status
git diff HEAD
git status --porcelain
```

**Input (b) — Current conversation (since last commit)**: Scans the agent's session conversation history back to the boundary anchor *"since last commit"*. The extraction target is limited to *decisions/insights* that occurred during the session (all utterances If there is no conversation within the boundary, only (a) is used.

**Input (c) — Optional slash argument**: User can add and highlight (b) in free text when called (e.g. `/omniverse-docs-sweep "Phase H completed + stdin DEVNULL invariant made explicit"`).

- (a) + (b) both empty → normal shutdown ("nothing to sweep" sign-off variant).
- Not empty → list of changed files + line-by-line diff + (b) preservation of extraction results, continued.

### Step 2 — L1 Mapping (Change Propagation Matrix)

Read + parse the “Change Propagation Matrix” table of root `CLAUDE.md`. Each row is in `| Changed target | Update together |` format. Match the change files in Step 1 with the matrix rows to extract *candidate docs that need to be updated together*.**STOP** (I5 — skill stale signal) if the matrix table cannot be found or a format variant is suspected. Never hard-code rules inside a skill.

Output: `{changed file: [files to update together]}` mapping.

### Step 3 — Derive L2 tactical candidates

- **(3a) Counter**:
  - Number of tools: Add up `grep -c '@mcp.tool()' src/omniverse_kit_mcp/tools/*.py` → Check the values ​​of root `CLAUDE.md` / `README.md`
  - test number: `pytest --collect-only -q` last line
  - Number of lines: `wc -l` in each CLAUDE.md / invariants / runbooks
- **(3b) Pointer**: Extract cross-refs (`docs/...`, `../...`) of all sub-CLAUDE.md / invariants / runbooks → Verify file existence. Among broken pointers, only *simple rename / path drift* are candidates (along with semantic transformation is L3).
- **(3c) Missing table entry**: Verify whether the new file in Step 1 is missing in the sub-CLAUDE.md "File Structure" table / root CLAUDE.md "Document Map" table / pull-doc table.

Record each candidate as `{file, before, after, reason}`.

### Step 4 — Identify L3 candidates

Comprehensive conversation extraction results + git commit msg + git status signals from Step 1 (b) (not applied, candidate only):
- Permanence intent keywords (extracted from Step 1 (b) + same search in commit msg): “Always from now on”, “Never
- New directory untracked (`git status --porcelain | grep '^?? .*/$'`)
- New sub-CLAUDE.md untracked
- Attempt to add permanent rule to `lessons-learned.md` detected (meta rule violation — incident log only)
- Detection of possible violation of root CLAUDE.md meta rule `deletions are limited to stale content`
- root CLAUDE.md "Change propagation matrix" self-modifying candidate

Preserve candidates in the “L3 candidates” section of Sign-off.

### Step 5 — Self-review A (automatic gate)

As a result of applying *in-memory* each L1+L2 candidate:
- **Linecap**: root `CLAUDE.md` ≤100 / sub-CLAUDE.md ≤150 / `docs/invariants/*.md` ≤200 / `docs/runbooks/*.md` ≤300 — Discard candidates if any one is exceeded
- **Matrix Residual**: Are all “files to be updated together” requested by L1 mapping included in the candidates?
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

Actual editing of each passing candidate with `Edit` tool. If there are multiple candidates in one file, the changes are combined and processed into 1 Edit call, if possible. **Does not apply to L3 candidates** — Sign-off reporting only.

### Step 8 — Post-verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_doc_integrity.py -q
.venv/Scripts/python.exe -m pytest tests/unit/ -q
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

All green → Proceed to Step 9. Even one fails → Step 9 skip + Sign-off "Verification fail" variant. **Changes remain in the working tree — no auto-revert** (risk of user in-progress task conflict).

### Step 9 — Auto-stage + Sign-off

```bash
git add <changed files>
```

Never call `git commit` / `git push` (Auto-stage only — user commits as a semantic unit). And the Sign-off output below.

## Stop Conditions

STOP and report on any:
- Step 1: `git diff HEAD` + `git status` are both empty → Normal shutdown ("nothing to sweep") — not an error
- Step 2: Matrix parse fail → STOP (root CLAUDE.md schema modification suspected, skill code modification may be necessary)
- Step 5: Discard all L1+L2 candidates as line cap/DO-NOT-EDIT violation/matrix remainder → STOP + report (human judgment required — transfer/split/compress)
- Step 6: All candidates are discarded for violating meta rules → STOP + Report
- Step 8: Post-verification fail → Step 9 skip + report
- I1–I6 violation → STOP

## Never Do

- ❌ Auto-generated (`docs/tool-catalog.md`) / immutable history (`docs/phase-*-validation-report.md`) / edit testbed-snapshot
- ❌ Edit other skill areas (`docs/references/extensions.json` / `extensions-catalog.md`, `docs/assets/isaac/assets/*.md` / `asset_inventory.md`)
- ❌ L3 candidate silent automatic application — always with dry-run report
- ❌ If Step 8 fails, `git add` (does not stage)
- ❌ Step 8 auto-revert changes after fail (risk of damage to user’s in-progress work)
- ❌ `git commit` / `git push` (Auto-stage only)
- ❌ root `CLAUDE.md` "Change propagation matrix" self-correction (change to matrix itself is L3)
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
- <file>: <Reason for discard — line cap / matrix residual / DO-NOT-EDIT infringement / meta rule / duplication> [Self-review A|B]
-...

Verification (Step 8):
- pytest tests/unit/test_doc_integrity.py: <N> passed
- pytest tests/unit/: <N> passed
- scripts/verify_mcp_sync.py: OK
- Cap: root <X>/150, sub max <X>/150, invariants max <X>/200, runbooks max <X>/300

Staged (commit/push pending — user decision):
- M <file>
-...

Next: git commit by user as a semantic unit. L3 candidate processing is instructed as “Apply L3 1 time” / “Ignore L3”.
```

### Variant — No-op (Step 1 stop)

```
🧹 omniverse-docs-sweep complete — nothing to sweep
git diff HEAD: empty
```

### Variant — Post-verification fail (Step 8 stop)

```
🧹 omniverse-docs-sweep complete (post-verification fail — does not stage)

L1+L2 applied:
- ... (Changes remain in the working tree — no auto-revert)

Verification fail:
- <item that failed among pytest / verify_mcp_sync> (<actual measurement vs cap / drift content>)

Action required: <Summary of causes> — Called again after user processing (migration / compression / division / drift correction).
```

## References (background only — do not read inline)

- root `CLAUDE.md` — "Change propagation matrix" (SoT) + meta rules (line hardcap, migration/delete rules, lessons-learned incident log) + DO-NOT-EDIT protection G1-G7
- `docs/CLAUDE.md` — Role of each file in docs directory + update rules
- `tests/unit/test_doc_integrity.py` — line cap / cross-ref / G1-G7 guard
- `scripts/verify_mcp_sync.py` — MCP catalog drift guard
- `.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md` — isomorphic patterns reference
- `.claude/skills/omniverse-asset-inventory-sync/SKILL.md` — isomorphic patterns reference

Answer in the same language as the question.