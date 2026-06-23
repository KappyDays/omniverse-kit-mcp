# Scenario Report Evidence Summary - 2026-06-24

## Scope

`scenario_last_report` JSON/Markdown now surfaces a compact `evidence_summary`
for executed steps that produced lidar point-cloud, viewport-framing, or visual
capture evidence. This lets an agent compare `scenario_plan.evidence_steps`
with the executed report before claiming the robot + RTX sensor workflow is
proven.

No live Kit app was launched for this batch. The change is a static reporter
shape improvement over the already live-smoked golden workflow.

## Robot + RTX Report Evidence

The unit-backed golden workflow report now exposes:

- `read_lidar_point_cloud`: `evidence_kind=rtx_lidar_point_cloud`,
  `status=passed`, `attempts=1/3`, `num_points=3`,
  `backend=omni.replicator.core`, `frames_waited=180`,
  `empty_reason=null` in JSON, `warning=null`, `truncated=false`
- `frame_robot_and_sensors`: `evidence_kind=viewport_framing`,
  `status=passed`, `camera_path=/OmniverseKit_Persp`, `prim_count=4`,
  `bbox_empty=false`
- `capture_visible_result`: `evidence_kind=visual_capture`,
  `status=passed`, redaction-compatible `capture_path`, `sha256=abc123`,
  `passed=true`

## Public Review Fixes

This batch also fixed two review findings before push:

- Inline `worker_thread_id=...` text is redacted by
  `scenario_last_report(..., redact_local_paths=true)`.
- `official_asset_verify` material timeout diagnostics now report unexecuted
  material checks as `unknown` instead of implying success.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_routes_through_runner -q`
  - `1 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `51 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_asset_module.py -q`
  - `49 passed`
- `.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\scenario\reporters.py tests\unit\test_scenario_integration.py`
  - passed
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - passed, catalog already up-to-date
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py tests\unit\test_doc_integrity.py tests\unit\test_public_repo_hygiene.py -q`
  - `37 passed, 2 skipped`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `766 passed, 16 skipped`

## Public Hygiene

This artifact contains no live worker IDs, account data, local absolute paths,
process IDs, raw Kit logs, or unredacted generated catalog paths.

- Pending push range public hygiene:
  `review_public_hygiene.py --base origin/main --head HEAD --format json --redact-samples`
  reported `finding_count=0`.
- 2026-06-24 session public hygiene:
  `review_public_hygiene.py --date 2026-06-24 --head HEAD --format json --redact-samples`
  reported `finding_count=0`.
- Pre-existing 2026-06-23 public history audit still reports seven
  `already_public` redacted findings outside this batch; normal push remains
  blocked until the user approves the public-history remediation plan.
