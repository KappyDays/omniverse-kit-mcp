# Public Hygiene Harvest Default Path

Date: 2026-06-23

## Scope

Public review found a pre-existing user-specific Isaac Sim install fallback in
`scripts/harvest_extension_metadata.py`. The script now relies on
`ISAAC_SIM_ROOT` when a local install path is needed and otherwise falls back to
the generic `C:/IsaacSim` path.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_harvest_bootstrap.py -q`: 77 passed.
- `.\.venv\Scripts\ruff.exe check scripts\harvest_extension_metadata.py tests\unit\test_harvest_bootstrap.py`: passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`: 17 passed, 1 skipped.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`: OK, 32 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`: 712 passed, 15 skipped.
- `git diff --check`: passed with CRLF conversion warnings only.
- Public scan of the new diff found no sensitive value or host-local path matches.

## Public Review

Added a unit guard that the harvest script source does not embed Windows
user-home install defaults.
