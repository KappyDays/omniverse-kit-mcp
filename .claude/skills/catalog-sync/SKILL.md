---
name: catalog-sync
description: Invoke after Kit / Isaac Sim / USD Composer install has been updated, to re-sync docs/references/extensions.json with the file system. Runs the canonical 6-step workflow (diff → integrity → harvest → render → enrichment → commit). Not for one-off catalog edits.
user-invocable: true
disable-model-invocation: true
metadata:
  version: "1.0.0"
---

# catalog-sync: Kit / App Update Re-sync

Prefix your first line with 📚 inline, not as its own paragraph.

**목표 (한국어)**: Kit / Isaac Sim / USD Composer 설치가 업데이트된 뒤, `docs/references/extensions.json` 을 실제 install tree 와 정합시키고 변경된 ext 를 enrichment 한다. 기존 수동 enrichment 는 절대 파기하지 않는다.

## When to Use

Invoke when the user says one of:
- "Kit <N> 업뎃됐어" / "Kit updated"
- "Isaac Sim <X.Y> 깔았어" / "USD Composer 새 버전 설치"
- "catalog sync" / "catalog 재동기" / "extensions.json 동기화"
- "extscache 바뀐 것 같아"

If the user just wants to edit a single ext entry (e.g. fix a typo in one summary), **do not use this skill** — direct JSON edit is cheaper.

## Invariants (Never Violate)

| ID | Rule | Why |
|----|------|-----|
| I1 | Do not overwrite existing `summary` / `key_symbols` / `mcp_research_hint` / `testbed_refs` of any entry whose `enrichment_status == "enriched"` | Those are manually curated (Phase A–E). Re-harvest loses them silently. |
| I2 | Always run harvest with `preserve_enrichment=True` (default). Never pass `--no-preserve-enrichment` without explicit user approval per invocation. | Same as I1. |
| I3 | Removed-from-install ext must stay in JSON with `enrichment_status="skipped"` + `skipped_reason="removed_from_install_v<new>"`. Do not delete the entry. | Archive value — the summary may be referenced by historical docs / commits. |
| I4 | Before every commit, verify: `pytest tests/unit/ -q` passes, `scripts/verify_mcp_sync.py` returns OK, `git diff docs/tool-catalog.md` is empty, `CLAUDE.md` ≤ 100 lines. | Root repo-level principle 6. |

Breaking any invariant → stop and report.

## Workflow

### Step 1 — Diff baseline

Run:
```bash
uv run python scripts/diff_catalog.py --verbose
```

Branch:
- exit 0 (no change) → report "already in sync" and stop the skill.
- exit 1 (changes) → record added / removed / version_bumped / category_changed lists, continue to Step 2.

### Step 2 — Integrity baseline

Run:
```bash
uv run pytest tests/unit/test_catalog_integrity.py -q
```

Branch:
- 13 passed → continue to Step 3.
- any fail → **STOP**. Report the failing invariant. Do not overwrite a broken catalog — the root cause must be fixed first.

### Step 3 — kit_version constants (⚠️ user input required)

Read `scripts/harvest_extension_metadata.py::APP_ROOTS`. If Step 1 showed many `version_bumped` entries or the user explicitly mentioned a major Kit bump, ask the user:

> "새 Kit / app 버전을 알려주세요 — 예: `Kit 111.0.2 / Isaac Sim 5.2.0`. 또는 `.kit` / `VERSION` 파일 경로를 주시면 자동 추출하겠습니다."

Then `Edit` the `APP_ROOTS["<app>"]["kit_version"]` and `["app_version"]` values. Skip if the user confirms no version change.

### Step 4 — Harvest (preserve enrichment)

Run:
```bash
uv run python scripts/harvest_extension_metadata.py
```

Verify the output's `harvested_per_app` distribution matches Step 1 diff. New ext arrive with `enrichment_status="bootstrap"`.

### Step 5 — Render + removed transition

Re-render markdown:
```bash
uv run python scripts/render_catalog_md.py
```

For each entry in Step 1's `removed` list, update:
- `enrichment_status = "skipped"`
- `skipped_reason = "removed_from_install_v<new_kit_version>"`

Use a one-shot Python script (load JSON → modify → dump with `indent=2, sort_keys=True, ensure_ascii=False`). Delete the script after use. **Never** `rm` the entry itself (violates I3).

### Step 6 — Enrich added ext (batch)

Split the `added` list:

| Count | Action |
|-------|--------|
| 0 | Skip to Step 7 |
| 1–49 | Single batch, one commit |
| 50+ | Split into batches of 50, one commit per batch |

For each ext in the batch (Phase A pattern):

1. Read `{source_dir}/{raw_dirname}/config/extension.toml` — extract title / description / keywords / category / dependencies.
2. Read `{public_modules[0]}/__init__.py` — extract `__all__` or top-level classes/functions → build `key_symbols` list of dicts: `{name, kind, desc}`.
3. Write a Korean `summary` (1–2 sentences, expand raw_description with domain context).
4. Write `mcp_research_hint` — how MCP might wrap this ext for natural-language tasks (what user request would trigger it, which MCP tool/pattern to extend).
5. Set `enriched_at` = current UTC ISO, `enrichment_status = "enriched"`.

Per-batch commit pattern:
```
chore(catalog): Kit <old>→<new> batch <N>/<M> — <K ext enriched>
```

### Step 7 — Final verify + commit + push

```bash
uv run python scripts/verify_mcp_sync.py
uv run pytest tests/unit/ -q
```

All invariants (I4) must pass. Then:

```bash
git add docs/references/extensions.json docs/references/extensions-catalog.md \
        docs/references/harvest-progress.json
# Include scripts/harvest_extension_metadata.py if APP_ROOTS was edited in Step 3
git commit -m "chore(catalog): Kit <old> → <new> sync — <N added / M removed / K version_bumped>"
git push origin main
```

## Branch Sizing (Expected Turn Count)

| Diff size | Turns | Commits |
|-----------|-------|---------|
| no change | 1 | 0 |
| ≤ 10 added, ≤ 5 removed | 5–7 | 1 |
| ~30 added | 8–15 | 1–2 |
| 50+ added (Kit major bump) | 15–30 | 3+ |

## Red Flags — STOP and Report

- Step 2 integrity test fails
- Step 4 harvest reports > 10 errors (mass toml parse failure = Kit package format broke)
- Step 6 `source_dir` path does not exist (stale `APP_ROOTS.root` — ask user for current install path)
- Step 7 `verify_mcp_sync.py` non-zero

## Never Do

- ❌ `--no-preserve-enrichment` (destroys manual enrichment)
- ❌ Overwrite `summary` / `key_symbols` / `mcp_research_hint` of `enriched` entries
- ❌ Delete `removed` entries from JSON (use skipped transition per I3)
- ❌ Ignore Step 2 failure and proceed anyway
- ❌ Commit without Step 7 verify
- ❌ `git push --force`

## Sign-off Template

```
📚 catalog-sync complete

Kit: <old> → <new>
App: <isaacsim_old → new> / <usd_composer_old → new>
Processed:
  - added (enriched):       N
  - removed (→ skipped):    M
  - version_bumped:         K
Commit(s): <hash> [, ...] (main, origin/main synced)
Principle-6 check: pytest <N_total> passed, verify_mcp_sync OK, tool-catalog diff empty, CLAUDE.md <N> lines
```

## References (Do Not Read Inline; Background Only)

- Pull-doc: `docs/references/CLAUDE.md` — "Kit / app 업데이트" section (human-readable summary of this workflow)
- Implementation: `scripts/diff_catalog.py`, `scripts/harvest_extension_metadata.py`, `scripts/render_catalog_md.py`
- Regression guard: `tests/unit/test_catalog_integrity.py` (13 invariants, must stay green)
- v2 schema spec: `docs/references/CLAUDE.md` — "extensions.json v2 스키마 주의사항" section

Answer in the same language as the question.
