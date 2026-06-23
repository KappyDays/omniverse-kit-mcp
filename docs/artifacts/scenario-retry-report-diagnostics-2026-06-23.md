# Scenario Retry Report Diagnostics (2026-06-23)

## Change

- Scenario step reports now include retry execution metadata:
  - `attempts`
  - `max_attempts`
  - `retry_failures`
- `retry_failures` records compact failed-attempt diagnostics: attempt number,
  status, error code, and message.
- A retry guard failure that prevents execution reports `attempts=0` and the
  declared `max_attempts`.
- Skipped steps report `attempts=0`, while hard timeout/error paths keep the
  configured `max_attempts` and include bounded retry-failure diagnostics when
  a retry policy was declared.

## Why

The robot + RTX sensor golden workflow intentionally retries idempotent lidar
point-cloud reads to absorb transient zero-point RTX buffers. Before this
change, a step that passed after retry looked the same as a first-attempt pass
in `scenario_last_report`, hiding useful live diagnostics from agents.

## Expected Report Shape

For a transient lidar empty-buffer read that passes on the second attempt:

```json
{
  "step_id": "read_lidar",
  "status": "passed",
  "attempts": 2,
  "max_attempts": 2,
  "retry_failures": [
    {
      "attempt": 1,
      "status": "failed",
      "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
      "message": "..."
    }
  ]
}
```

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_scenario_integration.py -q`
  - `29 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\ -q`
  - `680 passed, 15 skipped`
- `.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py`
  - `25 passed`
- `git diff --check`
  - passed with LF-to-CRLF working-copy warnings only
- Targeted assertions cover:
  - transient lidar empty-buffer failure passing on attempt `2/2`
  - `retry_failures[0].error_code=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
  - JSON `scenario_last_report` shape
  - Markdown scenario report `Attempts` column and `Retry Failures` section
  - unsafe non-idempotent retry declarations reporting `attempts=0`
  - skipped retry steps reporting `attempts=0`
  - hard timeout/error paths preserving retry context
  - long retry failure messages being truncated
