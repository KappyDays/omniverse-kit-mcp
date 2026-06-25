# Probe Live Evidence/Cleanup Assertions — 2026-06-25

Purpose: verify that `scripts/probe_mcp_surface.py` fails live scenario wrapper
proofs when required evidence kinds or cleanup preservation drift.

Command shape:

- Workspace-local stdio entry: `workspaces/isaac/instance-1`
- Scenario: `smoke/robot_rtx_sensor_golden_workflow.yaml`
- Added live expectations:
  - `--expect-live-status passed`
  - `--expect-live-cleanup-failures 0`
  - `--expect-live-evidence-kind rtx_lidar_point_cloud`
  - `--expect-live-evidence-kind viewport_framing`
  - `--expect-live-evidence-kind visual_capture`

Result:

- Exit code: `0`
- Runtime profile: `full`
- App profile: `isaac-sim`
- Tool count: `152`
- Runtime freshness: source/import clean
- Robot probe contract: `ROBOT_PROBE_UNKNOWN_PROFILE` with fallback order present
- Plan/dry-run: required plan fields present; scratch stage required; log capture recommended
- Live summary: `passed`
- Steps: `32` passed, `0` failed, `0` skipped
- Cleanup failed steps: `0`
- Evidence kinds:
  - `rtx_lidar_point_cloud`
  - `viewport_framing`
  - `visual_capture`
- WARN+ log capture (stop_after_capture=true): `passed`

Key live evidence:

- `read_lidar_point_cloud`: `512` points, attempts `1/3`, backend
  `isaacsim.sensors.experimental.rtx.LidarSensor`, warning `null`
- `capture_visible_result`: redacted capture path
  `<validation-api-capture>/capture_0277cf61b7fc.png`
- Capture SHA256:
  `100b1c2aaced1585954e6ae4facfe4e1c3102da5e00d51cf9b22e1771dabe9b1`
- Pixel mean average: `145.71787724247687`
- Pixel variance average: `1101.313644082391`

Visual inspection:

- NovaCarter is visible on the NVIDIA grid.
- Four gray lidar target cubes frame the robot.
- The top lidar is visible on the robot.
- The capture is not blank, black, flat, or off-camera.

Public hygiene:

- Local capture path was recorded only through the redacted
  `<validation-api-capture>/...` placeholder.
- No local absolute paths, process IDs, worker/thread IDs, or secrets are
  included in this artifact.
