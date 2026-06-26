# Post-Stop Guard Baseline Boundary - 2026-06-26

## Scope

This guards the wording boundary between post-stop-guard comparison artifacts
and current final-log close-gate proof artifacts.

## Guarded Contract

- `docs/mcp-usage-guide.md` labels
  `docs/artifacts/robot-rtx-golden-stop-guard-refresh-2026-06-26.md` as a
  baseline post-stop-guard Robot + RTX comparison refresh, not the current
  final-log proof.
- `docs/mcp-usage-guide.md` labels
  `docs/artifacts/official-asset-verify-stop-guard-refresh-2026-06-26.md` as a
  baseline post-stop-guard official verify comparison, not the current final-log
  proof.
- Current repeatable public proof remains anchored on
  `docs/artifacts/robot-rtx-golden-close-gate-live-refresh-2026-06-26.md`,
  `docs/artifacts/robot-rtx-controlled-failure-close-gate-live-refresh-2026-06-26.md`,
  `docs/artifacts/official-asset-verify-close-gate-live-refresh-2026-06-26.md`,
  and `docs/artifacts/official-asset-readonly-close-gate-live-refresh-2026-06-26.md`.
- `tests/unit/test_doc_references.py` asserts that the older "current
  post-stop-guard ... proof/refresh" wording does not return.

## Public Boundary

This artifact records only relative documentation paths and public-safe rule
text. It excludes local absolute paths, local capture paths, process IDs,
worker/thread IDs, secrets, raw logs, and generated catalog/cache records.

## Verification

- Initial full-unit verification caught that this boundary artifact was being
  misclassified as a stop-guard proof artifact because its filename contains
  `stop-guard`. `tests/unit/test_doc_references.py` now excludes `-boundary-`
  docs from close-metadata proof checks while still requiring close metadata for
  real stop/close proof artifacts.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: `3 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_stop_guard_artifacts_record_close_metadata tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed after the classification fix: `4 passed`.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `946 passed, 16 skipped`.
- `git diff --check` passed.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
