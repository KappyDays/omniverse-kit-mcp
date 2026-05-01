---
name: omniverse-asset-inventory-sync
description: Invoke after Isaac Sim 5.x or NVIDIA SimReady asset bucket update, or when an asset path in isaac_course/docs/assets/*.md or docs/assets/composer/*.md is reported as 404 / missing. Validates every USD URL in both inventories against NVIDIA Omniverse public S3 (HTTP HEAD) and walks the human through fixing invalid entries. Not for adding brand-new assets to the inventory, and not for Kit Extension code packages (use omniverse-kit-extension-catalog-sync for those).
user-invocable: true
disable-model-invocation: true
metadata:
  version: "1.1.0"
---

# omniverse-asset-inventory-sync: NVIDIA Omniverse USD Asset URL Validation

Prefix your first line with 🗂️ inline.

**목표**: 두 inventory 디렉토리의 모든 USD URL 이 NVIDIA S3 에서 여전히 valid 한지 검증하고 invalid 엔트리를 수정. Isaac Sim 5.x 패치 / SimReady release 후 stale path 가 누적되는 것을 방지.

**Watched scopes** (둘 다 같은 `omniverse-content-production` S3 bucket):
- `isaac_course/docs/assets/*.md` — Isaac Sim 5.1 번들 한정 (strict: `Isaac/5.1` 또는 `simready_content` prefix 만 허용)
- `docs/assets/composer/*.md` — USD Composer / 크로스앱 sample library (DigitalTwin / ArchVis / Vegetation 등 `$VAR` 자유 선언, bucket-level 검증만)
- README.md (catalog index) 는 URL 검증 대상 아님 — sub-md 의 메타정보만 등재

## When to Use

User says one of:
- "asset 경로가 안 맞아" / "asset 404 떠"
- "asset_inventory 업데이트" / "inventory sync"
- "Isaac Sim 5.2 깔았어" (asset 버킷 prefix 변경 가능성)
- "stage_load_usd 가 자꾸 fail"

**Skip** for adding a brand-new asset (직접 markdown 편집이 cheaper) or for non-NVIDIA assets (R4 — 3rd-party USD 금지).

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | Use full HTTPS S3 URLs only — `file://` prohibited (스테이지 로드 실패). |
| I2 | All sub-md must declare at least one `$VAR` prefix at the top (e.g. `$ISAAC` / `$SIM` for isaac_course, `$DT` / `$ARCHVIS` for composer). Every prefix URL must point to `omniverse-content-production` or `omniverse-content-staging` bucket. Do not hard-code full URLs in tables. |
| I3 | `루트:` 선언은 그 파일의 메인 카테고리 root. 표의 path 컬럼은 메인 root 기준 (e.g. `루트: $ISAAC/People/` + `Characters/Foo.usd` → `$ISAAC/People/Characters/Foo.usd`). 동일하게 composer 의 `루트: $DT/Datacenter/` + `Liquid_Cooling/...usd` 도 적용. |
| I4 | Pre-commit: `pytest tests/unit/test_asset_inventory_integrity.py -q` green, `verify_mcp_sync.py` OK, root `CLAUDE.md` ≤ 100 lines. |

Breaking any → STOP and report.

## Workflow

All Python invocations use `.venv/Scripts/python.exe` (Windows; bypasses uv lock contention with multi-instance MCP servers).

### Step 1 — Format integrity baseline

```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_asset_inventory_integrity.py -q
```

- 7 passed → continue.
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

> "NVIDIA 가 새 Isaac Sim asset 버킷 (예: `5.1` → `5.2`) 으로 옮긴 것 같습니다. 모든 sub-md 의 `$ISAAC` prefix 를 `Isaac/5.2/Isaac` 로 일괄 갱신할까요?"

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
| Asset folder confirmed missing on S3 | **Delete the row from markdown** + remove the model name from the corresponding category index table (e.g. AMR / 휴머노이드 row at the top of robots.md). Keeps the doc concise. |

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
git add isaac_course/docs/assets/ isaac_course/docs/asset_inventory.md docs/assets/composer/
git commit -m "fix(asset_inventory): <summary> — <N entries fixed>"
git push origin main
```

Commit message examples:
- `fix(asset_inventory): NTNU vendor 6 entries → NVIDIA + path rename`
- `fix(asset_inventory): Isaac Sim 5.1 → 5.2 prefix bump`
- `fix(asset_inventory): FrankaFR3 path → fr3.usd (NVIDIA renamed)`

## Stop Conditions

STOP and report on any:
- Step 1 integrity fail (markdown format broken)
- Step 5 doesn't converge after 3 rounds
- Step 6 verify_mcp_sync fail
- I1/I2/I3/I4 violation

## Never Do

- ❌ Keep a row whose asset folder no longer exists on S3 (delete it instead — doc must stay concise; no `(removed)` marker)
- ❌ Forget to update the category index table (e.g. AMR · 휴머노이드 abbreviations at the top of robots.md) when deleting / renaming a row
- ❌ Hard-code full HTTPS URLs in tables (use prefix variable)
- ❌ Use `file://` URLs (asset load fails)
- ❌ Add 3rd-party USD outside NVIDIA buckets (R4 in `isaac_course/CLAUDE.md`)
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
- `isaac_course/CLAUDE.md` — R4 (NVIDIA-only assets), R5 (asset diversity matrix)
- `isaac_course/docs/asset_inventory.md` — root index
- `isaac_course/docs/assets/{robots,environments,people,props,simready,other}.md` — per-category catalogs

Answer in the same language as the question.
