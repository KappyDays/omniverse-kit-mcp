# Public History Rewrite Plan

Date: 2026-06-23

## Status

No rewrite or force-push has been performed. This is the non-destructive plan
required before requesting approval for public-history remediation.

Current evidence:

- Default pending public hygiene gate: passed.
- Current-tree-only public hygiene gate: passed with `finding_count=0`.
- `--today --head HEAD` history audit: failed with `finding_count=7`.
- The affected commits are already contained in `origin/main`.
- Local `main` is currently `origin/main` + 24 commits; the pending range
  passes `scripts/review_public_hygiene.py --base origin/main --head HEAD`.

## Affected Commits

| commit | file | class | current tree |
|---|---|---|---|
| `ee5150e` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | user temp capture path | redacted |
| `a04c442` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | user temp capture path | redacted |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | local Kit install path | redacted |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | local Kit app file path | redacted |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | local startup log path | redacted |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | user temp capture path | redacted |
| `83beec8` | `tests/unit/test_public_repo_hygiene.py` | split user path fixture | generic fixture |

## Replacement Text

Use these public-safe replacements while preserving unrelated commit content:

- User temp capture path: `local validation capture path redacted`
- Local Kit executable path: `<local-kit-install>/kit/kit.exe`
- Local Kit app file path: `<local-kit-install>/apps/isaacsim.exp.full.kit`
- Local startup log path: `<local-kit-log>`
- Split user fixture: `localuser`

## Proposed Rewrite Procedure

Only after explicit approval:

1. Create a backup ref for the current head.
2. Rewrite only the affected added lines in the commits listed above.
3. Preserve current commit order and unrelated file content.
4. Re-run the verification commands below.
5. Review the rewritten range against `origin/main`.
6. Force-push only the approved branch.

## Verification After Rewrite

```powershell
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD --format json
.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q
git diff --check
```

Expected result after approved rewrite: all public hygiene commands exit 0.

## Validation Of This Plan

- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py`: passed
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --skip-history --format json`:
  passed with `finding_count=0`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`:
  `19 passed, 2 skipped`
- `git diff --check`: passed
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`: passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q`:
  `30 passed, 2 skipped`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD --format json`:
  failed as expected with `finding_count=7`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`:
  `750 passed, 16 skipped`

Additional validation after the latest local-only diagnostics batches:

- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json`:
  passed with `finding_count=0`
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --today --head HEAD --format json`:
  still failed as expected with the same `finding_count=7`

## Push Impact

The cleanup requires a history rewrite because the findings are already
reachable from `origin/main`. The final push must be a force-push, and any
collaborator or worker based on the old branch head must rebase or reset onto
the rewritten history.

## Boundary

This plan intentionally omits the original local paths. Use the JSON output from
`scripts/review_public_hygiene.py --today --head HEAD --format json` only as a
local diagnostic source, not as public artifact content.
