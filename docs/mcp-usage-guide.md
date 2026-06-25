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
| Diagnose a failed live action | Read-only probes first: `mcp_runtime_info`, `simulation_get_status`, `extension_capture_logs`, `stage_capture_snapshot`; if timeline control/timing tools fail, inspect `diagnostics.reason=simulation_status_error`, `diagnostics.reason=simulation_control_error`, `diagnostics.reason=simulation_step_error`, `diagnostics.reason=simulation_step_observe_error`, `diagnostics.reason=simulation_wait_until_error`, `diagnostics.reason=simulation_set_time_error`, and `diagnostics.fallback_tool_order` before retrying | `docs/tool-diagnostic-map.md`; then the relevant `docs/runbooks/*.md` if a known failure pattern matches |
| Drive a reproducible scenario | `scenario_plan`, `scenario_validate`, `scenario_last_report(report_format="markdown")` for quick triage or default JSON for exact fields; add `redact_local_paths=true` before copying live evidence into public docs | `docs/invariants/scenario-validation.md`, `scenarios/CLAUDE.md` |
| Prove the robot + RTX sensor golden path | `scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)`, `scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)`, `scenario_last_report(report_format="markdown", redact_local_paths=true)` for public-safe lidar/timeline/capture highlights; if lidar is empty, inspect JSON `diagnostic_next_actions` or Markdown `Diagnostic Next Actions` before widening the smoke | `docs/invariants/scenario-validation.md`, `src/omniverse_kit_mcp/modules/integration-facts.md` |
| Work with robot or character motion | `robot_list_arm_profiles`, `robot_load`, `robot_probe_arm_profile`, `robot_get_joint_positions`, `robot_get_joint_config`, `robot_get_joint_config_static`, `robot_gripper_control`, `robot_set_ee_target`, `robot_set_joint_positions`, `robot_navigate_to`, `robot_navigate_path`, `robot_drive_physics`, `robot_run_franka_pick_place`, `robot_get_ee_pose`, `robot_install_pick_place_playback_demo`, `robot_reset_pick_place_demo`, `robot_get_pick_place_demo_status`, `character_load`, `job_status`; choose `support_status=validated_pick_place` before pick/place playback, and inspect load/read/control errors `diagnostics.reason=robot_load_error`, `diagnostics.reason=robot_get_joint_positions_error`, `diagnostics.reason=robot_get_joint_config_error`, `diagnostics.reason=robot_get_static_joint_config_error`, `diagnostics.reason=robot_gripper_control_error`, `diagnostics.reason=robot_set_ee_target_error`, `diagnostics.reason=robot_set_joint_positions_error`, `diagnostics.reason=robot_navigate_to_error`, `diagnostics.reason=robot_navigate_path_error`, `diagnostics.reason=robot_drive_physics_error`, `diagnostics.reason=robot_franka_pick_place_error`, `diagnostics.reason=robot_get_ee_pose_error`, `diagnostics.reason=pick_place_profile_load_error`, `diagnostics.reason=pick_place_profile_asset_not_articulation`, `diagnostics.reason=pick_place_demo_install_error`, `diagnostics.reason=pick_place_demo_reset_error`, `ROBOT_PROBE_UNKNOWN_PROFILE` typed `data.checks.probe.evidence.fallback_tool_order`, unsupported/candidate/status-timeout `diagnostic_next_actions`, `diagnostics.target_status`, `diagnostics.timeout_s`, and `diagnostics.fallback_tool_order` before claiming proof or retrying broadly | `src/omniverse_kit_mcp/modules/CLAUDE.md`, `docs/invariants/scenario-validation.md` |
| Attach RTX sensors to a robot manually | Prefer the smoke scenario route; if manual, follow the robot + RTX sensor sequence in the invariant before calling `sensor_attach_rtx_camera`, `sensor_attach_rtx_depth_camera`, `sensor_attach_rtx_lidar`, `sensor_set_annotator`, or `sensor_lidar_get_point_cloud`; set `min_points>0` and read `diagnostic_next_actions`, `empty_reason`, `diagnostics.suggested_next`, `SENSOR_LIDAR_POINT_CLOUD_WARNING`, attach-error `diagnostics.reason=rtx_camera_attach_error`, `diagnostics.reason=rtx_depth_camera_attach_error`, `diagnostics.reason=rtx_lidar_attach_error`, annotator-error `diagnostics.reason=sensor_set_annotator_error`, and hard-error `diagnostics.reason=lidar_read_error` triage before widening retries | `docs/invariants/scenario-validation.md`, `src/omniverse_kit_mcp/modules/integration-facts.md` |
| Attach physics sensors or toggle sensor visualization | Use `stage_capture_snapshot` and `simulation_get_status` before calling `sensor_attach_contact`, `sensor_attach_imu`, or `sensor_set_visualization`; on failure inspect `diagnostics.reason=sensor_attach_contact_error`, `diagnostics.reason=sensor_attach_imu_error`, `diagnostics.reason=sensor_set_visualization_error`, requested prim/mount fields, and `diagnostics.fallback_tool_order` before changing stage contents or retrying broadly | `docs/tool-diagnostic-map.md`, `src/omniverse_kit_mcp/modules/integration-facts.md` |
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
scenario timing. JSON action entries use flat dotted keys such as
`diagnostics.reason` and `diagnostics.num_points`, not nested `diagnostics`
objects. Prefer the JSON root queue when exact routing matters: it includes
`phase`, source `status`, final step `error_code`, retry `error_code`, retry
`attempt`, and `final_step_status` when those fields are available.
For `STAGE_LOAD_ERROR` / `STAGE_OPEN_ERROR`, inspect `data.diagnostics.reason`,
the requested `usd_url` or `path`, `upstream_error_code`, `suggested_next`, and
`fallback_tool_order` before changing assets, replacing the scene, or widening
retries.
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
`diagnostics.fallback_tool_order`; if the capture itself errors, expect
`diagnostics.reason=capture_error` and `diagnostics.upstream_error_code` on the
same recovery path. The expected first recovery path is
`simulation_get_status` -> `viewport_frame_prims` -> `viewport_capture_assert`
-> `extension_capture_logs`.
If `viewport_frame_prims` itself errors, expect
`diagnostics.reason=viewport_frame_prims_error` with requested prim paths,
upstream error details, and `diagnostics.fallback_tool_order`; first confirm
the prims with `stage_capture_snapshot`, then check `simulation_get_status`,
retry `viewport_frame_prims`, and only then open logs. If direct
`viewport_capture` errors, inspect `diagnostics.reason=viewport_capture_error`,
requested viewport / camera / size fields, and `diagnostics.fallback_tool_order`
before changing render or camera code.
If manual framing helpers fail, inspect their typed data before changing the
scene: `viewport_focus_prim` exposes `diagnostics.prim_path`,
`viewport_project_points` exposes `diagnostics.point_count`, and
`viewport_set_camera_lookat` exposes requested eye/target/up fields. Follow
their `diagnostics.fallback_tool_order` before widening capture retries.

Robot + RTX live proof wrapper:
`mcp_runtime_info` -> `kit_app_start` -> `simulation_get_status` ->
`scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml)` ->
`scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml, dry_run=true)` ->
`extension_clear_logs` ->
`scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml)` ->
`scenario_last_report(report_format="markdown")` or
`scenario_last_report(report_format="markdown", redact_local_paths=true)` ->
`extension_capture_logs`.
Before validation, check `scenario_plan.phase_counts`, `total_steps`,
`preflight_requirements`, `stage_mutation_summary`, `stage_mutation_steps`, `simulation_state_summary`,
`simulation_state_steps`, `timeline_control_steps`, `evidence_steps`, and
`retry_steps` so a missing setup, stage/sensor mutation, simulation play gate,
viewport cleanup, lidar evidence, capture evidence, or idempotent retry gate is
caught before live stage mutation.
`preflight_requirements.runtime_info.checks` names the profile/freshness checks,
and robot-tagged scenarios also require the robot probe unknown-profile typed
error/fallback contract.
`scenario_plan.live_validation_checklist.steps` mirrors the wrapper order in a
machine-readable form; follow it before copying any live result into public
evidence.
`stage_mutation_summary.read_only=false` means the run needs a scratch/test
stage; then inspect `stage_mutation_steps` for exact touched steps. For retried evidence steps, inspect
`retry_steps[].key_args` next to the retry policy so thresholds such as
`min_points`, `max_points`, `frames_to_wait`, and `fail_on_warning` match the
intended failure or success proof. `simulation_state_summary.play_state_missing_count`
must be `0`; if not, inspect `simulation_state_steps` and add or move a
`simulation.play` step before the listed robot/sensor action. `automatic: true` cleanup steps are
runner-added safeguards, not YAML; inspect their `timeoutSeconds` before a
live proof because fallback cleanup is bounded independently of the MCP tool
call timeout.
`scenario_validate(..., dry_run=true)` returns the same plan fields plus
`dry_run`, `steps`, and `compiled`, so it is safe as a one-call preflight when
you are already on the validation tool path. Inspect `diagnostic_steps` for
read-only official asset catalog/status/search/resolve/get probes,
`preflight_requirements` for the consolidated runtime/scratch/log/play/retry gates,
`stage_mutation_summary` for read-only vs scratch-stage routing,
`stage_mutation_steps` for exact stage/live-scene side effects,
`simulation_state_summary`/`simulation_state_steps` for R2 play-state gates,
`timeline_control_steps` for play/pause/stop/step order, `evidence_steps` for
proof rows, and `retry_steps` for retry gates.
After editing `src/omniverse_kit_mcp`, use
`scripts/run_scenario_standalone.py --dry-run --input-overrides-json {...}` to
inspect the same plan shape before restarting a cached MCP host.
If first-class live tools are not exposed in the current parent host, use
`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/robot_rtx_sensor_golden_workflow.yaml --scenario-validate-dry-run --require-plan-fields --expect-preflight-runtime-check robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE --expect-preflight-runtime-check robot_probe_unknown_profile_fallback_tool_order --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-automatic-cleanup-timeout __fallback_cleanup_reset=30 --expect-scratch-stage-required true --expect-log-capture-recommended true`
to smoke the workspace-local stdio MCP entry, confirm profile/import freshness,
and confirm the plan plus `scenario_validate(dry_run=true)` field shape,
preflight runtime checks, bounded automatic cleanup, and exact live checklist
order without stage mutation.
Use `--live-preflight` by itself when you only need non-stage Kit attach,
timeline status, and request-scoped WARN/ERROR log capture before a mutating
scenario proof.
When you are ready to run the mutating scratch/test-stage proof from the same
parent/root session, rerun the same workspace-local command with
`--scenario-validate-live`, `--expect-live-cleanup-failures 0`,
`--expect-live-evidence-kind rtx_lidar_point_cloud`,
`--expect-live-evidence-kind viewport_framing`, and
`--expect-live-evidence-kind visual_capture`, plus
`--expect-live-evidence-field read_lidar_point_cloud:status=passed`,
`--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1`,
`--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false`, and
`--expect-live-evidence-field capture_visible_result:passed=true`; the script requires `--workspace`,
`--scenario-plan`, and `--scenario-validate-dry-run`, then follows the wrapper
order through `kit_app_start`, `simulation_get_status`, `extension_clear_logs`,
live `scenario_validate`, redacted Markdown `scenario_last_report`, and
`extension_capture_logs` while failing if the live report loses required
evidence rows, expected evidence field values, or cleanup preservation.
If you run the standalone script normally and plan to copy its report into a
public artifact, add `--report-format markdown --redact-local-paths`; the
default standalone report remains raw JSON+Markdown for local triage.
When using `input_overrides`, pass the same override dict to `scenario_plan` and
`scenario_validate` so the plan preview reflects the exact variable-substituted
prim paths and asset URLs that will run.
For parent-side plan-only smoke, remove `--scenario-validate-dry-run` from the
workspace-local probe command and add `--input-overrides-json '{"lidar_min_points":513}' --expect-retry-key-arg read_lidar_point_cloud:min_points=513`;
it then calls only `scenario_plan` and fails if the override does not reach `retry_steps[].key_args.min_points`.
Current public-safe plan-only override probe evidence is
`docs/artifacts/robot-rtx-plan-only-override-probe-2026-06-25.md`.
For bounded RTX lidar failure-shape checks, override
`lidar_min_points` above `lidar_max_points` instead of editing the scenario; the
expected failure is `SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS` on
`read_lidar_point_cloud` with cleanup preserved.
For a live controlled-failure probe, add `--scenario-validate-live`,
`--expect-live-status failed`, `--expect-live-cleanup-failures 0`, and
`--expect-live-evidence-kind rtx_lidar_point_cloud`, plus
`--expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`
`--expect-live-diagnostic-next-actions-min 1`, and
`--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`
so the wrapper fails only on the wrong terminal status, wrong failing
step/error code, missing or wrong diagnostic reason, missing report, missing
lidar evidence, or missing cleanup/log evidence.
Call `scenario_last_report` from the same MCP host process that ran
`scenario_validate`; a fresh stdio host has no in-memory latest report.

Raw live reports can include host-local capture paths, Kit log filenames,
process IDs, worker/thread IDs, and unstable Python object repr addresses.
For public evidence, request `redact_local_paths=true`; it redacts those local
identifiers while preserving SHA256/pixel stats and WARN/ERROR counts. Confirm
artifact paths look like `<validation-api-capture>/capture_<id>.png`, and run
the public hygiene checks.
Current public-safe Robot + RTX evidence anchors are
`docs/artifacts/robot-rtx-golden-default-live-pass-2026-06-25.md` for the
default success path and
`docs/artifacts/robot-rtx-lidar-controlled-failure-diagnostics-2026-06-25.md`
for the `lidar_min_points=513` diagnostics path. Wrapper-specific refreshes
are `docs/artifacts/robot-rtx-default-wrapper-refresh-2026-06-25.md` and
`docs/artifacts/robot-rtx-controlled-failure-wrapper-refresh-2026-06-25.md`.
The live probe assertion options are verified in
`docs/artifacts/probe-live-evidence-cleanup-assertions-2026-06-25.md`; the
Robot + RTX field-level live evidence assertions are verified in
`docs/artifacts/robot-rtx-live-evidence-field-assertions-2026-06-25.md`, and
numeric threshold assertions are verified in
`docs/artifacts/robot-rtx-live-evidence-threshold-assertions-2026-06-25.md`; the
controlled-failure step/error-code assertion is verified in
`docs/artifacts/robot-rtx-controlled-failure-step-error-assertion-2026-06-25.md`,
and controlled-failure diagnostic reason assertion is verified in
`docs/artifacts/robot-rtx-controlled-failure-diagnostic-field-assertion-2026-06-25.md`.
The doc-only durable-rule E2E probe recipe is verified in
`docs/artifacts/probe-assertion-durable-docs-e2e-2026-06-25.md`.
Use them as the comparison baseline when refreshing live proof, and replace or
supersede them only with a new pass/failure artifact that preserves the same
public-safety boundary.
When retrying RTX lidar reads, preserve `retry_failures[].data_summary` fields
such as `diagnostics.num_points`, `diagnostics.min_points`,
`diagnostics.cached_lidar_instance`, and
`diagnostics.readback_paths_attempted` in evidence notes; retry-root
`Diagnostic Next Actions` also surfaces them for quick triage.
For physics sensor attach and visualization toggles, treat typed failure data
as the first triage surface: `sensor_attach_contact` exposes requested
`prim_path`, `sensor_name`, `frequency`, `translation`, and `radius`;
`sensor_attach_imu` exposes requested mount fields; and
`sensor_set_visualization` exposes requested `sensor_prim` / `mode`. Follow
their `diagnostics.fallback_tool_order` before changing stage contents or
opening logs.

For `official_asset_*` zero-result or not-found responses, inspect
`diagnostics.reason`, `diagnostics.candidate_counts`,
`diagnostics.available_profiles`, `diagnostics.available_providers`,
`diagnostics.available_kinds`, `diagnostics.status_counts`,
`diagnostics.sample_names`, `diagnostics.suggested_next`, and
`diagnostics.fallback_tool_order` before changing `kind` / `app_profile` /
`provider` / `min_status` or falling back to `asset_search`.
For `OFFICIAL_ASSET_*_ERROR` responses, inspect `diagnostics.reason`,
`diagnostics.checked_catalog_path`, `diagnostics.error_type`,
`diagnostics.suggested_next`, and `diagnostics.fallback_tool_order`; if
`reason=catalog_parse_error`, regenerate the ignored official catalog before
retrying the official path.
Markdown `Data Summary Highlights` surfaces those bounded catalog details, so
use it for first-pass triage and switch to JSON when exact nested values are
needed.
For `official_asset_sync_status` profile diagnostics, compare
`diagnostics.catalog_status_counts` with
`diagnostics.matching_status_counts` and use `diagnostics.sample_names` only as
bounded retry hints.
If `official_asset_verify` returns `OFFICIAL_ASSET_NOT_FOUND`, treat it as a
preflight miss rather than a failed stage probe: inspect the same bounded
diagnostics, then go back through `official_asset_search` /
`official_asset_resolve` before retrying verify. In scenario reports, this path
appears in JSON `failure_summary` and `diagnostic_next_actions`, while
`evidence_summary` stays empty because no stage probe ran.
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
`scenario_plan(smoke/official_asset_verify_live.yaml)` ->
`scenario_validate(smoke/official_asset_verify_live.yaml, dry_run=true)` ->
`extension_clear_logs` ->
`scenario_validate(smoke/official_asset_verify_live.yaml)` ->
`scenario_last_report(report_format="markdown", redact_local_paths=true)` ->
`extension_capture_logs(level="WARN", stop_after_capture=true)`.
Before live execution, confirm `scenario_plan.stage_mutation_summary.read_only=false`,
`scenario_plan.stage_mutation_steps` includes the
`official_asset_verify_stage_probe` verify row, `scenario_plan.evidence_steps`
includes `evidence_kind=official_asset_verify` for the same step, and
`scenario_plan.diagnostic_steps` includes the preceding sync/search/resolve/get probes.
Use `scenario_plan(smoke/official_asset_catalog_diagnostics.yaml)` when you need
the read-only sync/search/resolve/get catalog diagnostic chain; its
`stage_mutation_summary.read_only` should be `true` and `stage_mutation_steps`
should be empty.
Read-only catalog diagnostics wrapper:
`mcp_runtime_info` -> `kit_app_start` -> `simulation_get_status` ->
`scenario_plan(smoke/official_asset_catalog_diagnostics.yaml)` ->
`extension_clear_logs` ->
`scenario_validate(smoke/official_asset_catalog_diagnostics.yaml)` ->
`scenario_last_report(report_format="markdown", redact_local_paths=true)` ->
`extension_capture_logs(level="WARN", stop_after_capture=true)`.
If first-class live tools are not exposed in the parent host, the same
workspace-local stdio probe can preflight the plan and dry-run validate shape
without stage mutation:
`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_verify_live.yaml --scenario-validate-dry-run --require-plan-field diagnostic_steps --require-plan-field evidence_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required true --expect-log-capture-recommended true`.
When promoting that official-asset probe to the mutating scratch/test-stage
proof, add `--scenario-validate-live`, `--expect-live-cleanup-failures 0`,
`--expect-live-evidence-kind official_asset_verify`,
`--expect-live-evidence-field official_asset_verify:verification_status=load_verified`,
`--expect-live-evidence-field official_asset_verify:kind=asset`, and
`--expect-live-evidence-field official_asset_verify:app_profile=isaac-sim` so
the live report must preserve the expected verification evidence row and
field values.
For the read-only catalog diagnostics path, use
`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract --scenario-plan smoke/official_asset_catalog_diagnostics.yaml --require-plan-field diagnostic_steps --require-plan-field stage_mutation_steps --require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs --expect-scratch-stage-required false --expect-log-capture-recommended true`.
After validation, request redacted JSON when you need exact fields; compare
`evidence_summary[]` with that plan row and check
`verification_status`, `kind`, `app_profile`, and either
`diagnostics.asset_checks` or `diagnostics.material_checks`; for timeout or
exception failures, also check `diagnostics.error_type` before deciding whether
to retry or widen the live proof. Use redacted JSON for exact public-safe fields
and redacted Markdown `Evidence Summary` for the compact evidence note.
Current public-safe official asset live evidence is
`docs/artifacts/official-asset-verify-live-pass-2026-06-25.md`. The live probe
assertion options for the same workflow are verified in
`docs/artifacts/official-asset-live-evidence-assertions-2026-06-25.md`, and
field-level evidence assertions are verified in
`docs/artifacts/official-asset-live-evidence-field-assertions-2026-06-25.md`.
Use them as the baseline for the bounded `official_asset_verify` load-quality
proof and refresh them when verification status, load-quality shape,
diagnostics, evidence kind/fields, cleanup count, or WARN/ERROR counts change.

Official asset on-demand live verify wrapper:
`mcp_runtime_info` -> `kit_app_start` -> `simulation_get_status` ->
`extension_clear_logs` -> `official_asset_sync_status(app_profile=...)` ->
`official_asset_search(app_profile=..., min_status="load_verified")` ->
`official_asset_resolve(app_profile=..., prefer_loadable=true)` ->
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
From a parent/root session without first-class live tools, run
`scripts/probe_mcp_surface.py --workspace workspaces/isaac/instance-1 --runtime-info --expect-tool-profile full --expect-app-profile isaac-sim --expect-tool-count 152 --require-runtime-fresh --require-robot-probe-error-contract`
for the same profile/import-freshness gate through the workspace-local stdio
entry; expectation options imply the `mcp_runtime_info` call even if
`--runtime-info` is omitted. The probe writes ignored `tmp_mcp_surface.json`
and prints only the repo-relative snapshot path, so stdout can be copied into
public evidence without exposing the local workspace root.

## Exact Signatures

After choosing the likely task route, use `docs/tool-catalog.md` for exact tool
names, signatures, parameters, and generated descriptions. Do not edit that file
by hand; regenerate it with `scripts/verify_mcp_sync.py`.
