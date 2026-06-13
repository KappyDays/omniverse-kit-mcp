# docs/references/ — Public-Safe References

## file

| File/Folder | what | Editable? |
|-----------|------|-----------|
| `sensor_menu_catalog.md` | `Create > Sensors` Menu Catalog. MCP resource source | ✅ Update when needed |
| `CLAUDE.md` | Instructions for working with this directory | ✅ Sync when editing tasks |

## Local-Only Generated References

The files below are not tracked in the public repo. Local Kit/Isaac Sim/USD
Generated artifacts that reflect Composer installation metadata or external document snapshots
Because.

-`extensions.json`
-`extensions-catalog.md`
-`harvest-progress.json`
-`app-specific/`
-`testbed-snapshot/`

## Regenerate command

-`.venv/Scripts/python.exe scripts/harvest_extension_metadata.py`
-`.venv/Scripts/python.exe scripts/render_catalog_md.py`
-`.venv/Scripts/python.exe -m pytest tests/unit/test_catalog_integrity.py -q`

The created file is `.gitignore` target. The durable rule that needs to be shared is the original catalog
Instead, it is summarized and reflected as `docs/invariants/` or `docs/runbooks/`.