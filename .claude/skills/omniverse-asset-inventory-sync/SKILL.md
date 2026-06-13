---
name: omniverse-asset-inventory-sync
description: Invoke after Isaac Sim 6.x or NVIDIA SimReady asset bucket update, or when an asset path in docs/assets/isaac/assets/*.md or docs/assets/composer/*.md is reported as 404 / missing. Validates every USD URL in both inventories against NVIDIA Omniverse public S3 (HTTP HEAD) and walks the human through fixing invalid entries. Not for adding brand-new assets to the inventory, and not for Kit Extension code packages (use omniverse-kit-extension-catalog-sync for those).
user-invocable: true
disable-model-invocation: true
metadata:
  version: "1.1.0"
---

# omniverse-asset-inventory-sync: NVIDIA Omniverse USD Asset URL Validation

Prefix your first line with 🗂️ inline.

**Goal**: Verify that all USD URLs in both inventory directories are still valid in NVIDIA S3 and fix invalid entries. Prevents stale paths from accumulating after Isaac Sim 6.x patch/SimReady release.

**Watched scopes** (both same `omniverse-content-production` S3 bucket):
- `docs/assets/isaac/assets/*.md` — Isaac Sim 6.0 bundle only (strict: only accepts `Isaac/6.0` or `simready_content` prefix)
- `docs/assets/composer/*.md` — USD Composer / cross-app sample library (DigitalTwin / ArchVis / Vegetation, etc. `$VAR` free declaration, bucket-level verification only)
- README.md (catalog index) is not subject to URL verification — only sub-md meta information is listed.

## When to Use

User says one of:
- “asset path is incorrect” / “asset 404”
- "asset_inventory update" / "inventory sync"
- “I installed Isaac Sim 5.2” (possibility of changing asset bucket prefix)
- "stage_load_usd keeps failing"

**Skip** for adding a brand-new asset (direct markdown editing is cheaper) or for non-NVIDIA assets (R4 — 3rd-party USD is prohibited).

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | Use full HTTPS S3 URLs only — `file://` prohibited (stage load failure). |
| I2 | All sub-md must declare at least one `$VAR` prefix at the top (e.g. `$ISAAC` / `$SIM` for `docs/assets/isaac/`, `$DT` / `$ARCHVIS` for `docs/assets/composer/`). Every prefix URL must point to `omniverse-content-production` or `omniverse-content-staging` bucket. Do not hard-code full URLs in tables. |
| I3 | The `Root:` declaration is the main category root of the file. The path column in the table is based on the main root (e.g. `Root: $ISAAC/People/` + `Characters/Foo.usd` → `$ISAAC/People/Characters/Foo.usd`). The same applies to composer's `Root: $DT/Datacenter/` + `Liquid_Cooling/...usd`. |
| I4 | Pre-commit: `pytest tests/unit/test_asset_inventory_integrity.py -q` green, `verify_mcp_sync.py` OK, root `CLAUDE.md` ≤ 100 lines. |

Breaking any → STOP and report.

## Workflow

All Python invocations use `.venv/Scripts/python.exe` (Windows; bypasses uv lock contention with multi-instance MCP servers).

### Step 1 — Format integrity baseline

```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_asset_inventory_integrity.py -q
```- 7 passed → continue.
- any fail → **STOP**. Fix format violation first; HEAD validation on broken format is meaningless.

### Step 2 — URL validity diff (network)

```bash
.venv/Scripts/python.exe scripts/diff_asset_inventory.py --verbose
```

Network HEAD requests against `omniverse-content-production.s3` and `omniverse-content-staging.s3`. Takes 5–15 s for ~100 URLs.

- exit 0 → "all asset URLs valid", stop the skill.
- exit 1 → record per-file invalid lists (404 / NET / 5xx). Continue.

### Step 3 — Prefix update (⚠️ user input if Isaac Sim major bump)

If many invalid URLs share the same `Isaac/5.X/Isaac` prefix (e.g. NVIDIA released `Isaac/5.2/Isaac`), ask:

> "It appears that NVIDIA has moved to a new Isaac Sim asset bucket (e.g. `6.0` → `6.1`). Shall we update the `$ISAAC` prefix of all sub-mds to `Isaac/6.1/Isaac` at once?"

Use `Edit` with `replace_all: true` for the prefix declaration line in each sub-md.

### Step 4 — Per-invalid resolution

For each invalid URL group:

| Symptom | Action |
|---------|--------|
| 404 only on a few entries | Use S3 LIST API (`?list-type=2&prefix=<dir>/&delimiter=/`, anonymous) on the parent dir to find the real `*.usd` file name; `Edit` the inventory row's file column. |
| 404 on whole `{Vendor}/` subtree | Vendor folder renamed or relocated. List `Robots/` (or category root) with S3 LIST API to find the new vendor name; `Edit`. |
| NET / timeout | Network — re-run Step 2; do not edit inventory. |
| 5xx | NVIDIA-side transient — re-run Step 2 in 5 min; do not edit inventory. |
| Mis-categorized (file exists at different vendor) | Move the row under the correct vendor section. |
| Asset folder confirmed missing on S3 | **Delete the row from markdown** + remove the model name from the corresponding category index table (e.g. AMR / humanoid row at the top of robots.md). Keeps the doc consistent. |

When a row's `model` column abbreviates two SKUs (e.g. `Humanoid/28` for both `Humanoid` and `Humanoid28`), split into two rows so each maps to one S3 folder.

### Step 5 — Re-validate

```bash
.venv/Scripts/python.exe scripts/diff_asset_inventory.py
```

Expect exit 0. If still invalid, return to Step 4 for unresolved items. STOP if 3 rounds fail to converge — escalate to user.

### Step 6 — Final verify + commit + push

```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_asset_inventory_integrity.py -q
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

I4 must hold. Then:

```bash
git add docs/assets/isaac/assets/ docs/assets/isaac/asset_inventory.md docs/assets/composer/
git commit -m "fix(asset_inventory): <summary> — <N entries fixed>"
git push origin main
```

Commit message examples:
- `fix(asset_inventory): NTNU vendor 6 entries → NVIDIA + path rename`
- `fix(asset_inventory): Isaac Sim 6.0 → 6.1 prefix bump`
- `fix(asset_inventory): FrankaFR3 path → fr3.usd (NVIDIA renamed)`

## Stop Conditions

STOP and report on any:
- Step 1 integrity fail (markdown format broken)
- Step 5 doesn't converge after 3 rounds
- Step 6 verify_mcp_sync fail
- I1/I2/I3/I4 violation

## Never Do

- ❌ Keep a row whose asset folder no longer exists on S3 (delete it instead — doc must stay concise; no `(removed)` marker)
- ❌ Forget to update the category index table (e.g. AMR · Humanoid abbreviations at the top of robots.md) when deleting / renaming a row
- ❌ Hard-code full HTTPS URLs in tables (use prefix variable)
- ❌ Use `file://` URLs (asset load fails)
- ❌ Add 3rd-party USD outside NVIDIA buckets (only `omniverse-content-production` / `omniverse-content-staging`)
- ❌ Commit without Step 5 re-validate exit 0
- ❌ `git push --force`

## Sign-off

```
🗂️ omniverse-asset-inventory-sync complete
Validated: <N> URLs across <M> files
Fixed: <K invalid entries> (<categorize: rename / vendor-move / prefix-bump>)
Commit: <hash> (origin/main synced)
Integrity: pytest 7 passed, verify_mcp_sync OK, CLAUDE.md <N> lines
```

## References (background only — do not read inline)

- `scripts/diff_asset_inventory.py` — implementation (HTTP HEAD validator)
- `tests/unit/test_asset_inventory_integrity.py` — 7 format invariants (no network)
- `docs/assets/isaac/asset_inventory.md` — root index
- `docs/assets/isaac/assets/{robots,environments,people,props,simready,other}.md` — per-category catalogs

Answer in the same language as the question.
