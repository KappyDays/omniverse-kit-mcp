# Public History Remediation - 2026-06-24

## Scope

This note records the public-safety review and approved remediation for history
findings that were already reachable from `origin/main`.

## Current Review State

- User approved public-history rewrite on 2026-06-24.
- Backup ref created before rewriting:
  `backup/public-history-2026-06-24-before-rewrite-20260624-101946`.
- Additional backup ref created before the second broader rewrite:
  `backup/public-history-2026-06-24-after-first-rewrite-20260624-103358`.
- Rewritten clean-history base before the follow-up guard commit:
  `aa9f2a367241d15cae0ff423d2b91f6ee97aeb60`.
- Current working tree public hygiene: clean under the current-tree gate.
- Named-day audits for 2026-06-23 and 2026-06-24 pass on the rewritten
  history.
- The remaining push action for this remediation is the approved
  `--force-with-lease` update of `origin/main` after final validation.

## Affected Public History

| Commit | Subject | File | Findings | Replacement target |
| --- | --- | --- | ---: | --- |
| `ee5150e263d89f8f4cfd16cd7b7b6f2ae3d3b21e` | `feat(scenarios): harden robot RTX sensor workflow` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | 1 | Replace local validation capture path with `<validation-api-capture>/capture_197e66404343.png`. |
| `a04c4424fbeeea4a27a8136f0d0b5479783a0b4a` | `fix(scenarios): stabilize robot RTX lidar workflow` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | 1 | Replace local validation capture path with `<validation-api-capture>/capture_5bb7fc671209.png`. |
| `688c661a64b7c0b1801cf9a0b1a79f276d821ba6` | `fix(scripts): load root env for standalone workspace runs` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | 6 | Replace local Kit install, Kit app file, temp Kit log, validation capture paths, and process IDs with `<local-kit-install>/...`, `<local-kit-log>/kit_1782189205.log`, `<validation-api-capture>/capture_3f1cfaca4517.png`, and `pid=<process-id>` placeholders. |
| `83beec817f7d476c2a33832f3c6a4cf715d7086b` | `test(repo): guard public history hygiene` | `tests/unit/test_public_repo_hygiene.py` | 1 | Rewrite the split-path fixture to use a stable placeholder user such as `localuser`, not the current OS account name. |
| `c844e4388615d8351b51b02f0bde904c75d5960d` | `feat(scenarios): redact process ids in public reports` | `docs/artifacts/scenario-public-redacts-process-ids-2026-06-24.md` | 1 | Replace the numeric process-ID example with a placeholder such as `pid=<number>`. |

## Completed Remediation Steps

These steps were performed only after the user explicitly approved
public-history rewriting and the required force-push impact.

1. Create a backup ref before rewriting:

   ```powershell
   git branch backup/public-history-2026-06-24-before-rewrite-20260624-101946 HEAD
   ```

2. Rewrote only blob text matching the affected public-safety patterns,
   preserving behavior and replacing local evidence strings with stable
   placeholders.
3. Re-ran the public-safety gates:

   ```powershell
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --base origin/main --head HEAD --redact-samples
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-23 --head HEAD --redact-samples
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --date 2026-06-24 --head HEAD --redact-samples
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --skip-history --redact-samples
   git diff --check
   ```

4. Review collaborator impact before force-pushing. Any clone based on the
   current public history will need to rebase or reset after the rewrite.

## Push Gate

The history remediation was approved and completed locally. Push must use an
explicit force-with-lease update after final tests and public-safety review:

```powershell
git push --force-with-lease origin main
```
