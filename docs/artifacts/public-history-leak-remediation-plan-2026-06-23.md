# Public history leak remediation plan - 2026-06-23

Status at 2026-06-23T20:47:51+09:00:

- Pending local range `75e032b..HEAD`: public hygiene guard passes.
- Current tracked tree plus untracked, non-ignored files: no public hygiene
  findings from `scripts/review_public_hygiene.py`.
- Day/session range `204cb83..HEAD`: public hygiene guard reports 7 findings.
- Already-pushed range `204cb83..origin/main`: same 7 findings, so push remains blocked until the user explicitly approves a history rewrite / force-push plan.

## Affected commits

| Commit | File | Finding class | Current tree status | Replacement text |
|---|---|---|---|---|
| `ee5150e` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | user temp capture path | redacted in current tree | `<validation-api-capture>/capture_197e66404343.png` |
| `a04c442` | `docs/artifacts/robot-rtx-sensor-golden-workflow-2026-06-23.md` | user temp capture path | redacted in current tree | `<validation-api-capture>/capture_5bb7fc671209.png` |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | local Kit executable path | redacted in current tree | `<local-kit-install>/kit/kit.exe` |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | local Kit app file path | redacted in current tree | `<local-kit-install>/apps/isaacsim.exp.full.kit` |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | local startup log path | redacted in current tree | `<local-kit-log>/kit_<epoch>.log` |
| `688c661` | `docs/artifacts/standalone-workspace-env-and-lidar-live-smoke-2026-06-23.md` | user temp capture path | redacted in current tree | `<validation-api-capture>/capture_3f1cfaca4517.png` |
| `83beec8` | `tests/unit/test_public_repo_hygiene.py` | split user path fixture | replaced in current tree by runtime/user-neutral fixture | `localuser` or runtime-selected test username |

## Required approval before action

History rewrite and force-push are intentionally not executed without explicit user approval.
If approved, preserve unrelated changes and rewrite only the affected text above.

## Verification after approved rewrite

```powershell
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "2026-06-23 00:00" --head HEAD
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "2026-06-23 00:00" --head HEAD --format json
.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q
git diff --check
```

## Push impact

- Force-push is required because affected commits are already reachable from `origin/main`.
- Any collaborators or worker threads based on the current public `main` must rebase or reset after the approved rewrite.
- Do not ask another worker to push from this branch until the rewritten history passes the checks above.
