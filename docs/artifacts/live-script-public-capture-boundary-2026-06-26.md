# Live Script Public Capture Boundary - 2026-06-26

## Gap

`scripts/CLAUDE.md` told agents to copy captures from `%TEMP%/validation_api_captures/`
into `docs/artifacts/phase-{id}/`, but did not explicitly say which parts of
that raw live output are safe for public artifacts.

## Fix

- `scripts/CLAUDE.md` now says to copy only the PNG payload to a stable
  `docs/artifacts/phase-{id}/...png` name.
- Public notes must not record raw temp paths, Kit log filenames, process IDs,
  or worker/thread IDs.
- Public notes should use redacted scenario reports when available, or script
  output with local paths removed, plus the public hygiene guard.
- `tests/unit/test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order`
  now pins that boundary so future script guidance cannot drift back to raw
  local evidence.

## Checks

- `.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py -q`
  -> 42 passed, 1 skipped.
- `.venv\Scripts\ruff.exe check tests\unit\test_doc_references.py scripts\review_public_hygiene.py`
  -> all checks passed.

## Live Boundary

No live MCP smoke was run for this batch. The change is a docs/test public
artifact boundary only and does not touch runtime behavior or mutate a stage.
