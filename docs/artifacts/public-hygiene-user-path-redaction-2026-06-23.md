# Public Hygiene User Path Redaction

Date: 2026-06-23

## Scope

This batch removes user-specific local path literals from public-facing upgrade
and implementation-plan documents while preserving the useful operational
evidence with placeholders such as `<repo-root>`, `<codex-worktrees>`, and
`<isaac-sim-6.0-root>`.

It also adds a tracked-file hygiene guard so future changes fail unit tests if
the same user-specific path class reappears in text files.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q`: 1 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`: 17 passed, 2 skipped.
- `.\.venv\Scripts\ruff.exe check tests\unit\test_public_repo_hygiene.py tests\unit\test_doc_integrity.py`: passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`: OK, 32 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`: 712 passed, 16 skipped.
- `git diff --check`: passed with CRLF conversion warnings only.
- Public scan of tracked files and the new diff found no user-specific local
  path matches in the cleaned class.

## Live Evidence

No live Kit smoke is required. This is a documentation hygiene and static guard
update only.
