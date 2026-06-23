# Standalone Workspace Env + RTX Lidar Live Smoke - 2026-06-23

## Trigger

While attempting the next live RTX lidar diagnostics pass from
`workspaces/isaac/instance-1`, `scripts/run_process_module_standalone.py start`
resolved `kit_exe` to the profile default `C:/IsaacSim/kit/kit.exe` and failed
with `FileNotFoundError: [WinError 2]`.

This was a bounded regression validation exception for the standalone helper
itself, not an ordinary app-launch workflow; normal live work should still use
the workspace-local MCP worker and `kit_app_start`.

Root cause: the standalone scripts were executed from the workspace directory,
so pydantic-settings looked for `.env` in that cwd and did not load the repo
root `.env` containing the verified Isaac Sim 6.0 install path.

## Fix

- `scripts/run_process_module_standalone.py`: chdir to `PROJECT_ROOT` before
  creating `AppConfig()`.
- `scripts/run_scenario_standalone.py`: chdir to `PROJECT_ROOT` before
  creating `AppConfig()`.
- Added `tests/unit/test_standalone_scripts.py` cwd guards for both scripts.

## Validation

- Workspace-cwd config check from `workspaces/isaac/instance-1`:
  - `effective_kit_exe`: `<local-kit-install>/kit/kit.exe`
  - `effective_kit_file`: `<local-kit-install>/apps/isaacsim.exp.full.kit`
  - `ext_port`: `8111`
- Focused tests:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_standalone_scripts.py tests\\unit\\test_config_multi_app.py tests\\unit\\test_process_module_multi_app.py -q`
  - Result: `38 passed`
- `git diff --check`: no whitespace errors; CRLF conversion warnings only.

## Live Smoke

Executed from `workspaces/isaac/instance-1` with
`ISAAC_MCP_APP_PROFILE=isaac-sim` and `ISAAC_MCP_INSTANCE_ID=1`.

- Start:
  - Result: `ok=true`, `status=started`, `ext_port=8111`, `pid=<process-id>`
  - Startup elapsed: `22.3s`
  - Startup log: `<local-kit-log>/kit_1782189205.log`
- Scenario:
  - Command: `scripts/run_scenario_standalone.py smoke/robot_rtx_sensor_golden_workflow.yaml`
  - Result: `PASSED`, `31 passed / 0 failed / 0 skipped`
  - Duration: `20509ms`
  - Lidar step: `read_lidar_point_cloud`
    - `num_points=512`
    - `backend=omni.replicator.core`
    - `frames_waited=60`
    - `truncated=true`
    - `warning=null`
    - `empty_reason=null`
    - `diagnostics.cached_lidar_instance=true`
    - `diagnostics.readback_paths_attempted=["cached_lidar_sensor","replicator_annotator"]`
  - Viewport capture:
    - Path: `<validation-api-capture>/capture_3f1cfaca4517.png`
    - SHA256: `4886170c74ed80f4164f6c48a81e3c65a43b0cb63e3d02f84a3623e352f3cb3b`
    - Pixel mean average: `145.6030591724537`
    - Pixel variance average: `1108.1403259124702`
- Stop:
  - Result: `ok=true`, `status=stopped`, `pid=<process-id>`
- Post-run:
  - `Get-Process -Name kit` returned no running process.

## Residual Risk

This smoke proved the success-path diagnostics shape. The zero-point
`empty_reason` classifications remain unit-backed; they should be observed in
future live failure captures if an RTX lidar buffer returns zero points.
