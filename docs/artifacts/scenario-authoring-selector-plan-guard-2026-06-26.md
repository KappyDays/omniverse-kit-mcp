# Scenario Authoring Selector Plan Guard

Date: 2026-06-26

Scope: static guard that scenario authoring guidance selectors still match the
compiled scenario plans used by Robot + RTX and official asset proof workflows.

## Guarded Contract

- Robot + RTX authoring selectors in `scenarios/CLAUDE.md` must remain backed by
  `scenarios/smoke/robot_rtx_sensor_golden_workflow.yaml` evidence steps:
  `read_lidar_point_cloud`, `frame_robot_and_sensors`, and
  `capture_visible_result`.
- Robot + RTX authoring evidence kinds must remain backed by compiled
  `evidence_steps`: `rtx_lidar_point_cloud`, `viewport_framing`, and
  `visual_capture`.
- Official asset live proof guidance must continue to use the
  `official_asset_verify` evidence kind from
  `smoke/official_asset_verify_live.yaml`.
- Official asset read-only diagnostic guidance must continue to use diagnostic
  step IDs from `smoke/official_asset_catalog_diagnostics.yaml`:
  `search_known_miss` and `get_pallet_wrong_profile`.

## Public Boundary

This artifact records only relative scenario/documentation paths, public step
IDs, evidence kinds, and rule text. It excludes local absolute paths, process
IDs, worker/thread IDs, secrets, raw logs, local capture paths, and generated
catalog records.

## Verification

- `python -m pytest tests/unit/test_doc_references.py::test_f3b_scenario_authoring_selectors_match_compiled_plans tests/unit/test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts tests/unit/test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: 3 tests.
- `python -m ruff check tests/unit/test_doc_references.py` passed.
- `python scripts/verify_mcp_sync.py` passed: registration/catalog sync green,
  37 tests.
- `python -m pytest tests/unit/ -q` passed: 945 tests, 16 skipped.
- `git diff --check` passed.
- `python scripts/review_public_hygiene.py --redact-samples` passed.
