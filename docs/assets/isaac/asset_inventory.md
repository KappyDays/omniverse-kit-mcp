# Isaac Sim 6.0 — Asset Catalog Index

**Actual measurement completed**: 2026-06-11 Isaac Sim 6.0 S3 LIST + HEAD verification (`scripts/diff_asset_inventory.py --verbose`: robots 228+ top-level USD/USDA included).
**Usage**: Read only the category files you need — no unnecessary token consumption.

---

## Bucket root URLs

| catalog | Bucket | Prefix |
|---|---|---|
| **Isaac Sim Assets** | `omniverse-content-production.s3-us-west-2.amazonaws.com` | `Assets/Isaac/6.0/Isaac/` |
| **SimReady Explorer** | `omniverse-content-staging.s3.us-west-2.amazonaws.com` | `Assets/simready_content/common_assets/props/` |

- `$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac`
-`$SIM` = `https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/common_assets/props`

Both buckets are public read. When calling `stage_load_usd`, use **full HTTPS URL** (`file://` is prohibited).

---

## File pointers by category

| request type | file to read | Summary of contents |
|---|---|---|
| Add robot / Recommend robot | `docs/assets/isaac/assets/robots.md` | 50 vendors · 203+ model folders · 228+ top-level USD/USDA · Index by type |
| Environment/Scene Loading | `docs/assets/isaac/assets/environments.md` | 12 environment folders · Major USD/USDA |
| People / Characters / Animation | `docs/assets/isaac/assets/people.md` | Named Characters · DH_Characters · Animations |
| Industrial prop (pallet, forklift, shelf) | `docs/assets/isaac/assets/props.md` | Isaac Core Props folder |
| Furniture/Box/Container | `docs/assets/isaac/assets/simready.md` | SimReady Props 1000+ Species Category List |
| RL Learning / Materials / Examples / Sensors | `docs/assets/isaac/assets/other.md` | IsaacLab · Materials · Samples · Sensors |

---

## Search Guide

```python
# Category list
asset_list()

# Browse a specific category
asset_list(category="robots", subpath="Unitree")
asset_list(category="environments", subpath="Simple_Warehouse")

# Browse SimReady (1000+ items, alphabetical pagination)
content_browse("$SIM", max_entries=500)
content_browse("$SIM/{name}")  # → {name}.usd is canonical
```