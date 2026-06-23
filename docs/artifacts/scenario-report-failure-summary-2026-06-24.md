# Scenario Report Failure Summary Evidence - 2026-06-24

## Purpose

Make failed scenario reports easier for agents to triage before opening the full
step table, retry list, or logs.

## Contract

- JSON reports now include top-level `failure_summary`.
- Markdown reports now include `## Failure Summary` before `## Step Results`.
- Each failed/error/timeout row carries the step id, phase, final status,
  attempts, retry failure count, final `error_code`, compact diagnostic data
  highlight when present, and the last retry failure when retries were used.
- Public-safe rendering still goes through `redact_local_paths=true` before
  copying evidence into docs.

## Unit Evidence

Targeted tests cover:

- Markdown escaping for failed step messages and last retry messages.
- Exhausted RTX lidar retry reports preserving the final step failure and the
  last retry diagnostic highlight in `failure_summary`.
- Scenario authoring docs mentioning `failure_summary` and Markdown
  `Failure Summary`.

Validation command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py tests\unit\test_doc_references.py -q
```

Live Isaac Sim was not rerun for this artifact; this batch only changes report
serialization shape over already collected scenario step results.
