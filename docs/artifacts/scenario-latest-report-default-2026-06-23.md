# Scenario Latest Report Default (2026-06-23)

## Change

- `scenario_last_report()` now returns the most recent `scenario_validate`
  report when `scenario_id` is omitted.
- `scenario_last_report(scenario_id=...)` still returns a named cached report.
- If no scenario has been executed in the current MCP process, the tool returns
  `{"error": "No scenario reports have been recorded"}`.

## Why

`scenarios/CLAUDE.md` already guided agents to call `scenario_last_report()`
after `scenario_validate`, but the tool signature required `scenario_id`. The
no-arg default removes that avoidable workflow mismatch while preserving
explicit lookup.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py::test_scenario_tools_present tests\unit\test_tools_registration.py::test_scenario_last_report_defaults_to_latest tests\unit\test_tools_registration.py::test_scenario_last_report_no_latest_error -q`
  - `3 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_catalog_sync.py -q`
  - `7 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `686 passed, 15 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - `27 passed`; generated `docs/tool-catalog.md` is included in this commit
- `git diff --check`
  - passed with LF-to-CRLF working-copy warnings only
