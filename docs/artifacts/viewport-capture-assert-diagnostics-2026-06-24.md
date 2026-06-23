# Viewport Capture Assert Diagnostics Evidence - 2026-06-24

## Scope

This batch improves the failure shape for `viewport_capture_assert` and scenario
reports. A blank or flat viewport capture now carries structured diagnostics so
agents can decide whether to re-frame, warm up, adjust lighting, inspect the
artifact, or capture extension logs before changing thresholds.

## Result Shape

Failed `viewport_capture_assert` results now include:

- `diagnostics.reason`
- `diagnostics.failure_codes`
- `diagnostics.pixel_mean_average`
- `diagnostics.pixel_variance_average`
- `diagnostics.min_mean`
- `diagnostics.min_variance`
- `diagnostics.suggested_next`
- `diagnostics.fallback_tool_order`

The expected first fallback order is:

1. `simulation_get_status`
2. `viewport_frame_prims`
3. `viewport_capture_assert`
4. `extension_capture_logs`

## Unit Evidence

Targeted checks:

```text
.\.venv\Scripts\python.exe -m pytest tests\unit\test_viewport_render_tools.py tests\unit\test_scenario_integration.py::test_report_promotes_viewport_capture_assert_diagnostics tests\unit\test_scenario_integration.py::test_robot_rtx_sensor_golden_workflow_reports_capture_assert_diagnostics -q
17 passed in 1.00s

.\.venv\Scripts\python.exe -m ruff check src\omniverse_kit_mcp\types\viewport.py src\omniverse_kit_mcp\modules\viewport_module.py src\omniverse_kit_mcp\scenario\reporters.py tests\unit\test_viewport_render_tools.py tests\unit\test_scenario_integration.py
All checks passed!
```

Broader checks:

```text
.\.venv\Scripts\python.exe scripts\verify_mcp_sync.py
verify_mcp_sync OK - safe to commit

.\.venv\Scripts\python.exe -m pytest tests\unit\test_viewport_render_tools.py tests\unit\test_scenario_integration.py -q
71 passed in 1.13s

.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_integrity.py tests\unit\test_doc_references.py -q
19 passed, 2 skipped in 1.36s

.\.venv\Scripts\python.exe -m pytest tests\unit\test_public_repo_hygiene.py -q
18 passed in 12.58s

.\.venv\Scripts\python.exe -m pytest tests\unit\ -q
772 passed, 16 skipped in 46.51s

git diff --check
passed
```

## Live Evidence

Bounded Isaac Sim MCP smoke was run from the workspace-local
`workspaces/isaac/instance-1` entry, not from the repo root. The scratch-stage
sequence was:

```text
mcp_runtime_info
kit_app_start
simulation_get_status
extension_clear_logs
stage_new
viewport_capture_assert(
  width=320, height=180, warmup_frames=4,
  min_mean=8.0, min_variance=1.0
)
extension_capture_logs(level=WARN, limit=200)
```

The scratch stage produced an intentionally blank frame:

- `error_code`: `VIEWPORT_CAPTURE_ASSERT_FAILED`
- `pixel_mean_average`: `0.0`
- `pixel_variance_average`: `0.0`
- `failure_codes`: `PIXEL_MEAN_BELOW_THRESHOLD`,
  `PIXEL_VARIANCE_BELOW_THRESHOLD`
- `diagnostics.reason`: `capture_blank_or_flat`
- `diagnostics.fallback_tool_order`: `simulation_get_status`,
  `viewport_frame_prims`, `viewport_capture_assert`, `extension_capture_logs`
- capture size: `320x180`
- capture hash:
  `686b412ef127822d0f9d992a9c452cfb31b5a0cd2a39d706981c40e07ba0c5ac`

Visual inspection of the PNG confirmed a black frame, matching the `0.0` mean
and variance stats. `extension_capture_logs(level=WARN)` returned three WARN
entries and no ERROR entries in the smoke transcript; the WARNs were associated
with stage replacement/plugin-release noise after `stage_new`, not the capture
diagnostic payload.

## Public Hygiene

This artifact intentionally contains only public-safe command output and no
private paths, credentials, tokens, hostnames, or proprietary asset references.
Push remains gated by the repository public-history review policy.

Public hygiene checks for this batch:

```text
review_public_hygiene.py --skip-history
finding_count=0

review_public_hygiene.py --today --head HEAD
finding_count=0

review_public_hygiene.py --date 2026-06-24 --head HEAD
finding_count=0

review_public_hygiene.py --base origin/main --head HEAD
finding_count=0
```

The older 2026-06-23 history audit still reports 7 `already_public` findings, so
normal push remains blocked until the repository history remediation gate is
approved or the residual public-history risk is explicitly accepted.
