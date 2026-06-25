# Robot RTX Integration Facts Proof Gate

Date: 2026-06-26

Scope: docs/test guard that the Robot + RTX pull-doc route includes exact live
proof assertions in `src/omniverse_kit_mcp/modules/integration-facts.md`, not
only in the usage guide and scenario invariant.

## Guarded Contract

- `src/omniverse_kit_mcp/modules/integration-facts.md` must route Robot + RTX
  proof to `smoke/robot_rtx_sensor_golden_workflow.yaml`.
- Success proof guidance must name the live evidence assertions for lidar
  status, lidar point threshold, viewport framing, and visual capture.
- Controlled-failure guidance must name the `lidar_min_points=513` boundary,
  `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`, diagnostic reason/minimum fields,
  and the exact lidar fallback tool order.

## Public Boundary

This artifact records only relative documentation/scenario paths, public step
IDs, public diagnostic field names, and public tool names. It excludes local
absolute paths, process IDs, worker/thread IDs, secrets, raw logs, local capture
paths, and generated catalog records; no local absolute paths are included.

## Verification

- `python -m pytest tests/unit/test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order tests/unit/test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests/unit/test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: 3 tests.
- `python -m ruff check tests/unit/test_doc_references.py` passed.
- `python scripts/verify_mcp_sync.py` passed: registration/catalog sync green,
  37 tests.
- `python -m pytest tests/unit/ -q` passed: 945 tests, 16 skipped.
- `git diff --check` passed.
- `python scripts/review_public_hygiene.py --redact-samples` passed.
