# Scenario Redaction Helper Direct Guard - 2026-06-26

## Scope

This records a direct unit guard for the scenario report redaction helper used
by public `scenario_validate` and `scenario_last_report` evidence paths.

## Guarded Contract

- `_redact_local_paths` recursively redacts tuple/list/dict payloads.
- Validation API capture paths become `<validation-api-capture>/...`.
- Kit temp log paths become `<local-kit-log>/...`.
- Windows user-home paths and sanitized Windows user-path slugs become
  `<local-user-path>`.
- Process ID keys such as `pid` and `child_pids` become `<process-id>`.
- Worker/thread keys such as `threadIds` and `pendingWorktreeIds` become
  `<worker-thread-id>`.
- Inline message text redacts `pid`, `process_id`, `thread_id`, and
  `pendingWorktreeId` values.

## Public Boundary

This artifact records only placeholder names and public-safe rule text. It
excludes local absolute paths, local capture paths, process IDs, worker/thread
IDs, secrets, raw logs, and generated catalog/cache records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_redact_local_paths_handles_nested_runtime_identifiers tests\unit\test_scenario_integration.py::test_reporters_can_redact_host_local_artifact_paths tests\unit\test_scenario_integration.py::test_official_verify_evidence_summary_redacts_public_sensitive_fields -q`
  passed: `3 passed`.
- `.\.venv\Scripts\ruff.exe check tests\unit\test_scenario_integration.py`
  passed.
