<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: scenario YAML required knowledge before starting authoring/verification work -->
# Scenario Validation — Invariants

Read this file before authoring `scenarios/**/*.yaml` or executing `scenario_validate`.
If R1/R1a/R2/R3 is violated, the verification result is invalid.

## R1. The actual output is an actual asset, and the fixture is a primitive.

- **Prohibited**: In user-facing deliverables, primitives may not substitute for requested chairs, robots, characters, or environments.
- **Accept real output**: Real USD from `asset_list` or known S3 path
  - `.../Environments/Office/Props/SM_Armchair.usd`
  - `.../Robots/NVIDIA/NovaCarter/nova_carter.usd`
  - `.../People/Characters/F_Business_02/F_Business_02.usd`
- **fixture exception**: prototype / unit test / smoke demo / diagnostic scenes may use controlled primitives, e.g. the robot pick/place 0.04 m cube fixture. Requested real assets still need bbox/fit/visual preflight.
- **SoT Catalog** (full S3 URL list): `docs/assets/isaac/asset_inventory.md` + `docs/assets/isaac/assets/*.md` — Candidate asset selection entry point before scenario authoring

### Reason (actual false positive)

Primitives and real assets differ in bbox, pivot, forward axis, material, and mesh topology; a cube can pass while an Armchair NavMesh step-up fails. Controlled fixtures are allowed only when they isolate the cause being tested.

## R1a. NavMesh bake requires timeline stopped

`navigation_bake` returns `bake=True` when called while playing, but `get_navmesh()`
= None (silent False Positive).

`stage_load_usd` / `robot_load` / `stage_create_prim` / `stage_set_property` /
`viewport_capture(settle_frames)` / `window_capture` are all timeline advance
Therefore, `simulation_stop` **recall** is required just before bake.

Standard sequence:
```
load → stop → bake → query_path → play → navigate_path
```

`robot_load` is a stage mutation, so it is prohibited during active async jobs. Isaac Sim
In 6.0 live verification, NovaCarter `navigate_path` job is pending/running.
When payload loading Franka, Kit/PhysX crash was reproduced. `robot_load` service is
Pending/running job is rejected with HTTP 400, and playing timeline is stopped first.

## R2. Robot operation only occurs in `simulation_play`

- Exception: `robot_load` is a stage mutation, so the playing state is stopped internally.
There must be no active async job.
- Required playing: `robot_set_joint_positions` / `robot_navigate_to` /
  `robot_navigate_path` / `robot_drive_physics` / `robot_gripper_control` /
`robot_set_ee_target`, etc. Movement, joints, and physics interaction

Reason: PhysX articulation view needs to run physics step to populate. Extension
`robot_service.navigate_path` returns HTTP 400 if `omni.timeline.is_playing()` does not pass.
refusal. scenario is required to place `simulation_play` in arrange.

## Robot + RTX sensor standard sequence

Combined robot/sensor smoke uses `scenarios/smoke/robot_rtx_sensor_golden_workflow.yaml`:
`stage_new -> load grid/light/robot -> create lidar target cubes -> play/stop
warm-up -> attach RTX camera -> set camera annotators -> play ->
step(frames=5) -> attach RTX lidar -> lidar visualization -> step(frames=180) ->
sensor.lidar_get_point_cloud(idempotent=true, retries.maxAttempts=3,
frames_to_wait=180, min_points=${variables.lidar_min_points} default 1,
fail_on_warning=true) -> pause ->
viewport.frame_prims -> viewport.capture_assert -> cleanup`.

Live proof wrapper: `mcp_runtime_info -> kit_app_start -> simulation_get_status -> scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml) -> scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml, dry_run=true) -> extension_clear_logs -> scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml) -> scenario_last_report(report_format="markdown", redact_local_paths=true) -> extension_capture_logs(level="WARN", stop_after_capture=true)`.
After the final log capture, record `data.capture_stop_requested=true`, `data.capture_stop_completed=true`, `data.capture_stop_timed_out=false`, and `data.capture_running=false` before treating the request-scoped log hook as closed.
Before stage mutation, `scenario_plan` or `scenario_validate(..., dry_run=true)` must expose matching `phase_counts`, `preflight_requirements`, `stage_mutation_summary`, `stage_mutation_steps`, `diagnostic_steps`, `evidence_steps`, `retry_steps`, `simulation_state_summary`, `simulation_state_steps`, `timeline_control_steps`, and `live_validation_checklist`; `stage_mutation_summary.read_only=false` requires scratch/test stage routing. Check `stage_mutation_steps` against the scratch/test stage boundary, plus `simulation_state_summary.play_state_missing_count` and `retry_steps[].key_args`, before live mutation. The dry-run belongs before `extension_clear_logs`; clear logs immediately before the mutating run. Dry-run-only output is plan proof, not live proof; do not cite `evidence_summary`, live status, cleanup count, or diagnostic fields as evidence unless a later non-dry-run `scenario_validate` ran through `--scenario-validate-live` with the matching `--expect-live-*` assertions.
Parent-side stdio probe must include `--scenario-validate-dry-run`, `--require-plan-fields`, `--expect-scratch-stage-required true`, `--expect-log-capture-recommended true`, and exact `--require-live-validation-tools mcp_runtime_info,kit_app_start,simulation_get_status,scenario_plan,scenario_validate,extension_clear_logs,scenario_validate,scenario_last_report,extension_capture_logs`.
Default live proof assertions are mandatory: `--expect-live-status passed`, `--expect-live-cleanup-failures 0`, `--expect-live-evidence-kind rtx_lidar_point_cloud`, `--expect-live-evidence-kind viewport_framing`, `--expect-live-evidence-kind visual_capture`, `--expect-live-evidence-field read_lidar_point_cloud:status=passed`, `--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1`, `--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false`, and `--expect-live-evidence-field capture_visible_result:passed=true`.
For controlled failure diagnostics, pass the same `input_overrides={"lidar_min_points": 513}` to `scenario_plan` and `scenario_validate`; assert `--expect-live-status failed`, `--expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`, `--expect-live-diagnostic-next-actions-min 1`, `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`, `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513`, and `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.fallback_tool_order='["simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]'`. The only fatal step should be `read_lidar_point_cloud`; cleanup must be preserved.

Do not use an RTX lidar prim as a viewport camera. Frame the robot/sensor prims
with a normal viewport camera and use `sensor.lidar_get_point_cloud` for lidar data.
Keep at least one target prim near the lidar scan plane; an empty flat grid can
legitimately produce zero point returns even when the sensor is attached.
Attach RTX lidar after the timeline is already playing; live Isaac Sim 6.0
evidence showed cold-attached lidar can stay on an empty GMO/scan buffer while a
fresh lidar attached during play returns points in the same stage.
When reusing the same Kit process, discard stale cached RTX lidar runtime state
before reattaching the same sensor path; otherwise an old render product can
hold the new scan buffer at zero points until the process is restarted.
Transient zero-point RTX buffers should be absorbed with step-level retries only
on idempotent sensor reads; inspect `scenario_last_report` fields
`failure_summary`, `failure_summary[].step_id`,
`failure_summary[].error_code`, `failure_summary[].last_retry_failure`,
`diagnostic_next_actions`,
`diagnostic_next_actions[].phase`, `diagnostic_next_actions[].status`,
`diagnostic_next_actions[].error_code`,
`diagnostic_next_actions[].final_step_status`,
`diagnostic_next_actions[]` flat keys `diagnostics.num_points` / `diagnostics.min_points`,
`step_results[].diagnostic_next_actions`,
`step_results[].retry_failures[].diagnostic_next_actions`,
`attempts`, `max_attempts`, `retry_failures`,
`retry_failures[].data_summary.num_points` / `retry_failures[].data_summary.diagnostics.num_points` / `retry_failures[].data_summary.diagnostics.min_points`,
`retry_failures[].data_summary.empty_reason`,
`retry_failures[].data_summary.diagnostics.cached_lidar_instance`,
`retry_failures[].data_summary.diagnostics.readback_paths_attempted`,
`data_summary.num_points`, `data_summary.empty_reason`,
`data_summary.diagnostics.reason`, `data_summary.diagnostics.num_points` / `data_summary.diagnostics.min_points`,
`data_summary.diagnostics.suggested_next`,
`data_summary.diagnostics.fallback_tool_order`,
`data_summary.diagnostics.upstream_error_code`,
`data_summary.diagnostics.cached_lidar_instance`,
`data_summary.diagnostics.readback_paths_attempted`,
`data_summary.raw_keys`, `data_summary.warning`,
`evidence_summary[].evidence_kind`,
`evidence_summary[].pixel_mean_average`,
`evidence_summary[].pixel_variance_average`,
`evidence_summary[].pixel_mean`, `evidence_summary[].pixel_variance`,
`data_summary.diagnostics.failure_codes`,
`data_summary.diagnostics.pixel_mean_average`,
`data_summary.diagnostics.pixel_variance_average`,
`data_summary.diagnostics.min_mean` /
`data_summary.diagnostics.min_variance` before opening logs. If
`viewport_capture_assert` fails, follow `simulation_get_status -> viewport_frame_prims -> viewport_capture_assert -> extension_capture_logs`; if `viewport_frame_prims` itself returns `VIEWPORT_FRAME_PRIMS_ERROR`, follow `diagnostics.reason=viewport_frame_prims_error`, `diagnostics.prim_paths`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` before changing camera code; if direct `viewport_capture` returns `VIEWPORT_CAPTURE_ERROR`, follow `diagnostics.reason=viewport_capture_error`, requested viewport/camera/size fields, and `diagnostics.fallback_tool_order` before changing render or camera code; if timeline control/timing returns `SIMULATION_CONTROL_ERROR`, `SIMULATION_STEP_ERROR`, `SIMULATION_STEP_OBSERVE_ERROR`, `SIMULATION_WAIT_UNTIL_ERROR`, or `SIMULATION_SET_TIME_ERROR`, follow `diagnostics.reason=simulation_control_error` / `diagnostics.reason=simulation_step_error` / `diagnostics.reason=simulation_step_observe_error` / `diagnostics.reason=simulation_wait_until_error` / `diagnostics.reason=simulation_set_time_error`, action/frame/wait/seek target fields, and `diagnostics.fallback_tool_order` before widening waits or frame counts; if `sensor_set_annotator` returns `SENSOR_SET_ANNOTATOR_ERROR`, follow `diagnostics.reason=sensor_set_annotator_error`, `diagnostics.sensor_prim`, `diagnostics.annotators`, `diagnostics.resolution`, and `diagnostics.fallback_tool_order` before changing camera sensors; if `sensor_lidar_get_point_cloud` returns `SENSOR_LIDAR_POINT_CLOUD_WARNING` under `fail_on_warning=true`, follow `diagnostics.reason=lidar_warning`, `diagnostics.suggested_next`, and `diagnostics.fallback_tool_order` before lowering thresholds; if it returns `SENSOR_LIDAR_GET_POINT_CLOUD_ERROR`, follow `diagnostics.reason=lidar_read_error`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` before widening retries.
Use `scenario_last_report(report_format="markdown", redact_local_paths=true)`
for public-safe quick `Diagnostic Next Actions` and `Data Summary Highlights`;
use default JSON for exact field values before copying anything into public docs.
If direct robot controls return `ROBOT_GRIPPER_CONTROL_ERROR` / `ROBOT_SET_EE_TARGET_ERROR`, inspect `diagnostics.reason=robot_gripper_control_error` / `diagnostics.reason=robot_set_ee_target_error`, requested prim/action/target fields, and `diagnostics.fallback_tool_order` before widening retries or changing robot profiles.
For idempotent retry steps, the scenario runner retries returned non-pass
results, hard step timeouts, and hard step exceptions; each failed attempt is
recorded in `retry_failures`.

## Official asset scenario proof sequence

Use `smoke/official_asset_catalog_diagnostics.yaml` for read-only sync/search/resolve/get diagnostics and `smoke/official_asset_verify_live.yaml` for bounded scratch/test-stage load-quality proof. Live wrapper: `mcp_runtime_info -> kit_app_start -> simulation_get_status -> scenario_plan(smoke/official_asset_verify_live.yaml) -> scenario_validate(smoke/official_asset_verify_live.yaml, dry_run=true) -> extension_clear_logs -> scenario_validate(smoke/official_asset_verify_live.yaml) -> scenario_last_report(report_format="markdown", redact_local_paths=true) -> extension_capture_logs(level="WARN", stop_after_capture=true)`.
Read-only catalog diagnostics wrapper: `mcp_runtime_info -> kit_app_start -> simulation_get_status -> scenario_plan(smoke/official_asset_catalog_diagnostics.yaml) -> scenario_validate(smoke/official_asset_catalog_diagnostics.yaml, dry_run=true) -> extension_clear_logs -> scenario_validate(smoke/official_asset_catalog_diagnostics.yaml) -> scenario_last_report(report_format="markdown", redact_local_paths=true) -> extension_capture_logs(level="WARN", stop_after_capture=true)`.
After the final log capture, record `data.capture_stop_requested=true`, `data.capture_stop_completed=true`, `data.capture_stop_timed_out=false`, and `data.capture_running=false` before treating the request-scoped log hook as closed.
Before live execution, `scenario_plan.stage_mutation_summary.read_only=false`, `scenario_plan.stage_mutation_steps` must include `official_asset_verify_stage_probe`, `scenario_plan.evidence_steps` must include `evidence_kind=official_asset_verify`, and `scenario_plan.diagnostic_steps` must include the preceding catalog probes.
Live proof assertions are mandatory: `--expect-live-status passed`, `--expect-live-cleanup-failures 0`, `--expect-live-evidence-kind official_asset_verify`, `--expect-live-evidence-field official_asset_verify:verification_status=load_verified`, `--expect-live-evidence-field official_asset_verify:kind=asset`, `--expect-live-evidence-field official_asset_verify:app_profile=isaac-sim`, and `--expect-live-evidence-field official_asset_verify:load_quality=content_verified_no_bbox`. Compare redacted JSON from `scenario_last_report(redact_local_paths=true)` (`report_format="json"` is the default) against `evidence_summary[]` for exact fields before copying public evidence.
For read-only catalog diagnostics, the live scenario status should remain `passed` even though `get_pallet_wrong_profile` is a continued `OFFICIAL_ASSET_NOT_FOUND` failure. Probe the diagnostic shape with `--scenario-validate-dry-run --scenario-validate-live`, `--expect-live-cleanup-failures 0`, `--expect-live-failure-step-error get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND`, `--expect-live-diagnostic-next-actions-min 2`, `--expect-live-diagnostic-field search_known_miss:diagnostics.reason=query_no_match`, `--expect-live-diagnostic-field get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`, and `--expect-live-diagnostic-field ...:diagnostics.fallback_tool_order='["official_asset_sync_status","official_asset_search","official_asset_resolve","official_asset_verify","asset_search"]'` for both diagnostic rows.

Read-only official asset diagnostic proof must include `--expect-live-status passed`
next to the continued `get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND`
assertion so the expected continued failure cannot mask a terminal scenario
status regression.

## R3. Viewport capture visual verification obligation

After `viewport_capture`, check the PNG with the `Read` tool.

**If only white/black background** is visible or the asset is small as a dot, **Fail** — in the following order:
Recapture after adjustment:

1. **Add/Adjust Lights** — If your scene does not have `DistantLight` or `DomeLight`,
   `stage_create_prim(prim_type="DistantLight")` + `stage_set_property(inputs:intensity=3000)`.
If it already exists, the intensity is doubled.
2. **Adjust camera position/angle** — `stage_set_property("/OmniverseKit_Persp",
Reset the asset bbox standard distance with "xformOp:translate", [x,y,z])` (small asset is
1~3 m, large env is 10~30 m outside)
3. **Adjust asset position** — Refer to the bounding box so that the asset center is in front of the viewport
Relocating the asset itself or camera target
4. After adjustment, re-invoke `viewport_capture` + re-verify Read. This cycle has a clear geometry
Repeat until visible; if it fails after 2-3 attempts, record an artifact or runbook candidate.

## Character standard sequence (T-pose prevention)

When character USD is loaded as a raw reference with `stage_load_usd`, BehaviorAgent/IRA binding can be missing and simulation_play may show T-pose or stop state.
**Must be `character_load`** (runtime API bind + `anim_graph_bound=true` compatible field).

Standard pattern:
```
character_load(...)
  → simulation_play
  → 1s sleep
  → simulation_pause
  → character_play_animation("Idle")
  → simulation_play
```

Subsequent calls must use response `sanitized_prim_path` (skin variants such as F_Business_02 move to `/World/Characters/{name}`).

## Scenario cleanup (prevent kit.exe shutdown hang)

scenario cleanup uses `simulation_play → simulation_stop` (final physics tick) before `kit_app_stop`; otherwise character runtime / NavMesh handle cleanup can hang kit.exe. Canonical pattern: `scenarios/smoke/character_control.yaml`.
Runner-added fallback cleanup must stay bounded and report a non-fatal cleanup step result instead of blocking `scenario_validate` report generation.

## Related Boundaries

- Scenario YAML Authoring Guide: `scenarios/CLAUDE.md`
- Scenario Engine (Arrange/Act/Assert/Cleanup, action_registry): `src/omniverse_kit_mcp/scenario/CLAUDE.md`
- Asset URL catalog entry point: `docs/assets/isaac/asset_inventory.md`
- Character domain constraints (actual measurement): `src/omniverse_kit_mcp/modules/CLAUDE.md`
- USD LOAD 4 CONDITION: `docs/invariants/usd-load.md`
- Promote permanent failure/improvement procedures to `docs/runbooks/` or `docs/invariants/`.
