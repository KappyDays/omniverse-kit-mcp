# Scenario Markdown List Escaping

Date: 2026-06-23

## Scope

Scenario Markdown reports now apply the same inline newline folding to Data
Summary Highlights, Retry Failures, and Artifacts sections. Step ids and
artifact paths in Markdown code spans use a delimiter that can safely contain
literal backticks.

This keeps quick triage readable when a diagnostic value or artifact path
contains newline text or a backtick-like token.

This batch also isolates the Markdown `scenario_validate` registration test so
its synthetic YAML is written under `tmp_path` instead of the repo's default
`scenarios/` directory.

## Verification

- Added unit coverage for:
  - a Data Summary Highlight value containing a newline
  - a step id containing a backtick
  - an artifact path containing a backtick and newline
  - Markdown scenario validation using a temporary `SCENARIOS_DIR`

## Live Evidence

No live Kit smoke was required. This is a pure reporter-formatting update for
already captured scenario summaries.
