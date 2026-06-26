# Dry-Run Live-Proof Boundary

Date: 2026-06-26

Scope: durable documentation guard for the rule that dry-run-only scenario
output can validate plan shape, but cannot be cited as Robot/RTX or official
asset live proof.

## Guarded Contract

- `docs/invariants/scenario-validation.md`, `scenarios/CLAUDE.md`, and
  `docs/mcp-usage-guide.md` now say: "Dry-run-only output is plan proof, not
  live proof."
- The guarded rule forbids citing `evidence_summary`, live status, cleanup
  count, or diagnostic fields as evidence unless a later non-dry-run
  `scenario_validate` ran through `--scenario-validate-live` with matching
  `--expect-live-*` assertions.
- `tests/unit/test_doc_references.py` asserts the boundary sentence and the
  required `--scenario-validate-live` / `--expect-live-*` anchors remain present
  in the invariant, scenario authoring guide, and usage guide.
- `scripts/CLAUDE.md` keeps the probe row split between dry-run-only
  plan/retry/cleanup expectations without stage mutation and live proof
  assertions gated by `--scenario-validate-live` plus scratch/read-only guards.
- Historical help-output evidence must not be written as a runnable artifact
  command using the probe script path plus `--help`; artifact command parsing
  requires runnable probe commands to include `--workspace`.
- `scenarios/CLAUDE.md` tells authors to check plan fields before mutating live
  runs, so read-only diagnostic live runs are not conflated with scratch-stage
  proofs.
- Scenario authoring wording refresh:
  - `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_artifact_probe_commands_parse -q`
    passed: `2 passed in 0.31s`.
  - `rg -n "before live runs|check these before live runs" scenarios\CLAUDE.md tests\unit\test_doc_references.py`
    returned no matches.

## Public Boundary

This artifact records only relative documentation paths, public option names,
and rule text. It excludes local absolute paths, process IDs, worker/thread
IDs, secrets, raw logs, local capture paths, and generated catalog records.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: `2 passed in 0.09s`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_official_asset_usage_guide_links_current_public_evidence_artifact tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: `3 passed in 0.28s`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_artifact_probe_commands_parse tests\unit\test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order -q`
  passed: `2 passed in 0.09s`.
- `rg -n "without live stage mutation" scripts docs\mcp-usage-guide.md docs\invariants scenarios tests\unit\test_doc_references.py`
  returned no matches.
- `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
  passed.
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
  `37 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
  `945 passed, 16 skipped`.
- `git diff --check` passed with only existing CRLF normalization warnings for
  touched text files.
- `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
  passed.
