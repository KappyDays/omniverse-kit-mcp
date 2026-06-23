# Public Hygiene Generic User Path Guard - 2026-06-23

## Scope

Follow-up public-readiness review of the 2026-06-23 commit range found that
the hygiene test encoded the local Windows username as split string fragments.
That avoided literal path matches, but it was still unnecessary in a public
repository.

## Fix

- Replaced the user-specific literal assembly with generic path regex guards.
- Covered Windows user-home paths, MSYS-style drive user-home paths,
  sanitized Windows-user path fragments, and Codex worktree paths.
- Kept environment-variable examples such as `$env:USERNAME` allowed.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`
  - `3 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`
  - `22 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - OK, `32 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `723 passed, 16 skipped`
- `git diff --check`
  - no whitespace errors; CRLF conversion warning only for the edited test file
- Public scan:
  - no tracked generated `docs/references/official-assets/` files
  - no added user-path, local username, or common credential-token matches

## Live Evidence

No live Kit smoke is required. This is a static public-repository hygiene guard
change.
