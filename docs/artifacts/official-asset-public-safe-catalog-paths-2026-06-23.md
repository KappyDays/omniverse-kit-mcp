# Official Asset Public-Safe Catalog Paths Evidence - 2026-06-23

## Scope

Harden `official_asset_*` runtime result shapes so catalog-location fields do
not expose host-local absolute paths when results are copied into public issues,
docs, PRs, or agent logs.

## Contract

- Repository catalog paths are reported as project-relative POSIX paths.
- Catalogs supplied from temporary or external directories are reported as
  `<external-catalog>/<filename>`.
- Internal cache keys and freshness checks still use real filesystem paths.
- The following public-facing fields are covered:
  - `data.catalog_path`
  - `data.catalog_identity.path`
  - `data.diagnostics.checked_catalog_path`

## Validation Results

Completed validation:

- `.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py tests\unit\test_public_repo_hygiene.py -q` - 44 passed.
- `.venv\Scripts\python.exe scripts\verify_mcp_sync.py` - OK, 32 passed.
- `.venv\Scripts\python.exe -m pytest tests\unit\ -q` - 713 passed, 16 skipped.

Live Isaac Sim validation is not required for this batch because the change is
offline catalog result-shape hardening and does not mutate a stage or call Kit.
