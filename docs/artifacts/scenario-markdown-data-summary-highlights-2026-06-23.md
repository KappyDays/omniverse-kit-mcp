# Scenario Markdown Data Summary Highlights

Date: 2026-06-23

## Scope

Scenario report formatting improvement for robot / RTX sensor workflow triage.
The behavior under validation is `scripts/run_scenario_standalone.py` Markdown
output, which is printed after the unchanged JSON report.

## Result

Markdown scenario reports now include `Data Summary Highlights` for steps whose
bounded `data_summary` contains diagnostic fields.

Verified highlighted fields:

- Lidar: `num_points`, `backend`, `frames_waited`, `raw_keys`, `warning`,
  `truncated`
- Timeline: nested `status.timeline_settled`,
  `status.timeline_settle_updates`, `status.is_playing`, `status.is_stopped`
- Capture: nested `artifact.path`, nested `artifact.sha256`, and capture
  assertion `passed`

JSON report shape is unchanged.

## Static Evidence

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `33 passed`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - tool catalog regenerated and matched committed output
  - registration + catalog-sync tests: `27 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `686 passed, 15 skipped`
- `git diff --check`
  - no whitespace errors; Git reported existing CRLF normalization warnings only

## Live Evidence

No live Isaac Sim smoke was run for this batch. The change formats an existing
`ScenarioRunSummary` into Markdown and does not call Kit, mutate the stage, or
change the JSON result shape. The prior golden workflow live proof remains the
behavioral evidence for the captured lidar, timeline, and viewport fields.
