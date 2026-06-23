# Scenario MCP Markdown Report Format

Date: 2026-06-23

## Scope

Expose the Markdown scenario report through MCP tools, not only through
`scripts/run_scenario_standalone.py`.

## Result

- `scenario_validate(..., report_format="markdown")` returns the Markdown
  report for the just-executed scenario.
- `scenario_last_report(report_format="markdown")` returns the latest cached
  Markdown report, or a named cached report with
  `scenario_last_report(scenario_id=..., report_format="markdown")`.
- Default `report_format="json"` is unchanged for both tools.
- `report_format="md"` is accepted as an alias for Markdown.
- Unknown report formats return a JSON error instead of throwing a tool
  exception.

## Verification Scope

This batch changes Python MCP wrapper/report formatting only. It does not add a
new tool, call Kit, mutate a stage, or change the scenario JSON report shape.
Live Isaac Sim smoke is therefore not required; `verify_mcp_sync.py` and unit
tests are the validation gates.

## Static Evidence

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py::test_scenario_last_report_defaults_to_latest tests\unit\test_tools_registration.py::test_scenario_last_report_can_return_markdown tests\unit\test_tools_registration.py::test_scenario_last_report_rejects_unknown_format tests\unit\test_tools_registration.py::test_scenario_last_report_no_latest_error -q`
  - `4 passed`
- Review follow-up coverage:
  - `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py::test_scenario_validate_can_return_markdown tests\unit\test_tools_registration.py::test_scenario_validate_rejects_unknown_format -q`
  - `3 passed`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - regenerated `docs/tool-catalog.md`
  - registration + catalog-sync tests: `29 passed`
  - exit code `1` because the generated catalog changed and must be committed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py::test_a4_sub_hardcap -q`
  - `1 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py -q`
  - `25 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - first run found `scenarios/CLAUDE.md: 151 > 150`; fixed by folding the
    report examples
  - rerun: `688 passed, 15 skipped`
- `git diff --check`
  - no whitespace errors; Git reported existing CRLF normalization warnings only
