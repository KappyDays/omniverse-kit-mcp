# Current vs Baseline Artifact Boundary

Date: 2026-06-26

Scope: documentation guard for usage-guide wording that distinguishes older
public-safe baseline evidence from current repeatable close-gate proof.

## Guarded Contract

- `docs/mcp-usage-guide.md` now labels the 2026-06-25 Robot/RTX and official
  asset live-pass files as baseline public-safe evidence, not current
  repeatable proof.
- The current repeatable Robot/RTX proof remains the 2026-06-26 final-log
  close-gate artifact plus its result-shape guard.
- The current repeatable official asset proof remains the 2026-06-26 final-log
  close-gate artifact plus its result-shape guard.
- `tests/unit/test_doc_references.py` asserts the baseline wording and the
  current close-gate ordering so a new agent does not promote historical
  baseline artifacts over the current proof path.

## Public Boundary

This artifact records only relative documentation paths, public artifact names,
and rule text. It excludes local absolute paths, process IDs, worker/thread
IDs, secrets, raw logs, local capture paths, and generated catalog records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: `3 passed in 0.24s`.
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
