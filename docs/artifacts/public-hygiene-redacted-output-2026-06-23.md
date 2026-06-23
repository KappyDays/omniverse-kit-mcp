# Public Hygiene Redacted Output

Date: 2026-06-23

## Change

`scripts/review_public_hygiene.py` now accepts `--redact-samples` for review
output that may be copied into public-safe notes.

The option masks the printed project path plus finding `detail` and `sample`
fields. It does not alter scan logic, matching rules, exit status, finding
counts, reachability classification, or commit SHAs.

## Why

The raw hygiene report is useful for local diagnosis, but raw finding samples
can contain the exact local path or secret-like literal that the report is
warning about. A redacted output mode lets agents prepare approval summaries
without copying the sensitive sample back into a public artifact.

## Verification

- JSON output redaction is covered with a temporary repository fixture.
- Text output redaction is covered with the same CLI path.
- Existing current-tree, history, today, and reachability behavior remains
  covered by the public hygiene unit suite.

## Public Hygiene Note

This artifact intentionally describes behavior without embedding raw local path
samples, process IDs, worker IDs, or generated catalog paths.
