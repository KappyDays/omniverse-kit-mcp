# Official Asset Read-Only Dry-Run Wrapper Gate - 2026-06-26

Purpose: close the doc-only gap where the read-only official asset diagnostics
wrapper required `--scenario-validate-dry-run` in canonical probe commands, but
the durable wrapper sequence omitted the explicit
`scenario_validate(..., dry_run=true)` step before `extension_clear_logs`.

## Commands

- Red check before the docs fix:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order -q`
- Workspace-local read-only dry-run probe:
  `.\.venv\Scripts\python.exe scripts\probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --scenario-validate-dry-run --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true`
- Green check after the docs fix:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order -q`

## Result

- The first targeted test failed because `docs/mcp-usage-guide.md` was missing
  `scenario_validate(smoke/official_asset_catalog_diagnostics.yaml, dry_run=true)`
  in the read-only wrapper sequence.
- The wrapper sequence is now fixed in `docs/mcp-usage-guide.md` and
  `docs/invariants/scenario-validation.md`: `scenario_plan` -> dry-run
  `scenario_validate` -> `extension_clear_logs` -> live `scenario_validate`.
- The docs now also distinguish the plan-level `--require-live-validation-tools`
  list from the CLI-level dry-run gate: the read-only live checklist has one
  live `scenario_validate` after `extension_clear_logs`, while
  `--scenario-validate-dry-run` remains mandatory for the probe wrapper.
- The mutating `stage_mutation_summary.read_only=false` gate is now named as
  the load-quality live proof gate, not a generic read-only diagnostics rule.
- Load-quality/read-only wording refresh:
  - `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_artifact_probe_commands_parse -q`
    passed: `2 passed in 0.33s`.
  - `rg -n "Before live execution" docs\mcp-usage-guide.md docs\invariants\scenario-validation.md tests\unit\test_doc_references.py`
    returned no matches.
- Current refresh checks:
  - `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py::test_f3b_official_asset_scenario_proof_wrapper_order tests\unit\test_doc_references.py::test_f3b_usage_guide_probe_commands_parse tests\unit\test_doc_references.py::test_f3b_artifact_probe_commands_parse -q`
    passed: `3 passed in 0.13s`.
  - `.\.venv\Scripts\python.exe -m ruff check tests\unit\test_doc_references.py`
    passed.
  - `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py` passed:
    `37 passed`.
  - `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q` passed:
    `946 passed, 16 skipped`.
  - `git diff --check` and
    `.\.venv\Scripts\python.exe scripts\review_public_hygiene.py --redact-samples`
    passed.
- The workspace-local dry-run probe exited 0.
- Runtime gate fields were fresh: `tool_profile=full`,
  `app_profile=isaac-sim`, `tool_count=152`,
  `source_newer_than_import=false`, and
  `restart_required_for_latest_mcp_code=false`.
- The plan and dry-run both reported `scenario_id=official_asset_catalog_diagnostics`,
  `total_steps=5`, `diagnostic_steps=true`, `stage_mutation_steps=true`,
  `live_validation_step_count=8`, `scratch_stage_required=false`, and
  `log_capture_recommended=true`.
- The generated `tmp_mcp_surface.json` snapshot is ignored and was not promoted
  as public evidence.

## Public Boundary

This artifact records only stable commands and compact plan/dry-run summaries.
No local absolute paths, worker/thread IDs, process IDs, secrets, raw Kit logs,
generated catalog records, or capture paths are included.
