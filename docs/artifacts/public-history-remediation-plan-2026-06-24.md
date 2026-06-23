# Public History Remediation Plan - 2026-06-24

## Scope

This note records the public-safety review for the current session and the
non-destructive remediation plan for history findings that were already
reachable from `origin/main`.

## Current Review State

- Current working tree public hygiene: clean.
- Pending local range `origin/main..HEAD`: clean under the pending-push audit.
- Commits created on 2026-06-24: 1 process-ID example finding, classified as
  `already_public`.
- Older history since 2026-06-23: 10 findings, all classified as
  `already_public`.

Because the remaining findings are already public, do not rewrite history,
force-push, or continue pushing from the affected branch without explicit user
approval.

## Affected Public History

| Commit | Subject | File | Findings | Replacement target |
| --- | --- | --- | ---: | --- |
| `ee5150e263d89f8f4cfd16cd7b7b6f2ae3d3b21e` | `feat(scenarios): harden robot RTX sensor workflow` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | 1 | Replace local validation capture path with `<validation-api-capture>/capture_197e66404343.png`. |
| `a04c4424fbeeea4a27a8136f0d0b5479783a0b4a` | `fix(scenarios): stabilize robot RTX lidar workflow` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | 1 | Replace local validation capture path with `<validation-api-capture>/capture_5bb7fc671209.png`. |
| `688c661a64b7c0b1801cf9a0b1a79f276d821ba6` | `fix(scripts): load root env for standalone workspace runs` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | 6 | Replace local Kit install, Kit app file, temp Kit log, validation capture paths, and process IDs with `<local-kit-install>/...`, `<local-kit-log>/kit_1782189205.log`, `<validation-api-capture>/capture_3f1cfaca4517.png`, and `pid=<process-id>` placeholders. |
| `83beec817f7d476c2a33832f3c6a4cf715d7086b` | `test(repo): guard public history hygiene` | `tests/unit/test_public_repo_hygiene.py` | 1 | Rewrite the split-path fixture to use a stable placeholder user such as `localuser`, not the current OS account name. |
| `c844e4388615d8351b51b02f0bde904c75d5960d` | `feat(scenarios): redact process ids in public reports` | `docs/artifacts/scenario-public-redacts-process-ids-2026-06-24.md` | 1 | Replace the numeric process-ID example with a placeholder such as `pid=<number>`. |

## Approved-Only Remediation Steps

Run these steps only after the user explicitly approves public-history
rewriting and the required force-push impact.

1. Create a backup ref before rewriting:

   ```powershell
   git branch backup/public-history-2026-06-23-before-rewrite HEAD
   ```

2. Rewrite only the affected commits above, preserving behavior and replacing
   the listed local evidence strings with stable placeholders.
3. Re-run the public-safety gates:

   ```powershell
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-23 --head HEAD --format json --redact-samples
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --skip-history --format json --redact-samples
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q
   git diff --check
   ```

4. Re-run the repo sync and relevant targeted tests:

   ```powershell
   .\.venv\Scripts\python.exe scripts\verify_mcp_sync.py
   .\.venv\Scripts\python.exe -m pytest tests\unit\ -q
   ```

5. Review collaborator impact before force-pushing. Any clone based on the
   current public history will need to rebase or reset after the rewrite.

## Push Gate

Normal push from the current branch remains blocked until either:

- the user approves and completes the history remediation above, or
- the user explicitly accepts the residual public-history risk.
