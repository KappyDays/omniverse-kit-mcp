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

## Public Boundary

No raw local absolute paths, local capture paths, worker/thread IDs, process
IDs, secrets, raw Kit logs, generated catalog records, or private workspace
state are included. This artifact records only the public route-table boundary
and the targeted doc-reference guard.
