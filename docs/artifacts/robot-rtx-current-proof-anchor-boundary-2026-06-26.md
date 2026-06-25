# Robot RTX Current Proof Anchor Boundary

Date: 2026-06-26

Scope: documentation guard for the Robot + RTX boundary between current
repeatable close-gate proof anchors and older baseline evidence.

## Guarded Contract

- `docs/invariants/scenario-validation.md` now names the current repeatable
  Robot + RTX public proof anchors:
  `docs/artifacts/robot-rtx-golden-close-gate-live-refresh-2026-06-26.md`,
  `docs/artifacts/robot-rtx-success-result-shape-guard-2026-06-26.md`, and
  `docs/artifacts/robot-rtx-controlled-failure-close-gate-live-refresh-2026-06-26.md`.
- `scenarios/CLAUDE.md` no longer leaves the Robot + RTX authoring gate at
  live status only; it repeats the mandatory success evidence kind/field
  assertions and controlled-failure diagnostic assertions.
- `docs/mcp-usage-guide.md` links this guard next to the existing current-vs-
  baseline Robot + RTX evidence boundary.
- `tests/unit/test_doc_references.py` asserts the strengthened authoring gate,
  invariant proof-anchor wording, and usage-guide artifact link.

## Public Boundary

This artifact records only relative documentation paths, public artifact names,
and rule text. It excludes local absolute paths, process IDs, worker/thread IDs,
secrets, raw logs, local capture paths, and generated catalog records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: `3 passed in 0.05s`.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `944 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
