<!-- Parent: ../CLAUDE.md -->
<!-- Scope: YAML scenario writing guide (no engine internal knowledge required) -->

# scenarios — YAML scenario authoring

YAML scenarios to verify Isaac Sim + Extension operation end-to-end. Even without knowing the engine internals, you can create a new scenario using just these directory instructions.

## ⚠️ Must read before writing

- R1/R1a/R2/R3 Validation Rules: `../docs/invariants/scenario-validation.md`
- Domain-specific runtime trap: `../src/omniverse_kit_mcp/modules/integration-facts.md`
- MCP tool signature: `../src/omniverse_kit_mcp/tools/CLAUDE.md`

## Source of truth

- **Schema**: `schema/scenario.schema.json` — Source of all field definitions. Also check with MCP resource `isaacsim://scenario-schema`
- Based on YAML path: environment variable `SCENARIOS_DIR` (default `scenarios/`). Root escape route is rejected by `_resolve_safe_path()`

## Directory

```
scenarios/
├── schema/scenario.schema.json        # JSON Schema (SoT)
└── smoke/                             # canonical examples
    ├── full_pipeline.yaml             # Cube lifecycle (create → move → play/stop → assert → diff → cleanup)
    ├── state_check_property.yaml      # state-check mode example
    ├── trigger_sync_cube.yaml         # Trigger mode (Extension sync)
    ├── usd_load_robot.yaml            # local USD load → prim/position validation
    ├── robot_joint_control.yaml       # Phase B+: asset_list → load → warm-up → joints → navigate → viewport
    ├── robot_rtx_sensor_golden_workflow.yaml # NovaCarter + RTX camera/lidar + capture_assert
    ├── official_asset_catalog_diagnostics.yaml # official_asset_* status/search/resolve/get diagnostics, read-only
    ├── official_asset_verify_live.yaml # official_asset_verify load-quality + cleanup smoke
    └── character_control.yaml         # Character load → play → navigate → cleanup (canonical shutdown-hang prevention)
```

`full_pipeline.yaml` handles stage WRITE + timeline + diff_snapshots at once, so it is good for reference when writing a new scenario.

## YAML structure

```yaml
apiVersion: isaacsim.validation/v1
kind: Scenario
metadata:
  id: <scenario_id>
  name: <display name>
  tags: [<tag>, ...]

spec:
  defaults: { stepTimeoutSeconds: 60, failFast: true }
  variables: { prim_path: "/World/Cube" }
  arrange: [<step>, ...]
  act: [<step>, ...]
  assert:
    - id: cube_position
      module: stage
      action: assert_property
      args:
        prim_path: ${variables.prim_path}
        property_name: xformOp:translate
        comparator: approx
        expected_value: [1.0, 2.0, 3.0]
        tolerance: 0.001
  cleanup: [<step>, ...]
```

- `module` enum: `{stage, viewport, lakehouse, extension, simulation, robot, job, asset, character, window, navigation, sensor, physics, lighting, material, replicator, omnigraph, content}` (18)
- `action` mapping protocol: action_registry of `../src/omniverse_kit_mcp/scenario/CLAUDE.md`
- `args` schema: Definition of `schema/scenario.schema.json` by action
- **Cleanup is always executed regardless of whether assert fails** (finally)

## Action guide for each module| module | Role | Details |
|--------|------|------|
| `stage` | READ / ASSERT / DIFF (capture_snapshot, assert_*, diff_snapshots) | context-aware diff → bottom |
| `simulation` | WRITE + timeline (stage_load_usd, create/set/delete_prim, play/pause/stop, stage_save/open/new) | **Stage WRITE is simulation routing** (not StageModule) |
| `viewport` | capture / capture_assert / frame_prims / compare_ssim / set_active_camera | Requires GUI mode; use `capture_assert` for nonblank smoke evidence |
| `robot` / `character` | Domain tool (load / navigate / joints / play_animation, etc.) | R2 (playing required) + detailed caveat: `../src/omniverse_kit_mcp/tools/CLAUDE.md` |
| `sensor` | RTX camera/lidar attach, annotators, point-cloud readback | Use `sensor.lidar_get_point_cloud` for lidar data; do not use lidar prims as viewport cameras. For robot+RTX timing/retry caveats, follow `../docs/invariants/scenario-validation.md` |
| `asset` / `extension` / `job` / `lakehouse` | list/search/external_* prepare / trigger / status / query | `lakehouse` is query only; `asset.external_*` prepares ignored-cache files and is not stage placement proof |

**GUI equivalent tools**: File menu (`stage_save/open/new`), Stage panel (`stage_get/set_selection`), Viewport toolbar (`viewport_set_active_camera`). `stage_create_prim(prim_type=...)` also accepts Camera / DistantLight / DomeLight / SphereLight / RectLight in addition to Cube/Sphere.

**Franka pick/place**: When dealing with Franka and object prim of the existing stage, use `robot.run_franka_pick_place` first. This action is the official Isaac Sim PickPlaceController/RMPflow/ParallelGripper route and does not use kinematic carry. The official controller's default hover height is absolute world Z=0.3, so it may be low for table-top objects, so check the wrapper's `end_effector_initial_height_source`. If the bbox center is not the actual grasp point, specify `picking_position` / `end_effector_orientation`. In the Assert step, use `stage_compute_world_bbox` and viewport capture together to check lift/final placement.

## Character scenario — YAML authoring specialization

BehaviorAgent/IRA / NavMesh / shutdown hang Details: `../src/omniverse_kit_mcp/modules/CLAUDE.md §"Character domain constraints"` + `../docs/invariants/scenario-validation.md §"Character standard sequence"`. YAML author checklist:

1. **navigate_to before and after**: R2 (playing required). Sequence: `play → navigate → job.status → pause`
2. **Viewport capture**: 6.0 character skin does not guarantee its own lighting/camera → arrange in `DomeLight` + `viewport_set_active_camera("/OmniverseKit_Persp")`. To avoid continuous call re-cache, frame advance with `simulation_play`
3. **Select character**: Search for `asset_list(category="people")`. DH UUID name automatically applies `_sanitize_prim_name` of `character_load` → Subsequent steps are based on response `sanitized_prim_path`
4. **Cleanup**: Run `simulation_play → simulation_stop` (last physics tick) before `kit_app_stop` — prevent shutdown hang

## Context-aware action: `stage.diff_snapshots`

Calculate diff by pulling the results of the preceding two `capture_snapshot` steps from ctx:```yaml
- id: diff_move
  module: stage
  action: diff_snapshots
  args:
    before_step_id: snapshot_before_move   # prior capture_snapshot step id
    after_step_id: snapshot_after_move
    min_changes: 1     # optional: FAIL if below this
    max_changes: 50    # optional: FAIL if above this
```

## Context-aware action: `job.status`

ASYNC Job polling. After resolving `job_id` in the preceding job-creation step (`robot_navigate_to`, `character_navigate_to`, etc.), poll `/jobs/{job_id}`:

```yaml
- id: wait_nav
  module: job
  action: status
  args:
    navigate_step_id: nav          # or job_id: "<literal>"
    expected_status: done          # optional — FAIL on mismatch
    poll_interval_s: 0.25
    max_polls: 30
```

If `expected_status` is not specified, only `error` termination is FAIL. terminal state: `done` / `error` / `canceled`.

##Other rules

- **`continueOnFailure: true`** — Optional step; non-passed results do not poison the scenario terminal status, and Markdown labels them as `error (continued)` / `failed (continued)`. Not related to `failFast`
- **Float Comparison** — Default tolerance `0.001`. action star `args.tolerance` override
- **Lakehouse** — `lakehouse_query` is only for pulling expected values (no inject/cleanup possible)

## run

```
scenario_validate(scenario_path="smoke/trigger_sync_cube.yaml")  # actual execution
scenario_plan(scenario_path="smoke/state_check_property.yaml")   # plan preview
Read resource isaacsim://scenarios                               # available scenario list
scenario_last_report(report_format="markdown")                   # quick triage; omit arg for JSON
scenario_last_report(report_format="markdown", redact_local_paths=true) # public-safe evidence copy
```
`scenario_last_report` includes `failure_summary`, diagnostics/retry data plus `evidence_summary` for official verify, lidar, viewport framing, and capture evidence; start failed triage from Markdown `Failure Summary`, use Markdown for quick report reading, use default JSON for exact fields, and use `scenario_last_report(redact_local_paths=true)` when those exact JSON fields will become public evidence (`report_format="json"` is the default). For live proof log capture, close with `extension_capture_logs(..., stop_after_capture=true)` and record `data.capture_stop_requested=true`, `data.capture_stop_completed=true`, `data.capture_stop_timed_out=false`, and `data.capture_running=false` before treating the capture hook as closed. `scenario_plan` exposes `total_steps`, `phase_counts`, `preflight_requirements`, `stage_mutation_summary`, `stage_mutation_steps`, `diagnostic_steps`, `evidence_steps`, `simulation_state_summary`, `simulation_state_steps`, `timeline_control_steps`, `retry_steps` with key args for retried evidence steps, `live_validation_checklist`, automatic cleanup, override `timeoutSeconds`, `idempotent`, `retries`, and `continueOnFailure`; check these before live runs, confirm `stage_mutation_summary.read_only=false` routes to scratch/test stage, and require `simulation_state_summary.play_state_missing_count=0` before robot or RTX sensor proof runs. `scenario_validate(..., dry_run=true)` returns the same plan fields plus `dry_run`, `steps`, and `compiled`. Dry-run-only output is plan proof, not live proof; do not cite `evidence_summary`, live status, cleanup count, or diagnostic fields as evidence unless a later non-dry-run `scenario_validate` ran through `--scenario-validate-live` with the matching `--expect-live-*` assertions. Authoring proof criteria: Robot+RTX live proof must assert `--expect-live-evidence-field read_lidar_point_cloud:status=passed`, `--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1`, `frame_robot_and_sensors:bbox_empty=false`, `capture_visible_result:passed=true`; controlled lidar failure must assert `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`, `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513`, and `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.fallback_tool_order='["simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]'`; official asset live proof must assert `official_asset_verify:verification_status=load_verified`, `official_asset_verify:kind=asset`, `official_asset_verify:app_profile=isaac-sim`, and `official_asset_verify:load_quality=content_verified_no_bbox`; official read-only catalog diagnostics must keep `stage_mutation_summary.read_only=true` and assert the two reason fields plus the two exact fallback assertions listed below. After editing `src/omniverse_kit_mcp`, use `scripts/run_scenario_standalone.py --dry-run` to inspect the same plan shape before restarting a cached MCP host; for a normal standalone report that will become public evidence, add `--report-format markdown --redact-local-paths`.
Official asset scenario authoring gates: live verify proof must assert `--expect-live-status passed`, `official_asset_verify:verification_status=load_verified`, `official_asset_verify:kind=asset`, `official_asset_verify:app_profile=isaac-sim`, and `official_asset_verify:load_quality=content_verified_no_bbox`; read-only catalog diagnostics must keep `stage_mutation_summary.read_only=true` and assert `--expect-live-status passed`, `--expect-live-failure-step-error get_pallet_wrong_profile=OFFICIAL_ASSET_NOT_FOUND`, `--expect-live-diagnostic-next-actions-min 2`, `--expect-live-diagnostic-field search_known_miss:diagnostics.reason=query_no_match`, `--expect-live-diagnostic-field get_pallet_wrong_profile:diagnostics.reason=app_profile_not_covered`, `--expect-live-diagnostic-field search_known_miss:diagnostics.fallback_tool_order='["official_asset_sync_status","official_asset_search","official_asset_resolve","official_asset_verify","asset_search"]'`, and `--expect-live-diagnostic-field get_pallet_wrong_profile:diagnostics.fallback_tool_order='["official_asset_sync_status","official_asset_search","official_asset_resolve","official_asset_verify","asset_search"]'`.
Robot+RTX scenario authoring gates: success live proof must assert `--expect-live-status passed`, `--expect-live-cleanup-failures 0`, `--expect-live-evidence-kind rtx_lidar_point_cloud`, `--expect-live-evidence-kind viewport_framing`, `--expect-live-evidence-kind visual_capture`, `--expect-live-evidence-field read_lidar_point_cloud:status=passed`, `--expect-live-evidence-field-min read_lidar_point_cloud:num_points=1`, `--expect-live-evidence-field frame_robot_and_sensors:bbox_empty=false`, and `--expect-live-evidence-field capture_visible_result:passed=true`; controlled lidar failure must assert `--expect-live-status failed`, `--expect-live-failure-step-error read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS`, `--expect-live-diagnostic-next-actions-min 1`, `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum`, `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.min_points=513`, and `--expect-live-diagnostic-field read_lidar_point_cloud:diagnostics.fallback_tool_order='["simulation_step","sensor_lidar_get_point_cloud","extension_capture_logs"]'`. Use current close-gate artifacts in `docs/mcp-usage-guide.md` as repeatable public proof anchors; older live-pass artifacts are baseline only.
## Procedure for creating a new scenario
1. Copy the most similar example of `smoke/`
2. Action / args check with `scenario.schema.json` or MCP resource `isaacsim://scenario-schema`
3. If you need a new action, use `../src/omniverse_kit_mcp/scenario/CLAUDE.md §"new action addition flow"` + `../docs/invariants/module-add.md`
4. Check compilation with `scenario_plan` → Run with `scenario_validate`
## Related Boundaries- Validation Rules (R1/R1a/R2/R3): `../docs/invariants/scenario-validation.md`
- Inside the engine (state_machine, action_registry, schema synchronization): `../src/omniverse_kit_mcp/scenario/CLAUDE.md`
- MCP tool catalog + domain caveat: `../src/omniverse_kit_mcp/tools/CLAUDE.md`, `../src/omniverse_kit_mcp/modules/integration-facts.md`
- Character constraints + Asset URL catalog: `../src/omniverse_kit_mcp/modules/CLAUDE.md`, `../docs/assets/isaac/asset_inventory.md`
