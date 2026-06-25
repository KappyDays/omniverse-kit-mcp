# Scenario Authoring Fallback CLI Quoting

Date: 2026-06-26

## Boundary

`probe_mcp_surface.py` JSON-decodes `--expect-live-diagnostic-field` values when
possible. New agents should copy fallback-order assertions in CLI-ready form:

```powershell
--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.fallback_tool_order='["simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]'
--expect-live-diagnostic-field search_known_miss:diagnostics.fallback_tool_order='["official_asset_sync_status","official_asset_search","official_asset_resolve","official_asset_verify","asset_search"]'
```

The older prose-only shape `diagnostics.fallback_tool_order=[tool, tool]` is not
specific enough for copy/paste live proof commands.

## Evidence

- `scenarios/CLAUDE.md` now uses CLI-ready JSON-quoted fallback arrays in the
  Robot + RTX controlled-failure and official read-only catalog diagnostics
  authoring gates.
- `tests/unit/test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order`
  now asserts both JSON-quoted fallback arrays remain present in the scenario
  authoring guide.

## Checks

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order -q`
  - Result: `1 passed`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
  - Result: passed.
