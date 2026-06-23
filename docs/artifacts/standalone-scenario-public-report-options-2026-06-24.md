# Standalone Scenario Public Report Options — 2026-06-24

## Objective

Reduce the chance of copying host-local paths or process/thread identifiers from
`scripts/run_scenario_standalone.py` normal-run output into public artifacts.

## Change

- Added `--report-format json|markdown|both|md` to normal standalone scenario runs.
- Added `--redact-local-paths` to pass reporter redaction through standalone
  JSON/Markdown output.
- Preserved the default local-triage behavior: normal runs still print raw
  JSON plus raw Markdown unless a report option is provided.
- Closed the standalone Lakehouse client alongside the Isaac REST client.
- Documented the public-safe command shape:
  `--report-format markdown --redact-local-paths`.

## Evidence

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_standalone_scripts.py tests\unit\test_doc_references.py -q`
  - Result: `22 passed, 1 skipped`
- `.\.venv\Scripts\python.exe -m ruff check scripts\run_scenario_standalone.py tests\unit\test_standalone_scripts.py tests\unit\test_doc_references.py`
  - Result: passed
- `.\.venv\Scripts\python.exe scripts\run_scenario_standalone.py --dry-run --report-format markdown --redact-local-paths --input-overrides-json '{"lidar_min_points":513}' smoke\robot_rtx_sensor_golden_workflow.yaml`
  - Result: exit 0, no REST clients created by dry-run path
  - Plan: `scenario_id=robot_rtx_sensor_golden_workflow`, `total_steps=32`
  - `phase_counts`: arrange=11, act=9, assert=5, cleanup=7
  - `evidence_steps`: `rtx_lidar_point_cloud`, `viewport_framing`,
    `visual_capture`
  - `retry_steps[0].key_args`: `min_points=513`, `max_points=512`,
    `frames_to_wait=180`, `fail_on_warning=true`

## Public Hygiene Notes

The new default remains intentionally raw for local debugging. Use
`--redact-local-paths` before moving standalone output into `docs/artifacts/` or
another public-facing note.
