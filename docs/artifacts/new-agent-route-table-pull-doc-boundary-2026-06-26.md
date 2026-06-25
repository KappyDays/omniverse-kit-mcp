# New-Agent Route Table Pull-Doc Boundary - 2026-06-26

Purpose: document the docs-only route-table fix that lets a fresh agent start
from root `CLAUDE.md` or `docs/mcp-usage-guide.md` and find the scenario
validation invariant plus scenario authoring guide before attempting Robot + RTX
or official asset live proofs.

## Change

- The official asset task route now points to
  `docs/invariants/scenario-validation.md` and `scenarios/CLAUDE.md` in addition
  to the official catalog and asset-discovery docs.
- The Robot + RTX golden-path task route now points to `scenarios/CLAUDE.md`
  alongside `docs/invariants/scenario-validation.md` and the integration facts.
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

## Public Boundary

No raw local absolute paths, local capture paths, worker/thread IDs, process
IDs, secrets, raw Kit logs, generated catalog records, or private workspace
state are included. This artifact records only the public route-table boundary,
targeted doc-reference guard, and compact dry-run summaries.
