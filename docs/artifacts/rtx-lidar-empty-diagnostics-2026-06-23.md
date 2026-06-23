# RTX Lidar Empty Diagnostics Contract - 2026-06-23

## Scope

- Added structured `empty_reason` and `diagnostics` fields to `sensor_lidar_get_point_cloud` results.
- Preserved existing `warning`, `raw_keys`, `backend`, `frames_waited`, and `min_points` / `fail_on_warning` behavior.
- Updated scenario Markdown highlights to show non-null `empty_reason` and `diagnostics.suggested_next` while avoiding `empty_reason=null` noise on passing reads.

## Empty Reason Codes

- `empty_scan_buffer`: scan payload was present but reported zero elements.
- `not_spun_up`: readback returned empty/no-points-yet data, usually before enough timeline updates.
- `no_usable_point_data`: payload had data but no extractable XYZ rows.
- `readback_unavailable`: Replicator / RTX readback path failed.
- `payload_parse_failed`: known payload parse/extraction failed.
- `unsupported_payload`: Kit returned an unsupported non-dict or unknown payload shape.
- `unknown_empty`: zero points with no more specific signal.

## Validation

- Focused tests: `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_sensor_tools.py tests\\unit\\test_sensor_ext_tools.py tests\\unit\\test_scenario_integration.py::test_scenario_runner_retries_transient_lidar_read_failure -q`
  - Result: `25 passed`
- Full unit tests: `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\ -q`
  - Initial result: `1 failed, 692 passed, 15 skipped` because `scenarios/CLAUDE.md` exceeded the sub-CLAUDE hardcap by one line after the doc update.
  - Follow-up result after wrapping fix: `693 passed, 15 skipped`
- Tool sync: `.\\.venv\\Scripts\\python.exe scripts\\verify_mcp_sync.py`
  - Registration + catalog tests: `32 passed`
  - Exit: failed before commit only because `docs/tool-catalog.md` was stale and regenerated; include the generated catalog diff in the commit.
- Whitespace: `git diff --check`
  - Result: no whitespace errors; Git reported CRLF conversion warnings only.

## Live Evidence

No live Isaac Sim smoke was run in this batch. The change is an MCP/extension result-shape and report-format contract update with unit coverage; the next live robot/RTX workflow smoke should inspect `empty_reason` and `diagnostics.suggested_next` if a zero-point read occurs.
