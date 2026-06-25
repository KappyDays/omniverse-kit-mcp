# Robot RTX Success Result-Shape Guard

Date: 2026-06-26

Scope: unit guard for the current public Robot + RTX close-gate success proof
artifact after the live workflow had already passed in
`docs/artifacts/robot-rtx-golden-close-gate-live-refresh-2026-06-26.md`.

## Guarded Contract

- `tests/unit/test_doc_references.py` now asserts that the current success
  artifact keeps the live result shape as `passed_steps=32`, `failed_steps=0`,
  `continued_steps=0`, `fatal_failed_steps=0`, and `cleanup_failed_steps=0`.
- The same guard keeps the success proof anchored to all three expected
  evidence kinds: `rtx_lidar_point_cloud`, `viewport_framing`, and
  `visual_capture`.
- The guard preserves the public evidence distinction between the durable
  minimum assertion `read_lidar_point_cloud:num_points>=1` and the observed
  replay value `num_points=512`.
- The guard also keeps the final log-capture close metadata explicit:
  `data.capture_stop_completed=true` and
  `data.capture_stop_timed_out=false`.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests\unit\test_doc_references.py::test_f3b_robot_rtx_success_artifact_commands_parse -q`
  passed: `2 passed in 0.05s`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `936 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
