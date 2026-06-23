<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Public-history leak found after commits were already pushed -->
# Public history leak remediation

Use this runbook when `scripts/review_public_hygiene.py --since ...` reports a
user-specific path, secret-like literal, generated reference, or split string
path from commits that may already be public.

## Immediate response

1. Stop pushing from the affected branch.
2. Run both gates and save the exact finding list:
   ```powershell
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "YYYY-MM-DD 00:00" --head HEAD
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "YYYY-MM-DD 00:00" --head HEAD --format json
   ```
3. Check whether the finding is only in pending local commits or already in
   `origin/<branch>`.
4. If already pushed, do not rewrite history, force-push, or ask another worker
   to push until the user explicitly approves the rewrite plan.

## Classify

| class | examples | default action |
|---|---|---|
| user path | `C:/Users/<user>/...`, temp capture/log paths | rewrite required for strict public-clean history |
| split user path | `"C:" + "/Users/" + "<user>" + ...` | rewrite required for strict public-clean history |
| secret-like | tokens, private keys, credentials | revoke/rotate first, then rewrite |
| generated corpus | tracked local catalogs under ignored reference dirs | remove from history |

Current-tree redaction is not sufficient for a public repository if the original
commit remains reachable from a public ref.

## Non-destructive preparation

Before requesting approval, produce a concise plan:

- affected commit SHAs and file paths
- whether each leak is still present in the current tree
- exact replacement text such as `<validation-api-capture>/...`,
  `<local-kit-install>/...`, `<local-kit-log>`, or `localuser`
- verification commands to run after rewrite
- push impact: force-push required, collaborators must rebase/reset

Safe inspection commands:

```powershell
git log --oneline --since "YYYY-MM-DD 00:00"
git show --format= --unified=0 <commit> -- <path>
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "YYYY-MM-DD 00:00" --head HEAD
.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "YYYY-MM-DD 00:00" --head HEAD --format json
```

## Approved rewrite checklist

Only after explicit user approval:

1. Create a backup ref or clone before rewriting.
2. Rewrite only the affected public-safe text, preserving unrelated changes.
3. Run:
   ```powershell
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py
   .\.venv\Scripts\python.exe scripts\review_public_hygiene.py --since "YYYY-MM-DD 00:00" --head HEAD
   .\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q
   git diff --check
   ```
4. Review the rewritten commit range against `origin/<branch>` before any push.
5. Force-push only the approved branch and report the old and new head SHAs.

## Related Boundaries

- Public hygiene invariant: `docs/invariants/public-repo-hygiene.md`
- Guard script: `scripts/review_public_hygiene.py`
- Regression tests: `tests/unit/test_public_repo_hygiene.py`
