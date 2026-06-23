# Scenario Official Candidate Count Highlights - 2026-06-23

## Scope

Official asset zero-result diagnostics include `candidate_counts`, but Markdown
scenario reports previously highlighted the reason and recovery tools without
showing the key count transitions. That made profile/filter misses harder to
triage from `scenario_last_report(report_format="markdown")`.

## Fixed Behavior

Scenario Markdown `Data Summary Highlights` now includes:

- `diagnostics.candidate_counts.total_entries`
- `diagnostics.candidate_counts.after_app_profile`
- `diagnostics.candidate_counts.query_matches`

This keeps the report compact while surfacing whether an official asset failure
is caused by catalog emptiness, app-profile filtering, or query mismatch.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_markdown_highlights_nested_diagnostic_reason_and_fallback -q`

No live Isaac Sim stage mutation was needed; this is reporter result-shape
coverage for existing scenario summaries.
