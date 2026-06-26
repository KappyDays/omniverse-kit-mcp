# Official Asset Current Proof Anchor Boundary

Date: 2026-06-26

Scope: documentation guard for the official asset pull-doc boundary between
current repeatable public proof anchors and older baseline evidence.

## Guarded Contract

- `docs/references/official-asset-catalog.md` labels the 2026-06-26
  close-gate official verify and read-only diagnostics artifacts as the current
  repeatable public proof anchors.
- Older stop-guard and live-pass artifacts linked from
  `docs/mcp-usage-guide.md` are historical or baseline public-safe evidence,
  not the current repeatable proof path.
- `docs/mcp-usage-guide.md` links this guard next to the current official asset
  close-gate proof and result-shape guard.
- `tests/unit/test_doc_references.py` asserts the pull-doc wording so new
  agents do not promote baseline evidence over the current close-gate path.
- The current anchor set is paired with
  `docs/artifacts/official-asset-pass-error-code-boundary-2026-06-26.md` and
  `docs/artifacts/probe-live-assertion-cli-boundary-2026-06-26.md` so the
  successful `official_asset_verify` pass row stays
  `official_asset_verify:error_code=...` free, while failed evidence rows use
  concrete `step_id` selectors for `error_code` and dotted nested diagnostics
  such as `verify_timeout_asset:diagnostics.error_type=TimeoutError`.
- The post-assertion live proof refreshes are also part of the current anchor
  set: `docs/artifacts/official-asset-verify-live-probe-refresh-2026-06-26.md`
  for mutating load-quality proof and
  `docs/artifacts/official-asset-readonly-diagnostic-live-probe-refresh-2026-06-26.md`
  for read-only diagnostic proof.

## Public Boundary

This artifact records only relative documentation paths, public artifact names,
and rule text. It excludes local absolute paths, process IDs, worker/thread IDs,
secrets, raw logs, local capture paths, and generated catalog records.

## Verification

- Initial targeted pytest caught a public-boundary wording mismatch because the
  new artifact split `worker/thread IDs` across a line break. The artifact text
  was fixed without weakening the shared artifact contract.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed after the fix: `3 passed in 0.04s`.
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
