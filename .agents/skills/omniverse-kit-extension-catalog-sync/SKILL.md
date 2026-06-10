---
name: omniverse-kit-extension-catalog-sync
description: Invoke after Kit / Isaac Sim / USD Composer install has been updated, to re-sync the local ignored Kit Extension catalog (docs/references/extensions.json) with the file system. Runs the canonical workflow (diff → integrity → harvest → render → enrichment → verify). Not for one-off catalog edits, and not for USD asset URLs (use omniverse-asset-inventory-sync for those).
metadata:
  version: "1.2.0"
---

# omniverse-kit-extension-catalog-sync: Kit Extension Catalog Re-sync

Prefix your first line with 📚 inline.

**목표**: Kit / Isaac Sim / USD Composer 설치 갱신 후 local ignored `docs/references/extensions.json` 을 install tree 와 정합시키고 신규 ext 를 enrichment. 기존 수동 enrichment 는 절대 파기하지 않는다. Public repo 에 generated catalog 는 commit 하지 않는다.

## When to Use

User says "Kit/Isaac Sim/USD Composer 업뎃됐어", "catalog sync", "extensions.json 동기화" 등. **Skip** for single-entry edits (typo fix 등) — direct JSON edit cheaper.

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | Do not overwrite `summary` / `key_symbols` / `mcp_research_hint` / `testbed_refs` of `enriched` entries (Phase A–E manual curation). |
| I2 | Always run harvest with `preserve_enrichment=True` (default). `--no-preserve-enrichment` requires explicit per-invocation user approval. |
| I3 | Removed-from-install ext stays in JSON with `enrichment_status="skipped"` + `skipped_reason="removed_from_install_v<new>"`. Never delete the entry. |
| I4 | Pre-finish: `pytest tests/unit/ -q` green, `verify_mcp_sync.py` OK, `git diff docs/tool-catalog.md` empty, root `AGENTS.md` present. |

Breaking any → STOP and report.

## Workflow

All Python invocations use `.venv/Scripts/python.exe` (Windows; bypasses `uv run` lock contention with multi-instance MCP servers).

### Step 1 — Diff baseline

```bash
.venv/Scripts/python.exe scripts/diff_catalog.py --verbose
```

- exit 0 → "already in sync", stop the skill.
- exit 1 → record `added` / `removed` / `version_bumped` / `category_changed`, continue.

### Step 2 — Integrity baseline

```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_catalog_integrity.py -q
```

- 13 passed → continue.
- any fail → **STOP**. Do not overwrite a broken catalog; fix root cause first.

### Step 3 — kit_version constants (⚠️ user input)

Inspect `scripts/harvest_extension_metadata.py::APP_ROOTS`. If many `version_bumped` or user mentioned major bump, ask:

> "새 Kit / app 버전을 알려주세요 — 예: `Kit 111.0.2 / Isaac Sim 5.2.0`. 또는 `.kit` / `VERSION` 파일 경로."

Then `Edit` `APP_ROOTS["<app>"]["kit_version"]` / `["app_version"]`. Skip if user confirms no change.

### Step 4 — Harvest (preserve enrichment)

```bash
.venv/Scripts/python.exe scripts/harvest_extension_metadata.py
```

Cross-check `harvested_per_app` distribution vs Step 1 diff. New ext arrive as `enrichment_status="bootstrap"`.

### Step 5 — Render + removed transition

```bash
.venv/Scripts/python.exe scripts/render_catalog_md.py
```

For each Step 1 `removed` entry, set `enrichment_status="skipped"` + `skipped_reason="removed_from_install_v<new>"`. Use a one-shot Python script (load → modify → dump with `indent=2, sort_keys=True, ensure_ascii=False`); delete after use. **Never** delete the entry itself (I3).

### Step 6 — Enrich added ext (batch of 50)

For each ext in the batch (Phase A pattern):

1. Read `{source_dir}/{raw_dirname}/config/extension.toml` — title / description / keywords / category / dependencies.
2. Read `{public_modules[0]}/__init__.py` — `__all__` or top-level classes/functions → `key_symbols` list of dicts `{name, kind, desc}`.
3. Korean `summary` (1–2 sentences, expand raw_description with domain context).
4. `mcp_research_hint` — how MCP would wrap this ext (which natural-language task triggers it, which existing tool/pattern to extend).
5. `enriched_at` = current UTC ISO, `enrichment_status="enriched"`.

Batch ≤ 49: 1 commit. Batch ≥ 50: split, 1 commit per 50 with message:

```
chore(catalog): Kit <old>→<new> batch <N>/<M> — <K ext enriched>
```

### Step 7 — Final verify

```bash
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
.venv/Scripts/python.exe -m pytest tests/unit/ -q
```

I4 must hold. Generated files under `docs/references/` are ignored; do not stage
or commit them. If Step 3 edited `scripts/harvest_extension_metadata.py`, stage
and commit only that script change after summarizing it to the user.

## Stop Conditions

STOP and report on any:
- Step 2 integrity fail
- Step 4 harvest > 10 errors (toml parse mass failure = Kit format change)
- Step 6 source path missing (stale `APP_ROOTS.root` — ask user for current install path)
- Step 7 `verify_mcp_sync.py` non-zero
- Any I1/I2/I3/I4 violation

## Sign-off

```
📚 omniverse-kit-extension-catalog-sync complete
Kit: <old>→<new> · App: <isaacsim>/<usd_composer>
Processed: <N added enriched / M removed→skipped / K version_bumped>
Generated catalog: local ignored files only
Principle-6: pytest <N> passed, verify_mcp_sync OK, tool-catalog clean, AGENTS.md present
```

## References (background only — do not read inline)

- `docs/references/CLAUDE.md` — pull-doc with local generated catalog rules
- `scripts/diff_catalog.py` · `harvest_extension_metadata.py` · `render_catalog_md.py` — implementation
- `tests/unit/test_catalog_integrity.py` — 13 invariants regression guard

Answer in the same language as the question.
