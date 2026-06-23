# Scenario Diagnostic Next-Action Metadata - 2026-06-24

## Improvement

`scenario_last_report` JSON now keeps routing metadata on the top-level
`diagnostic_next_actions` queue:

- `phase`
- source `status`
- source `error_code`
- retry `attempt`
- `final_step_status` for retry failures

The per-step and per-retry `diagnostic_next_actions` payloads remain focused on
diagnostic content such as `suggested_next`, `fallback_tool_order`,
`empty_reason`, and official asset check dictionaries.

## Why This Matters

Robot + RTX sensor and official asset workflows can pass after an idempotent
retry while still preserving a failed attempt that explains what happened. The
top-level queue now lets an agent connect the recommended next tool order to the
failing phase, retry attempt, and error code without first walking the full
`step_results` tree.

## Evidence

Targeted unit coverage now checks:

- step-level official asset diagnostics still keep structured next-action
  payloads.
- retry-level RTX lidar diagnostics preserve `attempt`, failed source
  `status`, source `error_code`, and `final_step_status`.

Public report guidance was updated in:

- `docs/mcp-usage-guide.md`
- `docs/invariants/scenario-validation.md`
