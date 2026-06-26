# New-Agent Route Table Pull-Doc Boundary - 2026-06-26

Purpose: document the docs-only route-table fix that lets a fresh agent start
from root `CLAUDE.md` or `docs/mcp-usage-guide.md` and find the scenario
validation invariant plus scenario authoring guide before attempting Robot + RTX
or official asset live proofs.

## Change

- The official asset task route now points to
  `docs/invariants/scenario-validation.md` and `scenarios/CLAUDE.md` in addition
  to the official catalog and asset-discovery docs.
- The official asset task route now pins `scenario_plan` before
  `scenario_validate(..., dry_run=true)` before the live `scenario_validate(...)`
  call for both `smoke/official_asset_verify_live.yaml` and
  `smoke/official_asset_catalog_diagnostics.yaml`.
- In assertion wording: official asset task route now pins scenario_plan before
  dry-run before explicit live `scenario_validate(<scenario>.yaml)`.
- The Robot + RTX golden-path task route now points to `scenarios/CLAUDE.md`
  alongside `docs/invariants/scenario-validation.md` and the integration facts.
- The Robot + RTX golden-path task route now also pins `scenario_plan` before
  `scenario_validate(..., dry_run=true)` before the live `scenario_validate(...)`
  call, matching the official asset route-table pattern.
- Root `CLAUDE.md` now has explicit Robot + RTX and official asset scenario
  proof rows in the required pull-doc table.
- `tests/unit/test_doc_references.py` guards both route rows so the entry-point
  tables cannot silently drop the durable scenario proof docs.

## Verification

- Targeted validation for this batch is expected to include
  `tests/unit/test_doc_references.py::test_f3b_usage_guide_task_routes_point_to_live_proof_pull_docs`
  and
  `tests/unit/test_doc_references.py::test_f3b_root_claude_routes_live_proofs_to_pull_docs`.
- No live MCP run is required because this is a docs-only entrypoint routing
  fix. The underlying live proof baselines remain the existing Robot + RTX and
  official asset close-gate artifacts.
- Current refresh:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_usage_guide_task_routes_point_to_live_proof_pull_docs tests\unit\test_doc_references.py::test_f3b_root_claude_routes_live_proofs_to_pull_docs tests\unit\test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts -q`
  initially caught that the route row used shorthand live `scenario_validate(...)`
  instead of explicit scenario paths. After fixing the row to use explicit live
  `scenario_validate(smoke/official_asset_catalog_diagnostics.yaml)` and
  `scenario_validate(smoke/official_asset_verify_live.yaml)`, it passed:
  `3 passed in 0.26s`.
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

## Robot Route Dry-Run Refresh

- The Robot + RTX route row was refreshed to make the route-table command order
  explicit: `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)` ->
  `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml, dry_run=true)`
  -> `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)`.
- Targeted validation for the refresh:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_usage_guide_task_routes_point_to_live_proof_pull_docs tests\unit\test_doc_references.py::test_f3b_usage_guide_artifact_links_exist -q`
  passed: 2 tests.
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

## Post-Route Dry-Run Recheck

After the root/usage-guide route rows were tightened, the workspace-local Isaac
Sim MCP entry was rechecked with the three doc-only probe commands. All exited
0 without live stage mutation:

- `smoke/robot_rtx_sensor_golden_workflow.yaml`: `tool_profile=full`,
  `app_profile=isaac-sim`, `tool_count=152`, `source_newer_than_import=false`,
  `restart_required_for_latest_mcp_code=false`, `scratch_stage_required=true`,
  `log_capture_recommended=true`, `live_validation_step_count=9`,
  `play_state_missing_count=0`, and fallback cleanup
  `__fallback_cleanup_reset.timeoutSeconds=30`.
- `smoke/official_asset_verify_live.yaml`: required `diagnostic_steps`,
  `evidence_steps`, and `stage_mutation_steps` were present, with
  `scratch_stage_required=true`, `log_capture_recommended=true`, and
  `live_validation_step_count=9`.
- `smoke/official_asset_catalog_diagnostics.yaml`: required
  `diagnostic_steps` and `stage_mutation_steps` were present, with
  `scratch_stage_required=false`, `log_capture_recommended=true`, and
  `live_validation_step_count=8`.
- The generated `tmp_mcp_surface.json` snapshot remained ignored and was not
  promoted as public evidence.

## Post-Assertion Boundary Recheck

A fresh agent starting only from root `CLAUDE.md` or `docs/mcp-usage-guide.md`
now reaches the current durable proof criteria after following the route-table
pull-docs:

- Robot + RTX success proof gates are documented with
  `--expect-live-evidence-field read_lidar_point_cloud:status=passed`,
  `--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1`,
  `--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false`, and
  `--expect-live-evidence-field capture_visible_result:passed=true`.
- Robot + RTX controlled lidar failure proof remains anchored on
  `--expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
  plus exact diagnostic fields for `diagnostics.reason`,
  `diagnostics.min_points`, and `diagnostics.fallback_tool_order`. Optional
  `read_lidar_point_cloud:error_code=...` evidence assertions do not replace
  the terminal failure-step contract.
- Official asset load-quality pass proof gates are documented with
  `official_asset_verify:verification_status=load_verified`,
  `official_asset_verify:kind=asset`,
  `official_asset_verify:app_profile=isaac-sim`, and
  `official_asset_verify:load_quality=content_verified_no_bbox`.
- The successful official asset pass row is explicitly
  `official_asset_verify:error_code=...` free. Failed or timeout-shaped
  official asset evidence rows must assert row-specific `error_code` and
  public-safe nested diagnostics only with the concrete failed `step_id`
  selector, for example
  `verify_timeout_asset:diagnostics.error_type=TimeoutError`.
- The CLI/report contract for dotted evidence diagnostics remains guarded in
  `docs/artifacts/probe-live-assertion-cli-boundary-2026-06-26.md`, and the
  official asset pass-vs-failed-row `error_code` boundary remains guarded in
  `docs/artifacts/official-asset-pass-error-code-boundary-2026-06-26.md`.
- The latest post-assertion live probe refresh anchors are
  `docs/artifacts/robot-rtx-success-live-probe-refresh-2026-06-26.md`,
  `docs/artifacts/robot-rtx-controlled-failure-live-probe-refresh-2026-06-26.md`,
  `docs/artifacts/official-asset-verify-live-probe-refresh-2026-06-26.md`, and
  `docs/artifacts/official-asset-readonly-diagnostic-live-probe-refresh-2026-06-26.md`.

## Public Boundary

No raw local absolute paths, local capture paths, worker/thread IDs, process
IDs, secrets, raw Kit logs, generated catalog records, or private workspace
state are included. This artifact records only the public route-table boundary,
targeted doc-reference guard, and compact dry-run summaries.
