# RTX Lidar Diagnostics Suggestion Coverage - 2026-06-23

## Scope

Strengthen unit evidence for the RTX lidar empty-read diagnostics used by the
robot + RTX sensor golden workflow.

## Contract

`sensor_lidar_get_point_cloud` empty-read diagnostics must guide the agent
toward the right next action:

- Empty scan / not spun up / unknown empty data -> keep simulation playing, step
  more frames, keep scan targets near the lidar plane, then retry an idempotent
  read.
- Readback unavailable -> inspect the RTX sensor stack and extension logs.
- Payload parse or unsupported payload -> capture raw keys/backend and inspect
  the Kit lidar payload shape.
- Non-empty results must not include empty-read guidance.

## Validation Results

Completed validation:

- `.venv\Scripts\python.exe -m pytest tests\unit\test_sensor_ext_tools.py -q` - 17 passed.
- `.venv\Scripts\python.exe scripts\verify_mcp_sync.py` - OK, 32 passed.
- `.venv\Scripts\python.exe -m pytest tests\unit\ -q` - 721 passed, 16 skipped.

Live Isaac Sim validation is not required for this batch because it only adds
unit coverage for existing diagnostics helper behavior.
