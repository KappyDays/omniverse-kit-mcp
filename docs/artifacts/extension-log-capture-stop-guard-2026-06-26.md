# Extension Log Capture Stop Guard - 2026-06-26

Purpose: harden the request-scoped carb log capture close path after a live
official asset diagnostic proof exposed a final `extension_capture_logs`
timeout and then a hung validation endpoint.

Change summary:

- `LogCaptureService.request_stop(timeout_s=1.0)` now performs hook removal in
  a daemon worker and returns bounded stop metadata instead of letting the REST
  request block indefinitely.
- `/extension/logs?stop_after_capture=true` now returns:
  - `capture_stop_requested`
  - `capture_stop_completed`
  - `capture_stop_timed_out`
  - `capture_stop_timeout_s`
  - updated `capture_running`
- MCP `extension_capture_logs` preserves the same metadata in its typed result.
- Durable guidance now tells agents to inspect `data.capture_stop_timed_out` and
  `data.capture_running` before assuming the request-scoped hook closed.

Unit evidence:

- `tests/unit/test_log_capture.py` covers:
  - completed hook stop
  - bounded timeout when fake `remove_logger()` blocks
- `tests/unit/test_extension_module.py` covers MCP preservation of stop
  metadata.
- Targeted result: `18 passed`.
- Full unit result: `920 passed, 16 skipped`.

Live reflection evidence:

- Reflection route: validation_api code change, so workspace-local
  `scripts/run_process_module_standalone.py restart --profile isaac-sim
  --instance 1` was used.
- Restart result: `ok=true`, `status=started`, `caches_cleared=4`.
- Health after restart: `ok=true`, `extension_enabled=true`, `busy=false`.
- Direct request-scoped log close:
  - `ok=true`
  - `capture_running=false`
  - `capture_stop_requested=true`
  - `capture_stop_completed=true`
  - `capture_stop_timed_out=false`
  - `capture_stop_timeout_s=1.0`
- MCP preflight after restart passed:
  `mcp_runtime_info`, `kit_app_start`, `simulation_get_status`,
  `extension_clear_logs`, and `extension_capture_logs`.

Public hygiene:

- This artifact intentionally omits local absolute paths, process IDs, raw Kit
  logs, worker/thread IDs, and secrets.
