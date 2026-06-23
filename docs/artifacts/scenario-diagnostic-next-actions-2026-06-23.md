# Scenario Diagnostic Next Actions

Date: 2026-06-23

## Change

Scenario reports now expose action-oriented diagnostics when step or retry
diagnostics contain `suggested_next` or `fallback_tool_order`:

- JSON: top-level and per-step/per-retry `diagnostic_next_actions`.
- Markdown: `Diagnostic Next Actions` section.

This keeps the existing `Data Summary Highlights` and `Retry Failures` sections
intact, but gives agents a smaller action-oriented list to check first when
RTX lidar reads, official asset searches, or app-profile diagnostics fail or
return an empty diagnostic result.

## Covered Fields

- `diagnostics.reason`
- `empty_reason`
- `suggested_next`
- `diagnostics.fallback_tool_order`
- `diagnostics.readback_paths_attempted`

## Validation Plan

- Unit coverage extends the existing official asset diagnostics, sync status
  diagnostics, and transient RTX lidar retry tests.
- The change is report-only and does not alter scenario execution order,
  retry behavior, or live stage state.

## Public Hygiene Note

This artifact uses only generic field names and no host-local paths, process
IDs, worker IDs, or raw capture/cache paths.
