# Scenario Retry Data Summary Docs - 2026-06-23

## Scope

Documentation follow-up for scenario retry diagnostics.

The agent-facing docs now point operators to `retry_failures[].data_summary`
before relying on retry failure message strings. This locks in the intended
tool order after `scenario_validate`:

1. Read the latest scenario report in JSON for exact fields.
2. Inspect `retry_failures[].data_summary` for failed retry attempts.
3. Use Markdown only as the quick public-safe triage view.
4. Open logs after the structured fields are exhausted.

## Public Hygiene

No host-local paths, worker IDs, process IDs, or temporary capture paths are
recorded here.

## Validation

- Doc integrity/reference tests: `19 passed, 2 skipped`.
- `git diff --check`: passed.
- `scripts/verify_mcp_sync.py`: passed, including `34 passed` catalog tests.
- Public hygiene current/pending gates: passed.
- Full unit suite: `750 passed, 16 skipped`.

## Known Public-History Gate

The current tree and pending commit range are public-safe. The day-wide public
history audit still reports the previously identified seven findings already
reachable from `origin/main`; no new finding was introduced by this batch.
