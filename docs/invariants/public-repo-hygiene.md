# Public Repo Hygiene Invariant

Read this before any commit/push intended for a public branch.

## Required Gate

Run the current-tree and pending-history guard before push:

```powershell
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py
```

For an explicit review range, use:

```powershell
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base <base> --head HEAD
```

For a session/day audit after commits may already have been pushed, use:

```powershell
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-23 --head HEAD
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "2026-06-23 00:00" --head HEAD
```

For output that may be copied into a public-safe review note, add
`--redact-samples` so project paths and finding samples are masked while the
scan logic and finding counts stay unchanged.

The current-tree scan includes tracked files plus untracked, non-ignored files
from `git ls-files --others --exclude-standard`; ignored local evidence caches
stay outside the public gate. The default history scan uses the current branch
upstream merge-base through `HEAD`, so local commits that are about to be pushed
are reviewed. `--today` expands to local midnight for the current day and is the
preferred quick command for "all commits pushed or prepared today" reviews.
Use `--date YYYY-MM-DD` when reviewing a named day after local midnight has
already moved on.
History findings are classified against the current upstream or `origin/main`:
`already_public` means the commit is reachable from that public ref, and
`pending_push` means it is still only in the scanned local range.

## Blocking Findings

- User-specific paths such as real Windows/MSYS user-home paths, Codex local
  worktree paths, and sanitized local path slugs.
- Secret-like literals such as private keys and common token prefixes.
- Tracked generated local references under `docs/references/extensions*`,
  `docs/references/app-specific/`, `docs/references/testbed-snapshot/`, or
  `docs/references/official-assets/`.

## Evidence Rules

- Public artifacts may include hashes, counts, ports, and redacted placeholders.
- Redact local install roots, temp paths, worker/thread IDs, process IDs, and
  raw generated catalog/cache paths.
- If a finding was already pushed, report it clearly. Do not rewrite history or
  force-push without explicit user approval. Use
  `docs/runbooks/public-history-leak.md` to prepare a non-destructive
  remediation plan.

## Related Checks

- `tests/unit/test_public_repo_hygiene.py`
- `docs/runbooks/public-history-leak.md`
- `git diff --check`
- `scripts/verify_mcp_sync.py` when tool/docs catalog sync is relevant
