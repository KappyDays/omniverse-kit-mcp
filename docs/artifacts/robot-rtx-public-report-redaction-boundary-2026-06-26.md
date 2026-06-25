# Robot + RTX Public Report Redaction Boundary Refresh - 2026-06-26

Purpose: document the docs-only fix that makes the Robot + RTX live proof
wrapper's public evidence boundary unambiguous. Public proof uses
`scenario_last_report(report_format="markdown", redact_local_paths=true)`;
raw `scenario_last_report(report_format="markdown")` is local, same-host triage
only.

## Change

- `docs/mcp-usage-guide.md` now lists only the redacted Markdown report in the
  Robot + RTX canonical live proof wrapper.
- The raw Markdown report is explicitly described as private same-host triage
  and not copyable into public artifacts.
- `tests/unit/test_doc_references.py` guards that the wrapper no longer offers a
  raw-or-redacted public choice.

## Verification

- Targeted unit/static checks for this batch are expected to include
  `tests/unit/test_doc_references.py::test_f3b_robot_rtx_live_proof_wrapper_order`
  and
  `tests/unit/test_doc_references.py::test_f3b_robot_rtx_usage_guide_links_current_public_evidence_artifacts`.
- No live MCP run is required because this refresh only tightens documented
  public evidence routing. Existing live close-gate artifacts remain the live
  proof baseline.

## Public Boundary

No raw local absolute paths, local capture paths, worker/thread IDs, process
IDs, secrets, raw Kit logs, or generated catalog records are included. This
artifact records only the durable doc boundary and targeted test expectation.
