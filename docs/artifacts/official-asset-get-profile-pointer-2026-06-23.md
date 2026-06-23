# Official Asset Get Profile Pointer

Date: 2026-06-23

## Review Finding

Today's public review found that `official_asset_search`, `official_asset_resolve`,
`official_asset_verify`, and `official_asset_sync_status` accepted
`app_profile`, but `official_asset_get` did not. A profile-specific search could
therefore return an id from `latest-isaac-sim.json` and then lose that profile
context during `get`.

## Fix

- `official_asset_get(asset_id, app_profile=None)` now routes through the same
  profile-specific latest pointer lookup as the other official asset tools.
- Not-found and catalog-unavailable diagnostics preserve the requested
  `app_profile`.
- The official asset reference tells agents to carry `app_profile` through
  search, resolve, get, and verify.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py::test_official_asset_get_uses_profile_latest_pointer -q`: 1 passed.
- `.\.venv\Scripts\ruff.exe check src\omniverse_kit_mcp\modules\asset_module.py src\omniverse_kit_mcp\tools\module_tools.py tests\unit\test_asset_module.py`: passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py -q`: 42 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py -q`: 25 passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`: OK, 32 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`: 17 passed, 1 skipped.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`: 711 passed, 15 skipped.
- `git diff --check`: passed with CRLF conversion warnings only.
- Public scan of the new diff found no sensitive value or host-local path matches.

## Live Evidence

No live Kit smoke is required. This is an offline catalog pointer and MCP tool
signature alignment fix covered by synthetic catalog tests.
