# Scenario Report Runtime Field Redaction

Date: 2026-06-26

Scope: unit evidence that public-safe scenario reports redact runtime
identifiers in both JSON and Markdown report forms.

## Guarded Fields

`tests/unit/test_tools_registration.py::test_scenario_last_report_can_redact_local_paths`
now covers:

- local validation capture paths
- `process_id`
- nested `child_pids`
- `worker_thread_id`
- nested `pending_worktree_id`

The redacted JSON and Markdown outputs must include `<process-id>` and
`<worker-thread-id>` while excluding the raw fixture identifiers.

## Evidence

- Targeted command:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_tools_registration.py::test_scenario_last_report_can_redact_local_paths tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts -q`
- Targeted result: `2 passed`.

## Public Boundary

- Static/unit validation only.
- No live scenario was run and no stage was mutated.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, Kit
  logs, generated catalog records, or capture paths are included.
