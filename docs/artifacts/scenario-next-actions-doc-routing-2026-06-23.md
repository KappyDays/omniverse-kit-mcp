# Scenario Next Actions Doc Routing

Date: 2026-06-23

## Change

The scenario usage docs now route agents to action-oriented report fields before
opening logs or changing robot/RTX timing:

- JSON: `diagnostic_next_actions`,
  `step_results[].diagnostic_next_actions`, and
  `step_results[].retry_failures[].diagnostic_next_actions`.
- Markdown: `Diagnostic Next Actions`, followed by `Data Summary Highlights`.

## Rationale

The report serializer exposes bounded next-action payloads when diagnostics
carry `suggested_next` or `fallback_tool_order`. The docs should point agents
to those fields first so robot/RTX/official-asset triage starts from structured
evidence rather than message strings or console logs.

## Verification

- Documentation-only change; no live stage mutation required.
- Target checks: doc integrity/reference tests and public hygiene gate.

## Public Hygiene Note

This artifact contains only field names and workflow guidance. It does not
include local paths, worker IDs, process IDs, logs, or generated catalog paths.
