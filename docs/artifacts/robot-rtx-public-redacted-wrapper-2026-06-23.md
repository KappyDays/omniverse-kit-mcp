# Robot RTX Public Redacted Wrapper - 2026-06-23

## Change

The canonical Robot + RTX live proof wrapper now uses
`scenario_last_report(report_format="markdown", redact_local_paths=true)` for
public evidence. The usage-guide test also pins both the quick Markdown report
token and the redacted public-evidence token before log capture.

## Why

Robot + RTX live reports can include host-local capture paths. Public evidence
should preserve useful SHA256, pixel-stat, lidar, and WARN/ERROR summaries
without copying local paths into tracked docs.

## Evidence Plan

- `tests/unit/test_doc_references.py` pins the wrapper order and redaction
  guidance.
- Doc integrity/reference checks guard the artifact and docs hierarchy.
- Public hygiene checks guard against path leakage before commit/push.

## Live Scope

No live Isaac Sim run was needed. This batch updates the documented wrapper and
its unit guard only; it does not mutate a stage.

## Validation Results

- Targeted doc tests: 2 passed.
- Doc integrity/reference checks: 19 passed, 2 skipped.
- `scripts/review_public_hygiene.py`: passed for current tree and pending
  history.
- `git diff --check`: passed.
- `scripts/verify_mcp_sync.py`: OK, 34 sync tests passed.
- `scripts/review_public_hygiene.py --base origin/main --head HEAD`: passed
  for the pending push range.
- Full unit suite: 750 passed, 16 skipped.
- `scripts/review_public_hygiene.py --today --head HEAD`: still reports the
  pre-existing public-history findings; this batch introduced no new finding.
