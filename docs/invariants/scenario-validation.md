<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: scenario YAML required knowledge before starting authoring/verification work -->
# Scenario Validation — Invariants

Read this file before authoring `scenarios/**/*.yaml` or executing `scenario_validate`.
If R1/R1a/R2/R3 is violated, the verification result is invalid.

## R1. The actual output is an actual asset, and the fixture is a primitive.

- **Prohibited**: In user-facing digital twin / 3D modeling / scenario deliverable
Verification using primitives (Cube/Sphere, etc.) as a substitute for chairs, robots, and characters
- **Accept real output**: Real USD from `asset_list` or known S3 path
  - `.../Environments/Office/Props/SM_Armchair.usd`
  - `.../Robots/NVIDIA/NovaCarter/nova_carter.usd`
  - `.../People/Characters/F_Business_02/F_Business_02.usd`
- **fixture exception**: prototype / unit test / smoke demo / diagnostic scene
Controlled test objects are allowed as primitives. Example: robot pick/place playback demo
0.04 m native cube fixture. However, if you specify the actual asset, the same bbox/fit/visual
Must pass preflight.
- **SoT Catalog** (full S3 URL list): `docs/assets/isaac/asset_inventory.md` + `docs/assets/isaac/assets/*.md` — Candidate asset selection entry point before scenario authoring

### Reason (actual false positive)

In verification of actual output, the primitives are bbox·pivot·forward axis·physics material·mesh
False positives occur frequently because the topology characteristics are different from the actual asset. Example: In chair sit verification
Cube passes, but actual Armchair NavMesh step-up fails. Conversely, controller smoke
The size and shape of the fixture must be controlled to separate the cause, so primitives are allowed.

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

Live proof wrapper: `mcp_runtime_info -> kit_app_start ->
simulation_get_status -> extension_clear_logs ->
scenario_plan(smoke/robot_rtx_sensor_golden_workflow.yaml) ->
scenario_validate(smoke/robot_rtx_sensor_golden_workflow.yaml) ->
scenario_last_report(report_format="markdown", redact_local_paths=true) ->
extension_capture_logs`.
For controlled failure diagnostics, pass the same
`input_overrides={"lidar_min_points": 513}` to `scenario_plan` and
`scenario_validate`; this should fail only `read_lidar_point_cloud`, preserve
cleanup, and surface `error_code`, `suggested_next`, and fallback order.

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
`diagnostic_next_actions`,
`diagnostic_next_actions[].phase`, `diagnostic_next_actions[].status`,
`diagnostic_next_actions[].error_code`,
`diagnostic_next_actions[].final_step_status`,
`step_results[].diagnostic_next_actions`,
`step_results[].retry_failures[].diagnostic_next_actions`,
`attempts`, `max_attempts`, `retry_failures`,
`retry_failures[].data_summary.num_points`,
`retry_failures[].data_summary.empty_reason`,
`retry_failures[].data_summary.diagnostics.cached_lidar_instance`,
`retry_failures[].data_summary.diagnostics.readback_paths_attempted`,
`data_summary.num_points`, `data_summary.empty_reason`,
`data_summary.diagnostics.reason`,
`data_summary.diagnostics.suggested_next`,
`data_summary.diagnostics.fallback_tool_order`,
`data_summary.diagnostics.cached_lidar_instance`,
`data_summary.diagnostics.readback_paths_attempted`,
`data_summary.raw_keys`, `data_summary.warning`,
`evidence_summary[].evidence_kind`,
`evidence_summary[].pixel_mean_average`,
`evidence_summary[].pixel_variance_average`,
`evidence_summary[].pixel_mean`, and `evidence_summary[].pixel_variance` before
opening logs.
Use `scenario_last_report(report_format="markdown", redact_local_paths=true)`
for public-safe quick `Diagnostic Next Actions` and `Data Summary Highlights`;
use default JSON for exact field values before copying anything into public docs.
For idempotent retry steps, the scenario runner retries returned non-pass
results, hard step timeouts, and hard step exceptions; each failed attempt is
recorded in `retry_failures`.

## R3. Viewport capture visual verification obligation

After `viewport_capture`, be sure to check the PNG time with the `Read` tool.

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
Repeat until visible — if it fails after 2-3 attempts, replace the task with artifact or new
Recorded as a runbook candidate

## Character standard sequence (T-pose prevention)

When character USD is loaded as a raw reference with `stage_load_usd`, BehaviorAgent/IRA runtime
Due to missing binding, simulation_play may result in T-pose or stop state.
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

Subsequent calls must use `sanitized_prim_path` in the response (skin variants such as F_Business_02
automatically moves to `/World/Characters/{name}`).

## Scenario cleanup (prevent kit.exe shutdown hang)

scenario cleanup uses `simulation_play → simulation_stop` (final physics tick)
Must be executed before `kit_app_stop`. When omitted, character runtime / NavMesh internal handle cleanup
kit.exe hangs due to timing issue. canonical pattern:
`scenarios/smoke/character_control.yaml`

## Related Boundaries

- Scenario YAML Authoring Guide: `scenarios/CLAUDE.md`
- Scenario Engine (Arrange/Act/Assert/Cleanup, action_registry): `src/omniverse_kit_mcp/scenario/CLAUDE.md`
- Asset URL catalog entry point: `docs/assets/isaac/asset_inventory.md`
- Character domain constraints (actual measurement): `src/omniverse_kit_mcp/modules/CLAUDE.md`
- USD LOAD 4 CONDITION: `docs/invariants/usd-load.md`
- Iterative failure/improvement items: Recorded in the relevant work artifact, once it becomes a permanent procedure
Promote to `docs/runbooks/` or `docs/invariants/`
