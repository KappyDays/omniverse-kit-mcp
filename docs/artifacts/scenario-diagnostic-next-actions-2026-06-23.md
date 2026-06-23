# Scenario Diagnostic Next Actions

Date: 2026-06-23

## Change

Scenario Markdown reports now add a `Diagnostic Next Actions` section when
step or retry diagnostics contain `suggested_next` or `fallback_tool_order`.

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
  retry behavior, live stage state, or JSON report shape.

## Public Hygiene Note

This artifact uses only generic field names and no host-local paths, process
IDs, worker IDs, or raw capture/cache paths.
