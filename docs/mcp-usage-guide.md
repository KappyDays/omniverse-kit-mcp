# MCP Usage Guide

Use this guide before opening the full generated tool catalog. It routes common
tasks to the first MCP tools to try and the canonical project docs to read next.
The generated signature reference remains `docs/tool-catalog.md`.

## Task Routes

| Task | First tools | Then read |
|---|---|---|
| Start, attach, or inspect the app | `mcp_runtime_info`, `kit_app_start`, `simulation_get_status` | `docs/invariants/live-worker-coordination.md`, `docs/invariants/process-lifecycle.md` |
| Check running Kit instances before recovery work | `process_list_kit_instances`, `mcp_runtime_info` | `docs/invariants/multi-app.md`, `docs/invariants/process-lifecycle.md` |
| Choose an official NVIDIA asset or material | `official_asset_sync_status`, `official_asset_search`, `official_asset_resolve`, `official_asset_verify`; for repeatable read-only diagnostics use `scenario_validate(smoke/official_asset_catalog_diagnostics.yaml)`, and for one bounded live load-quality proof use `scenario_validate(smoke/official_asset_verify_live.yaml)` | `docs/references/official-asset-catalog.md`, `docs/invariants/asset-discovery.md` |
| Build a visible scene | `official_asset_search`, `asset_search`, `stage_load_usd`, `viewport_frame_prims`, `viewport_capture_assert` | `docs/invariants/usd-load.md`, `docs/invariants/visual-validation.md` |
| Inspect or edit the USD stage | `stage_capture_snapshot`, `stage_compute_world_bbox`, `stage_set_property`, `stage_create_prim` | `src/omniverse_kit_mcp/tools/CLAUDE.md` |
| Diagnose a failed live action | Read-only probes first: `mcp_runtime_info`, `simulation_get_status`, `extension_capture_logs`, `stage_capture_snapshot` | `docs/tool-diagnostic-map.md`; then the relevant `docs/runbooks/*.md` if a known failure pattern matches |
| Drive a reproducible scenario | `scenario_plan`, `scenario_validate`, `scenario_last_report(report_format="markdown")` for quick triage or default JSON for exact fields; add `redact_local_paths=true` before copying live evidence into public docs | `docs/invariants/scenario-validation.md`, `scenarios/CLAUDE.md` |
| Prove the robot + RTX sensor golden path | `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)`, `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)`, `scenario_last_report(report_format="markdown", redact_local_paths=true)` for public-safe lidar/timeline/capture highlights; if lidar is empty, inspect JSON `diagnostic_next_actions` or Markdown `Diagnostic Next Actions` before widening the smoke | `docs/invariants/scenario-validation.md`, `src/omniverse_kit_mcp/modules/integration-facts.md` |
| Work with robot or character motion | `robot_list_arm_profiles`, `robot_load`, `robot_probe_arm_profile`, `character_load`, `job_status` | `src/omniverse_kit_mcp/modules/CLAUDE.md`, `docs/invariants/scenario-validation.md` |
| Attach RTX sensors to a robot manually | Prefer the smoke scenario route; if manual, follow the robot + RTX sensor sequence in the invariant before calling `sensor_attach_rtx_lidar` / `sensor_lidar_get_point_cloud`; set `min_points>0` and read `diagnostic_next_actions`, `empty_reason`, and `diagnostics.suggested_next` on zero-point results | `docs/invariants/scenario-validation.md`, `src/omniverse_kit_mcp/modules/integration-facts.md` |
| Capture GUI or menu evidence | `window_capture`, `window_list`, `window_menu_list`, `window_menu_trigger` | `docs/invariants/visual-validation.md`, `src/omniverse_kit_mcp/tools/CLAUDE.md` |
| Find a missing capability to wrap | `extension_search`, then duplicate-check `docs/tool-catalog.md` | `docs/references/CLAUDE.md`, `docs/invariants/mcp-tool-add.md` |

Standalone scenario runs print JSON plus Markdown; follow the scenario
validation invariant for report-field triage.
For retried sensor steps, check `retry_failures[].data_summary` before relying
on the retry failure message string; it preserves bounded machine-readable
diagnostics for failed attempts.
Reports include `diagnostic_next_actions` in JSON and `Diagnostic Next Actions`
in Markdown when diagnostic payloads carry `suggested_next` or
`fallback_tool_order`; follow that section before opening logs or changing
scenario timing. Prefer the JSON root queue when exact routing matters: it
includes `phase`, source `status`, final step `error_code`, retry
`error_code`, retry `attempt`, and `final_step_status` when those fields are
available.
Failed reports also include JSON `failure_summary` and Markdown `Failure
Summary` before the full step table. Start there to identify final fatal,
continued, cleanup, and exhausted-retry rows, then drill into
`diagnostic_next_actions`, `retry_failures`, and `evidence_summary` for exact
tool-order and evidence details.
Reports also include JSON `evidence_summary` and Markdown `Evidence Summary`
when executed steps produced compact official-asset-verify, lidar,
viewport-framing, or visual-capture evidence; compare it with
`scenario_plan.evidence_steps` before claiming an official asset, robot/RTX, or
visual workflow is proven. `scenario_plan.evidence_steps` uses
report-compatible evidence kinds: viewport/window `capture` and viewport
`capture_assert` plan rows use `evidence_kind=visual_capture`; use
`module`/`action` to distinguish raw capture from assertion gates. For
`viewport_capture_assert`, inspect the visual-capture row's `passed`,
`pixel_mean_average`, `pixel_variance_average`, `pixel_mean`,
`pixel_variance`, and `warmup_frames_used` fields before relying on the image
as nonblank evidence.
If it fails, read `diagnostic_next_actions` for `diagnostics.reason`,
`diagnostics.failure_codes`, pixel averages, threshold fields, and
`diagnostics.fallback_tool_order`; the expected first recovery path is
`simulation_get_status` -> `viewport_frame_prims` -> `viewport_capture_assert`
-> `extension_capture_logs`.

Robot + RTX live proof wrapper:
`mcp_runtime_info` -> `kit_app_start` -> `simulation_get_status` ->
`extension_clear_logs` -> `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)` ->
`scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)` ->
`scenario_last_report(report_format="markdown")` or
`scenario_last_report(report_format="markdown", redact_local_paths=true)` ->
`extension_capture_logs`.
Before validation, check `scenario_plan.phase_counts`, `total_steps`,
`evidence_steps`, and `retry_steps` so a missing setup, sensor, viewport,
cleanup, lidar evidence, capture evidence, or idempotent retry gate is caught
before live stage mutation. For retried evidence steps, inspect
`retry_steps[].key_args` next to the retry policy so thresholds such as
`min_points`, `max_points`, `frames_to_wait`, and `fail_on_warning` match the
intended failure or success proof. `automatic: true` cleanup steps are
runner-added safeguards, not YAML.
`scenario_validate(..., dry_run=true)` returns the same plan fields plus
`dry_run`, `steps`, and `compiled`, so it is safe as a one-call preflight when
you are already on the validation tool path.
After editing `src/omniverse_kit_mcp`, use
`scripts/run_scenario_standalone.py --dry-run --input-overrides-json {...}` to
inspect the same plan shape before restarting a cached MCP host.
If you run the standalone script normally and plan to copy its report into a
public artifact, add `--report-format markdown --redact-local-paths`; the
default standalone report remains raw JSON+Markdown for local triage.
When using `input_overrides`, pass the same override dict to `scenario_plan` and
`scenario_validate` so the plan preview reflects the exact variable-substituted
prim paths and asset URLs that will run.
For bounded RTX lidar failure-shape checks, override
`lidar_min_points` above `lidar_max_points` instead of editing the scenario; the
expected failure is `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS` on
`read_lidar_point_cloud` with cleanup preserved.
Call `scenario_last_report` from the same MCP host process that ran
`scenario_validate`; a fresh stdio host has no in-memory latest report.

Raw live reports can include host-local capture paths, Kit log filenames,
process IDs, worker/thread IDs, and unstable Python object repr addresses.
For public evidence, request `redact_local_paths=true`; it redacts those local
identifiers while preserving SHA256/pixel stats and WARN/ERROR counts. Confirm
artifact paths look like `<validation-api-capture>/capture_<id>.png`, and run
the public hygiene checks.
When retrying RTX lidar reads, preserve `retry_failures[].data_summary` fields
such as `diagnostics.cached_lidar_instance` and
`diagnostics.readback_paths_attempted` in evidence notes.

For `official_asset_*` zero-result or not-found responses, inspect
`diagnostics.reason`, `diagnostics.candidate_counts`,
`diagnostics.available_profiles`, `diagnostics.available_providers`,
`diagnostics.available_kinds`, `diagnostics.status_counts`,
`diagnostics.sample_names`, `diagnostics.suggested_next`, and
`diagnostics.fallback_tool_order` before changing `kind` / `app_profile` /
`provider` / `min_status` or falling back to `asset_search`.
Markdown `Data Summary Highlights` surfaces those bounded catalog details, so
use it for first-pass triage and switch to JSON when exact nested values are
needed.
For `official_asset_sync_status` profile diagnostics, compare
`diagnostics.catalog_status_counts` with
`diagnostics.matching_status_counts` and use `diagnostics.sample_names` only as
bounded retry hints.
For `official_asset_verify` failed records, inspect `diagnostics.reason` plus
`diagnostics.asset_checks` or `diagnostics.material_checks` before retrying or
placing the asset in a user scene. JSON `diagnostic_next_actions` carries the
target/current status plus the relevant check dict when a verify failure also
provides `suggested_next` or a fallback order. JSON `evidence_summary` and
Markdown `Evidence Summary` also expose `evidence_kind=official_asset_verify`,
`verification_status`, `kind`, `app_profile`, and bounded diagnostics, so use
them as the compact proof row for `scenario_validate(smoke/official_asset_verify_live.yaml)`.

Official asset scenario proof wrapper:
`mcp_runtime_info` -> `kit_app_start` -> `simulation_get_status` ->
`extension_clear_logs` -> `scenario_plan(smoke/official_asset_verify_live.yaml)` ->
`scenario_validate(smoke/official_asset_verify_live.yaml)` ->
`scenario_last_report(report_format="json", redact_local_paths=true)` ->
`scenario_last_report(report_format="markdown", redact_local_paths=true)` ->
`extension_capture_logs(level="WARN")` and
`extension_capture_logs(level="ERROR")`.
Before live execution, confirm `scenario_plan.evidence_steps` includes
`evidence_kind=official_asset_verify` for the verify step. After validation,
compare JSON `evidence_summary[]` with that plan row and check
`verification_status`, `kind`, `app_profile`, and either
`diagnostics.asset_checks` or `diagnostics.material_checks`; for timeout or
exception failures, also check `diagnostics.error_type` before deciding whether
to retry or widen the live proof. Use redacted JSON for exact public-safe fields
and redacted Markdown `Evidence Summary` for the compact evidence note.

Official asset on-demand live verify wrapper:
`mcp_runtime_info` -> `kit_app_start` -> `simulation_get_status` ->
`extension_clear_logs` -> `official_asset_sync_status(app_profile=...)` ->
`official_asset_search(app_profile=..., min_status="load_verified")` ->
`official_asset_get(app_profile=...)` ->
`official_asset_verify(app_profile=..., timeout_s=180)` ->
`simulation_get_status` -> `extension_capture_logs(level="WARN")` and
`extension_capture_logs(level="ERROR")`. Capture logs in the same live MCP host
session that ran `official_asset_verify`; one-shot stdio hosts do not preserve
the previous host's in-memory/log-capture state.

## Timeline Control

`simulation_play`, `simulation_pause`, and `simulation_stop` return timeline
state after the Kit update loop has accepted the command. Treat their
`is_playing` / `is_stopped` fields as the settled post-action state; check
`timeline_settled` and `timeline_settle_updates` when diagnosing slow or stale
timeline transitions. Use `simulation_get_status` when a later step needs an
independent read-back.

## Profile Selection

`MCP_SERVER_TOOL_PROFILE` controls registration-time tool exposure:

| Profile | Use |
|---|---|
| `full` | Default compatibility mode. Registers the complete generated tool surface. |
| `core` | Smaller everyday authoring and diagnostics surface. |
| `app` | Slim app-workflow surface with invariant tool names across `ISAAC_MCP_APP_PROFILE`; unsupported app-specific capabilities fail at runtime with capability errors. |
| `custom` | Starts from `core`, then applies `MCP_SERVER_TOOL_INCLUDE` and `MCP_SERVER_TOOL_EXCLUDE` tokens. |

Set `MCP_SERVER_TOOL_PROFILE=full` and restart the MCP host to roll back to the
complete compatibility surface.

Call `mcp_runtime_info` after MCP host startup to confirm the active
`tool_profile`, `app_profile`, registered `tool_count`, omitted groups/tools,
and custom include/exclude tokens before comparing a slim profile against the
full catalog.

## Exact Signatures

After choosing the likely task route, use `docs/tool-catalog.md` for exact tool
names, signatures, parameters, and generated descriptions. Do not edit that file
by hand; regenerate it with `scripts/verify_mcp_sync.py`.
