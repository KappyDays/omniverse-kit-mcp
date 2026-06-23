# Scenario Markdown Table Escaping

Date: 2026-06-23

## Scope

Scenario Markdown reports now escape pipe characters in Step Results table
cells and fold embedded newlines to `<br>`. This prevents module error messages
such as `bridge | retry` or multi-line exception text from breaking the table
that agents use for quick scenario triage.

Retry failure messages are also folded to a single Markdown list item line.

## Verification

- Added unit coverage for a step id and failure message containing `|` plus
  newline text.

## Live Evidence

No live Kit smoke was required. This is a pure reporter-formatting update for
already captured scenario summaries.
