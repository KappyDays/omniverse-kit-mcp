# Robot Arm MCP Probe Matrix - 2026-06-15

## Scope

This artifact records MCP probe evidence for Isaac Sim built-in robot arm
profiles in the current working tree.

Probe success is not pick/place validation. A profile is only
`validated_pick_place` when there is durable live pick/place proof. Capability
probe rows below only show that MCP load/joint/gripper/IK/EE-pose surfaces were
reachable, or that an unsupported capability was recorded cleanly.

## Evidence Sources

- Static catalog from `builtin_robot_arm_profiles()`:
  - total profiles: 41
  - `validated_pick_place`: 1
  - `candidate_pick_place`: 10
  - `ik_only`: 12
  - `profile_only`: 18
- Continuation checkpoint workers, 2026-06-17:
  - Runtime `tool_count=143` values below are pre-new-tool worker evidence
    captured before this branch's external asset MCP tools increased the
    generated catalog to 146 tools.
  - `workspaces/isaac/instance-1` fresh MCP runtime reported
    `tool_count=143`, `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - the no-Kit `robot_list_arm_profiles` planning surface was present:
    `recommended_probe_mode_by_profile`,
    `recommended_probe_mode_reasons`,
    `dynamic_probe_recommended_profiles`, and
    `static_only_probe_recommended_profiles`; the catalog partition was
    `29` dynamic-recommended plus `12` static-only known-timeout profiles
  - `workspaces/isaac/instance-1` smoke-probed exactly `franka_panda`,
    `franka_fr3`, `factory_franka`, `ur10`, and `kawasaki_rs007l`;
    all five returned `mcp_controllability=dynamic_joint_control`,
    `ur10` recorded gripper unsupported/skipped, and no timeout,
    batch-abort, hard-failure, or lifecycle-recovery rows were reported
  - `workspaces/isaac/instance-2` then ran the dynamic-recommended matrix in
    small batches; batches 1-5 produced 25 clean
    `dynamic_joint_control` rows, while the final dynamic batch degraded:
    `ridgeback_franka` timed out at `joint_config`, `simulation_stop` and
    cleanup timed out, `ridgeback_ur5` was batch-aborted, and the follow-up
    `simulation_get_status` took about `91.7s` before returning
    `SIMULATION_STATUS_ERROR`
  - because that host degraded, static-only hazard triage was not run on
    instance-2 and no dynamic retry was attempted
  - `workspaces/isaac/instance-1` subsequently refreshed all 12 known
    dynamic-timeout hazards with `dynamic_checks=false` in three static-only
    batches: `ur3`, `ur5`, `ur20`, `lite6`, `lite6_gripper`, `uf850`,
    `xarm6`, `xarm7`, `openarm_unimanual`, `openarm_bimanual`, `dofbot`,
    and `so101_new_calib`
  - those 12 refreshed rows all returned
    `mcp_controllability_counts={"static_load_articulation_metadata":4}`
    per batch, for 12 aggregate static metadata rows; all intentionally had
    `overall_ok=false` because dynamic joint read/write, safe nudge, gripper,
    IK, and EE-pose checks were skipped by `dynamic_checks=false`
  - refreshed static-only triage failure lists were empty:
    `timed_out_profiles=[]`, `batch_timeout_profiles=[]`,
    `batch_aborted_profiles=[]`, `hard_failure_profiles=[]`, and
    `lifecycle_recovery_profiles=[]`; final instance-1 host health remained
    responsive with `simulation_get_status` about `12ms`
  - no continuation worker edited files or performed git operations
  - no row from these probes is pick/place validation, and no new profile was
    promoted to `validated_pick_place`
- Bounded Franka Panda pick/place selector worker, 2026-06-17:
  - Runtime `tool_count=143` here is also pre-new-tool worker evidence, not a
    current catalog count for this branch.
  - `workspaces/isaac/instance-1` fresh MCP runtime reported
    `tool_count=143`, `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - `kit_app_start` spawned Isaac Sim instance 1 on port `8111` as PID
    `[redacted]` in about `23.0s`; `simulation_get_status` was responsive in
    about `170ms` with `is_playing=false`, `is_stopped=true`, and
    `current_time=0.0`
  - after `extension_clear_logs`,
    `robot_install_pick_place_playback_demo(profile_name="franka_panda")`
    returned in about `164ms`; the MCP tool call passed, but the data result
    was `ok=false`, `status=unsupported`,
    `support_status=candidate_pick_place`,
    `diagnostics.known_pick_place_blocker=true`, and
    `diagnostics.known_pick_place_blocker_reason` reported the cycle-2
    repeatability blocker where the cache-fix rerun avoided the prior
    `ParallelGripper` `NoneType` crash but still failed with insufficient lift
    for durable proof
  - selector proof fields were `done=false`, `lifted=false`, `placed=false`,
    `max_lift_delta=0.0`, `object_fit_ok=false`,
    `object_fit_reason="Profile has no active validated pick/place adapter."`,
    `controller_event=0`, `steps=0`, and `uses_kinematic_carry=false`
  - per the bounded stop rule, playback status was not called after the
    unsupported known-blocker selector result; WARN+ capture passed with
    `count=0`
  - no `done + lifted + placed` proof was produced, and `franka_panda` remains
    not validated / known pick-place blocker
- Stabilization checkpoint worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, owned Kit PID `[redacted]`
  - `mcp_runtime_info` reported a fresh MCP runtime:
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - `robot_list_arm_profiles` returned `count=41` and exposed the planning
    fields `recommended_probe_mode_by_profile`,
    `recommended_probe_mode_reasons`, `dynamic_probe_recommended_profiles`,
    and `static_only_probe_recommended_profiles`
  - the planning groups partitioned the catalog as `29 + 12 = 41`; the
    static-only group exactly matched the known dynamic-timeout hazard list:
    `ur3`, `ur5`, `ur20`, `lite6`, `lite6_gripper`, `uf850`, `xarm6`,
    `xarm7`, `openarm_unimanual`, `openarm_bimanual`, `dofbot`, and
    `so101_new_calib`
  - pre-probe `simulation_get_status` returned in `17ms`; `kit_app_start`
    attached/idempotently checked readiness in about `1.5s`
  - required smoke batch for `franka_panda`, `franka_fr3`,
    `factory_franka`, `ur10`, and `kawasaki_rs007l` completed in about
    `11.1s` with no timeout or lifecycle-recovery rows; this is probe
    evidence only, and no row was treated as new pick/place validation
  - full dynamic-recommended coverage was rerun in small batches for all 29
    dynamic-recommended profiles:
    `franka_panda`, `franka_fr3`, `factory_franka`, `ur3e`, `ur5e`, `ur10`,
    `ur10e`, `ur16e`, `ur30`, `kawasaki_rs007l`, `kawasaki_rs007n`,
    `kawasaki_rs013n`, `kawasaki_rs025n`, `kawasaki_rs080n`,
    `kinova_gen3`, `kinova_j2n6s300`, `kinova_j2n7s300`,
    `kuka_kr210_l150`, `cobotta_pro_900`, `cobotta_pro_1300`,
    `fanuc_crx10ia_l`, `flexiv_rizon4`, `techman_tm12`, `sawyer`,
    `ridgeback_franka`, `ridgeback_ur5`, `so100`, `unitree_z1`, and `nex10`
  - worker health checks stayed responsive through the dynamic batches:
    observed post-batch status calls included `18ms`, `18ms`, `12ms`, and
    `48ms`; no host collapse was observed during the dynamic-recommended
    rerun
  - batch 1 returned a passed batch envelope but included row-level hard
    failures for `factory_franka`, `ur3e`, and `ur10`; those rows remain
    failures, not MCP-controllability proof. A WARN snapshot was captured
    because that row shape was unexpected.
  - due to parent nudge timing, the final dynamic batch
    `ridgeback_franka`, `ridgeback_ur5`, `so100`, `unitree_z1`, `nex10`
    ran twice (`14.3s` then `9.9s`); the duplicate is recorded here and is
    not counted as additional profile coverage
  - the first static-only hazard batch for `ur3`, `ur5`, `ur20`, `lite6`,
    `lite6_gripper`, and `uf850` completed in about `68.0s`; due to parent
    nudge timing it was then duplicated once more in about `66.0s`
  - the worker could not be cleanly driven through the second static-only
    hazard batch (`xarm6`, `xarm7`, `openarm_unimanual`, `openarm_bimanual`,
    `dofbot`, `so101_new_calib`) and the requested isolated `ur3` dynamic
    retry before parent stop/recovery prompts crossed with pending worker
    prompts; therefore this stabilization checkpoint does not claim a fresh
    full 41-profile matrix rerun
  - static-only hazard evidence for the remaining six known dynamic-timeout
    profiles remains available from earlier documented static-policy workers
    in this artifact, but it was not refreshed by this worker
  - no profile was promoted to `validated_pick_place`; `franka_fr3` remains
    the only profile with durable live pick/place proof
- Current-code live worker, thread `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - started cleanly in about `24.6s`
  - live MCP schema exposed `robot_probe_arm_profile.timeout_s` and
    `robot_probe_arm_profiles.per_profile_timeout_s` plus `batch_timeout_s`
  - tiny `batch_timeout_s=0.001` smoke returned a per-profile
    `probe_batch_timeout` row for `factory_franka` with `overall_ok=false`
    instead of hanging or failing the batch call
  - fresh individual probes ran for `franka_panda`, `franka_fr3`,
    `factory_franka`, `ur10`, and `kawasaki_rs007l`
  - bounded batches ran for `validated_pick_place`, candidate Franka, and
    candidate UR; candidate Kawasaki was not run after the UR batch degraded
    the host
- Post-hardening live worker, thread `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`
  - initial PID `[redacted]` was hung (`Responding=False`) and `kit_app_start`
    timed out twice at the 120s MCP caller ceiling
  - `process_list_kit_instances` showed PID `[redacted]`, port `[redacted]`,
    `is_this_mcp_instance=true`; `kit_app_restart` was therefore allowed under
    the confirmed-hang lifecycle exception
  - restarted cleanly as PID `[redacted]`, ready in about `52.0s`, with initial
    `simulation_get_status` in `16ms`
  - fresh `ur10` smoke passed and proved the new `stage_reset_stop` probe check
  - candidate UR batch with `per_profile_timeout_s=45`, `batch_timeout_s=60`
    returned full rows for both `ur10` and `ur10e`, no timeout or abort rows
  - final `simulation_get_status` returned in `5ms`; host stayed responsive
  - candidate Kawasaki batch with `per_profile_timeout_s=45`,
    `batch_timeout_s=90` returned full `overall_ok=true` rows for all five
    Kawasaki profiles
  - non-UR IK-only families were probed in small batches or single-profile
    calls: Denso, Fanuc, Flexiv, Kuka, mobile manipulator, and Techman
  - `ur16e` passed as an individual IK-only UR probe; `ur3` then timed out,
    cleanup also timed out, and a follow-up status call took about `91.8s`
    before returning `SIMULATION_STATUS_ERROR`
  - additional lifecycle-recovered passes completed the remaining catalog
    coverage without file edits: Kinova, OpenArm, Rethink, RobotStudio,
    UFactory, Unitree, profile-only UR, Yahboom, Yaskawa, and the remaining
    IK-only UR variants
  - live `ROBOT_PROBE_BATCH_ABORTED` rows were reproduced for
    `openarm_bimanual`, `lite6_gripper`, `uf850`, `xarm6`, `xarm7`, and `ur30`
    after an earlier profile in the same batch timed out with unhealthy cleanup;
    `openarm_bimanual`, `lite6_gripper`, `uf850`, `xarm6`, and `xarm7` were
    later rerun in isolation and now have direct warmup-timeout evidence, while
    `ur30` was later rerun in isolation and now has direct dynamic
    joint-control evidence
  - `ridgeback_franka` was corrected with a final current-code single-profile
    probe: gripper/IK/EE passed, but safe nudge failed on
    `dummy_base_prismatic_x_joint`
  - together with the current-code worker rows above, all 41 catalog profiles
    now have durable row-level live evidence: full probe success, profile
    timeout, isolated warmup timeout, or historical batch-aborted evidence
    superseded by direct isolated evidence
- Historical live worker, thread `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - ran exploratory single-profile smoke, candidate batches, and an IK-only UR
    attempt before the final probe timeout implementation
  - useful for rough family prioritization only; safe-nudge evidence is stale
- Historical live worker, thread `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - ran five-frame smoke before `batch_timeout_s` was exposed in the live
    schema and before the final partial-progress interpretation was rerun
- Fresh mobile-selector validation worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`
  - first `ridgeback_franka` run with `timeout_s=25` timed out before
    safe-nudge evidence and degraded the host
  - lifecycle-checked restart of the owned instance produced PID `[redacted]`,
    ready in about `23.7s`
  - rerun with `timeout_s=60` proved the new mobile-base joint skip: safe
    nudge selected `panda_joint1` at joint index `3` instead of
    `dummy_base_prismatic_x_joint`; `overall_ok=true`
  - follow-up `ridgeback_ur5` probe also proved the selector: safe nudge
    selected `ur_arm_shoulder_pan_joint` at joint index `3` instead of dummy
    base joints; `overall_ok=true`, with IK/EE pose still skipped unsupported
- Fresh mobile UR EE-frame smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, MCP server PID `[redacted]`, REST port `[redacted]`
  - profile freshness check confirmed `ridgeback_ur5` exposes EE-frame
    candidates `tool0`, `ee_link`, `wrist_3_link`, `ur_arm_tool0`,
    `ur_arm_ee_link`, and `ur_arm_wrist_3_link`
  - because `validation_api` changed, the worker restarted only the owned
    port `[redacted]` Kit process from PID `[redacted]` to PID `[redacted]`; the non-owned
    port `[redacted]` process was left untouched
  - `ridgeback_ur5` dynamic probe completed in about `4.47s` with
    `overall_ok=true` and `mcp_controllability=dynamic_joint_control`
  - safe nudge used `ur_arm_shoulder_pan_joint` at index `3`; gripper was
    skipped as unsupported; IK was skipped/unsupported due a Lula c-space seed
    dimension error
  - EE pose succeeded for requested `tool0` through concrete USD prim
    `ur_arm_wrist_3_link`, with `attempted_frames=["tool0"]`
  - pre/final `simulation_get_status` stayed responsive and stopped
    (`31ms`/`25ms`); no WARN/ERROR capture was needed
  - this is probe and EE telemetry proof only, not pick/place validation
- Fresh validation_api Lula seed-index live smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, Kit PID `[redacted]`
    after restart
  - because `validation_api` changed, the worker restarted only the owned
    port `[redacted]` Kit process from PID `[redacted]` to PID `[redacted]`; the non-owned
    port `[redacted]` process was left untouched
  - pre/final `simulation_get_status` stayed responsive and stopped
    (`477ms`/`14ms`)
  - `kawasaki_rs007l` returned normally in about `4.7s` with
    `overall_ok=true`, `mcp_controllability=dynamic_joint_control`,
    safe nudge on `joint1[0]` with `readback_ok=true`, and gripper open
    evidence for `finger_joint`, `left_inner_finger_joint`, and
    `right_inner_finger_joint`
  - `kawasaki_rs007l` IK no longer failed at Lula c-space seed construction:
    it reached the solve path for `gripper_center` and cleanly recorded
    `ROBOT_SET_EE_TARGET_ERROR` because the default target did not converge;
    EE pose still resolved requested `tool0` through `onrobot_rg2_base_link`
    with `attempted_frames=["tool0"]`
  - `ridgeback_ur5` returned normally in about `3.1s` with
    `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, safe
    nudge on `ur_arm_shoulder_pan_joint[3]`, unsupported gripper recorded as
    skipped, IK success with `solution_count=6` for `tool0`, and EE pose
    resolved requested `tool0` through `ur_arm_wrist_3_link` with
    `attempted_frames=["tool0"]`
  - no WARN/ERROR capture was needed because both probes returned normally
    and host health stayed responsive
  - this is probe and IK/EE telemetry proof only, not pick/place validation
- Fresh Kawasaki IK target sweep worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`
  - pre-sweep `simulation_get_status` was responsive/stopped in about `29ms`
  - setup `robot_probe_arm_profile(profile_name="kawasaki_rs007l",
    cleanup=false, safe_nudge=false)` returned normally in about `1.2s`
    and left `/World/MCPProbe/kawasaki_rs007l` loaded; the built-in default
    probe target still did not converge, as expected before the parent ladder
    patch was live in MCP
  - direct `robot_set_ee_target` case A, target pose
    `[0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0]` with omitted frame, returned a
    handled `ROBOT_SET_EE_TARGET_ERROR` because Lula did not converge on
    `ee=gripper_center`
  - direct `robot_set_ee_target` case B, target pose
    `[0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0]` with omitted frame, succeeded in
    about `48ms` with `end_effector_frame=gripper_center` and
    `solution_count=6`; cases C-F were skipped because B was the first
    success
  - cleanup used `stage_new` and final `simulation_get_status` stayed
    responsive/stopped in about `23ms`; no WARN/ERROR capture was needed
  - this proves a reachable Kawasaki IK target for the adapter, not
    pick/place behavior
- Post-target-ladder freshness check on the same worker:
  - `mcp_runtime_info` reported MCP process PID `[redacted]`,
    `source_newer_than_import=true`,
    `stale_source_modules=["omniverse_kit_mcp.modules.robot_module"]`, and
    `restart_required_for_latest_mcp_code=true`
  - the worker did not run `robot_probe_arm_profile` after the parent
    target-ladder patch because the stale MCP import could not prove current
    source behavior
  - this was a transient stale-runtime blocker for patched-probe live proof,
    not a profile failure; the later fresh worker below supersedes it
- Fresh patched target-ladder worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, MCP PID `[redacted]`, REST port `[redacted]`, Kit PID
    `35252`
  - `mcp_runtime_info` reported `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - `kit_app_start` attached to the existing owned instance; no restart was
    needed
  - pre-probe `simulation_get_status` passed in about `20ms`
  - `robot_probe_arm_profile(profile_name="kawasaki_rs007l",
    reset_stage=true, safe_nudge=true, cleanup=true, dynamic_checks=true,
    timeout_s=45)` returned normally in about `2.0s` with
    `overall_ok=true` and `mcp_controllability=dynamic_joint_control`
  - load/articulation/joint checks passed with `dof_count=12`;
    safe nudge used `joint1`, target `0.010000000000603231`, readback
    `0.009969132021069527`, and restored/settled; gripper opened
    `finger_joint`, `left_inner_finger_joint`, and
    `right_inner_finger_joint`
  - IK matched the patched ladder: the `default` target
    `[0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0]` failed as a handled
    `ROBOT_SET_EE_TARGET_ERROR`, then `kawasaki_relaxed_orientation`
    selected target `[0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0]` and succeeded
    with `end_effector_frame=gripper_center` and `solution_count=6`
  - EE pose also passed: requested `tool0`, resolved
    `onrobot_rg2_base_link`, `attempted_frames=["tool0"]`
  - final `simulation_get_status` passed in about `29ms`; WARN/ERROR log
    capture was not needed because the expected default-target no-convergence
    was handled and host health stayed responsive
  - this proves the current-code Kawasaki probe target ladder and dynamic
    MCP controllability for `kawasaki_rs007l`; it is not pick/place
    validation and does not promote the profile
- Fresh Kawasaki sibling IK ladder worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, MCP PID `[redacted]`, REST port `[redacted]`, Kit PID
    `42336`
  - `mcp_runtime_info` reported `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - `kit_app_start` attached to the existing owned instance; no restart was
    needed
  - pre-probe and final `simulation_get_status` were responsive/stopped in
    about `25ms` and `18ms`
  - `robot_probe_arm_profiles(status_filter=["candidate_pick_place"],
    family_filter=["kawasaki"], reset_stage_per_profile=true,
    safe_nudge=true, cleanup=true, dynamic_checks=true,
    per_profile_timeout_s=45, batch_timeout_s=180)` returned normally in
    about `11.2s` with `count=5` and no timeout or abort rows
  - `kawasaki_rs007l`, `kawasaki_rs007n`, `kawasaki_rs013n`, and
    `kawasaki_rs025n` each returned `overall_ok=true`,
    `mcp_controllability=dynamic_joint_control`, safe nudge on `joint1`,
    RG2 gripper open success on `finger_joint`, `left_inner_finger_joint`,
    and `right_inner_finger_joint`, EE pose success for requested `tool0`
    resolved through `onrobot_rg2_base_link`, and IK success after the
    `default` target failed cleanly and `kawasaki_relaxed_orientation`
    selected a `solution_count=6` result
  - `kawasaki_rs080n` returned `overall_ok=true` and
    `mcp_controllability=dynamic_joint_control`; load/joints/safe-nudge,
    gripper, EE pose, and cleanup all passed, but IK was a clean skipped
    `ROBOT_SET_EE_TARGET_ERROR` because both `default` and
    `kawasaki_relaxed_orientation` failed to converge
  - the worker ran one supplemental `kawasaki_rs013n` single probe only
    because its batch row was truncated in the client transcript; it matched
    the batch outcome and took about `1.6s`
  - WARN/ERROR log capture was not needed because the batch completed without
    timeout or host degradation; `rs080n` no-convergence is bounded probe
    telemetry, not a host failure
  - this supersedes the older Kawasaki sibling seed-dimension blocker rows for
    current-code IK proof on `rs007n`, `rs013n`, and `rs025n`; it does not
    prove pick/place behavior or promote any Kawasaki profile
- Fresh RS080N direct IK target sweep and post-patch probe worker, threads
  `[worker-id-redacted]` and
  `[worker-id-redacted]`:
  - direct sweep on existing fresh MCP PID `[redacted]`, port `[redacted]`, Kit PID
    `42336`, proved `kawasaki_rs080n` target case C
    `[0.7, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0]` succeeds after the default
    `[0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0]` and relaxed-low
    `[0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0]` targets no-converge
  - parent patch added a profile-specific
    `kawasaki_rs080n_relaxed_forward` probe target after the default and
    generic Kawasaki relaxed targets in
    `src/omniverse_kit_mcp/modules/robot_module.py`
  - focused regression coverage now verifies `kawasaki_rs080n` attempts
    `default`, `kawasaki_relaxed_orientation`, then
    `kawasaki_rs080n_relaxed_forward`
  - fresh same-directory MCP worker PID `[redacted]` proved the patched import was
    current: `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, `stale_source_modules=[]`,
    `robot_module.py` file mtime `1781545253968`, MCP import epoch
    `1781545324467`
  - post-patch
    `robot_probe_arm_profile(profile_name="kawasaki_rs080n",
    reset_stage=true, safe_nudge=true, cleanup=true, dynamic_checks=true,
    timeout_s=45)` returned normally in about `1.7s` with
    `overall_ok=true`, `support_status=candidate_pick_place`, and
    `mcp_controllability=dynamic_joint_control`
  - safe nudge used `joint1` at index `0`, readback
    `0.009999888017773628`, progress `0.9999888017772336`, with restore and
    settle true; RG2 gripper opened `finger_joint`,
    `left_inner_finger_joint`, and `right_inner_finger_joint`
  - IK selected `kawasaki_rs080n_relaxed_forward`, target pose
    `[0.7, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0]`,
    `end_effector_frame=gripper_center`, and `solution_count=6`; the first
    two attempted targets remain recorded as handled
    `ROBOT_SET_EE_TARGET_ERROR` no-converge rows
  - EE pose passed for requested `tool0`, resolved through
    `onrobot_rg2_base_link`, with attempted frames `["tool0"]`; cleanup and
    final health were responsive/stopped around `14ms`
  - this completes current-code IK target proof for all five candidate
    Kawasaki profiles, but it remains probe/IK telemetry only and does not
    prove or promote pick/place behavior
- Fresh phase-aware timeout validation worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - `unitree_z1` single-profile rerun with `timeout_s=25` completed in about
    `10.0s` with `overall_ok=true`; gripper/IK/EE pose were skipped
    unsupported, not treated as failures
  - `dofbot` single-profile rerun with `timeout_s=25` returned
    `ROBOT_PROBE_PROFILE_TIMEOUT`; evidence included
    `last_phase=warmup_step`, completed checks `stage_reset_stop`,
    `stage_reset`, `load`, `articulation`, and `simulation_play`,
    `profile_name=dofbot`, and `prim_path=/World/MCPProbe/dofbot`
  - `dofbot` timeout cleanup capped both `simulation_stop` and cleanup at
    `3s`, and the final status check returned `SIMULATION_STATUS_ERROR` after
    about `91.7s`
  - lifecycle cleanup later confirmed unambiguous ownership for port `[redacted]`,
    restarted instance-2 from old PID `[redacted]` to PID `[redacted]` in about `36.8s`,
    and restored `simulation_get_status` to `728ms`
- Fresh phase-operation timeout validation worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - pre-probe status returned in `21ms`, timeline stopped, and logs were
    cleared
  - `dofbot` single-profile rerun with `timeout_s=25` returned in about
    `23.3s` with `overall_ok=false`
  - `warmup_step.error_code=ROBOT_PROBE_WARMUP_STEP_TIMEOUT` and
    `warmup_step.evidence.timeout_kind=phase_operation`
  - no downstream `joint_config`, `joint_read`, `safe_nudge`, `gripper`, `ik`,
    or `ee_pose` checks appeared after the warmup timeout
  - cleanup evidence included
    `simulation_stop.error_code=ROBOT_PROBE_SIMULATION_STOP_TIMEOUT` and
    `cleanup.error_code=ROBOT_PROBE_CLEANUP_TIMEOUT`
  - final responsiveness failed: `simulation_get_status` returned
    `SIMULATION_STATUS_ERROR` after about `91.7s`
  - lifecycle recovery confirmed PID `[redacted]` was the unambiguously owned
    instance-2 process on port `[redacted]`, restarted it to PID `[redacted]` in about
    `24.2s`, and restored `simulation_get_status` to `25ms`
- Parent follow-up patch after the phase-operation worker:
  - dynamic `simulation_play` / `warmup_step` / `safe_nudge` timeout cleanup is
    now recorded as deferred lifecycle recovery instead of sending immediate
    `simulation_stop` / `stage_delete_prim` calls into a likely wedged Kit
    loop
  - unit coverage now asserts `ROBOT_PROBE_SIMULATION_STOP_DEFERRED`,
    `ROBOT_PROBE_CLEANUP_DEFERRED`, no downstream robot checks, no post-timeout
    stop/delete request, and batch abort reason
    `profile_timeout_cleanup_deferred`
  - this cleanup-deferred behavior was subsequently live-proven by the worker
    below
- Parent follow-up patch after result-classification audit:
  - phase-operation timeouts such as
    `warmup_step.error_code=ROBOT_PROBE_WARMUP_STEP_TIMEOUT` now classify the
    top-level probe row as `mcp_controllability=blocked_timeout` with
    `probe_capability_level=0` / `blocked_timeout`
  - this prevents dynamic warmup/play timeout rows from falling through to
    `load_articulation_only`, which could be overread as partial
    controllability evidence
  - unhandled per-profile probe exceptions in a batch now classify as
    `mcp_controllability=blocked_profile_error` with
    `probe_capability_level=0` / `blocked_profile_error`, while preserving the
    row-local `ROBOT_PROBE_PROFILE_ERROR` check and continuing later profiles
  - non-timeout dynamic phase failures, such as `simulation_play` or
    `warmup_step` returning `ok=false`, now classify as
    `mcp_controllability=blocked_phase_error` with
    `probe_capability_level=0` / `blocked_phase_error`
  - IK probe classification now mirrors EE-pose classification: missing Lula
    config/import support is skipped as unsupported, while a non-unsupported
    IK target/solver failure is preserved as a failed `ik` check instead of
    being hidden as unsupported
  - focused unit coverage asserts both single-profile and batch rows carry the
    blocked timeout classification, that hard-error rows remain distinct from
    load/articulation evidence, and that non-timeout play/warmup failures are
    blocked phase errors; this is static classification hardening, not new live
    robot evidence
- Fresh IK-classification smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`, MCP entry `[mcp-entry-redacted]`,
    MCP PID `[redacted]`, Kit port `[redacted]`, Kit PID `[redacted]`
  - `mcp_runtime_info`: `tool_count=143`,
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`,
    `stale_source_modules=[]`
  - `kit_app_start` attached to the already-running healthy instance; host
    health was responsive before, between probes, and after, with final
    `simulation_get_status.duration_ms=12`
  - single-profile probes with `reset_stage=true`, `safe_nudge=true`,
    `cleanup=true`, `dynamic_checks=true`, and `timeout_s=45`:
    `franka_panda`, `franka_fr3`, `factory_franka`, `ur10`,
    `kawasaki_rs007l`
  - all five rows returned `overall_ok=true`,
    `mcp_controllability=dynamic_joint_control`, and
    `probe_capability_level_name=ik_or_ee_telemetry`
  - `ur10` recorded missing gripper as row-local skipped/unsupported
    (`No gripper joints found`) while IK and EE pose succeeded
  - `kawasaki_rs007l` preserved non-unsupported IK target evidence:
    the `default` target returned `ROBOT_SET_EE_TARGET_ERROR` because Lula did
    not converge, then `kawasaki_relaxed_orientation` succeeded using
    `gripper_center`; EE pose resolved requested `tool0` through
    `onrobot_rg2_base_link`
  - this live smoke confirms probe classification/telemetry behavior only; it
    is not pick/place validation and does not promote any profile
- Parent follow-up discoverability patch:
  - `robot_list_arm_profiles` now exposes
    `known_dynamic_timeout_profiles` and
    `known_dynamic_timeout_profile_reasons`, derived from the same durable live
    timeout table used by
    `robot_probe_arm_profiles(static_only_for_known_dynamic_timeouts=true)`
  - the visible hazard list lets callers plan broad matrix refreshes without
    accidentally launching known host-degrading dynamic probes
  - the Isaac system prompt now also points agents to inspect those fields
    before broad profile batches
  - unit coverage asserts the hazard list is catalog-consistent and includes
    the current known dynamic-timeout rows; this is safety/discoverability
    hardening, not new robot controllability evidence
- Parent follow-up probe-mode planning patch:
  - `robot_list_arm_profiles` now also exposes
    `dynamic_probe_recommended_profiles` and
    `static_only_probe_recommended_profiles`
  - parent follow-up adds `recommended_probe_mode_by_profile` and
    `recommended_probe_mode_reasons` so each profile carries a direct planning
    mode (`dynamic_with_bounded_timeouts` or
    `static_only_known_dynamic_timeout`) plus the reason for that mode
  - the static-only recommendation group is exactly the known dynamic-timeout
    set, and the dynamic recommendation group plus static-only group partitions
    the built-in profile catalog
  - `mcp_runtime_info` now exposes `robot_arm_profiles_result_fields` so a
    no-Kit freshness gate can verify those list-profile result fields before a
    live matrix run
  - this is static/unit-tested planning metadata for safer broad refreshes; it
    does not prove dynamic joint control and does not validate pick/place
- Fresh no-Kit planning-field worker turn
  `[worker-id-redacted]` live-proved the new fields in a
  freshly loaded workspace-local MCP host without touching Kit:
  `mcp_runtime_info` reported MCP PID `[redacted]`, `tool_count=143`, fresh source,
  no restart requirement, no stale modules, and
  `robot_arm_profiles_result_fields` containing both
  `dynamic_probe_recommended_profiles` and
  `static_only_probe_recommended_profiles`; `robot_list_arm_profiles()` then
  returned normally in `222ms` with `count=41`, `validated_pick_place_profiles`
  still exactly `["franka_fr3"]`,
  `known_pick_place_blocker_profiles=["franka_panda","factory_franka"]`,
  `static_only_probe_recommended_profiles` exactly equal to
  `known_dynamic_timeout_profiles`, disjoint dynamic/static groups whose sizes
  were `29 + 12 = 41`, `ur20` static-only recommended, and `ur30` dynamic
  recommended. The worker made no Kit lifecycle, simulation, probe, raw REST,
  git, or file-edit calls. This proves no-Kit catalog planning behavior only,
  not robot MCP controllability or pick/place validation.
- Fresh deferred-cleanup validation worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, initial PID `[redacted]`
  - pre-probe status returned in `23ms`, timeline stopped, and logs were
    cleared
  - `dofbot` single-profile rerun with `timeout_s=25` returned in about
    `17.3s`, result `duration_ms=17014`, with `overall_ok=false`
  - `warmup_step.error_code=ROBOT_PROBE_WARMUP_STEP_TIMEOUT` and
    `warmup_step.evidence.timeout_kind=phase_operation`
  - no downstream `joint_config`, `joint_read`, `safe_nudge`, `gripper`, `ik`,
    or `ee_pose` checks appeared after the warmup timeout
  - cleanup was deferred as intended:
    `simulation_stop.error_code=ROBOT_PROBE_SIMULATION_STOP_DEFERRED`,
    `cleanup.error_code=ROBOT_PROBE_CLEANUP_DEFERRED`, and
    `cleanup.evidence.requires_lifecycle_recovery=true`
  - deferring cleanup did not keep the host responsive: final
    `simulation_get_status` returned `SIMULATION_STATUS_ERROR` after about
    `91.8s`
  - lifecycle recovery confirmed PID `[redacted]` was the unambiguously owned
    instance-2 process on port `[redacted]`; port `[redacted]` PID `[redacted]` was external and
    left untouched; restart created PID `[redacted]` in about `35.4s`, and final
    status returned in `584ms`
- Parent follow-up patch after deferred cleanup still degraded the host:
  - `robot_probe_arm_profile` and `robot_probe_arm_profiles` now accept
    `dynamic_checks`; default `true` preserves full load/joint/gripper/IK/EE
    probing
  - `dynamic_checks=false` performs load/articulation-only hazard triage,
    records physics-dependent checks as
    `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED`, cleans up without starting timeline
    physics, and keeps `overall_ok=false`
  - this is partial Level 1-2 evidence only, not probe-level MCP
    controllability and not pick/place validation
  - unit coverage is green; the worker below live-proves the behavior for
    `dofbot`; other hazardous rows still need static-only reruns before their
    load/articulation evidence is refreshed
- Fresh static-only hazard-triage validation worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - pre-probe `simulation_get_status` returned in `16ms`, timeline stopped
  - `dofbot` with `dynamic_checks=false`, `timeout_s=25`, `reset_stage=true`,
    `safe_nudge=true`, and `cleanup=true` completed in about `3.1s`
  - `load` and `articulation` succeeded with `has_articulation=true`
  - `simulation_play`, `warmup_step`, `joint_config`, `joint_read`,
    `safe_nudge`, `gripper`, `ik`, and `ee_pose` were all skipped with
    `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED`
  - `cleanup` succeeded; there was no phase-timeout or deferred-cleanup row
  - `overall_ok=false`, as required for load/articulation-only partial
    evidence
  - final `simulation_get_status` returned in `15ms`, timeline stopped; the
    host stayed responsive
  - WARN capture returned `3` entries and ERROR capture returned `1` entry:
    one USD stage reference-count warning, one dofbot material binding warning,
    and one `omni.ui.python` invalid null prim callback error from a
    property/camera/robot-poser UI rebuild path
- Parent follow-up static metadata patch:
  - `robot_get_joint_config_static` now exposes USD joint-prim metadata without
    calling articulation runtime initialization
  - `robot_probe_arm_profile(dynamic_checks=false)` records
    `static_joint_config` before marking runtime `simulation_play`,
    `warmup_step`, `joint_config`, `joint_read`, `safe_nudge`, `gripper`, `ik`,
    and `ee_pose` disabled
  - static joint config is diagnostic hazard-triage metadata only:
    `static_only=true`, `order_reliable=false`, no fallback to runtime joint
    APIs, no write-order proof, no MCP joint-control proof, and no pick/place
    validation
- Static USD metadata smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`
  - first fresh host PID was `[redacted]`; pre-probe status returned in `19ms`
    with the timeline stopped
  - initial `dofbot` static-only probe completed without host slowdown but
    returned `static_joint_config.dof_count=0`, which exposed that static USD
    joint-type matching was too narrow
  - WARN/ERROR capture then failed after about `91.7s` with
    `EXTENSION_LOGS_ERROR`; no reliable log counts were produced from that
    capture path
  - after suffix-based joint-type matching, the host was restarted to PID
    `55420`; a stale MCP-import client reached the static endpoint but surfaced
    `ROBOT_GET_STATIC_JOINT_CONFIG_ERROR` for `dofbot` because sparse USD
    numeric attributes included `None`
  - the same stale-client run proved a fallback `franka_panda` static-only
    path: `static_joint_config` succeeded with
    `source=usd_joint_prims_static`, `static_only=true`,
    `order_reliable=false`, `dof_count=10`, and first names
    `panda_finger_joint1`, `panda_finger_joint2`, `panda_joint1`,
    `panda_joint2`, `panda_joint3`
- Fresh MCP-import static metadata smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, existing owned Kit PID
    `55420`; no second Kit instance was launched
  - pre-probe status returned `ok=true` in about `18ms`, timeline stopped
  - `dofbot` with `dynamic_checks=false` succeeded for load, articulation,
    static joint config, and cleanup; post-probe status returned in about
    `14ms`
  - `static_joint_config` reported `source=usd_joint_prims_static`,
    `static_only=true`, `order_reliable=false`, `dof_count=13`, and first names
    `joint1`, `joint2`, `joint3`, `joint4`,
    `Wrist_Twist_RevoluteJoint`
  - this proves only static USD metadata extraction for `dofbot`; it does not
    prove dynamic joint read/write order, safe nudge, gripper control, IK,
    EE-pose, or pick/place behavior
- Fresh FactoryFranka pick/place proof attempt worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - pre-proof `simulation_get_status` returned in about `12ms`
  - `robot_install_pick_place_playback_demo(profile_name="factory_franka")`
    completed successfully for robot prim `/World/FactoryFranka`
  - immediate fit preflight passed: object bbox about
    `0.040 x 0.040 x 0.040 m`, fit limit `0.075 m`, and
    `uses_kinematic_carry=false`
  - the first Stop -> Play proof cycle did not produce durable pick/place
    proof: `robot_get_pick_place_demo_status` after playback returned an MCP
    error after about `91.7s`
  - the parent nudge classified the first cycle as timeout/non-proof; no
    `done/lifted/placed` cycle summary was captured
  - follow-up `simulation_stop` also returned `SIMULATION_CONTROL_ERROR` after
    about `91.7s`, showing the live host degraded after the playback timeout
  - WARN capture, ERROR capture, and final pre-cleanup
    `simulation_get_status` each timed out after about `91.7s`; WARN/ERROR
    counts are unavailable because the extension log path was unresponsive
  - lifecycle cleanup found unambiguous ownership for port `[redacted]` / PID
    `12592` and left an external instance on port `[redacted]` alone; `kit_app_restart`
    recovered the owned MCP instance as PID `[redacted]`, and post-restart
    `simulation_get_status` returned in about `20ms`
  - this attempt blocks, rather than promotes, `factory_franka`
- Post-failure parent hardening:
  - `robot_get_pick_place_demo_status(timeout_s=...)` now applies a
    caller-side timeout and records
    `ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT` instead of letting a status
    poll consume the full REST/MCP timeout budget
  - a follow-up extension hardening patch now reports cached
    `diagnostics.playback_progress` on playback status: controller event tick
    counts, first/last steps per event, and bounded samples of object center,
    lift delta, and distance-to-target
  - playback status uses the bbox metrics cached during install/reset/tick/final
    refresh rather than doing a fresh bbox traversal in the status endpoint; the
    next FactoryFranka live debug run should inspect those progress samples
    before and during any bounded proof cycle
  - this is proof-loop diagnostics hardening only; it does not validate
    `factory_franka` pick/place
- Fresh playback-progress diagnostics-surface smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`; the worker saw owned Kit PID
    `60548` plus non-owned port `[redacted]` and restarted only the owned instance
    because `validation_api` changed
  - `kit_app_restart` completed in about `38.9s`, cleared four caches, and
    started new Kit PID `[redacted]`; post-restart pre-install status was
    responsive/stopped in `146ms`
  - MCP runtime was intentionally noted as stale for `module_tools` and
    `prompts` because parent docstring/prompt files were newer than import, but
    the exposed tools were sufficient for this Kit-side diagnostics smoke
  - installed validated `franka_fr3` at `/World/FR3ProgressDiag` with object
    `/World/PickCubeProgressDiag`; no `simulation_play` was run
  - immediate `robot_get_pick_place_demo_status(timeout_s=1.0)` returned in
    `19ms` and included `diagnostics.playback_progress` with
    `current_event=0`, `current_event_ticks=0`, `sample_interval_steps=30`,
    `sample_limit=32`, and zero samples before playback
  - object fit remained OK: measured bbox about
    `0.040 x 0.040 x 0.040 m`, fit limit `0.075 m`, fit axis `x`
  - final status stayed responsive/stopped in `12ms`; WARN/ERROR capture was
    skipped because install/status/final health did not fail or degrade
  - this proves only the live diagnostics surface for cached bbox metrics and
    `diagnostics.playback_progress`; it is not pick/place validation and does
    not promote any profile
- Bounded playback-status smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - attached to the existing healthy instance in about `2.2s`; initial
    `simulation_get_status` returned in `24ms`
  - live `robot_get_pick_place_demo_status(timeout_s=0.25)` accepted the new
    argument and returned the expected no-demo-installed module error in
    about `20ms`, not a schema rejection or long REST timeout
  - installed `franka_fr3` bounded smoke demo at `/World/FR3BoundedStatus`;
    immediate status with `timeout_s=1.0` returned in about `37ms`,
    `object_fit_ok=true`, bbox `0.040 x 0.040 x 0.040 m`, fit limit
    `0.075 m`, and `uses_kinematic_carry=false`
  - bounded smoke polls with `timeout_s=1.0` stayed fast (`47ms`, `46ms`,
    `37ms`, `19ms`) and reached `status=done`, `steps=917`,
    `controller_event=10`, `lifted=true`, `placed=true`; no
    `ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT` occurred
  - this is tool-surface/bounded-smoke evidence only, not a new durable
    pick/place proof or promotion
- Bounded FactoryFranka playback-status diagnostic worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`
  - attached to existing PID `[redacted]`; port `[redacted]` / PID `[redacted]` was
    non-owned and left untouched; initial `simulation_get_status` returned in
    about `24ms`
  - live `robot_get_pick_place_demo_status(timeout_s=0.25)` accepted the new
    argument and returned in about `15ms`; it observed leftover FR3 state
    rather than a schema rejection or long REST timeout
  - installed `factory_franka` bounded diagnostic demo at
    `/World/FactoryFrankaBoundedDiag` in about `2081ms`, with
    `support_status=candidate_pick_place`,
    `controller_strategy=same_family_franka_candidate`,
    `object_fit_ok=true`, bbox about `0.040 x 0.040 x 0.040 m`, fit limit
    `0.075 m`, and `uses_kinematic_carry=false`
  - immediate `robot_get_pick_place_demo_status(timeout_s=1.0)` returned in
    about `14ms`: `status=idle`, `steps=0`, `controller_event=0`, fit still OK
  - one bounded diagnostic cycle stopped and reset quickly, then
    `simulation_play` returned `passed` in about `16ms` while reporting
    `is_playing=false`
  - the first bounded playback status poll returned
    `ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT` after about `1006ms`
  - follow-up `simulation_stop` degraded to `SIMULATION_CONTROL_ERROR` after
    about `91.8s`, supporting the hypothesis that the bounded caller timeout
    records the failure quickly but the FactoryFranka playback/controller path
    still degrades the Kit host
  - pre-restart WARN/ERROR capture was skipped because the REST path had
    already shown degraded responsiveness; lifecycle cleanup restarted only the
    owned port `[redacted]` instance from PID `[redacted]` to PID `[redacted]`, final
    `simulation_get_status` returned in about `26ms`, and post-restart WARN
    capture returned `0` entries
  - this is bounded timeout/failure evidence only; it does not create durable
    `factory_franka` pick/place proof or promotion
- Fresh direct FactoryFranka playback-progress diagnostic worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - fresh MCP runtime PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`, `stale_source_modules=[]`, and the
    low-level direct install schema accepted `robot_description`,
    `max_grasp_width_m`, and `fit_clearance_m`
  - no Kit instance was running; `kit_app_start` started fresh owned port
    `8111` / Kit PID `[redacted]` in about `23.1s`
  - direct diagnostic path loaded `factory_franka` from its S3 profile URL at
    `/World/FactoryFranka`; `robot_load` returned `ok=true` and
    `has_articulation=true`
  - low-level `robot_install_franka_pick_place_playback_demo` accepted the new
    arguments and returned `status=idle`, `object_fit_ok=true`,
    `object_fit_limit_m=0.075`, `object_fit_measured_m=0.0399999991`, and
    `uses_kinematic_carry=false`
  - immediate bounded status returned in about `25ms` with
    `diagnostics.playback_progress` present, `current_event=0`,
    `current_event_ticks=0`, and no samples before playback
  - after `simulation_play`, the first bounded poll returned in about `18ms`
    with `status=picking`, `steps=162`, `controller_event=1`, and progress
    counts `{0:124, 1:38}`; event `1` began at step `125`, samples showed no
    lift, and distance-to-target stayed about `0.715914`
  - the second and final bounded poll returned in about `25ms` as a controlled
    tool failure, not a host timeout: status `failed`, last error that the
    official controller did not finish within `240` playback ticks,
    `done=false`, `lifted=false`, `placed=false`,
    `max_lift_delta=0.0`, `final_distance=0.715914`, and
    `controller_event=1`
  - host health stayed responsive: pre/post `simulation_get_status` returned
    in about `27ms`/`21ms`, and `simulation_stop` completed in about `23ms`
  - WARN/ERROR capture after the bounded failure returned quickly and included
    USD reference-count / diagnostics-muted warnings plus a PhysX TGS
    articulation velocity-iterations warning for `/World/FactoryFranka`; no
    host degradation was observed
  - this improves FactoryFranka controller-step evidence and proves the new
    direct proof arguments in a fresh MCP host, but it is still not durable
    pick/place validation and does not promote `factory_franka`
- Parent follow-up patch after the fresh direct FactoryFranka diagnostic:
  - playback progress diagnostics now record joint readback motion and official
    action joint-target deltas (`max_joint_delta_from_initial`,
    `max_action_joint_position_delta`, `action_joint_positions_seen`, and
    per-sample joint/action fields)
  - this is diagnostic-surface hardening only; promotion still requires durable
    live grasp/lift/place proof
- Fresh direct FactoryFranka joint/action telemetry worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`, MCP entry `[mcp-entry-redacted]`
  - MCP runtime was fresh: PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`, `stale_source_modules=[]`, and
    `restart_required=false`
  - the previously running owned Kit on port `[redacted]` / PID `[redacted]` was
    restarted only because `omni.mycompany.validation_api` changed; fresh Kit
    PID `[redacted]` was ready in about `26.5s`
  - pre-run health was responsive/stopped in about `31ms`; process inventory
    showed only the owned port `[redacted]` Kit
  - direct diagnostic path loaded `factory_franka` at
    `/World/FactoryFrankaTelemetryDiag` from its S3 profile URL; `robot_load`
    returned `ok=true` and `has_articulation=true`
  - low-level install at `/World/PickCubeTelemetryDiag` accepted
    `robot_description="Franka"`, `max_grasp_width_m=0.08`,
    `fit_clearance_m=0.005`, `object_size=0.04`, and `max_steps=300`;
    fit/carry preflight returned `object_fit_ok=true`,
    `object_fit_limit_m=0.075`, `object_fit_measured_m=0.0399999991`, and
    `uses_kinematic_carry=false`
  - idle status proved the new fields loaded in the extension:
    `max_joint_delta_from_initial=0.0`,
    `max_action_joint_position_delta=0.0`, and
    `action_joint_positions_seen=false`
  - playback poll 1 returned `status=picking`, `steps=217`,
    `controller_event=1`, event counts `{0:124, 1:93}`, event first steps
    `{0:1, 1:125}`, event last steps `{0:124, 1:217}`,
    `max_joint_delta_from_initial=2.433140754699707`,
    `max_action_joint_position_delta=0.02078986167907715`, and
    `action_joint_positions_seen=true`
  - playback poll 2 was a terminal bounded failure:
    `status=failed`, `steps=300`, `controller_event=1`, event counts
    `{0:124, 1:176}`, event first steps `{0:1, 1:125}`, event last steps
    `{0:124, 1:300}`, `max_joint_delta_from_initial=2.7101761177182198`,
    `max_action_joint_position_delta=0.02078986167907715`, and
    `action_joint_positions_seen=true`
  - representative samples show official action targets and joint motion but no
    object lift: step `1` event `0` had joint max abs `0.0365753472`, action
    delta max abs `0.0197449923`, action count `7`, lift `-0.002725`, and
    distance `0.715896`; step `125` event `1` had joint max abs
    `1.8500274420`, action delta max abs `0.0148808956`, action count `7`,
    lift `-0.005750`, and distance `0.715914`; step `300` event `1` had
    joint max abs `2.7101761177`, action delta max abs `0.0060884058`, action
    count `7`, lift `-0.005750`, and distance `0.715914`
  - object result stayed unvalidated: `done=false`, `lifted=false`,
    `placed=false`, `final_distance=0.7159140101325272`, and
    `max_lift_delta=0.0`
  - post-run health stayed responsive: status while playing returned in about
    `30ms`, `simulation_stop` returned in about `25ms`, final stopped status
    returned in about `12ms`, and WARN capture returned quickly with four
    warnings (USD reference-count, muted USD diagnostics, and a PhysX TGS
    articulation velocity-iteration warning for
    `/World/FactoryFrankaTelemetryDiag`)
  - this narrows the FactoryFranka event-1 stall: the official controller is
    emitting joint targets and the articulation readback moves substantially,
    but the object never lifts or moves toward placement; this is not
    pick/place validation and does not promote `factory_franka`
- Parent follow-up patch after the joint/action telemetry rerun:
  - playback progress diagnostics now record the observed gripper/end-effector
    world position, minimum end-effector distance to pick and target, and
    matching per-sample reach distances
  - this is diagnostic-surface hardening only; it does not make
    `factory_franka` validated or route it through profile-selected playback
- Fresh direct FactoryFranka end-effector reach telemetry worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`, MCP entry `[mcp-entry-redacted]`
  - MCP runtime was fresh: PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`, `stale_source_modules=[]`, and
    `restart_required_for_latest_mcp_code=false`
  - the owned Kit on port `[redacted]` was restarted only to reload
    `omni.mycompany.validation_api`: old PID `[redacted]`, fresh PID `[redacted]`,
    ready in about `26.6s`
  - pre-run health was responsive/stopped in about `15ms`; final health was
    responsive/stopped in about `19ms`
  - direct diagnostic path loaded `factory_franka` at
    `/World/FactoryFrankaEETelemetryDiag`; `robot_load` returned `ok=true`
    and `has_articulation=true`
  - low-level install at `/World/PickCubeEETelemetryDiag` accepted
    `robot_description="Franka"`, `max_grasp_width_m=0.08`,
    `fit_clearance_m=0.005`, `object_size=0.04`, and `max_steps=300`;
    fit/carry preflight returned `object_fit_ok=true`, reason
    `"Object bbox fits within gripper opening."`, axis `x`, limit `0.075`,
    and measured width `0.03999999910593033`
  - idle status proved the new EE fields loaded in the extension:
    `end_effector_pose_seen=false` with pick/target reach distances `null`
    before playback
  - terminal playback result stayed a bounded failure: `status=failed`,
    `last_error` reported the official controller did not finish within `300`
    playback ticks, `steps=300`, `controller_event=1`, event counts
    `{0:124, 1:176}`, event first steps `{0:1, 1:125}`, event last steps
    `{0:124, 1:300}`, `max_joint_delta_from_initial=2.7101761177182198`,
    `max_action_joint_position_delta=0.02078986167907715`, and
    `action_joint_positions_seen=true`
  - new EE reach telemetry was live and bounded:
    `end_effector_pose_seen=true`,
    `min_end_effector_distance_to_pick=0.09593506298402886`, and
    `min_end_effector_distance_to_target=0.7506843518273172`
  - representative samples now show the gripper approaches the pick point but
    still does not lift the object: step `1` event `0` EE position
    `[0.1036605984, 0.0023944108, 0.8794910312]`, EE-to-pick
    `0.9449406693`, EE-to-target `0.9864109439`; step `125` event `1` EE
    position `[0.4225837290, 0.3065714240, 0.4600594938]`, EE-to-pick
    `0.4588738024`, EE-to-target `0.7876943716`; step `300` event `1` EE
    position `[0.3023269773, 0.3810941875, 0.1107262522]`, EE-to-pick
    `0.0959350630`, EE-to-target `0.7506843518`
  - object result stayed unvalidated: `done=false`, `lifted=false`,
    `placed=false`, `final_distance=0.7159140101325272`, and
    `max_lift_delta=0.0`
  - WARN capture returned quickly with four warnings (USD reference-count, two
    muted USD diagnostics warnings, and a PhysX articulation velocity-iteration
    warning for `/World/FactoryFrankaEETelemetryDiag`); no host degradation was
    observed
  - this narrows the FactoryFranka failure again: the hand reaches close to the
    pick point but the object is never lifted, so the next adapter work should
    focus on grasp/contact/timing rather than controller command emission; this
    is not pick/place validation and does not promote `factory_franka`
- Fresh direct FactoryFranka explicit timing worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`, MCP entry `[mcp-entry-redacted]`
  - MCP runtime was fresh: PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`, `stale_source_modules=[]`, and
    `restart_required=false`
  - the owned Kit on port `[redacted]` was reused without restart: PID `[redacted]`;
    pre-run and final health were responsive/stopped in about `18ms`
  - direct diagnostic path loaded `factory_franka` at
    `/World/FactoryFrankaTimingDiag`; `robot_load` returned `ok=true` and
    `has_articulation=true`
  - low-level install at `/World/PickCubeTimingDiag` used
    `max_steps=1000` and explicit
    `events_dt=[0.008,0.005,1.0,0.1,0.05,0.05,0.0025,1.0,0.008,0.08]`;
    fit/carry preflight returned `object_fit_ok=true`, axis `x`, limit
    `0.075`, measured width `0.03999999910593033`, and
    `uses_kinematic_carry=false`
  - poll 1 reached `status=picking`, `steps=152`, `controller_event=1`,
    event counts `{0:124, 1:28}`, `current_event_ticks=28`,
    `min_end_effector_distance_to_pick=0.38101521029483304`,
    `min_end_effector_distance_to_target=0.7876339876880483`,
    `max_joint_delta_from_initial=2.1892025470733643`,
    `max_action_joint_position_delta=0.02078986167907715`,
    `done=false`, `lifted=false`, `placed=false`,
    `final_distance=0.7159140101325272`, and `max_lift_delta=0.0`
  - terminal poll reached `status=failed`, `steps=325`,
    `controller_event=2`, with event counts `{0:124, 1:200, 2:1}`,
    event first steps `{0:1, 1:125, 2:325}`, event last steps
    `{0:124, 1:324, 2:325}`, `current_event_ticks=1`,
    `min_end_effector_distance_to_pick=0.057429154653559675`,
    `min_end_effector_distance_to_target=0.7482561028148201`,
    `max_joint_delta_from_initial=2.783524878323078`,
    `max_action_joint_position_delta=0.02078986167907715`,
    `done=false`, `lifted=false`, `placed=false`,
    `final_distance=0.0`, and `max_lift_delta=0.0`
  - this proved the earlier `max_steps=300` run was partly under-budget:
    the explicit timing path advanced into event `2` and the hand reached
    within about `0.0574m` of the pick point, but the object was still not
    lifted or placed
  - terminal failure was a telemetry/action parsing bug in
    `_float_sequence(getattr(actions, "joint_positions", None))`:
    `float() argument must be a string or a real number, not 'list'`;
    this is diagnostic failure evidence, not pick/place validation, and it
    does not promote `factory_franka`
- Parent follow-up patch after the explicit timing diagnostic:
  - `_float_sequence` and `_int_sequence` now flatten nested numeric
    containers before scalar conversion, covering the official controller
    action shape that appeared at event `2`
  - focused regression coverage now exercises nested action joint positions,
    nested joint indices, and nested initial joint positions through
    `_franka_pick_place_demo_joint_progress`
  - this is telemetry hardening only; it does not make `factory_franka`
    validated or route it through profile-selected playback
- Post-fix direct FactoryFranka explicit timing worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`, MCP entry `[mcp-entry-redacted]`
  - MCP runtime was fresh before live work: PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - the owned Kit on port `[redacted]` was restarted from PID `[redacted]` to fresh PID
    `72288` to load the patched validation API extension; startup took about
    `26.5s`, and post-restart health was responsive/stopped in about `21ms`
  - direct diagnostic path loaded `factory_franka` at
    `/World/FactoryFrankaTimingPostFix`; install at
    `/World/PickCubeTimingPostFix` used the same `max_steps=1000` and explicit
    ten-phase `events_dt=[0.008,0.005,1.0,0.1,0.05,0.05,0.0025,1.0,0.008,0.08]`;
    install returned idle with `object_fit_ok=true`, reason
    `"Object bbox fits within gripper opening."`, initial axis `x`, limit
    `0.075`, measured `0.03999999910593033`, and
    `uses_kinematic_carry=false`
  - poll 1 reached `status=picking`, `steps=184`, `controller_event=1`,
    `current_event_ticks=60`, event counts `{0:124, 1:60}`,
    `max_joint_delta=2.3533387184143066`,
    `max_action_delta=0.02078986167907715`,
    `action_joint_positions_seen=true`, `end_effector_pose_seen=true`,
    `min_end_effector_distance_to_pick=0.3271833767909723`,
    `min_end_effector_distance_to_target=0.7876339876880483`,
    `done=false`, `lifted=false`, `placed=false`,
    `final_distance=0.7159140101325272`, and `max_lift_delta=0.0`
  - poll 2 advanced past the prior crash point to `status=placing`,
    `steps=340`, `controller_event=4`, `current_event_ticks=4`, event counts
    `{0:124, 1:200, 2:1, 3:11, 4:4}`,
    `max_joint_delta=2.7967487648129463`,
    `max_action_delta=0.6218158416450024`,
    `min_end_effector_distance_to_pick=0.04157026071353777`,
    `min_end_effector_distance_to_target=0.738057256147102`,
    `done=false`, `lifted=false`, `placed=false`,
    `final_distance=0.7159084660154741`, and `max_lift_delta=0.0`; the
    previous `float() argument must be a string or a real number, not 'list'`
    failure did not recur
  - poll 3 reached `status=placing`, `steps=552`, `controller_event=6`,
    `current_event_ticks=176`, event counts
    `{0:124, 1:200, 2:1, 3:11, 4:20, 5:20, 6:176}`,
    `min_end_effector_distance_to_pick=0.041107170889927866`,
    `min_end_effector_distance_to_target=0.2654902900263401`,
    `done=false`, `lifted=false`, `placed=false`,
    `final_distance=0.7056631767940493`, and `max_lift_delta=0.0`
  - final captured poll reached `status=placing`, `steps=806`,
    `controller_event=8`, `current_event_ticks=28`, event counts
    `{0:124, 1:200, 2:1, 3:11, 4:20, 5:20, 6:401, 7:1, 8:28}`,
    `min_end_effector_distance_to_pick=0.041107170889927866`,
    `min_end_effector_distance_to_target=0.039860781501272396`,
    `done=false`, `lifted=false`, `placed=false`,
    `final_distance=0.7056631767940493`, and `max_lift_delta=0.0`; final
    captured object center was
    `[0.29903602600097656, 0.33930206298828125, 0.019999904558062553]`
  - after a worker context compaction, the parent requested bounded cleanup;
    `simulation_stop` returned in about `25ms` and final
    `simulation_get_status` returned with `is_playing=false`,
    `is_stopped=true`, `current_time=0.0`, and responsiveness about `17ms`
  - WARN/ERROR logs were not additionally captured during finalization because
    the latest worker instruction allowed only stop/health actions
  - this row proves the parser fix and later-event progression through event
    `8`, but the object still was not lifted or placed in captured evidence;
    no durable pick/place proof and no support promotion are claimed
- Parent follow-up patch after the post-fix explicit timing diagnostic:
  - FactoryFranka playback progress diagnostics now record current gripper
    aperture, action gripper aperture when available, object-width margins,
    and representative per-sample gripper joint positions
  - focused regression coverage exercises aperture and object-width margin
    summarization without requiring live Kit
  - this is telemetry hardening only; it does not make `factory_franka`
    validated or route it through profile-selected playback
- Fresh direct FactoryFranka gripper aperture telemetry worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`, MCP entry `[mcp-entry-redacted]`
  - MCP runtime was fresh before live work: PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - the owned Kit on port `[redacted]` was restarted from PID `[redacted]` to PID
    `42336` to load the patched validation API extension; startup took about
    `26.5s`, and final host health after stop stayed responsive/stopped in
    about `15ms`
  - direct diagnostic path loaded `factory_franka` at
    `/World/FactoryFrankaApertureDiag`; install at
    `/World/PickCubeApertureDiag` used `max_steps=1000` and explicit
    ten-phase `events_dt=[0.008,0.005,1.0,0.1,0.05,0.05,0.0025,1.0,0.008,0.08]`
  - fit/carry preflight returned `object_fit_ok=true`, reason
    `"Object bbox fits within gripper opening."`, initial axis `x`, limit
    `0.075`, measured width `0.03999999910593033`, and
    `uses_kinematic_carry=false`
  - final captured poll reached `status=placing`, `steps=815`,
    `controller_event=8`, event counts
    `{0:124, 1:200, 2:1, 3:11, 4:20, 5:20, 6:401, 7:1, 8:37}`,
    first steps `{0:1, 1:125, 2:325, 3:326, 4:337, 5:357, 6:377, 7:778, 8:779}`,
    last steps `{0:124, 1:324, 2:325, 3:336, 4:356, 5:376, 6:777, 7:778, 8:815}`,
    and `current_event_ticks=37`
  - EE/action telemetry still showed approach and command motion:
    `end_effector_pose_seen=true`,
    `min_end_effector_distance_to_pick=0.041107170889927866`,
    `min_end_effector_distance_to_target=0.039860781501272396`,
    `max_joint_delta_from_initial=2.7967487648129463`,
    `max_action_joint_position_delta=0.6218158416450024`, and
    `action_joint_positions_seen=true`
  - new gripper telemetry was live:
    `gripper_aperture_seen=true`, `action_gripper_aperture_seen=false`,
    `min_gripper_aperture_m=0.0001669081847239795`,
    `max_gripper_aperture_m=0.08000793680548668`,
    `min_action_gripper_aperture_m=null`,
    `max_action_gripper_aperture_m=null`,
    `min_gripper_object_width_margin_m=-0.04489676958324096`, and
    `min_action_gripper_object_width_margin_m=null`
  - representative samples show the gripper aperture crossing the object width:
    step `337`/event `4` aperture `0.05671320669353008`, object width
    `0.03999999910593033`, margin `0.016713207587599754`; step `377`/event
    `6` aperture `0.02929834336683257`, object width
    `0.04506372617290355`, margin `-0.015765382806070982`; step `778`/event
    `7` aperture `0.00016724588931538165`, object width
    `0.04506373239161032`, margin `-0.04489648650229494`; step `810`/event
    `8` aperture `0.08000001683831215`, object width
    `0.04506373239161032`, margin `0.034936284446701826`
  - object outcome remained `done=false`, `lifted=false`, `placed=false`,
    `final_distance=0.7056631767940493`, `max_lift_delta=0.0`, with final
    captured object center
    `[0.29903602600097656, 0.33930206298828125, 0.019999904558062553]`
  - the prior nested action parse failure did not recur through event `8` /
    step `815`; WARN/ERROR logs were not captured because no host degradation
    or terminal failure occurred during the bounded run
  - this row proves gripper aperture/object-width telemetry, not grasp success:
    the gripper closes below object width in telemetry, but the object is not
    lifted or placed in captured evidence; no durable pick/place proof and no
    support promotion are claimed
- Fresh direct FactoryFranka grasp-geometry sweep worker, thread
  `[worker-id-redacted]`, turn
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`, MCP entry `[mcp-entry-redacted]`
  - MCP runtime was fresh before the sweep: PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - attached to the already-owned Kit on port `[redacted]`, PID `[redacted]`; no restart
    was needed for this sweep, and final host health after Variant F stayed
    responsive/stopped in about `19ms`
  - all variants used the direct low-level FactoryFranka playback installer
    with `uses_kinematic_carry=false`, the FactoryFranka S3 asset,
    `object_size=0.04`, `max_grasp_width_m=0.08`,
    `fit_clearance_m=0.005`, `max_steps=1000`, explicit ten-phase
    `events_dt=[0.008,0.005,1.0,0.1,0.05,0.05,0.0025,1.0,0.008,0.08]`,
    object initial position `[0.3,0.35,0.02575]`, and target position
    `[0.45,-0.35,0.02575]`
  - Variant A `baseline_repeat` was captured at step `433`, event `6`,
    `status=placing`, with `done=false`, `lifted=false`, `placed=false`,
    min EE pick/target distances about `0.041107m` / `0.520182m`,
    `final_distance=0.705663`, `max_lift_delta=0.0`, min gripper aperture
    about `0.000166908m`, and min object-width margin about `-0.04489677m`
  - Variant B `explicit_center_high` used `picking_position=[0.3,0.35,0.045]`
    and reached terminal failed step `917`, event `10`, with last error
    `"Object was not lifted..."`; `done=true`, but `lifted=false` and
    `placed=false`, min EE pick/target distances about `0.041073m` /
    `0.039853m`, `final_distance=0.715413`, and `max_lift_delta=0.0`
  - Variant C `explicit_center_low` used `picking_position=[0.3,0.35,0.020]`
    and was captured at step `908`, event `9`, with `done=false`,
    `lifted=false`, `placed=false`, min EE pick/target distances about
    `0.041093m` / `0.039861m`, `final_distance=0.705652`, and
    `max_lift_delta=0.0`
  - Variant D `offset_down_2cm` used `end_effector_offset=[0.0,0.0,-0.02]`
    and was captured at step `912`, event `9`, with `done=false`,
    `lifted=false`, `placed=false`, min EE pick/target distances about
    `0.040109m` / `0.028165m`, `final_distance=0.708746`, and
    `max_lift_delta=0.0`; this was the best target-distance result in the
    sweep but still not proof
  - Variant E `offset_up_2cm` used `end_effector_offset=[0.0,0.0,0.02]`
    and was captured at step `818`, event `8`, with `done=false`,
    `lifted=false`, `placed=false`, min EE pick/target distances about
    `0.058505m` / `0.059840m`, `final_distance=0.709968`, and
    `max_lift_delta=0.0`
  - Variant F `scriptnode_orientation_hint` used
    `picking_position=[0.3,0.35,0.020]` and
    `end_effector_orientation=[0.0,1.0,0.0,0.0]`; it reached terminal failed
    step `917`, event `10`, with last error `"Object was not lifted..."`,
    `done=true`, but `lifted=false` and `placed=false`, min EE pick/target
    distances about `0.041052m` / `0.197405m`, `final_distance=0.716193`,
    and `max_lift_delta=0.0`
  - representative F samples showed the gripper crossing the object width
    without lift: step `337`/event `4` aperture `0.056095868`, margin
    `0.016095869`; step `357`/event `5` aperture `0.041729832`, margin
    `0.001290119`; step `377`/event `6` aperture `0.033319041`, margin
    `-0.007120558`; step `779`/event `8` aperture `0.000167316`, margin
    `-0.040272293`
  - Variant G was not run because F did not lift and did not improve the
    target-distance/contact path versus D
  - this row narrows FactoryFranka grasp geometry again: explicit
    pick-height, EE offset, and the prior FR3 ScriptNode orientation hint do
    not produce durable lift/place proof in this low-level playback path; no
    support promotion is claimed
- Parent follow-up patch after the grasp-geometry sweep:
  - FactoryFranka direct run and installed playback diagnostics now record
    `diagnostics.requested_pick_strategy`, including requested picking
    position/source, object initial position, target position, resolved hover
    height and source, EE offset/orientation, events_dt, max_steps, and
    reset-on-play when applicable
  - focused regression coverage records explicit geometry requests without
    requiring live Kit
  - this is telemetry hardening only; it does not make `factory_franka`
    validated or route it through profile-selected playback
- Fresh direct FactoryFranka requested-strategy telemetry-surface smoke,
  thread `[worker-id-redacted]`:
  - after the parent telemetry patch, the worker restarted only its owned
    `instance-1` Kit on port `[redacted]`, replacing PID `[redacted]` with PID `[redacted]`;
    the restarted host was ready in about `26.7s`
  - MCP runtime was fresh before the smoke: `tool_count=143`,
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - installed an idle direct FactoryFranka demo at
    `/World/FactoryFrankaStrategySmoke` with object
    `/World/PickCubeStrategySmoke`; no playback cycle was run
  - immediate `robot_get_pick_place_demo_status(timeout_s=1.0)` returned
    `status=idle`, `steps=0`, `current_event=0`, `object_fit_ok=true`,
    `fit_axis=x`, `fit_measured_extent=0.03999999910593033`,
    `fit_limit=0.075`, and `uses_kinematic_carry=false`
  - the live status response exposed
    `diagnostics.requested_pick_strategy` with
    `picking_position_source=explicit`,
    `picking_position=[0.3, 0.35, 0.02]`,
    `object_initial_position=[0.3, 0.35, 0.02575]`,
    `target_position=[0.45, -0.35, 0.02575]`,
    `end_effector_initial_height=0.3`,
    `end_effector_initial_height_source=official_default`,
    `end_effector_offset=[0.0, 0.0, -0.019999999552965164]`,
    `end_effector_orientation=[0.0, 1.0, 0.0, 0.0]`,
    `events_dt=[0.008, 0.005, 1.0, 0.1, 0.05, 0.05, 0.0025, 1.0, 0.008, 0.08]`,
    `max_steps=1000`, and `reset_on_play=true`
  - final `simulation_get_status` after cleanup stayed responsive in about
    `20ms`
  - this proves the requested-strategy diagnostics are live-visible after
    restart; it is not playback proof, lift/place evidence, or a
    FactoryFranka promotion
- Parent follow-up patch after the requested-strategy telemetry smoke:
  - FactoryFranka playback progress diagnostics now record
    `min_end_effector_distance_to_object`,
    `gripper_closed_on_object_width_seen`,
    `min_end_effector_distance_to_object_during_closed_gripper`, and
    `min_end_effector_xy_distance_to_object_during_closed_gripper`
  - per-sample progress rows also record EE-to-object distance, XY
    EE-to-object distance, and whether the observed gripper aperture was at or
    below the measured object width
  - focused static regression coverage verifies these contact-window fields
    without live Kit; the next live FactoryFranka run still must prove actual
    grasp, lift, and place before any promotion
- Fresh direct FactoryFranka contact-window diagnostics smoke, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`; fresh MCP runtime PID `[redacted]` reported
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - no running Kit instances were present, so the worker started a fresh owned
    Kit on port `[redacted]`, PID `[redacted]`; no restart or non-owned process mutation
    was needed
  - loaded the FactoryFranka USD at
    `/World/FactoryFrankaContactTelemetry` and installed the direct low-level
    playback demo for object `/World/PickCubeContactTelemetry` with
    `object_size=0.04`, `max_grasp_width_m=0.08`, and
    `fit_clearance_m=0.005`
  - immediate pre-playback `robot_get_pick_place_demo_status(timeout_s=1.0)`
    exposed `diagnostics.playback_progress` with all four contact-window
    fields present:
    `min_end_effector_distance_to_object=null`,
    `gripper_closed_on_object_width_seen=false`,
    `min_end_effector_distance_to_object_during_closed_gripper=null`, and
    `min_end_effector_xy_distance_to_object_during_closed_gripper=null`
  - a short bounded sample (`simulation_play`,
    `simulation_step_observe(frames=120)`, status, then `simulation_stop`)
    stayed responsive and populated the new telemetry:
    `min_end_effector_distance_to_object=0.041107170889927866`,
    `gripper_closed_on_object_width_seen=true`,
    `min_end_effector_distance_to_object_during_closed_gripper=0.058858394036590496`,
    and
    `min_end_effector_xy_distance_to_object_during_closed_gripper=0.006803149706765672`
  - final status remained responsive and stopped, but the sample did not
    complete pick/place: final demo status was `placing`, `done=false`,
    `placed=false`, `lifted=false`, and `max_lift_delta=0.0`
  - this proves the contact-window diagnostic fields are live-visible and can
    populate during a bounded FactoryFranka playback sample; it is not durable
    pick/place validation and does not promote `factory_franka`
- Parent follow-up patch after the contact-window diagnostics smoke:
  - `diagnostics.playback_progress.contact_window` now classifies the
    closed-gripper window as one of:
    `no_closed_gripper_width_window`,
    `closed_gripper_width_window_missing_ee_distance`,
    `closed_gripper_width_window_not_xy_aligned`,
    `closed_gripper_width_window_inside_bbox_sphere`, or
    `closed_gripper_width_window_xy_aligned_outside_bbox_sphere`
  - the classification also reports object grasp width, object bbox half
    diagonal, XY margin to object half-width, and 3D distance margin to the
    object bbox sphere
  - focused static coverage includes a live-shaped FactoryFranka value set
    from the 120-frame sample, classifying it as
    `closed_gripper_width_window_xy_aligned_outside_bbox_sphere`; this is a
    triage clue for the next FactoryFranka adapter attempt, not validation
- Fresh direct FactoryFranka contact-window classification recheck, thread
  `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-1`, MCP entry
    `[mcp-entry-redacted]`; MCP PID `[redacted]` was fresh with
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - because the parent changed `omni.mycompany.validation_api`, the worker
    restarted only the owned Kit on port `[redacted]` from PID `[redacted]` to PID
    `38820`; no non-owned instances were touched
  - direct low-level path loaded FactoryFranka at
    `/World/FactoryFrankaContactWindowClassify` and installed the demo for
    `/World/PickCubeContactWindowClassify` with `object_size=0.04`,
    `max_grasp_width_m=0.08`, and `fit_clearance_m=0.005`
  - initial status exposed the full
    `diagnostics.playback_progress.contact_window` object with
    `classification="no_closed_gripper_width_window"`,
    `gripper_closed_on_object_width_seen=false`,
    `object_grasp_width_m=0.03999999910593033`, and
    `object_bbox_half_diagonal_m=0.034641015377090495`
  - after a bounded `120`-frame playback sample, the status object reported
    `classification="closed_gripper_width_window_xy_aligned_outside_bbox_sphere"`,
    `gripper_closed_on_object_width_seen=true`,
    `object_grasp_width_m=0.04506306113462499`,
    `object_bbox_half_diagonal_m=0.0376210879956117`,
    `min_end_effector_distance_to_object_during_closed_gripper=0.058859105088898606`,
    `min_end_effector_xy_distance_to_object_during_closed_gripper=0.006804023900120447`,
    `xy_aligned_during_closed_gripper=true`,
    `inside_object_bbox_sphere_during_closed_gripper=false`,
    `closed_gripper_xy_margin_to_object_half_width_m=-0.01572750666719205`,
    and
    `closed_gripper_distance_margin_to_object_bbox_sphere_m=0.021238017093286904`
  - the sample still ended `status=placing`, `done=false`, `lifted=false`,
    `placed=false`, and `max_lift_delta=0.0`; final
    `simulation_get_status` stayed responsive and stopped in about `10ms`
  - this live-restarts and proves the classification surface after the
    validation API patch, but it is not durable pick/place validation and does
    not promote `factory_franka`
- Parent follow-up patch after the contact-window classification recheck:
  - `diagnostics.playback_progress` and
    `diagnostics.playback_progress.contact_window` now record object-motion
    isolation during the closed-gripper-width window:
    `max_object_lift_delta_during_closed_gripper`,
    `max_object_xy_motion_during_closed_gripper`,
    `lift_height_tolerance_m`, and
    `lift_threshold_met_during_closed_gripper`
  - this is telemetry hardening only; it helps distinguish "gripper closed and
    XY-aligned" from "object lifted while gripper was closed" and does not make
    `factory_franka` validated
- Fresh direct FactoryFranka object-motion contact-window smoke, thread
  `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-1`, MCP entry
    `[mcp-entry-redacted]`; MCP PID `[redacted]` was fresh with
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - because the parent changed `omni.mycompany.validation_api`, the worker
    restarted only the owned Kit on port `[redacted]` from PID `[redacted]` to PID
    `44528`; no non-owned instances were touched
  - direct low-level path loaded FactoryFranka at
    `/World/FactoryFrankaObjectMotionClassify` and installed the demo for
    `/World/PickCubeObjectMotionClassify` with `object_size=0.04`,
    `max_grasp_width_m=0.08`, and `fit_clearance_m=0.005`
  - initial status exposed the new object-motion fields with
    `max_object_lift_delta_during_closed_gripper=null`,
    `max_object_xy_motion_during_closed_gripper=null`,
    `lift_height_tolerance_m=0.03`, and
    `lift_threshold_met_during_closed_gripper=false`
  - after one bounded `120`-frame playback sample, the top-level progress and
    `contact_window` object both reported
    `max_object_lift_delta_during_closed_gripper=-0.0027249995321035336`,
    `max_object_xy_motion_during_closed_gripper=0.011446855657808945`,
    `lift_height_tolerance_m=0.03`, and
    `lift_threshold_met_during_closed_gripper=false`
  - the same sample classified the closed-gripper window as
    `closed_gripper_width_window_xy_aligned_outside_bbox_sphere`, with
    `min_end_effector_distance_to_object_during_closed_gripper=0.05885847672507068`,
    `min_end_effector_xy_distance_to_object_during_closed_gripper=0.006814230916412223`,
    `xy_aligned_during_closed_gripper=true`, and
    `inside_object_bbox_sphere_during_closed_gripper=false`
  - final demo status still ended `status=placing`, `done=false`,
    `lifted=false`, `placed=false`, and `max_lift_delta=0.0`; final
    `simulation_get_status` stayed responsive and stopped in about `10ms`
  - this proves the object-motion diagnostics are live-visible and populated,
    but the object did not lift during the closed-gripper window; no
    pick/place validation or promotion is claimed
- Parent follow-up patch after the object-motion contact-window smoke:
  - `diagnostics.playback_progress` and
    `diagnostics.playback_progress.contact_window` now also record closed-window
    Z separation between the end effector and object:
    `min_abs_end_effector_z_distance_to_object_during_closed_gripper`,
    `signed_end_effector_z_distance_at_min_abs_during_closed_gripper`,
    `object_half_height_m`, `z_aligned_during_closed_gripper`,
    `closed_gripper_z_margin_to_object_half_height_m`, and `axis_hint`
  - this is static/unit-tested telemetry hardening only until a fresh
    validation_api restart rechecks it live; it is meant to distinguish
    FactoryFranka "XY aligned but vertically outside the object height" from
    true contact/lift, and does not promote `factory_franka`
- Fresh direct FactoryFranka Z-separation contact-window smoke, thread
  `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-1`, MCP entry
    `[mcp-entry-redacted]`; MCP PID `[redacted]` was fresh with
    `source_newer_than_import=false` and `stale_source_modules=[]`
  - because the parent changed `omni.mycompany.validation_api`, the worker
    restarted only the owned Kit on port `[redacted]` from PID `[redacted]` to PID
    `42916`; no non-owned or port `[redacted]` instances were touched
  - direct low-level path loaded FactoryFranka at
    `/World/FactoryFrankaZContactDiag` and installed the demo for
    `/World/PickCubeZContactDiag` with `object_size=0.04`,
    `max_grasp_width_m=0.08`, `fit_clearance_m=0.005`, and
    `create_demo_scene=true`
  - immediate `robot_get_pick_place_demo_status(timeout_s=1.0)` returned in
    about `14ms`; all six Z-separation `contact_window` fields were present
    with `min_abs_end_effector_z_distance_to_object_during_closed_gripper=null`,
    `signed_end_effector_z_distance_at_min_abs_during_closed_gripper=null`,
    `object_half_height_m=0.019999999552965164`,
    `z_aligned_during_closed_gripper=false`,
    `closed_gripper_z_margin_to_object_half_height_m=null`, and
    `axis_hint="no_closed_gripper_width_window"`
  - after one bounded `120`-frame playback sample and `simulation_stop`, the
    post-sample status returned in about `19ms` at `status=placing`,
    `controller_event=6`, `steps=442`, `done=false`, `lifted=false`,
    `placed=false`, `object_fit_ok=true`, and `uses_kinematic_carry=false`
  - the post-sample contact window was classified as
    `closed_gripper_width_window_xy_aligned_outside_bbox_sphere` with
    `axis_hint="z_offset_outside_object_height"`,
    `min_abs_end_effector_z_distance_to_object_during_closed_gripper=0.0520634651184082`,
    `signed_end_effector_z_distance_at_min_abs_during_closed_gripper=0.0520634651184082`,
    `object_half_height_m=0.02000017329974136`,
    `z_aligned_during_closed_gripper=false`, and
    `closed_gripper_z_margin_to_object_half_height_m=0.03206329181866684`
  - final `simulation_get_status` stayed responsive and stopped in about
    `15ms`; WARN/ERROR capture and viewport proof were intentionally skipped
    because the smoke had no unexpected failure or host degradation and was
    diagnostics-surface proof only
  - this live-proves that the Z-separation fields are surfaced and populated
    after a validation API restart, and it narrows the closed-gripper failure
    to vertical separation outside the object's half-height; it is not MCP
    controllability proof, not pick/place validation, and does not promote
    `factory_franka`
- Bounded FactoryFranka Z-offset adapter-geometry trial, same thread
  `[worker-id-redacted]`:
  - same owned `workspaces/isaac/instance-1` runtime; MCP PID `[redacted]` stayed
    fresh with no stale modules, the only Kit instance was still owned on port
    `8111` with PID `[redacted]`, and no restart was needed
  - Variant A loaded `/World/FactoryFrankaZOffset032`, installed
    `/World/PickCubeZOffset032`, and requested
    `end_effector_offset=[0.0, 0.0, -0.032]`,
    `end_effector_orientation=[0.0, 1.0, 0.0, 0.0]`, and `max_steps=1000`;
    one bounded `260`-frame sample ended `status=placing`,
    `controller_event=6`, `steps=386`, `done=false`, `lifted=false`,
    `placed=false`, `max_lift_delta=0.0`, and
    `final_distance=0.7135504125660336`
  - Variant A worsened the contact window to
    `classification=closed_gripper_width_window_not_xy_aligned`,
    `axis_hint=xy_offset_outside_object_width`,
    `min_abs_end_effector_z_distance_to_object_during_closed_gripper=0.5327797774225473`,
    `object_half_height_m=0.020000049485944846`, and
    `closed_gripper_z_margin_to_object_half_height_m=0.5127797279366025`;
    closed-gripper object lift delta stayed negative
    (`-0.0009764358103275285`) with XY motion about `0.011661181052890908`
  - Variant B loaded `/World/FactoryFrankaZOffset052`, installed
    `/World/PickCubeZOffset052`, and requested
    `end_effector_offset=[0.0, 0.0, -0.052]`,
    `end_effector_orientation=[0.0, 1.0, 0.0, 0.0]`, and `max_steps=1000`;
    one bounded `260`-frame sample ended `status=placing`,
    `controller_event=6`, `steps=396`, `done=false`, `lifted=false`,
    `placed=false`, `max_lift_delta=0.0`, and
    `final_distance=0.7166629870917137`
  - Variant B also ended
    `classification=closed_gripper_width_window_not_xy_aligned`,
    `axis_hint=xy_offset_outside_object_width`,
    `min_abs_end_effector_z_distance_to_object_during_closed_gripper=0.796035636216402`,
    `object_half_height_m=0.02000184394744811`, and
    `closed_gripper_z_margin_to_object_half_height_m=0.776033792268954`;
    closed-gripper lift delta crossed the configured threshold
    (`0.034318160295486455`) but without final `done`, `lifted`, or `placed`
    and with the contact window still XY-misaligned
  - final host health stayed responsive after both variants; no WARN/ERROR log
    capture, third variant, repeat cycle, code edit, or git operation was run
  - simple negative end-effector Z offsets are now live-disproven as a
    FactoryFranka promotion path: they did not produce durable lift/place proof
    and do not promote `factory_franka`
- Parent follow-up patch after the Z-offset adapter trial:
  - `diagnostics.playback_progress` and nested
    `diagnostics.playback_progress.contact_window` now record signed
    end-effector-to-object delta vectors for the closed-gripper window:
    `end_effector_object_delta_at_min_distance_during_closed_gripper`,
    `end_effector_object_delta_at_min_xy_distance_during_closed_gripper`, and
    `end_effector_object_delta_at_min_abs_z_during_closed_gripper`
  - progress samples also include `end_effector_object_delta`, so future
    FactoryFranka adapter trials can distinguish "outside" from directional
    XY/Z offset instead of relying only on unsigned margins
  - focused static regression coverage verifies the fields, reset behavior, and
    bounded progress-sample shape; this remains telemetry hardening only
- Fresh direct FactoryFranka signed-delta telemetry smoke, thread
  `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-1`, MCP entry
    `[mcp-entry-redacted]`; MCP PID `[redacted]` was fresh with
    `source_newer_than_import=false`, `stale_source_modules=[]`,
    `tool_count=143`, and robot probe timeout defaults `90.0` / `90.0` /
    `105.0`
  - because the parent changed `omni.mycompany.validation_api`, the worker
    restarted only the owned Kit on port `[redacted]` from PID `[redacted]` to PID
    `56656`; no non-owned instances were listed or touched
  - direct low-level path loaded FactoryFranka at
    `/World/FactoryFrankaSignedDeltaDiag` and installed
    `/World/FactoryFrankaSignedDeltaCube` with the prior explicit strategy:
    `picking_position=[0.3,0.35,0.02]`,
    `end_effector_orientation=[0.0,1.0,0.0,0.0]`,
    `end_effector_offset=[0.0,0.0,-0.02]`, `object_size=0.04`, and
    `max_steps=600`
  - immediate preplay status was `idle`; the new signed-delta keys existed in
    both `diagnostics.playback_progress` and nested `contact_window`, with
    `null` values before playback
  - after `simulation_play`, the first bounded status poll returned in about
    `26ms` and already had a closed-gripper window with non-null signed delta
    vectors:
    `[-0.16773882508277893,-0.3364330865442753,0.862981878221035]` at
    min distance/min XY distance and
    `[-0.196339413523674,-0.3476055832579732,0.8564660307019949]` at min
    absolute Z distance
  - the same sample classified as
    `closed_gripper_width_window_not_xy_aligned` with
    `axis_hint="xy_offset_outside_object_width"`,
    `xy_aligned_during_closed_gripper=false`,
    `z_aligned_during_closed_gripper=false`,
    `inside_object_bbox_sphere_during_closed_gripper=false`,
    `lift_threshold_met_during_closed_gripper=false`, `done=false`,
    `lifted=false`, and `placed=false`
  - `simulation_stop` and final `simulation_get_status` both returned quickly
    (`19ms` and about `11ms`); no WARN/ERROR capture, long proof loop, or
    profile selector route was run
  - this live-proves the signed-delta diagnostics are surfaced and populated;
    it is not MCP controllability proof, not pick/place validation, and does
    not promote `factory_franka`
- Parent follow-up patch after the signed-delta smoke:
  - `contact_window` classification now distinguishes a closed-gripper window
    that is still far from the object as
    `closed_gripper_width_window_far_from_object`, with
    `far_from_object_during_closed_gripper`,
    `closed_gripper_far_distance_threshold_m`, and
    `closed_gripper_distance_over_far_threshold_m`
  - the far-contact axis hint uses the dominant signed EE-object delta axis,
    for example `z_offset_far_from_object` for the latest live-shaped vector
    `[-0.16773882508277893,-0.3364330865442753,0.862981878221035]`
  - focused static regression coverage verifies that live-shaped vector and
    keeps near-but-outside-bbox classifications distinct
- Fresh direct FactoryFranka far-contact classification rerun, same thread
  `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-1`, MCP entry
    `[mcp-entry-redacted]`; MCP PID `[redacted]` was fresh with
    `source_newer_than_import=false`, `stale_source_modules=[]`,
    `tool_count=143`, and robot probe timeout defaults `90.0` / `90.0` /
    `105.0`
  - because the parent changed `omni.mycompany.validation_api`, the worker
    restarted only the owned Kit on port `[redacted]` from PID `[redacted]` to PID
    `71132`; no non-owned instances were listed or touched
  - direct low-level path loaded FactoryFranka at
    `/World/FactoryFrankaFarContactDiag` and installed
    `/World/FactoryFrankaFarContactCube` with the same explicit strategy:
    `picking_position=[0.3,0.35,0.02]`,
    `end_effector_orientation=[0.0,1.0,0.0,0.0]`,
    `end_effector_offset=[0.0,0.0,-0.02]`, `object_size=0.04`, and
    `max_steps=600`
  - immediate preplay status was `idle`; nested `contact_window` exposed
    `far_from_object_during_closed_gripper=false`,
    `closed_gripper_far_distance_threshold_m=0.07464101448302082`,
    `closed_gripper_distance_over_far_threshold_m=null`,
    `classification=no_closed_gripper_width_window`, and
    `axis_hint=no_closed_gripper_width_window`
  - after `simulation_play`, the first bounded status poll had
    `gripper_closed_on_object_width_seen=true` and classified the same
    closed-gripper window as
    `closed_gripper_width_window_far_from_object` with
    `axis_hint="z_offset_far_from_object"`,
    `far_from_object_during_closed_gripper=true`,
    `closed_gripper_distance_over_far_threshold_m=0.8666672545233468`, and
    the same signed deltas:
    `[-0.16773882508277893,-0.3364330865442753,0.862981878221035]` at
    min distance/min XY distance and
    `[-0.196339413523674,-0.3476055832579732,0.8564660307019949]` at min
    absolute Z distance
  - alignment/proof booleans remained
    `xy_aligned_during_closed_gripper=false`,
    `z_aligned_during_closed_gripper=false`,
    `inside_object_bbox_sphere_during_closed_gripper=false`,
    `lift_threshold_met_during_closed_gripper=false`, `done=false`,
    `lifted=false`, and `placed=false`
  - `simulation_stop` and final `simulation_get_status` both returned quickly
    (`26ms` and about `15ms`); WARN/ERROR capture, profile selector route, and
    long proof loop were skipped because the host stayed healthy
  - this live-proves the far-contact classification surface for the observed
    closed-gripper window; it is not MCP controllability proof, not pick/place
    validation, and does not promote `factory_franka`
- Parent follow-up patch after the far-contact classification rerun:
  - `diagnostics.playback_progress` now records all-time EE-to-object approach
    minima outside the closed-gripper window:
    `min_end_effector_xy_distance_to_object`,
    `min_abs_end_effector_z_distance_to_object`,
    `signed_end_effector_z_distance_at_min_abs_to_object`,
    `end_effector_object_delta_at_min_distance`,
    `end_effector_object_delta_at_min_xy_distance`, and
    `end_effector_object_delta_at_min_abs_z`
  - nested `diagnostics.playback_progress.approach_window` classifies the
    approach trajectory separately from the closed-gripper `contact_window`,
    so FactoryFranka can distinguish "approached the object but missed in Z"
    from "closed while far from the object"
  - focused unit coverage verifies the live-shaped fields and approach-window
    classification margins; this is diagnostics hardening only, not validation
- Fresh direct FactoryFranka approach-window diagnostics smoke, same worker
  thread `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-1`, MCP entry
    `[mcp-entry-redacted]`; MCP PID `[redacted]` was fresh with `tool_count=143`,
    `source_newer_than_import=false`, and no stale modules
  - because the parent changed `omni.mycompany.validation_api`, the worker
    restarted only the owned Kit on port `[redacted]` from PID `[redacted]` to PID `[redacted]`;
    no non-owned instances were listed or touched
  - direct low-level path loaded FactoryFranka at
    `/World/FactoryFrankaApproachDiag`, installed
    `/World/FactoryFrankaApproachCube`, and immediate preplay status exposed
    `approach_window` plus every all-time EE/object delta key with null values
    before playback
  - one bounded status poll after `simulation_play` populated
    `approach_window.classification=approach_window_xy_aligned_outside_bbox_sphere`,
    `axis_hint=z_offset_outside_object_height`,
    `min_end_effector_distance_to_object=0.047829756171164264`,
    `min_end_effector_xy_distance_to_object=0.007903502475505735`,
    `min_abs_end_effector_z_distance_to_object=0.0339291263371706`, and
    `signed_end_effector_z_distance_at_min_abs_to_object=0.0339291263371706`
  - all-time signed deltas were
    `[-0.010070651769638062,-0.02760830521583557,0.037736574187874794]` at
    min distance,
    `[0.007901966571807861,0.0001558065414428711,0.28844790533185005]` at min
    XY distance, and
    `[-0.0024915337562561035,-0.03883817791938782,0.0339291263371706]` at min
    absolute Z distance; approach margins were
    `approach_xy_margin=-0.012168247530239946`,
    `approach_z_margin=0.013929000279090373`,
    `approach_distance_margin=0.013105830636459467`, and
    `approach_distance_over_far_threshold=-0.027037669375031895`
  - the same poll returned terminal
    `ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED` because the official controller did
    not finish within `600` playback ticks; `simulation_stop` and final
    `simulation_get_status` returned quickly, and WARN+ capture returned
    `count=0`
  - comparison `contact_window` still classified the closed-gripper window as
    `closed_gripper_width_window_far_from_object` with
    `axis_hint=z_offset_far_from_object`; `done=false`, `lifted=false`,
    `placed=false`, and `max_lift_delta=0.0`
  - this live-proves the approach-window diagnostics surface for a bounded
    FactoryFranka sample; it is not MCP controllability proof, not pick/place
    validation, and does not promote `factory_franka`
- Fresh bounded next-offset diagnostics-surface smoke, thread
  `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-2`, MCP entry
    `[mcp-entry-redacted]`; process inventory showed external/non-owned Kit PID
    `8528` on port `[redacted]` and owned instance-2 PID `[redacted]` on port `[redacted]`
  - because the parent changed `omni.mycompany.validation_api`, the worker
    restarted only owned instance-2; new PID `[redacted]`, port `[redacted]`, ready in
    `35.0s`; pre-check `simulation_get_status` passed in `46ms`
  - validated `franka_fr3` idle install returned `status=idle`,
    `object_fit_ok=true`, and `uses_kinematic_carry=false`; no
    `simulation_play` call was made for this FR3 check
  - `robot_get_pick_place_demo_status(timeout_s=5)` returned in `17ms` and
    proved both `approach_window` and `contact_window` expose all seven
    recommendation fields:
    `diagnostic_end_effector_offset_delta_m`,
    `diagnostic_end_effector_offset_delta_source`,
    `diagnostic_end_effector_offset_base_m`,
    `diagnostic_end_effector_offset_applied_delta_m`,
    `diagnostic_end_effector_offset_next_m`,
    `diagnostic_end_effector_offset_delta_limited`, and
    `diagnostic_end_effector_offset_delta_limit_m`
  - FR3 idle values were null for the delta/base/applied/next/source fields,
    `diagnostic_end_effector_offset_delta_limited=false`, and
    `diagnostic_end_effector_offset_delta_limit_m=0.05` in both windows
  - optional direct FactoryFranka diagnostic loaded the profile S3 USD at
    `/World/FactoryFrankaNextOffsetDiag`, installed the low-level demo with
    `end_effector_offset=[0,0,0]`, `object_fit_ok=true`, played only a
    30-frame bounded sample, and returned status in `17ms`
  - FactoryFranka ended with bounded
    `ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED` at `steps=180`,
    `controller_event=1`, and `last_error="Official PickPlaceController did
    not finish within 180 playback ticks"`; host status stayed responsive
    after `simulation_stop`
  - populated FactoryFranka recommendation fields were capped to the diagnostic
    step limit: `approach_window` classified
    `approach_window_far_from_object`, `axis_hint=z_offset_far_from_object`,
    raw `delta_m=[0,0,-0.2842158079147339]`, `base_m=[0,0,0]`,
    `applied_delta_m=[0,0,-0.05]`, `next_m=[0,0,-0.05]`, and
    `delta_limited=true`; `contact_window` similarly classified
    `closed_gripper_width_window_far_from_object` with raw
    `delta_m=[0,0,-0.8364660311490297]`, the same capped applied/next offset,
    and `limit_m=0.05`
  - WARN+ capture after the optional bounded FactoryFranka failure returned 6
    WARN entries and no ERROR entries; this proves live visibility of bounded
    next-offset diagnostics only, not pick/place validation or promotion
- Fresh exact next-offset FactoryFranka trial, same instance-2 worker thread
  `[worker-id-redacted]`:
  - parent first hardened the offset recommendation helper to reject
    non-finite base/delta values; focused unit coverage now verifies non-finite
    deltas produce no applied/next offset and non-finite bases fall back to a
    safe `[0,0,0]` base for finite deltas
  - because the parent changed `omni.mycompany.validation_api`, the worker
    again restarted only owned instance-2; external/non-owned PID `[redacted]` on
    port `[redacted]` was left untouched, owned port `[redacted]` restarted from PID
    `68580` to PID `[redacted]`, and pre-trial health returned in `151ms`
  - direct low-level path loaded FactoryFranka at
    `/World/FactoryFrankaNextOffsetTrial`, installed
    `/World/FactoryFrankaNextOffsetCube` with
    `end_effector_offset=[0,0,-0.05]`, `end_effector_orientation=[0,1,0,0]`,
    `max_steps=600`, `object_fit_ok=true`, and
    `uses_kinematic_carry=false`; immediate idle status returned in `20ms`
  - after the first bounded `simulation_step(frames=260)`, status returned in
    `38ms` as `placing`, `steps=475`, `controller_event=6`, no error,
    `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`,
    and `final_distance=0.7155928062`
  - after the second bounded step burst, status returned in `33ms` as
    `failed` with `ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED`,
    `last_error="Official PickPlaceController did not finish within 600
    playback ticks"`, `steps=600`, `controller_event=6`, `done=false`,
    `lifted=false`, `placed=false`, `max_lift_delta=0.0`, and the same final
    distance
  - final proximity improved over the previous baseline diagnostic but did not
    produce lift/place: min EE distances were pick `0.046850498`, target
    `0.224221945`, object `0.046800660`, and closed-gripper object
    `0.077873044`
  - final approach diagnostics classified
    `approach_window_xy_aligned_outside_bbox_sphere` with
    `axis_hint=z_offset_outside_object_height`, raw/applied delta
    `[0,0,-0.013915723639092256]`, next offset
    `[0,0,-0.06391572438415032]`, `delta_limited=false`, and `limit_m=0.05`
  - final contact diagnostics classified
    `closed_gripper_width_window_far_from_object` with
    `axis_hint=z_offset_far_from_object`, raw/applied delta
    `[0,0,-0.048665222229919244]`, next offset
    `[0,0,-0.0986652229749773]`, `delta_limited=false`, and `limit_m=0.05`
  - `simulation_stop` returned in `18ms`, final `simulation_get_status`
    returned in about `13ms` stopped at `0.0`, and WARN+ capture returned 4
    WARN entries and no ERROR entries; this is useful adapter-geometry
    evidence only and does not promote `factory_franka`
- Fresh deeper-offset FactoryFranka comparison, same instance-2 worker thread
  `[worker-id-redacted]`:
  - no restart was needed because the validation API code had not changed since
    the prior successful instance-2 restart; `process_list_kit_instances` saw
    only owned PID `[redacted]` on port `[redacted]`, `kit_app_start` attached to it, and
    initial `simulation_get_status` returned in `19ms`
  - Variant A loaded `/World/FactoryFrankaOffset064`, installed
    `/World/FactoryFrankaOffset064Cube` with
    `end_effector_offset=[0,0,-0.064]`, `object_fit_ok=true`, and
    `uses_kinematic_carry=false`; after the first 260-frame burst it was
    `placing`, `steps=501`, `controller_event=6`, no error, `done=false`,
    `lifted=false`, `placed=false`, `max_lift_delta=0.0`, and
    `final_distance=0.7153383920`
  - after the second bounded burst, Variant A failed cleanly with
    `ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED`,
    `last_error="Official PickPlaceController did not finish within 600
    playback ticks"`, `steps=600`, `controller_event=6`, `done=false`,
    `lifted=false`, `placed=false`, `max_lift_delta=0.0`, and min EE distances
    pick `0.0468414682`, target `0.1278011094`, object `0.0467858534`,
    closed-gripper object `0.0761453481`
  - Variant A final diagnostics classified the approach window as
    `approach_window_xy_aligned_outside_bbox_sphere` with
    `axis_hint=z_offset_outside_object_height`, raw/applied delta
    `[0,0,-0.0138869315]`, next offset `[0,0,-0.0778869345]`, and the contact
    window as `closed_gripper_width_window_not_xy_aligned` with
    `axis_hint=xy_offset_outside_object_width`, raw/applied delta
    `[0.0145284633,0.0076526479,0]`, next offset
    `[0.0145284633,0.0076526479,-0.0640000030]`
  - Variant B loaded `/World/FactoryFrankaOffset099`, installed
    `/World/FactoryFrankaOffset099Cube` with
    `end_effector_offset=[0,0,-0.099]`, `object_fit_ok=true`, and
    `uses_kinematic_carry=false`; after the first 260-frame burst it was
    `placing`, `steps=532`, `controller_event=6`, no error, `done=false`,
    `lifted=false`, `placed=false`, `max_lift_delta=0.0`, and
    `final_distance=0.6634314373`
  - after the second bounded burst, Variant B failed cleanly with the same
    max-tick error at `steps=600`, `controller_event=6`, `done=false`,
    `lifted=false`, `placed=false`, `max_lift_delta=0.0025671795`,
    `final_distance=0.6634314373`, and min EE distances pick `0.0477902614`,
    target `0.0813630504`, object `0.0477381246`, closed-gripper object
    `0.0760379921`
  - Variant B final diagnostics classified the approach window as
    `approach_window_xy_aligned_outside_bbox_sphere` with
    `axis_hint=z_offset_outside_object_height`, raw/applied delta
    `[0,0,-0.0139074019]`, next offset `[0,0,-0.1129074013]`, and the contact
    window as `closed_gripper_width_window_not_xy_aligned` with
    `axis_hint=xy_offset_outside_object_width`, raw/applied delta
    `[0.0126288106,0.0075458044,0]`, next offset
    `[0.0126288106,0.0075458044,-0.0989999995]`
  - compared with the prior exact `-0.05m` trial, both deeper offsets remain
    non-promoting because neither completed nor produced durable lift/place
    proof; `-0.064m` improved target proximity but did not lift the object,
    while `-0.099m` improved final distance and target proximity further with
    only tiny object lift/motion below the lift threshold
  - `simulation_stop`, final health, and WARN+ capture stayed responsive;
    WARN+ logs contained 2 WARN entries and no validation or promotion is
    claimed
- Fresh combined XY/Z FactoryFranka comparison, same instance-2 worker thread
  `[worker-id-redacted]`:
  - no restart was needed; `process_list_kit_instances` saw one owned
    instance-2 only, `kit_app_start` attached to PID `[redacted]` on port `[redacted]`,
    and the initial host checks were responsive
  - Variant C loaded `/World/FactoryFrankaOffsetXY099`, installed
    `/World/FactoryFrankaOffsetXY099Cube` with
    `end_effector_offset=[0.0126288105,0.0075458046,-0.0989999995]`,
    `object_fit_ok=true`, and `uses_kinematic_carry=false`; after the first
    260-frame burst it was `placing`, `steps=492`, `controller_event=6`,
    `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`, and
    `final_distance=0.6756008308`
  - after the second bounded burst, Variant C failed cleanly with
    `ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED`,
    `last_error="Official PickPlaceController did not finish within 600
    playback ticks"`, `steps=600`, `controller_event=6`, `done=false`,
    `lifted=false`, `placed=false`, `max_lift_delta=0.0025472418`, and min EE
    distances pick `0.0424825331`, target `0.0879629643`, object
    `0.0424523130`, closed-gripper object `0.0770285634`
  - Variant C final diagnostics classified the approach window as
    `approach_window_xy_aligned_outside_bbox_sphere` with
    `axis_hint=z_offset_outside_object_height`, raw/applied delta
    `[0,0,-0.0139113424]`, next offset
    `[0.0126288105,0.0075458046,-0.1129113418]`, and the contact window as
    `closed_gripper_width_window_not_xy_aligned` with
    `axis_hint=xy_offset_outside_object_width`, raw/applied delta
    `[0.0005696993,0.0005887131,0]`, next offset
    `[0.0131985098,0.0081345177,-0.0989999995]`
  - Variant D loaded `/World/FactoryFrankaOffsetXY113`, installed
    `/World/FactoryFrankaOffsetXY113Cube` with
    `end_effector_offset=[0.0126288105,0.0075458046,-0.1129074022]`,
    `object_fit_ok=true`, and `uses_kinematic_carry=false`; after the first
    260-frame burst it was `placing`, `steps=557`, `controller_event=6`,
    `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`, and
    `final_distance=0.6668715948`
  - after the second bounded burst, Variant D failed cleanly with the same
    max-tick error at `steps=600`, `controller_event=6`, `done=false`,
    `lifted=false`, `placed=false`, `max_lift_delta=0.0025672056`,
    `final_distance=0.6668715948`, and min EE distances pick `0.0431613465`,
    target `0.0664822579`, object `0.0431490112`, closed-gripper object
    `0.0734793595`
  - Variant D final diagnostics classified the approach window as
    `approach_window_xy_aligned_outside_bbox_sphere` with
    `axis_hint=z_offset_outside_object_height`, raw/applied delta
    `[0,0,-0.0139061717]`, next offset
    `[0.0126288105,0.0075458046,-0.1268135739]`, and the contact window as
    `closed_gripper_width_window_xy_aligned_outside_bbox_sphere` with
    `axis_hint=z_offset_outside_object_height`, raw/applied delta
    `[0,0,-0.0154195932]`, next offset
    `[0.0126288105,0.0075458046,-0.1283269955]`
  - compared with the prior `-0.05m`, `-0.064m`, and `-0.099m` trials, both
    combined offsets remain non-promoting because they failed at 600 ticks with
    no durable lift/place proof; Variant D has the best target EE proximity so
    far (`0.0664822579`) and changes the contact classifier to XY-aligned, but
    the object lift remains tiny and below threshold
  - final stop/status/log capture stayed responsive; WARN+ logs contained 2
    WARN entries and 0 ERROR entries, and no validation or promotion is claimed
- Fresh deeper combined-Z FactoryFranka host-degradation check, same
  instance-2 worker thread `[worker-id-redacted]`:
  - no restart was needed before the trial; `process_list_kit_instances` saw
    only the owned instance-2 Kit PID `[redacted]` on port `[redacted]`, `kit_app_start`
    attached to it, initial `simulation_get_status` passed, and scoped logs
    were cleared
  - Trial E loaded `/World/FactoryFrankaOffsetXY128` from the live profile
    catalog URL and installed `/World/FactoryFrankaOffsetXY128Cube` through the
    direct low-level `robot_install_franka_pick_place_playback_demo` path, not
    the profile selector
  - install returned `status=idle`, `object_fit_ok=true`, and requested offset
    `[0.0126288105,0.0075458046,-0.1283269972]` with
    `end_effector_orientation=[0,1,0,0]`, `object_size=0.04`,
    explicit pick `[0.3,0.35,0.02]`, target `[0.45,-0.35,0.02575]`,
    and the same explicit `events_dt`
  - `simulation_play` returned, but the first bounded
    `simulation_step(frames=260)` failed after about `91740ms` with
    `SIMULATION_STEP_ERROR`; the immediate
    `robot_get_pick_place_demo_status(timeout_s=3)` then timed out with
    `ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT`
  - the second burst was intentionally not run; cleanup `simulation_stop`
    failed after about `91663ms` with `SIMULATION_CONTROL_ERROR`, final
    `simulation_get_status` failed after about `91618ms` with
    `SIMULATION_STATUS_ERROR`, and `extension_capture_logs(level="WARN")`
    failed after about `91720ms` with `EXTENSION_LOGS_ERROR`
  - terminal playback fields were unavailable after play because status timed
    out: no reliable `steps`, `controller_event`, `done`, `lifted`, `placed`,
    lift delta, final distance, EE proximity, or approach/contact-window
    diagnostics were captured
  - the final read-only process list still saw owned Kit PID `[redacted]` alive on
    port `[redacted]`, so the durable evidence is a live host-degradation blocker,
    not a clean controller failure and not adapter progress
  - scoped recovery immediately afterward found PID `[redacted]` already absent,
    started a fresh owned instance-2 Kit with `kit_app_start`, and confirmed
    new PID `[redacted]` on port `[redacted]` with `simulation_get_status` responsive in
    about `23ms`
  - this deeper combined-Z attempt does not validate or promote
    `factory_franka`; it narrows the next adapter direction away from simply
    following deeper Z recommendations without an additional stability/control
    change
- Parent follow-up after the Trial E host-degradation evidence:
  - `robot_list_arm_profiles` now exposes
    `known_pick_place_blocker_profiles` and
    `known_pick_place_blocker_profile_reasons`, distinct from dynamic-probe
    timeout hazards
  - `factory_franka` is recorded as a known pick/place playback blocker because
    direct Franka-family playback trials still lack durable lift/place proof
    and the deeper combined-Z offset trial degraded simulation/status/log calls
  - this machine-readable blocker is planning metadata only: it does not negate
    FactoryFranka probe-level MCP controllability and does not promote or
    validate pick/place
- Post-parent-patch profile metadata freshness gate, same thread
  `[worker-id-redacted]`:
  - the worker checked the existing instance-1 MCP host before running fresh
    UR/Kawasaki probes for the parent-side EE-frame metadata patch
  - `mcp_runtime_info` still reported `source_newer_than_import=false`,
    `stale_source_modules=[]`, and `tool_count=143`, but
    `robot_list_arm_profiles` exposed stale profile metadata:
    `ur10.end_effector_frame_candidates=["tool0", "ee_link"]` instead of the
    patched `["tool0", "ee_link", "wrist_3_link"]`, and
    `kawasaki_rs007l.end_effector_frame_candidates=["tool0", "ee_link",
    "right_gripper"]` instead of starting with `onrobot_rg2_base_link`
  - the worker intentionally did not run `ur3e` or `kawasaki_rs007l` probes
    because the live host could not prove it was serving the current profile
    catalog
  - parent follow-up now tracks `omniverse_kit_mcp.robot_arm_profiles` in
    `mcp_runtime_info.source_modules`, so future live gates can detect this
    cached-profile stale-runtime case; this is runtime-freshness hardening, not
    probe or pick/place validation
- Fresh runtime profile-catalog gate and five-profile probe smoke, thread
  `[worker-id-redacted]`:
  - same workspace `workspaces/isaac/instance-1`, MCP entry
    `[mcp-entry-redacted]`; fresh MCP PID `[redacted]`, `tool_count=143`,
    `source_newer_than_import=false`, and `stale_source_modules=[]`
  - `mcp_runtime_info.source_modules` included
    `omniverse_kit_mcp.robot_arm_profiles`, loaded from
    `src\omniverse_kit_mcp\robot_arm_profiles.py`, with
    `newer_than_mcp_import=false`
  - exactly one owned Kit instance was present on port `[redacted]`, PID `[redacted]`;
    no `kit_app_start`, restart, or kill was needed
  - metadata gates passed: `ur10.end_effector_frame_candidates=["tool0",
    "ee_link", "wrist_3_link"]`, and
    `kawasaki_rs007l.end_effector_frame_candidates=["onrobot_rg2_base_link",
    "tool0", "ee_link", "right_gripper"]`
  - bounded single-profile probes with `reset_stage=true`, `safe_nudge=true`,
    and `timeout_s=45` completed for `franka_panda`, `franka_fr3`,
    `factory_franka`, `ur10`, and `kawasaki_rs007l`; every row returned
    `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, and
    `probe_capability_level_name=ik_or_ee_telemetry`
  - unsupported gripper handling remained clean for `ur10`
    (`ROBOT_GRIPPER_CONTROL_ERROR`, no gripper joints) without failing the
    probe; no profile timed out or blocked the batch sequence
  - `kawasaki_rs007l` EE pose requested and resolved
    `onrobot_rg2_base_link` with `attempted_frames=["onrobot_rg2_base_link"]`,
    and IK succeeded on `kawasaki_relaxed_orientation` after the default target
    failed cleanly
  - final `simulation_get_status` passed in about `11ms`, stopped; this is
    fresh MCP profile metadata and probe-controllability evidence only, not
    pick/place validation, and it promotes no profiles
- Post-diagnostic profile-selector safety gate:
  - `robot_install_pick_place_playback_demo(profile_name=...)` now routes only
    profiles whose `support_status` is `validated_pick_place` into executable
    playback; candidate, IK-only, and profile-only profiles return an explicit
    `status="unsupported"` instead of launching unvalidated playback
  - `factory_franka` remains `candidate_pick_place`, but the default
    profile-selected playback path is blocked before robot load/install REST
    calls; this prevents the known same-family FactoryFranka playback timeout
    from being hit accidentally
  - unit coverage verifies the profile-selector boundary: only `franka_fr3`
    currently routes to the validated Franka playback adapter, while
    `franka_panda` and `factory_franka` return unsupported blocker
    diagnostics with `uses_kinematic_carry=false`
- Fresh profile-selector safety-gate smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - attached to the already-healthy instance in about `1.8s`; initial
    `simulation_get_status` returned in `12ms`, timeline stopped
  - process inventory showed a single Kit process, owned by this MCP instance;
    no non-owned or port `[redacted]` instance was observed
  - one selector call
    `robot_install_pick_place_playback_demo(profile_name="factory_franka",
    robot_prim_path="/World/FactoryFrankaSafetyGate")` returned in about
    `222ms` with `data.ok=false`, `status=unsupported`,
    `support_status=candidate_pick_place`,
    `controller_strategy=same_family_franka_candidate`,
    `uses_kinematic_carry=false`, and `steps=0`
  - `stage_assert_prim_exists(should_exist=false)` passed for
    `/World/FactoryFrankaSafetyGate`, proving the selector did not load the
    FactoryFranka asset or install playback state
  - final `simulation_get_status` returned in `11ms`, timeline still stopped
  - no Play cycle or status loop was run; this is safety-gate verification, not
    durable pick/place proof
- Fresh static-only blocked-profile triage worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - attached to the already-healthy instance in about `1.8s`; initial
    `simulation_get_status` returned in `12ms`
  - process inventory showed a single Kit process, owned by this MCP instance;
    no non-owned or port `[redacted]` instance was observed
  - ran direct `robot_probe_arm_profile(..., safe_nudge=false,
    cleanup=true, dynamic_checks=false, timeout_s=30)` for
    `openarm_unimanual`, `openarm_bimanual`, `so101_new_calib`, `lite6`,
    `lite6_gripper`, `uf850`, `xarm6`, `xarm7`, `ur3`, `ur5`, `ur20`, and
    `ur30`
  - every direct static-only row completed without profile timeout, cleanup
    timeout, or deferred cleanup; `load`, `articulation`, and `cleanup` were OK,
    while all dynamic checks were skipped as `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED`
  - durations were about `2.2s`, `7.0s`, `1.7s`, `1.6s`, `2.9s`, `5.4s`,
    `6.3s`, `3.0s`, `1.6s`, `1.6s`, `1.9s`, and `5.4s`, respectively
  - final `simulation_get_status` returned in `15ms`; no restart, playback,
    safe nudge, gripper, IK, or EE-pose checks were run
- Parent follow-up patch after the static-only triage run:
  - added `robot_get_joint_config_static`, a REST/MCP diagnostic path that reads
    USD-authored joint prim metadata without `simulation_play` or
    `SingleArticulation.initialize()`
  - `robot_probe_arm_profile(dynamic_checks=false)` now records an optional
    `static_joint_config` check before marking physics-dependent checks as
    `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED`
  - this keeps `joint_config`, `joint_read`, and `safe_nudge` skipped under
    `dynamic_checks=false`; static metadata is not write-order proof and does
    not promote the row to probe-level controllability
  - if an older validation API is still loaded, the static endpoint failure is
    recorded as `ROBOT_PROBE_STATIC_JOINT_CONFIG_UNAVAILABLE`; the probe does
    not fall back to runtime `robot_get_joint_config`
- Fresh live static-metadata smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - no `kit.exe` processes were running at preflight, so the worker started a
    fresh host instead of restarting
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - process inventory showed a single Kit process, owned by this MCP instance;
    initial `simulation_get_status` returned in `19ms`, timeline stopped
  - first `dofbot` static-only smoke exposed zero static DOFs, then the
    suffix-matching patch plus stale MCP import exposed a sparse-USD `None`
    parsing error for the same profile
  - WARN/ERROR capture on that worker failed after about `91.7s` with
    `EXTENSION_LOGS_ERROR`; no reliable log counts are claimed from that path
  - after parser hardening, a stale-client fallback `franka_panda` static-only
    probe succeeded with `dof_count=10`, `static_only=true`, and
    `order_reliable=false`
- Fresh MCP-import static metadata smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, existing owned Kit PID
    `55420`; no second Kit instance was launched
  - `dofbot` with `dynamic_checks=false` succeeded for load, articulation,
    static joint config, and cleanup; pre/post status returned in about
    `18ms`/`14ms`
  - `static_joint_config` reported `dof_count=13`,
    `source=usd_joint_prims_static`, `static_only=true`, and
    `order_reliable=false`
  - this proves only static USD metadata extraction, not dynamic joint control,
    probe-level controllability, or pick/place validation
- Parent follow-up patch after known hazardous dynamic rows remained risky:
  - `robot_probe_arm_profiles(static_only_for_known_dynamic_timeouts=true)` is
    now an opt-in batch policy that routes profiles with direct durable dynamic
    timeout evidence to `dynamic_checks=false`
  - routed rows include a `dynamic_probe_policy` check with
    `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` and stay `overall_ok=false`
  - current known direct dynamic-timeout profiles are `dofbot`, `lite6`,
    `lite6_gripper`, `openarm_bimanual`, `openarm_unimanual`,
    `so101_new_calib`, `uf850`, `ur3`, `ur5`, `ur20`, `xarm6`, and `xarm7`
  - historical batch-aborted rows are intentionally not auto-routed until
    isolated dynamic probes prove their own timeout hazard; the current
    historical batch-abort-only gap is closed for `openarm_bimanual`,
    `lite6_gripper`, `uf850`, `xarm6`, and `xarm7`, while `ur30` was later
    superseded by isolated dynamic joint-control proof and is not a
    known-hazard routing candidate
- Fresh static-policy routing smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - `kit_app_start` attached to an existing healthy instance; no restart was
    used
  - pre-batch `simulation_get_status` was responsive, timeline stopped, and
    returned in about `16ms`
  - `robot_probe_arm_profiles(status_filter=["ik_only"], family_filter=["ur"],
    limit=2, dynamic_checks=true,
    static_only_for_known_dynamic_timeouts=true, per_profile_timeout_s=45,
    batch_timeout_s=70)` returned normally in about `3.7s`
  - returned profiles were `ur3` and `ur3e`
  - `ur3` was routed to static-only evidence as expected:
    `dynamic_probe_policy.error_code=ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD`,
    `dynamic_checks_effective=false`, `static_joint_config` present with 6 DOFs,
    dynamic checks skipped, and `overall_ok=false`
  - `ur3e` stayed on the dynamic path in the same batch:
    no `dynamic_probe_policy`, `overall_ok=true`, 6-DOF joint read/control
    checks succeeded, safe nudge moved `shoulder_pan_joint` toward target and
    restored/settled, and IK succeeded for `tool0`
  - post-batch `simulation_get_status` stayed responsive and stopped, returning
    in about `12ms`
  - this proves opt-in routing behavior only; it does not prove joint-control for
    static-routed `ur3` and is not pick/place validation
- Parent follow-up recommendation hardening:
  - `recommended_next_status` now requires the critical load/articulation/joint
    read path before recommending anything above `profile_only`
  - IK-only recommendations now require an actual non-skipped IK probe success,
    not merely a catalog `robot_description`
  - existing catalog `candidate_pick_place` profiles can remain advisory
    candidates after critical probe evidence succeeds, but this still does not
    promote them to `validated_pick_place` or route them to executable playback
  - blocked rows now preserve the current catalog support status as their
    advisory `recommended_next_status`; a timeout, batch abort, or hard profile
    error is missing/blocked evidence, not evidence for an automatic downgrade
- Parent follow-up MCP controllability classification:
  - `robot_probe_arm_profile` and `robot_probe_arm_profiles` now return
    `mcp_controllability` plus `mcp_controllability_reason` for every row
  - `dynamic_joint_control` means dynamic load/articulation/joint read and safe
    joint nudge succeeded
  - `dynamic_joint_read_only` means dynamic load/articulation/joint read
    succeeded but write/control proof was skipped or did not pass
  - `static_load_articulation_metadata` means load/articulation plus static USD
    joint metadata only; it is not dynamic joint-control proof
  - `blocked_timeout`, `blocked_batch_timeout`, and `blocked_batch_abort` are
    blocker classifications, not MCP controllability proof
- Existing-worker result-shape exposure smoke, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, REST port `[redacted]`, PID `[redacted]`
  - `kit_app_start` attached to the existing healthy instance; no restart was
    used
  - pre-smoke `simulation_get_status` was responsive, timeline stopped, and
    returned in about `14ms`
  - `robot_probe_arm_profile(profile_name="ur3e", reset_stage=true,
    safe_nudge=true, cleanup=true, dynamic_checks=true, timeout_s=45)`
    returned normally in about `1.23s`
  - row evidence was still dynamically healthy: `overall_ok=true`,
    `recommended_next_status=candidate_pick_place`, load/joint config/joint
    read/safe nudge/IK OK, gripper skipped as no built-in gripper, and EE pose
    skipped unsupported
  - `data.mcp_controllability` and `data.mcp_controllability_reason` were
    missing from this live result, so the existing live MCP server was stale
    relative to the parent worktree for the result-shape change
  - post-smoke `simulation_get_status` stayed responsive and stopped, returning
    in about `13ms`
  - this is stale-exposure evidence only; it does not invalidate the in-process
    unit coverage and is not pick/place validation
- Parent follow-up MCP runtime freshness diagnostic:
  - `mcp_runtime_info` is now a read-only Process tool that reports MCP server
    PID, cwd, loaded source mtimes, registered tool count, and whether
    `RobotArmProfileProbeResult` exposes `mcp_controllability` fields
  - after changing `src/omniverse_kit_mcp`, live workers must call it before
    result-shape validation and restart the MCP host/thread if the tool or
    fields are absent, or if source files are newer than MCP import time
  - this diagnostic prevents repeating the stale-client ambiguity above; it
    does not itself prove robot controllability or pick/place behavior
- Parent follow-up EE-frame candidate adapter:
  - probe metadata now carries profile-level EE-frame candidates for Franka,
    UR, and Kawasaki families
  - `robot_probe_arm_profile` uses those profile hints plus a successful IK
    result's `end_effector_frame` when reading EE pose, and records
    `attempted_frames` for success or unsupported/skipped outcomes
  - unsupported candidate attempts remain skipped/unsupported, while a real
    non-unsupported EE-pose failure is preserved instead of being hidden by a
    later missing-frame fallback
  - this is probe telemetry hardening only; it is not pick/place validation
- Fresh EE-frame adapter live smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, MCP runtime PID `[redacted]`, Kit port `[redacted]`,
    fresh Kit PID `[redacted]`
  - `mcp_runtime_info` was present, reported `143` tools,
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, no stale source modules, and
    the probe result shape included `mcp_controllability`
  - pre-smoke `simulation_get_status` returned in about `24ms`
  - `ur3e` dynamic probe returned in about `5.6s` with `overall_ok=true` and
    `mcp_controllability=dynamic_joint_control`; IK used `tool0`; EE pose
    recorded `attempted_frames=["tool0","ee_link",null]`; the final null
    request reached the backend default `panda_hand`; the check stayed
    skipped/unsupported rather than silently defaulting first to `panda_hand`
  - post-UR3e `simulation_get_status` returned in about `12ms`
  - `kawasaki_rs007l` dynamic probe returned in about `2.6s` with
    `overall_ok=true` and dynamic joint-control evidence; IK and EE pose stayed
    skipped/unsupported, and EE pose recorded
    `attempted_frames=["tool0","ee_link","right_gripper",null]` instead of
    failing the probe
  - final `simulation_get_status` returned in about `18ms`; WARN/ERROR capture
    was skipped because both probes returned normally and host health stayed
    responsive
  - this is probe telemetry and MCP controllability evidence only, not
    pick/place validation
- Parent follow-up validation_api EE-pose alias resolver:
  - extension-side `robot_get_ee_pose` now expands common requested frames to
    USD prim-name aliases before returning unsupported; UR `tool0`/`ee_link`
    can resolve through wrist/link aliases, and Kawasaki requested tool/gripper
    frames can resolve through `onrobot_rg2_base_link` when present
  - the returned `end_effector_frame` is the concrete resolved USD prim name,
    while probe-level telemetry still records the originally requested frame
  - this is EE telemetry hardening only; it does not add IK, gripper, or
    pick/place validation
- Fresh validation_api EE-pose alias live smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, MCP runtime PID `[redacted]`, REST port `[redacted]`,
    restarted Kit PID `[redacted]`
  - `mcp_runtime_info` was present, reported `143` tools, and no MCP source
    modules were newer than import
  - process discovery found owned port `[redacted]` Kit PID `[redacted]`, so the worker
    ran `kit_app_restart`; restart completed in about `22.9s` with
    `caches_cleared=4`
  - pre-smoke `simulation_get_status` was responsive and stopped, returning in
    about `17ms`
  - `ur3e` dynamic probe returned `overall_ok=true` with
    `mcp_controllability=dynamic_joint_control`; IK used `tool0`; EE pose
    requested `tool0` and resolved through concrete USD prim `wrist_3_link`
    with `attempted_frames=["tool0"]`
  - post-UR3e `simulation_get_status` returned in about `15ms`
  - `kawasaki_rs007l` dynamic probe returned `overall_ok=true` with dynamic
    joint-control evidence; EE pose resolved through concrete USD prim
    `onrobot_rg2_base_link` for requested `tool0`, with
    `attempted_frames=["tool0"]`; IK stayed cleanly skipped/unsupported due to
    a Lula c-space seed dimension error
  - final `simulation_get_status` was responsive in about `16ms`; WARN/ERROR
    capture was not needed because both probes returned normally and host
    health stayed responsive
  - this is MCP probe telemetry proof only, not pick/place validation
- Fresh validation_api EE-pose alias live smoke worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-2`
  - MCP entry `[mcp-entry-redacted]`, MCP runtime PID `[redacted]`, REST port `[redacted]`,
    fresh Kit PID `[redacted]`
  - `mcp_runtime_info` was present, reported `143` tools, and no MCP source
    modules were newer than import
  - process discovery found only a non-owned port `[redacted]` Kit process, so the
    worker started a fresh owned instance-2 host rather than touching port
    `8111`; startup completed in about `34.7s`
  - pre-smoke `simulation_get_status` was responsive and stopped, returning in
    about `29ms`
  - `ur3e` dynamic probe returned `overall_ok=true` with
    `mcp_controllability=dynamic_joint_control`; IK used requested frame
    `tool0`; EE pose requested `tool0` and resolved through concrete USD prim
    `wrist_3_link` with `attempted_frames=["tool0"]`
  - post-UR3e `simulation_get_status` returned in about `17ms`
  - `kawasaki_rs007l` dynamic probe returned `overall_ok=true` with dynamic
    joint-control evidence; EE pose resolved through concrete USD prim
    `onrobot_rg2_base_link` for requested `tool0`, with
    `attempted_frames=["tool0"]`; IK stayed cleanly skipped/unsupported due to
    a Lula c-space seed dimension error
  - final single-smoke `simulation_get_status` was responsive in about `21ms`
  - the same worker then broadened EE-alias telemetry without restarting the
    healthy host: the candidate UR batch returned `overall_ok=true` for
    `ur10` and `ur10e`, with dynamic joint control, clean unsupported gripper
    skips, IK success, and EE pose resolved for requested `tool0`
  - candidate UR details: `ur10` IK used `ee_link` and EE pose resolved
    `ee_link`; `ur10e` IK used `tool0` and EE pose resolved `ee_link`; both
    EE-pose rows recorded `attempted_frames=["tool0"]`
  - the IK-only UR batch with `static_only_for_known_dynamic_timeouts=true`
    routed `ur3` and `ur5` to static-only known-hazard rows that are not
    controllability proof, while `ur3e`, `ur5e`, and `ur16e` returned
    `overall_ok=true`, dynamic joint control, IK success for `tool0`, and EE
    pose resolved through `wrist_3_link` for requested `tool0`
  - the candidate Kawasaki batch returned `overall_ok=true` and dynamic joint
    control for all five profiles; gripper open succeeded, IK stayed cleanly
    unsupported/skipped with the known Lula seed-dimension error, and EE pose
    resolved through `onrobot_rg2_base_link` for requested `tool0` on
    `kawasaki_rs007l`, `kawasaki_rs007n`, `kawasaki_rs013n`,
    `kawasaki_rs025n`, and `kawasaki_rs080n`
  - sibling-batch health stayed responsive and stopped: pre-batch status about
    `23ms`, after candidate UR `15ms`, after IK-only UR `19ms`, and final
    status about `20ms`; WARN/ERROR capture was not needed because there were
    no unexpected probe failures, timeouts, or health degradation
  - this is MCP probe telemetry proof only, not pick/place validation
- Fresh MCP-runtime/result-shape worker, thread
  `[worker-id-redacted]`:
  - workspace `workspaces/isaac/instance-1`
  - MCP entry `[mcp-entry-redacted]`, MCP server PID `[redacted]`, Kit port `[redacted]`,
    existing Kit PID `[redacted]`
  - `mcp_runtime_info` returned `tool_count=143`,
    `has_mcp_runtime_info_tool=true`,
    `robot_probe_result_has_mcp_controllability=true`,
    `source_newer_than_import=false`,
    `restart_required_for_latest_mcp_code=false`, and
    `stale_source_modules=[]`
  - pre-smoke `simulation_get_status` was responsive in about `22ms`, timeline
    stopped
  - `robot_probe_arm_profile(profile_name="ur3e", reset_stage=true,
    safe_nudge=true, cleanup=true, dynamic_checks=true, timeout_s=45)`
    returned normally in about `1.4s`
  - result-shape fields were live:
    `mcp_controllability=dynamic_joint_control` and
    `mcp_controllability_reason="Dynamic load, articulation, joint read, and
    safe joint nudge succeeded."`
  - `overall_ok=true`, `recommended_next_status=ik_only`; load,
    `joint_config`, `joint_read`, safe nudge, and IK were OK; gripper was
    skipped as no built-in gripper candidate; EE pose was skipped unsupported
    because the default `panda_hand` frame is not present on UR3e
  - post-smoke `simulation_get_status` stayed responsive in about `15ms`
  - no restart or WARN/ERROR capture was needed; this proves live MCP freshness
    and result-shape exposure only, not pick/place validation
- Existing durable pick/place proof:
  - `docs/artifacts/robot-pickplace/franka-fr3-pickplace-live-proof-2026-06-15.md`
- Existing Panda non-proof evidence:
  - `docs/artifacts/robot-pickplace/franka-panda-pickplace-nonproof-2026-06-16.md`
  - three fresh `franka_panda` repeatability attempts in worker
    `[worker-id-redacted]` did not produce durable
    pick/place proof: the original run failed cycle 2 with a ParallelGripper
    `NoneType` callback error, the wrapper-refresh rerun reproduced that
    crash, and the cache-fix rerun avoided the crash but failed cycle 2
    because the object was not lifted enough.

## Probe Semantics

- Critical MCP capability checks: load, articulation, joint config, joint read,
  and optional safe nudge when requested.
- Gripper, IK, and EE-pose checks may be recorded as skipped/unsupported when
  the profile or asset lacks that capability or currently lacks a usable frame.
  IK target no-converge or solver failures are not classified as unsupported
  unless they match explicit missing-Lula/import/support markers.
- Current parent batch summaries also expose `ik_target_failure_profiles` for
  rows whose IK command surface was present but failed bounded target attempts.
  This separates Kuka-style target convergence gaps from unsupported IK while
  remaining probe-triage evidence only.
- Timeout-only and error-only rows now report `overall_ok=false`.
- Timeout rows now include progress evidence for newly-run probes:
  `last_phase`, `completed_checks`, `profile_name`, and `prim_path`. Earlier
  live timeout rows in this artifact predate that refinement unless they are
  explicitly rerun. The fresh `dofbot` rerun proves this evidence in the live
  timeout path.
- After the fresh `dofbot` progress-evidence run, the parent code was further
  hardened so dynamic `simulation_play` / `warmup_step` phases use a bounded
  operation timeout, stop downstream capability checks on failure, keep
  `overall_ok=false` when critical checks did not run, and batch-abort
  remaining rows if phase-timeout cleanup also times out. The later
  `[worker-id-redacted]` worker proved this live for `dofbot`:
  the row recorded `ROBOT_PROBE_WARMUP_STEP_TIMEOUT` with
  `timeout_kind=phase_operation` and no downstream checks.
- Current parent classification also reports phase-operation timeout rows as
  `mcp_controllability=blocked_timeout` and `probe_capability_level=0`, so
  timed-out warmup/play rows are blocker evidence rather than
  `load_articulation_only` evidence.
- Current parent classification also reports unhandled per-profile batch errors
  as `mcp_controllability=blocked_profile_error` and
  `probe_capability_level=0`, so unexpected hard errors are explicit blocker
  evidence rather than implicit load/articulation results.
- Current parent probe-call exception rows now include `hard_failure=true`
  alongside `exception_type`, while timeout rows keep `hard_failure=false`.
  This separates Kit/client exceptions from bounded timeout evidence; it is
  result-shape hardening only and not new live robot proof.
- Current parent classification also reports non-timeout dynamic phase failures
  as `mcp_controllability=blocked_phase_error` and
  `probe_capability_level=0`, so play/warmup failures do not masquerade as
  `load_articulation_only` evidence.
- After that live result showed cleanup still degraded the host, the current
  parent code now defers cleanup after timed-out dynamic phases instead of
  sending immediate stop/delete calls. This records `*_DEFERRED` checks with
  `requires_lifecycle_recovery=true` and aborts remaining batch rows with reason
  `profile_timeout_cleanup_deferred`. The
  `[worker-id-redacted]` worker proved the deferred row live for
  `dofbot`, but the host still became unresponsive afterward, so lifecycle
  restart remains required for this failure class.
- For profiles already known to wedge during dynamic warmup, use
  `dynamic_checks=false` to collect load/articulation-only evidence without
  claiming probe-level controllability. Rows from this mode must remain
  `overall_ok=false` because joint config/read and control surfaces were not
  exercised. The `[worker-id-redacted]` worker proved this
  static-only path live for `dofbot` and left instance-2 responsive; the
  `[worker-id-redacted]` worker then proved the same
  load/articulation-only path for twelve previously timed-out or batch-aborted
  profiles on instance-1.
- For broad matrix refreshes, the new
  `static_only_for_known_dynamic_timeouts=true` batch option can route only
  profiles with direct dynamic-timeout evidence to the static-only path while
  still running neighboring profiles dynamically. It records
  `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` as policy evidence. This is a host
  protection and evidence-preservation mode, not proof of joint read/write,
  safe nudge, gripper, IK, EE-pose, or pick/place behavior. Worker
  `[worker-id-redacted]` live-proved this routing for `ur3`
  while keeping neighboring `ur3e` on the dynamic path in the same batch.
- Parent follow-up now exposes the same
  `static_only_for_known_dynamic_timeouts=true` opt-in on
  `robot_probe_arm_profile`, so a single known-hazard profile can be routed to a
  static-only row with `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` policy evidence
  instead of re-running its known host-degrading dynamic path. This is static
  hazard triage only; it is not dynamic MCP controllability or pick/place proof.
- Parent follow-up also makes `robot_probe_arm_profile.timeout_s` default to
  `90.0`, matching the batch per-profile default. Omitting `timeout_s` now
  records a bounded single-profile timeout row instead of risking an unbounded
  MCP caller hang; pass `timeout_s=null` only for deliberate unbounded
  diagnostics. `mcp_runtime_info` now reports this default via
  `robot_probe_arm_profile_timeout_default_s` so a live worker can prove a
  fresh MCP import before relying on the default.
- Fresh instance-1 worker `[worker-id-redacted]` then proved
  the runtime/default shape in-band: `mcp_runtime_info` reported
  `robot_probe_arm_profile_timeout_default_s=90.0`,
  `robot_probe_arm_profiles_per_profile_timeout_default_s=90.0`, and
  `robot_probe_arm_profiles_batch_timeout_default_s=105.0`, with no stale
  source modules. The worker then ran one `franka_panda` probe with
  `timeout_s` omitted; it returned normally with `overall_ok=true`,
  `mcp_controllability=dynamic_joint_control`, and final host health
  responsive. This proves the omitted-timeout call path and fresh runtime
  default only, not pick/place validation.
- After the instance-2 worker exposed UR timeout cleanup as a host-health risk,
  the parent patch now stops the timeline before probe stage resets, bounds
  timeout cleanup to `3s` per cleanup call, and records remaining batch rows as
  `probe_batch_aborted` when a timed-out profile's cleanup also times out.
  `stage_reset_stop`, healthy tight UR batching, and the live batch-abort path
  are proven by the instance-1 reruns.
- `overall_ok=true` on a probe does not mean pick/place works.
- `recommended_next_status` from a probe is advisory and does not promote the
  static catalog. It is evidence-sensitive: IK-only recommendations require a
  successful non-skipped IK probe, while catalog candidates remain candidates
  only when the critical load/articulation/joint path works. Blocked rows
  preserve the current catalog support status instead of recommending a
  downgrade from missing evidence.
- `mcp_controllability` is the machine-readable probe evidence class for MCP
  controllability claims. Use it before reporting a profile as controllable:
  static-only and blocked rows are explicit non-controllability evidence.
- `probe_capability_level` is the machine-readable handoff matrix level for
  probe evidence only. It is capped below durable pick/place validation: timeout
  or batch-blocked rows are Level 0, load/articulation/static-metadata hazard
  rows are Level 1, dynamic joint read is Level 2, safe-nudge write proof is
  Level 3, gripper control can reach Level 4, and IK/EE-pose telemetry can
  reach Level 5. Levels 6-7 still require separate adapter and durable
  pick/place proof.
- Batch probe results now summarize row evidence with
  `mcp_controllability_counts`, `mcp_controllability_profiles`,
  `probe_capability_level_name_counts`, `probe_capability_level_name_profiles`,
  `timed_out_profiles`, `blocked_profiles`, `hard_failure_profiles`,
  `lifecycle_recovery_profiles`, `unsupported_capability_profiles`,
  `ik_target_failure_profiles`, `static_metadata_profiles`,
  `known_dynamic_timeout_routed_profiles`, and `dynamic_joint_control_profiles`.
  These summary fields are triage helpers
  derived from rows; they do not promote any profile or replace per-row proof.
  `lifecycle_recovery_profiles` names rows whose stop/cleanup checks were
  deferred or timed out and therefore require host lifecycle recovery before
  more live probes.
- Parent follow-up adds `profile_names=[...]` to
  `robot_probe_arm_profiles` for exact ordered small-batch reruns. Unknown
  requested names are recorded as row-level `ROBOT_PROBE_UNKNOWN_PROFILE`
  hard failures, so a typo does not silently disappear and does not fail the
  whole batch. This is tool-surface hardening only, not new live robot proof.
- Parent follow-up splits omitted `profile_names` from explicit
  `profile_names=[]`: omitting the field still selects the full catalog, while
  an explicit empty list selects zero profiles. This prevents accidental broad
  live probes when a caller builds an empty exact-selection list. This is
  static/unit-tested selector hardening, not new live robot proof.
- Fresh no-Kit worker turn `[worker-id-redacted]`
  live-proved the empty exact-selection runtime behavior in a freshly loaded
  workspace-local MCP host without touching Kit: `mcp_runtime_info` reported
  MCP PID `[redacted]`, `tool_count=143`, fresh source, no restart requirement, no
  stale modules, and `profile_names` present in both batch request/result
  fields; `robot_probe_arm_profiles(profile_names=[], batch_timeout_s=10)`
  returned normally with `profile_names=[]`, `requested_count=0`, `count=0`,
  `results=[]`, and empty summary maps/lists. The worker did not call
  `kit_app_start`, `process_list_kit_instances`, `simulation_get_status`, or
  any robot profile probe. This proves empty-selector/result-shape behavior
  only, not MCP controllability or pick/place validation.
- Fresh selector-proof worker turn `[worker-id-redacted]`
  live-proved the new exact ordered selector in a freshly loaded
  workspace-local MCP host: `mcp_runtime_info` reported MCP PID `[redacted]`,
  `tool_count=143`, fresh source, no restart requirement, no stale modules,
  `profile_names` present in both `robot_probe_batch_request_fields` and
  `robot_probe_batch_result_fields`, then an owned instance-1 Kit on port
  `8111`/PID `[redacted]` returned a five-profile
  `robot_probe_arm_profiles(profile_names=[...])` batch normally in
  `10627ms`. The top-level `profile_names` and row order exactly matched the
  request, all rows had `probe_proves_pick_place=false`, and unsupported
  gripper evidence stayed row-level. This proves selector/result-shape and
  probe evidence only, not pick/place validation or profile promotion.
- Fresh no-Kit worker turn `[worker-id-redacted]`
  verified a newly loaded workspace-local MCP host exposes those batch summary
  fields without starting Kit: `mcp_runtime_info` reported MCP PID `[redacted]`,
  `tool_count=143`, fresh source, no restart requirement, no stale modules,
  `robot_probe_batch_result_has_summary=true`, and
  `robot_probe_batch_result_fields=["count","requested_count","status_filter",
  "family_filter","mcp_controllability_counts",
  "probe_capability_level_name_counts","timed_out_profiles",
  "blocked_profiles","hard_failure_profiles",
  "unsupported_capability_profiles","static_metadata_profiles",
  "dynamic_joint_control_profiles","results"]`. This is MCP host
  import/result-shape proof only, not profile controllability or pick/place
  validation.
- Fresh no-Kit worker turn `[worker-id-redacted]`
  verified the newly added known-hazard routing summary field in a freshly
  loaded workspace-local MCP host without starting Kit: `mcp_runtime_info`
  reported MCP PID `[redacted]`, `tool_count=143`, fresh source, no restart
  requirement, no stale modules, `robot_probe_batch_result_has_summary=true`,
  and `robot_probe_batch_result_fields=["count","requested_count",
  "status_filter","family_filter","mcp_controllability_counts",
  "probe_capability_level_name_counts","timed_out_profiles",
  "blocked_profiles","hard_failure_profiles",
  "unsupported_capability_profiles","static_metadata_profiles",
  "known_dynamic_timeout_routed_profiles","dynamic_joint_control_profiles",
  "results"]`. This is MCP host import/result-shape proof only, not profile
  controllability or pick/place validation.
- Fresh no-Kit worker turn `[worker-id-redacted]`
  verified the newly added lifecycle-recovery summary field in a freshly
  loaded workspace-local MCP host without starting Kit: `mcp_runtime_info`
  reported MCP PID `[redacted]`, `tool_count=143`, fresh source, no restart
  requirement, no stale modules, `robot_probe_batch_result_has_summary=true`,
  and `robot_probe_batch_result_fields=["count","requested_count",
  "status_filter","family_filter","mcp_controllability_counts",
  "probe_capability_level_name_counts","timed_out_profiles",
  "blocked_profiles","hard_failure_profiles","lifecycle_recovery_profiles",
  "unsupported_capability_profiles","static_metadata_profiles",
  "known_dynamic_timeout_routed_profiles","dynamic_joint_control_profiles",
  "results"]`. This is MCP host import/result-shape proof only, not profile
  controllability or pick/place validation.
- Fresh no-Kit worker turn `[worker-id-redacted]`
  verified the newly added IK-target-failure summary field in a freshly loaded
  workspace-local MCP host without starting Kit: `mcp_runtime_info` reported
  MCP PID `[redacted]`, `tool_count=143`, fresh source, no restart requirement, no
  stale modules, `robot_probe_batch_result_has_summary=true`, and
  `ik_target_failure_profiles` present in
  `robot_probe_batch_result_fields`. This is MCP host import/result-shape proof
  only, not profile controllability or pick/place validation.
- Fresh no-Kit worker turn `[worker-id-redacted]` verified
  the running workspace-local MCP host imports the new capability-level result
  shape without starting Kit: `mcp_runtime_info` reported MCP PID `[redacted]`,
  `tool_count=143`, fresh source, no restart requirement, no stale modules,
  and `robot_probe_result_has_probe_capability_level=true` with
  `probe_capability_level`, `probe_capability_level_name`, and
  `probe_capability_level_reason` present in `robot_probe_result_fields`.
  `process_list_kit_instances` returned `instances=[]`. This is result-shape
  freshness only, not MCP controllability or pick/place validation.
- The existing instance-1 worker did not expose the new
  `mcp_controllability` fields after the parent code change, even though the
  same `ur3e` dynamic probe stayed healthy. Fresh worker
  `[worker-id-redacted]` closes that result-shape gap:
  `mcp_runtime_info` reported fresh source and the live `ur3e` row returned
  `mcp_controllability=dynamic_joint_control`.
- Fresh instance-2 child worker `[worker-id-redacted]`
  closed the direct-evidence gap for `lite6_gripper`: fresh MCP runtime PID
  `60176`, Kit PID `[redacted]` on port `[redacted]`, pre-probe status responsive,
  isolated dynamic probe returned a bounded warmup-step timeout after
  load/articulation/play, downstream robot checks were not reached, post-probe
  status degraded after about `53.3s`, WARN capture could not connect to REST,
  and scoped cleanup left port `[redacted]` clear. This is not pick/place validation.
- Fresh instance-2 child worker `[worker-id-redacted]`
  closed the direct-evidence gap for `uf850`: fresh MCP runtime PID `[redacted]`,
  Kit PID `[redacted]` on port `[redacted]`, pre-probe status responsive, isolated dynamic
  probe returned a bounded warmup-step timeout after load/articulation/play,
  downstream robot checks were not reached, post-probe status degraded after
  about `85.3s`, WARN capture could not connect to REST, `kit_app_stop`
  reported the instance already not running, and final process checks showed
  port `[redacted]` clear. This is not pick/place validation.
- Fresh instance-2 child worker `[worker-id-redacted]`
  verified current-code UFactory static known-hazard routing after `uf850` was
  added to the known dynamic-timeout table: fresh MCP runtime PID `[redacted]`, Kit
  PID `[redacted]` on port `[redacted]`, pre/post status responsive and stopped, the
  profile-only UFactory batch returned all five rows in about `7.7s`, and
  `lite6`, `lite6_gripper`, `uf850`, `xarm6`, and `xarm7` all recorded
  `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with static joint metadata,
  dynamic checks disabled by policy, load/articulation/cleanup OK, WARN capture
  with no ERROR/FATAL entries, and final port `[redacted]` clear. This is static
  hazard-routing telemetry only, not joint-control or pick/place validation.
- Follow-up turn `[worker-id-redacted]` in the same
  instance-2 worker verified the remaining known dynamic-timeout families with
  `static_only_for_known_dynamic_timeouts=true`: fresh MCP runtime PID `[redacted]`,
  Kit PID `[redacted]` on port `[redacted]`, pre/final status responsive and stopped,
  OpenArm returned two static known-hazard rows in about `8.0s`, RobotStudio
  kept `so100` on the dynamic path and routed `so101_new_calib` static in about
  `3.1s`, Yahboom routed `dofbot` static in about `2.6s`, and profile-only UR
  routed `ur20` static while keeping `ur30` dynamic healthy in about `3.3s`.
  WARN/ERROR capture returned 18 WARN-or-higher entries including one
  UI-property ERROR, but there was no probe timeout or host degradation; owned
  Kit stop completed and final `process_list_kit_instances` returned
  `instances=[]`. Parent also verified no live Win32 process for PID `[redacted]`
  and no LISTENING socket on `8112`. This is static hazard-routing and
  mixed-batch telemetry only, not joint-control proof for static rows or
  pick/place validation.
- Continue to use `mcp_runtime_info` as the first in-band freshness check:
  absent tool, absent result fields, or source files newer than MCP import time
  means the live MCP host is stale and must be restarted before claiming the
  current result shape.

## Current-Code Smoke Matrix

Rows in this section come from thread `[worker-id-redacted]`
after the final timeout and safe-nudge partial-progress patches were loaded by
a fresh MCP host.

| profile | status | family | load/artic/joints/read | safe_nudge evidence | gripper | IK | EE pose | probe result | pick/place state |
|---|---|---|---|---|---|---|---|---|---|
| `franka_panda` | `candidate_pick_place` | `franka` | ok | `panda_joint1[0]`: original `0.00379`, target `0.01379`, readback `0.00857`; `readback_ok=false`, `moved_toward_target=true`, `progress_ratio=0.478`, settled/restored in 5 frames | ok | ok | ok | `overall_ok=true` | candidate only; later 2026-06-16 repeatability proof failed cycle 2 |
| `franka_fr3` | `validated_pick_place` | `franka` | ok | `fr3_joint1[0]`: original `-0.00021`, target `0.00979`, readback `0.00660`; `readback_ok=false`, `moved_toward_target=true`, `progress_ratio=0.681`, settled/restored in 5 frames | ok | ok | ok | `overall_ok=true` | durable FR3 proof exists separately |
| `factory_franka` | `candidate_pick_place` | `franka` | ok | `panda_joint1[0]`: original `-0.00486`, target `0.00514`, readback `-0.00093`; `readback_ok=false`, `moved_toward_target=true`, `progress_ratio=0.394`, settled/restored in 5 frames | ok | ok | ok | `overall_ok=true` | pick/place proof attempt timed out during cycle 1; later deeper offset trial degraded host; not validated |
| `ur10` | `candidate_pick_place` | `ur` | ok | `shoulder_pan_joint[0]`: original `-0.000000124`, target `0.009999876`, readback `0.009999750`; `readback_ok=true`, `progress_ratio=1.000`, settled/restored in 5 frames | skipped unsupported | ok | ok | `overall_ok=true` | not validated |
| `kawasaki_rs007l` | `candidate_pick_place` | `kawasaki` | ok | `joint1[0]`: original `0.0`, target `0.01000`, readback `0.00997`; `readback_ok=true`, `progress_ratio=0.997`, settled/restored in 5 frames | ok | ok; `default` target failed no-converge, then `kawasaki_relaxed_orientation` succeeded | ok; requested `tool0`, resolved `onrobot_rg2_base_link` | `overall_ok=true`; non-unsupported IK target failure preserved as attempted-target evidence | not validated |

## Current-Code Batch Matrix

| batch | profiles returned | result | notes |
|---|---|---|---|
| synthetic batch timeout: `candidate_pick_place` + Franka, `limit=2`, `batch_timeout_s=0.001` | `factory_franka` | `probe_batch_timeout`, `overall_ok=false` | returned in about `276ms`; no batch-level hang |
| historical pre-demotion `validated_pick_place`, `per_profile_timeout_s=90`, `batch_timeout_s=105` | `franka_panda`, `franka_fr3` | both `overall_ok=true` at probe level | safe-nudge partial-progress evidence preserved; `franka_panda` is now superseded by the 2026-06-16 non-proof artifact and is no longer catalog `validated_pick_place` |
| candidate Franka, `per_profile_timeout_s=90`, `batch_timeout_s=105` | `factory_franka` | `overall_ok=true` | remains `candidate_pick_place`; not promoted |
| pre-hardening candidate UR on instance-2, `per_profile_timeout_s=90`, `batch_timeout_s=105` | `ur10`, `ur10e` | `ur10`: `ROBOT_PROBE_PROFILE_TIMEOUT`; `ur10e`: `ROBOT_PROBE_BATCH_TIMEOUT` | call returned normally after about `103s`, but the host became unresponsive afterward |
| post-hardening candidate UR on restarted instance-1, `per_profile_timeout_s=45`, `batch_timeout_s=60` | `ur10`, `ur10e` | both `overall_ok=true`; no timeout or abort rows | host stayed responsive; final status returned in about `5ms` |
| post-hardening candidate Kawasaki on restarted instance-1, `per_profile_timeout_s=45`, `batch_timeout_s=90` | `kawasaki_rs007l`, `kawasaki_rs007n`, `kawasaki_rs013n`, `kawasaki_rs025n`, `kawasaki_rs080n` | all `overall_ok=true`; no timeout or abort rows | load/joints/safe-nudge/gripper ok; IK and EE pose skipped unsupported |
| validation_api EE-alias candidate UR on instance-2, `per_profile_timeout_s=45`, `batch_timeout_s=120` | `ur10`, `ur10e` | both `overall_ok=true`, `mcp_controllability=dynamic_joint_control`; no timeout or abort rows | unsupported grippers skipped cleanly; `ur10` IK `ee_link` and EE pose resolved `ee_link`; `ur10e` IK `tool0` and EE pose resolved `ee_link`; both requested `tool0` with `attempted_frames=["tool0"]` |
| validation_api EE-alias IK-only UR on instance-2 with `static_only_for_known_dynamic_timeouts=true`, `per_profile_timeout_s=45`, `batch_timeout_s=180` | `ur3`, `ur5`, `ur3e`, `ur5e`, `ur16e` | `ur3` and `ur5` returned static-only known-hazard rows; `ur3e`, `ur5e`, and `ur16e` returned `overall_ok=true`, `mcp_controllability=dynamic_joint_control` | static-only rows are not controllability proof; dynamic rows had IK `tool0` and EE pose resolved `wrist_3_link` for requested `tool0` with `attempted_frames=["tool0"]` |
| validation_api EE-alias candidate Kawasaki on instance-2, `per_profile_timeout_s=45`, `batch_timeout_s=180` | `kawasaki_rs007l`, `kawasaki_rs007n`, `kawasaki_rs013n`, `kawasaki_rs025n`, `kawasaki_rs080n` | all `overall_ok=true`, `mcp_controllability=dynamic_joint_control`; no timeout or abort rows | load/joints/safe-nudge/gripper ok; IK cleanly unsupported/skipped with Lula seed-dimension error; EE pose resolved `onrobot_rg2_base_link` for requested `tool0` with `attempted_frames=["tool0"]` |
| validation_api Lula seed-index single-profile smokes on instance-1 | `kawasaki_rs007l`, `ridgeback_ur5` | both `overall_ok=true`, `mcp_controllability=dynamic_joint_control`; no timeout rows; final host status responsive in about `14ms` | `kawasaki_rs007l` reached Lula solve without seed-dimension failure but the default `gripper_center` target did not converge; `ridgeback_ur5` IK succeeded for `tool0` with `solution_count=6`; both EE-pose checks resolved concrete USD frames |
| Kawasaki direct IK target sweep plus fresh patched probe ladder | `kawasaki_rs007l` | direct case B target succeeded with `solution_count=6`; later fresh MCP runtime probe returned `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, and selected `kawasaki_relaxed_orientation` after the default target failed cleanly | patched `robot_probe_arm_profile` now has durable live proof for the RS007L target ladder; this remains probe/IK telemetry only, not pick/place validation |
| current-code Kawasaki sibling IK ladder batch | `kawasaki_rs007l`, `kawasaki_rs007n`, `kawasaki_rs013n`, `kawasaki_rs025n`, `kawasaki_rs080n` | all five returned `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, no timeout or abort rows, final host health responsive; `rs007l`, `rs007n`, `rs013n`, and `rs025n` selected `kawasaki_relaxed_orientation` after default no-converge with `solution_count=6`; `rs080n` initially recorded both targets as clean no-converge | superseded by the RS080N direct sweep and patch below; still useful sibling-batch evidence that no row timed out or degraded the host |
| RS080N direct IK target sweep and post-patch probe | `kawasaki_rs080n` | direct target case C `[0.7,0.0,0.5,0.0,0.0,1.0,0.0]` succeeded with `solution_count=6` after default and relaxed-low no-converged; parent patch added `kawasaki_rs080n_relaxed_forward`; fresh MCP PID `[redacted]` proved the patched import was fresh and the post-patch probe selected `kawasaki_rs080n_relaxed_forward`, returning `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, safe nudge/gripper/EE/cleanup ok | current-code IK target proof now covers RS080N too; this remains probe/IK telemetry only, not pick/place validation |
| fresh IK-classification five-profile smoke on instance-1, `timeout_s=45` each | `franka_panda`, `franka_fr3`, `factory_franka`, `ur10`, `kawasaki_rs007l` | all five returned `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, and `probe_capability_level_name=ik_or_ee_telemetry`; final host health responsive | current MCP import was fresh; `ur10` gripper stayed skipped unsupported without failing the row; `kawasaki_rs007l` preserved default-target no-converge as an attempted-target failure before relaxed-orientation IK success; this remains probe telemetry only |
| current-code exact `profile_names` selector live smoke on instance-1 | `franka_panda`, `franka_fr3`, `factory_franka`, `ur10`, `kawasaki_rs007l` | fresh worker `[worker-id-redacted]`; MCP PID `[redacted]`, owned Kit port `[redacted]` PID `[redacted]`; `robot_probe_arm_profiles(profile_names=[...], per_profile_timeout_s=45, batch_timeout_s=180)` returned normally in `10627ms` with `count=5`, `requested_count=5`, top-level `profile_names` and row order exactly matching the request, all five `overall_ok=true`, `mcp_controllability_counts={"dynamic_joint_control": 5}`, `probe_capability_level_name_counts={"ik_or_ee_telemetry": 5}`, `pick_place_validation_status_counts={"known_pick_place_blocker": 2, "catalog_validated_pick_place": 1, "not_validated_by_probe": 2}`, `unsupported_capability_profiles=["ur10"]`, and no timed-out, blocked, hard-failure, or lifecycle-recovery rows | proves the new exact ordered batch selector and row-level unsupported-capability handling on a fresh MCP runtime; every row reported `probe_proves_pick_place=false`, so this is probe/tool-surface evidence only and does not promote any profile |
| fresh bounded-default single-profile smoke on instance-1, `timeout_s` omitted | `franka_panda` | `mcp_runtime_info` proved fresh MCP import with single-profile default `90.0`, batch per-profile default `90.0`, batch timeout default `105.0`, and no stale source modules; omitted-timeout probe returned normally with `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, and `probe_capability_level_name=ik_or_ee_telemetry` | proves runtime default exposure and one bounded omitted-timeout call path only; not a timeout-stress test and not pick/place validation |
| historical pre-demotion pick/place-boundary result-shape batch smoke on instance-1 | `franka_panda` | worker `[worker-id-redacted]`; fresh MCP PID `[redacted]`; owned Kit port `[redacted]` PID `[redacted]`; batch returned in about `9.2s` with `count=1`, `requested_count=1`, `mcp_controllability_counts={"dynamic_joint_control": 1}`, `probe_capability_level_name_counts={"ik_or_ee_telemetry": 1}`, historical `pick_place_validation_status_counts={"catalog_validated_pick_place": 1}`, historical `pick_place_validation_status_profiles={"catalog_validated_pick_place": ["franka_panda"]}`, and no timed-out, blocked, hard-failure, or lifecycle-recovery profiles | superseded by 2026-06-16 non-proof evidence; current code reports `franka_panda` as `known_pick_place_blocker`, with `probe_proves_pick_place=false`; this remains live probe/runtime result-shape evidence only, not pick/place proof or promotion |
| historical pre-demotion profile-map result-shape batch smoke on instance-1 | `franka_panda` | worker `[worker-id-redacted]`; fresh MCP PID `[redacted]`; owned Kit port `[redacted]` PID `[redacted]`; batch returned in about `2.4s` with `count=1`, `requested_count=1`, `mcp_controllability_counts={"dynamic_joint_control": 1}`, `mcp_controllability_profiles={"dynamic_joint_control": ["franka_panda"]}`, `probe_capability_level_name_counts={"ik_or_ee_telemetry": 1}`, `probe_capability_level_name_profiles={"ik_or_ee_telemetry": ["franka_panda"]}`, historical `pick_place_validation_status_counts={"catalog_validated_pick_place": 1}`, historical `pick_place_validation_status_profiles={"catalog_validated_pick_place": ["franka_panda"]}`, and no timed-out, blocked, hard-failure, or lifecycle-recovery profiles | superseded by 2026-06-16 non-proof evidence; current code reports `franka_panda` as `known_pick_place_blocker`, with `probe_proves_pick_place=false`; this remains live profile-map/result-shape proof only, not pick/place proof or promotion |
| fresh patched Denso IK-only target-ladder and EE-frame small batches | `cobotta_pro_900`, `cobotta_pro_1300` | both `overall_ok=true`, `mcp_controllability=dynamic_joint_control`; no timeout or abort rows | load/joints/safe-nudge ok; gripper skipped unsupported; `cobotta_pro_900` selected `relaxed_orientation` after default no-converge; `cobotta_pro_1300` selected `default`; fresh post-patch EE probe resolved requested `onrobot_rg6_base_link` for both with `attempted_frames=["onrobot_rg6_base_link"]` |
| post-hardening single-profile IK-only non-UR probes | `fanuc_crx10ia_l`, `flexiv_rizon4`, `kuka_kr210_l150`, `techman_tm12` | all `overall_ok=true`; no timeout or abort rows | unsupported capabilities recorded as skipped per profile; fresh Kuka rerun recorded both `default` and `relaxed_orientation` IK targets as clean no-converge attempts |
| Kuka direct IK target sweep and fresh patched probe ladder | `kuka_kr210_l150` | direct sweep on instance-1, MCP PID `[redacted]`, owned Kit PID `[redacted]`, loaded `/World/KukaTargetSweep`; relaxed targets `[1.5,0.0,1.2,0.0,0.0,1.0,0.0]`, `[1.2,0.0,1.0,0.0,0.0,1.0,0.0]`, and `[1.8,0.0,1.2,0.0,0.0,1.0,0.0]` returned bounded no-convergence errors with `ee=tool0`; `[1.5,0.0,1.2,1.0,0.0,0.0,0.0]` succeeded with `tool0` and a six-joint solution; fresh instance-2 patched probe used MCP PID `[redacted]`, Kit PID `[redacted]`, port `[redacted]`, no stale source modules, and returned normally in `3753ms` with `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, `load/joint_config/joint_read/safe_nudge/ik/ee_pose/cleanup=true`, gripper skipped unsupported, selected `kuka_forward_high_identity` after `default` and `relaxed_orientation` failed cleanly with `ROBOT_SET_EE_TARGET_ERROR`, `tool0`, and `solution_count=6`; final sim health remained responsive | current-code probe ladder is now live-proven for Kuka; this is IK/probe controllability evidence only, not gripper proof, pick/place validation, or support-status promotion |
| mobile-manipulator IK-only single profile with mobile UR EE-frame and seed-index patches | `ridgeback_ur5` | `overall_ok=true`, `mcp_controllability=dynamic_joint_control` after fresh instance-1 reruns | safe nudge skipped mobile-base dummy joints and nudged `ur_arm_shoulder_pan_joint`; gripper unsupported; latest IK succeeded for `tool0` with `solution_count=6`; EE pose resolved `ur_arm_wrist_3_link` for requested `tool0` with `attempted_frames=["tool0"]` |
| post-hardening mobile-manipulator candidate single profile | `ridgeback_franka` | `overall_ok=true` after fresh-selector rerun | new selector skipped mobile-base dummy joints and nudged `panda_joint1`; gripper, IK, and EE pose passed |
| post-hardening IK-only UR single profiles | `ur16e`, `ur3`, `ur3e`, `ur5`, `ur5e` | `ur16e`, `ur3e`, `ur5e`: `overall_ok=true`; `ur3`, `ur5`: `ROBOT_PROBE_PROFILE_TIMEOUT` | `ur3` and `ur5` cleanup timed out and degraded the host; `ur5e` was recovered and probed in a final single-profile pass |
| profile-only Kinova | `kinova_gen3`, `kinova_j2n6s300`, `kinova_j2n7s300` | all `overall_ok=true`; no timeout or abort rows | safe nudge ok; no gripper; IK skipped no robot description; EE pose skipped unsupported |
| profile-only OpenArm | `openarm_unimanual`, `openarm_bimanual` | `openarm_unimanual`: `ROBOT_PROBE_PROFILE_TIMEOUT`; `openarm_bimanual`: isolated `ROBOT_PROBE_WARMUP_STEP_TIMEOUT` after an earlier historical `ROBOT_PROBE_BATCH_ABORTED` row; fresh current-code static-policy batch routed both through `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` | `openarm_bimanual` no longer relies only on inherited batch-abort evidence; static-policy batch proves safer broad-refresh routing for OpenArm, not dynamic joint control |
| profile-only Rethink and RobotStudio | `sawyer`, `so100`, `so101_new_calib` | `sawyer`, `so100`: `overall_ok=true`; `so101_new_calib`: `ROBOT_PROBE_PROFILE_TIMEOUT`; fresh current-code RobotStudio static-policy batch kept `so100` dynamic healthy and routed `so101_new_calib` through `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` | `so101_new_calib` cleanup timed out and degraded the host on the dynamic path; static-policy batch proves mixed-family routing, not joint-control proof for `so101_new_calib` |
| profile-only UFactory | `lite6`, `lite6_gripper`, `uf850`, `xarm6`, `xarm7` | `lite6`: `ROBOT_PROBE_PROFILE_TIMEOUT`; `lite6_gripper`, `uf850`, `xarm6`, and `xarm7`: isolated `ROBOT_PROBE_WARMUP_STEP_TIMEOUT`; fresh current-code static-policy batch routed all five through `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` | `lite6_gripper`, `uf850`, `xarm6`, and `xarm7` no longer rely only on inherited batch-abort evidence; the static-policy batch proves safer broad-refresh routing for all five UFactory rows, not dynamic joint control |
| profile-only Unitree | `unitree_z1` | fresh single-profile rerun: `overall_ok=true`; earlier batch row had `ROBOT_PROBE_PROFILE_TIMEOUT` | current evidence is clean probe controllability; earlier timeout row is kept as historical behavior |
| profile-only UR | `ur20`, `ur30` | `ur20`: `ROBOT_PROBE_PROFILE_TIMEOUT`; `ur30`: fresh isolated `overall_ok=true`, `mcp_controllability=dynamic_joint_control` after an earlier historical `ROBOT_PROBE_BATCH_ABORTED` row; fresh current-code static-policy batch routed `ur20` through `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` while keeping `ur30` dynamic healthy | `ur30` load/joints/safe-nudge/cleanup ok; gripper skipped no built-in candidate; IK skipped no robot description; EE pose unsupported; no pick/place validation; `ur20` static-policy row is not joint-control proof |
| profile-only Yahboom | `dofbot` | dynamic rerun: `ROBOT_PROBE_WARMUP_STEP_TIMEOUT`, `overall_ok=false`, no downstream checks, stop/cleanup `*_DEFERRED`; static-only rerun: load/articulation ok, dynamic checks skipped as `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED`; fresh current-code static-policy batch routed `dofbot` through `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` | dynamic path still degraded the host; static-policy routing kept the host responsive but is only known-hazard static evidence |
| profile-only Yaskawa | `nex10` | `overall_ok=true`; no timeout or abort rows | safe nudge ok; no gripper; IK skipped no robot description; EE pose ok |
| direct static-only blocked-row triage | `openarm_unimanual`, `openarm_bimanual`, `so101_new_calib`, `lite6`, `lite6_gripper`, `uf850`, `xarm6`, `xarm7`, `ur3`, `ur5`, `ur20`, `ur30` | all returned `overall_ok=false` by design with load/articulation/cleanup OK and dynamic checks skipped as `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED` | direct load/articulation evidence now exists for these rows; this does not supersede dynamic timeout/blocker evidence for rows with later blocker proof, and it is not controllability proof for rows without later dynamic evidence; `ur30` now has later dynamic joint-control proof |
| current-code static policy live smoke | `ur3`, `ur3e` with `static_only_for_known_dynamic_timeouts=true` | `ur3`: static-only row with `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD`, 6-DOF static joint metadata, `overall_ok=false`; `ur3e`: full dynamic row, `overall_ok=true` | worker `[worker-id-redacted]` returned normally in about `3.7s`; proves opt-in batch routing can protect known direct timeout rows while keeping neighboring profiles on the dynamic path; no new joint-control or pick/place claim for `ur3` |
| current-code single-profile UR5 static policy live smoke | `ur5` with `robot_probe_arm_profile(..., dynamic_checks=true, static_only_for_known_dynamic_timeouts=true, timeout_s=45)` | returned normally in about `1.8s`; `overall_ok=false`, `mcp_controllability=static_load_articulation_metadata`, `probe_capability_level_name=load_articulation_static_metadata`, `dynamic_probe_policy.error_code=ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD`, 6-DOF `static_joint_config` from `usd_joint_prims_static`, and dynamic checks disabled for joint config/read, safe nudge, gripper, IK, and EE pose | worker `[worker-id-redacted]`; fresh MCP PID `[redacted]`, Kit port `[redacted]` PID `[redacted]`; pre/final simulation status responsive/stopped; this proves the single-profile guard shape only, not dynamic joint control or pick/place validation for `ur5` |
| current-code UFactory static policy live smoke | `lite6`, `lite6_gripper`, `uf850`, `xarm6`, `xarm7` with `static_only_for_known_dynamic_timeouts=true` | all five rows returned `overall_ok=false`, `mcp_controllability=static_load_articulation_metadata`, `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD`, static joint metadata, dynamic checks skipped as `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED`, and load/articulation/cleanup OK | worker `[worker-id-redacted]` returned normally in about `7.7s`, kept the host responsive, captured WARNs with no ERROR/FATAL entries, and cleared owned port `[redacted]`; this proves broad-refresh hazard routing for UFactory rows including `uf850`, not joint-control or pick/place validation |
| current-code remaining known-timeout static policy live smoke | `openarm_unimanual`, `openarm_bimanual`, `so100`, `so101_new_calib`, `dofbot`, `ur20`, `ur30` with `static_only_for_known_dynamic_timeouts=true` | OpenArm: both rows static known-hazard (`11` and `22` static DOFs); RobotStudio: `so100` dynamic `dynamic_joint_control`, `so101_new_calib` static known-hazard (`6` DOFs); Yahboom: `dofbot` static known-hazard (`13` DOFs); profile-only UR: `ur20` static known-hazard (`6` DOFs), `ur30` dynamic `dynamic_joint_control` | follow-up turn `[worker-id-redacted]` kept the host responsive through all four small batches and owned cleanup; captured 18 WARN-or-higher entries including one UI-property ERROR but no timeout/degradation; final process list returned `instances=[]` and parent verified no live PID/listener on `8112`; this proves safer broad-refresh routing for the remaining known hazards, not joint-control or pick/place validation for static rows |

## Historical Candidate Batch Matrix

These rows come from thread `[worker-id-redacted]`. They remain
useful for prioritization, but current-code claims should be based on the
fresh smoke and batch evidence above.

| profile | status | family | historical evidence | current conclusion |
|---|---|---|---|---|
| `factory_franka` | `candidate_pick_place` | `franka` | load/articulation/joints/gripper/IK/EE ok; stale safe-nudge failed | fresh current-code smoke and batch now pass at probe level |
| `ur10` | `candidate_pick_place` | `ur` | overall ok; load/articulation/joints/safe-nudge/IK/EE ok; gripper skipped unsupported | post-hardening smoke and tight candidate batch pass at probe level; fresh EE-alias batch also resolved EE pose through `ee_link` |
| `ur10e` | `candidate_pick_place` | `ur` | load/articulation/joints/IK/EE ok; stale safe-nudge failed; gripper support not proven | post-hardening tight candidate batch passes at probe level; fresh EE-alias batch also resolved EE pose through `ee_link` |
| `kawasaki_rs007l` | `candidate_pick_place` | `kawasaki` | load/articulation/joints/gripper ok; stale safe-nudge failed; IK/EE skipped unsupported | post-hardening candidate batch passes at probe level; fresh EE-alias batch resolves EE pose through `onrobot_rg2_base_link`, while IK remains unsupported |
| `kawasaki_rs007n` | `candidate_pick_place` | `kawasaki` | load/articulation/joints/gripper ok; stale safe-nudge failed; IK/EE skipped unsupported | post-hardening candidate batch passes at probe level; fresh EE-alias batch resolves EE pose through `onrobot_rg2_base_link`, while IK remains unsupported |
| `kawasaki_rs013n` | `candidate_pick_place` | `kawasaki` | overall ok at probe level; load/articulation/joints/gripper ok; IK/EE skipped unsupported | post-hardening candidate batch passes at probe level; fresh EE-alias batch resolves EE pose through `onrobot_rg2_base_link`, while IK remains unsupported |
| `kawasaki_rs025n` | `candidate_pick_place` | `kawasaki` | overall ok at probe level; load/articulation/joints/gripper ok; IK/EE skipped unsupported | post-hardening candidate batch passes at probe level; fresh EE-alias batch resolves EE pose through `onrobot_rg2_base_link`, while IK remains unsupported |
| `kawasaki_rs080n` | `candidate_pick_place` | `kawasaki` | overall ok at probe level; load/articulation/joints/gripper ok; IK/EE skipped unsupported | post-hardening candidate batch passes at probe level; fresh EE-alias batch resolves EE pose through `onrobot_rg2_base_link`, while IK remains unsupported |
| `ridgeback_franka` | `candidate_pick_place` | `mobile_manipulator` | load path reached; stale safe-nudge failed on `dummy_base_prismatic_x_joint` | fresh-selector rerun now passes safe nudge by choosing `panda_joint1`; gripper/IK/EE also pass |

## Timed Out Or Blocked

| scope | evidence | impact |
|---|---|---|
| Pre-hardening candidate UR batch on instance-2 | `ur10` returned a per-profile `ROBOT_PROBE_PROFILE_TIMEOUT`; `ur10e` returned `ROBOT_PROBE_BATCH_TIMEOUT`; batch call returned normally after about `103s` | superseded for UR by post-hardening instance-1 rerun, but still documents the failure mode |
| Pre-hardening instance-2 host responsiveness after UR batch | `extension_capture_logs(level="WARN")` timed out after about `91.6s`; follow-up `simulation_get_status` timed out after about `91.8s`; Windows reported PID `[redacted]` as `Responding=False` | candidate Kawasaki batch and broader matrix were stopped in this host |
| Pre-hardening instance-2 Kit log | no explicit `[Error]`, `[Fatal]`, traceback, or exception lines found by worker grep; crashreporter warnings began around `2026-06-15T07:37:33Z`; `py-spy.exe` launched as PID `[redacted]`; a local Kit crash dump zip was created under the user-local Omniverse data directory; repeated waits for `crashreport.gui.exe` followed | treat the old host as unhealthy after UR batch timeout |
| Instance-1 startup before recovery | PID `[redacted]` owned port `[redacted]`, `is_this_mcp_instance=true`, but `kit_app_start` timed out twice and Windows reported `Responding=False` | recovered by lifecycle-allowed `kit_app_restart` |
| Post-hardening candidate UR batch on instance-1 | `ur10` and `ur10e` both returned full `overall_ok=true` rows with `stage_reset_stop ok=true`; no timeout or abort rows | UR candidate batch is now MCP-controllable in this tight rerun; still not pick/place validated |
| FactoryFranka pick/place proof attempt | Fit preflight passed, but first playback cycle status poll returned an MCP error after about `91.7s`; follow-up `simulation_stop`, WARN capture, ERROR capture, and final pre-cleanup `simulation_get_status` also timed out/errored after about `91.7s`; lifecycle cleanup unambiguously restarted owned port `[redacted]` from PID `[redacted]` to PID `[redacted]`, after which status returned in about `20ms`; no `done/lifted/placed` evidence was captured | `factory_franka` remains `candidate_pick_place`; the Franka-family adapter needs timeout/root-cause work before promotion can be considered |
| FactoryFranka bounded playback-status diagnostic | Install and fit preflight passed again, immediate bounded status returned in about `14ms`, but the first bounded playback poll returned `ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT` after about `1.0s`; follow-up `simulation_stop` still degraded to `SIMULATION_CONTROL_ERROR` after about `91.8s`; cleanup restarted only owned port `[redacted]` from PID `[redacted]` to PID `[redacted]`, after which status returned in about `26ms`; a fresh selector-gate smoke then returned unsupported in about `222ms`, created no `/World/FactoryFrankaSafetyGate` prim, and left status responsive in `11ms`; parent follow-up now adds cached `diagnostics.playback_progress` for the next live debug run | caller-side bounded status records the timeout quickly, but FactoryFranka playback still degrades the host after play; the current profile selector blocks this route by default and no validation or promotion is claimed |
| Fresh direct FactoryFranka playback-progress diagnostic | Fresh instance-1 MCP runtime exposed the new low-level direct install args; fresh Kit PID `[redacted]` loaded `/World/FactoryFranka`, install/fit preflight passed, immediate status exposed empty `diagnostics.playback_progress`, first playback poll reached `status=picking`, `steps=162`, `controller_event=1`, event counts `{0:124, 1:38}`, no lift, and distance-to-target about `0.715914`; second bounded poll failed cleanly at `max_steps=240` with `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`, `final_distance=0.715914`, and the host stayed responsive/stoppable | direct proof arguments and controller-progress diagnostics are live-proven; FactoryFranka still fails before lift/place and remains `candidate_pick_place` |
| Playback joint/action telemetry hardening and rerun | Parent patch adds progress summary fields for max joint readback delta, max official action joint-target delta, action-position presence, and matching per-sample fields; focused extension tests cover bounded progress and action-index summarization; fresh telemetry rerun on Kit PID `[redacted]` reached terminal bounded failure at `steps=300`, `controller_event=1`, with `action_joint_positions_seen=true`, `max_joint_delta_from_initial=2.7101761177182198`, and `max_action_joint_position_delta=0.02078986167907715` | FactoryFranka event-1 failure is no longer a no-command/no-motion mystery: official actions and joint movement are present, but the cube is never lifted or placed; no pick/place validation and no promotion |
| Playback end-effector reach telemetry hardening and rerun | Parent patch adds progress summary fields for observed EE pose and min EE-to-pick/target distances plus per-sample EE position/reach distances; fresh telemetry rerun on Kit PID `[redacted]` reached terminal bounded failure at `steps=300`, `controller_event=1`, with `end_effector_pose_seen=true`, `min_end_effector_distance_to_pick=0.09593506298402886`, `min_end_effector_distance_to_target=0.7506843518273172`, and final sample EE position `[0.3023269773, 0.3810941875, 0.1107262522]`; object result stayed `done=false`, `lifted=false`, `placed=false`, `final_distance=0.7159140101325272`, `max_lift_delta=0.0` | FactoryFranka is no longer simply failing before observed approach: the hand reaches near the pick point but the cube is never lifted; next adapter work should target grasp/contact/timing. No pick/place validation and no promotion |
| Explicit FactoryFranka timing and nested-action parser hardening | Pre-fix explicit timing run with `max_steps=1000` advanced into event `2` at step `325`, got EE within about `0.0574m` of the pick point, and failed on nested action telemetry parsing (`float() argument must be a string or a real number, not 'list'`); parent patch now flattens nested numeric action/joint containers and adds regression coverage; post-fix live rerun restarted owned Kit to PID `[redacted]`, reached event `8` at step `806` without the parse failure, got EE-to-target down to about `0.0399m`, but still reported `done=false`, `lifted=false`, `placed=false`, and cleanup stop/health returned in about `25ms`/`17ms` | parser failure is fixed and later controller events are reachable; FactoryFranka still lacks durable lift/place proof and remains unpromoted |
| FactoryFranka gripper aperture/object-width telemetry | Parent patch adds progress summary fields for current gripper aperture, action gripper aperture when available, and object-width margins; focused tests cover aperture and margin summarization; live rerun restarted owned Kit to PID `[redacted]`, reached event `8` at step `815`, observed `gripper_aperture_seen=true`, `action_gripper_aperture_seen=false`, current aperture range `0.0001669081847239795` to `0.08000793680548668`, and `min_gripper_object_width_margin_m=-0.04489676958324096`; representative event-7/8 samples showed the gripper closing below object width and later reopening, while `done=false`, `lifted=false`, `placed=false`, `final_distance=0.7056631767940493`, `max_lift_delta=0.0`; the nested action parse failure did not recur | gripper/object margin telemetry is live and useful for grasp triage, but it does not prove grasp, lift, or place; no pick/place validation and no promotion |
| FactoryFranka grasp-geometry sweep | Fresh bounded variants A-F compared baseline, explicit high/low pick positions, +/-2cm EE offsets, and the prior FR3 ScriptNode orientation hint `[0,1,0,0]`; all stayed no-lift/no-place with `max_lift_delta=0.0`; Variant D got the closest EE-to-target result at about `0.028165m` but still did not lift; F terminally failed with `Object was not lifted...`; G was skipped because F did not improve lift/contact | explicit pick geometry and the ScriptNode orientation hint are not enough for FactoryFranka durable proof; no pick/place validation and no promotion |
| FactoryFranka requested-strategy telemetry surface | After restarting only the owned `instance-1` Kit to pick up the validation extension patch, an idle direct FactoryFranka demo status exposed `diagnostics.requested_pick_strategy` with the exact explicit pick position `[0.3, 0.35, 0.02]`, object start `[0.3, 0.35, 0.02575]`, target `[0.45, -0.35, 0.02575]`, official-default hover height `0.3`, EE offset `[0.0, 0.0, -0.019999999552965164]`, orientation `[0.0, 1.0, 0.0, 0.0]`, events_dt, max_steps, and reset-on-play; status was idle at step `0`, `object_fit_ok=true`, `uses_kinematic_carry=false`, and final health stayed responsive | requested geometry is now live-visible for apples-to-apples FactoryFranka reruns; this was not a playback cycle and does not validate pick/place |
| FactoryFranka contact-window diagnostics surface | Fresh instance-1 MCP runtime and fresh Kit PID `[redacted]` loaded `/World/FactoryFrankaContactTelemetry`; immediate status exposed all four new `diagnostics.playback_progress` contact-window keys; a 120-frame bounded sample populated `min_end_effector_distance_to_object=0.041107170889927866`, `gripper_closed_on_object_width_seen=true`, `min_end_effector_distance_to_object_during_closed_gripper=0.058858394036590496`, and `min_end_effector_xy_distance_to_object_during_closed_gripper=0.006803149706765672`, with final health responsive; parent follow-up classifies that shape as `closed_gripper_width_window_xy_aligned_outside_bbox_sphere`; a restart recheck on fresh Kit PID `[redacted]` exposed the full `contact_window` object and again classified the bounded sample as `closed_gripper_width_window_xy_aligned_outside_bbox_sphere` with `xy_aligned_during_closed_gripper=true` and `inside_object_bbox_sphere_during_closed_gripper=false`; the object-motion recheck on fresh Kit PID `[redacted]` reported `max_object_lift_delta_during_closed_gripper=-0.0027249995321035336`, `max_object_xy_motion_during_closed_gripper=0.011446855657808945`, and `lift_threshold_met_during_closed_gripper=false` | contact-window telemetry is live-proven and now more diagnostic, but bounded samples still ended without lift/place evidence; latest sample ended `placing`, `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`; no pick/place validation and no promotion |
| FactoryFranka Z-separation contact-window diagnostics | After restarting only the owned `instance-1` Kit to PID `[redacted]`, a direct low-level FactoryFranka demo at `/World/FactoryFrankaZContactDiag` exposed all six new Z-separation `contact_window` fields immediately; one 120-frame bounded playback sample ended `status=placing`, `controller_event=6`, `steps=442`, `done=false`, `lifted=false`, `placed=false`, and classified the closed-gripper window as `closed_gripper_width_window_xy_aligned_outside_bbox_sphere` with `axis_hint="z_offset_outside_object_height"`, `min_abs_end_effector_z_distance_to_object_during_closed_gripper=0.0520634651184082`, `object_half_height_m=0.02000017329974136`, and `closed_gripper_z_margin_to_object_half_height_m=0.03206329181866684`; final health stayed responsive | Z-separation telemetry is live-proven and identifies vertical separation outside object half-height during the closed-gripper window; this is diagnostics-surface proof only, not MCP controllability or pick/place validation, and no promotion is claimed |
| FactoryFranka simple Z-offset adapter trial | Same fresh owned instance then tested direct low-level variants with `end_effector_orientation=[0,1,0,0]` and offsets `-0.032m` and `-0.052m`; both installed and ran one bounded 260-frame sample with final health responsive, but A ended `status=placing`, `steps=386`, `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`, `classification=closed_gripper_width_window_not_xy_aligned`, and `axis_hint=xy_offset_outside_object_width`; B ended `status=placing`, `steps=396`, `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`, same XY-misaligned classification/hint, and no durable placement despite a closed-window lift-delta signal | simple negative EE Z offsets are live-disproven as a promotion path; useful adapter clue only, no MCP controllability proof, no pick/place validation, no promotion |
| FactoryFranka signed-delta contact-window diagnostics | After restarting only the owned `instance-1` Kit to PID `[redacted]`, a direct low-level FactoryFranka demo at `/World/FactoryFrankaSignedDeltaDiag` exposed the new signed-delta keys at both `diagnostics.playback_progress` and nested `contact_window`; the first bounded playback poll populated min-distance/min-XY deltas `[-0.16773882508277893,-0.3364330865442753,0.862981878221035]` and min-abs-Z delta `[-0.196339413523674,-0.3476055832579732,0.8564660307019949]`, then `simulation_stop` and final health returned quickly | signed directional EE-object offsets are live-proven for the closed-gripper window; the sample still reported `closed_gripper_width_window_not_xy_aligned`, `axis_hint=xy_offset_outside_object_width`, `done=false`, `lifted=false`, and `placed=false`, so no pick/place validation or promotion |
| FactoryFranka approach-window diagnostics | After restarting only the owned `instance-1` Kit to PID `[redacted]`, a direct low-level FactoryFranka demo at `/World/FactoryFrankaApproachDiag` exposed `approach_window` and all-time EE/object delta keys before playback; one bounded playback poll populated `approach_window_xy_aligned_outside_bbox_sphere`, `axis_hint=z_offset_outside_object_height`, min EE/object distance `0.047829756171164264`, min XY distance `0.007903502475505735`, min abs Z distance `0.0339291263371706`, all-time min-distance delta `[-0.010070651769638062,-0.02760830521583557,0.037736574187874794]`, min-XY delta `[0.007901966571807861,0.0001558065414428711,0.28844790533185005]`, and min-abs-Z delta `[-0.0024915337562561035,-0.03883817791938782,0.0339291263371706]`; the same bounded sample terminally failed at `600` playback ticks, then stopped cleanly and final health stayed responsive with WARN+ count `0` | approach-window telemetry is live-proven and now separates approach geometry from closed-gripper contact; comparison `contact_window` still reported `closed_gripper_width_window_far_from_object`, `done=false`, `lifted=false`, `placed=false`, and `max_lift_delta=0.0`, so no MCP controllability proof, no pick/place validation, and no promotion |
| FactoryFranka exact `-0.05m` next-offset trial | After finite-value recommendation hardening, instance-2 restarted only owned port `[redacted]` to PID `[redacted]` while leaving external port `[redacted]` untouched; the direct low-level run used `end_effector_offset=[0,0,-0.05]`, reached `placing` at `steps=475`, `controller_event=6`, and final status failed cleanly at `steps=600` with `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`, final distance `0.7155928062`, min EE-to-pick `0.046850498`, min EE-to-target `0.224221945`, and min EE-to-object `0.046800660`; stop/final health stayed responsive, WARN+ count was 4 with no ERROR entries | `-0.05m` improved proximity and got beyond early event-1 failure, but still produced no lift/place proof; final diagnostics suggest deeper Z offsets (`next_m` about `-0.064m` approach, `-0.099m` contact). This is adapter-geometry guidance only, not validation or promotion |
| FactoryFranka `-0.064m`/`-0.099m` offset comparison | Same instance-2 PID `[redacted]` stayed healthy without restart. The `-0.064m` direct run reached `placing`, event `6`, then failed at `steps=600` with `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0`, final distance `0.7153383920`, and final min EE-to-target `0.1278011094`; the `-0.099m` direct run also reached `placing`, event `6`, then failed at `steps=600` with `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0025671795`, final distance `0.6634314373`, and final min EE-to-target `0.0813630504`; final health stayed responsive and WARN+ count was 2 | deeper Z offsets improved proximity but still did not produce durable lift/place proof; the next adapter attempt should combine the Z recommendation with XY/contact adjustment and timing analysis. This is non-promoting adapter evidence only |
| FactoryFranka combined XY/Z offset comparison | Same instance-2 PID `[redacted]` stayed healthy without restart. Variant C with offset `[0.0126288105,0.0075458046,-0.0989999995]` failed at `steps=600` with `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0025472418`, final distance `0.6756008308`, final min EE-to-target `0.0879629643`, and contact still `closed_gripper_width_window_not_xy_aligned`; Variant D with offset `[0.0126288105,0.0075458046,-0.1129074022]` failed at `steps=600` with `done=false`, `lifted=false`, `placed=false`, `max_lift_delta=0.0025672056`, final distance `0.6668715948`, final min EE-to-target `0.0664822579`, and contact `closed_gripper_width_window_xy_aligned_outside_bbox_sphere`; final health stayed responsive and WARN+ count was 2 | combined offsets improved the geometry signal, especially D's target proximity and XY-aligned contact classification, but still did not produce durable lift/place proof. This is non-promoting adapter evidence only |
| Playback-progress diagnostics-surface smoke | After restarting only the owned instance-2 Kit for the `validation_api` patch, a validated `franka_fr3` demo installed successfully and immediate status returned in `19ms` with `diagnostics.playback_progress` present (`current_event=0`, `current_event_ticks=0`, `sample_interval_steps=30`, `sample_limit=32`, zero samples before playback); final status stayed responsive in `12ms`; no play cycle was run | live evidence that the status surface exposes cached progress diagnostics; not pick/place validation or a profile promotion |
| Post-hardening `ur3` individual IK-only probe | dynamic row returned `ROBOT_PROBE_PROFILE_TIMEOUT`; cleanup reported `ROBOT_PROBE_SIMULATION_STOP_TIMEOUT` and `ROBOT_PROBE_CLEANUP_TIMEOUT`; follow-up `simulation_get_status` took about `91.8s` and returned `SIMULATION_STATUS_ERROR`; a later direct static-only rerun loaded, detected articulation, cleaned up, and kept final status responsive | `ur3` remains a high-priority UR dynamic timeout teardown target, but direct load/articulation evidence now exists |
| Post-hardening live abort path | `openarm_bimanual`, `lite6_gripper`, `uf850`, `xarm6`, `xarm7`, and `ur30` returned `ROBOT_PROBE_BATCH_ABORTED` after an earlier same-batch profile timed out with unhealthy cleanup | abort path is now both unit-tested and live-proven; aborted rows are explicit blocked evidence, not MCP-controllability proof; `openarm_bimanual`, `lite6_gripper`, `uf850`, `xarm6`, and `xarm7` were later rerun in isolation and superseded by direct warmup-timeout evidence, while `ur30` was later superseded by direct dynamic joint-control proof |
| IK-only UR family | `ur16e`, `ur3e`, and `ur5e` returned `overall_ok=true`; `ur3` and `ur5` returned `ROBOT_PROBE_PROFILE_TIMEOUT` with unhealthy cleanup and post-status failures around `91.7s`; both later passed direct static-only load/articulation/cleanup probes | `ur3` and `ur5` remain UR dynamic timeout teardown targets; `ur3e`/`ur5e` are probe-controllable but not pick/place validated |
| Superseded profile-only healthy timeout | `unitree_z1` returned `ROBOT_PROBE_PROFILE_TIMEOUT` in an earlier batch, but timeout cleanup was healthy and post-status returned in about `15ms`; a fresh single-profile rerun now returns `overall_ok=true` | keep the timeout as historical host-behavior evidence, but treat `unitree_z1` as currently MCP-controllable at probe level |
| Profile-only unhealthy timeouts | `openarm_unimanual`, `so101_new_calib`, `lite6`, `ur20`, and `dofbot` returned `ROBOT_PROBE_PROFILE_TIMEOUT` with cleanup stop/cleanup timeout and post-status failures around `91.6s` to `91.8s`; later static-only reruns for `openarm_unimanual`, `so101_new_calib`, `lite6`, and `ur20` loaded, detected articulation, cleaned up, and kept the host responsive; `openarm_bimanual` later returned an isolated `ROBOT_PROBE_WARMUP_STEP_TIMEOUT` after load/articulation/play, stop/cleanup were deferred, follow-up status degraded to `SIMULATION_STATUS_ERROR` after about `75.4s`, and WARN capture failed with `EXTENSION_LOGS_ERROR` because REST was no longer accepting requests; `lite6_gripper` later returned the same isolated warmup-step timeout shape, with follow-up status degraded after about `53.3s`, WARN capture failing because REST was no longer accepting requests, and the owned port clear after scoped cleanup; `uf850` later returned the same isolated warmup-step timeout shape, with follow-up status degraded after about `85.3s`, WARN capture failing because REST was no longer accepting requests, and owned port `[redacted]` clear after scoped cleanup | dynamic timeout teardown remains required before deeper adapter work; static-only evidence does not prove joint control |
| Static-only hazard triage | `dofbot` with `dynamic_checks=false` completed in about `3.1s`; later direct static-only probes for `openarm_unimanual`, `openarm_bimanual`, `so101_new_calib`, `lite6`, `lite6_gripper`, `uf850`, `xarm6`, `xarm7`, `ur3`, `ur5`, `ur20`, and `ur30` also completed; all had load/articulation/cleanup OK and physics-dependent checks skipped with `ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED`; fresh current-code static-policy batches then routed UFactory, OpenArm, `so101_new_calib`, `dofbot`, and `ur20` through `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` while preserving healthy dynamic neighbors such as `so100` and `ur30` | durable load/articulation-only evidence now exists for the static path, and the broad-refresh known-hazard guard now has live proof beyond UFactory; not proof of joint control, MCP controllability, or pick/place behavior for static rows; `ur30` now has later dynamic proof |
| Direct profile-only blocked rows | `openarm_bimanual`, `lite6_gripper`, `uf850`, `xarm6`, `xarm7`, and `ur30` were batch-aborted after an earlier unhealthy timeout in their family batch; all six later completed direct static-only load/articulation/cleanup probes without timeout; `openarm_bimanual`, `lite6_gripper`, `uf850`, `xarm6`, and `xarm7` now also have isolated dynamic warmup-timeout evidence; `ur30` now has isolated dynamic joint-control evidence | these rows are no longer missing direct load/articulation evidence; `openarm_bimanual`, `lite6_gripper`, `uf850`, `xarm6`, and `xarm7` have isolated dynamic blocker proof, and `ur30` has direct MCP controllability proof |

## Guarded Hazard Ledgers

These tables mirror the code-owned guard ledgers returned by
`robot_list_arm_profiles` as `known_dynamic_timeout_profile_reasons` and
`known_pick_place_blocker_profile_reasons`. They document live evidence used for
safer routing and playback triage only. Dynamic timeout guard rows are not
dynamic joint-control proof; pick/place blocker rows do not negate probe-level
MCP controllability and do not promote or demote profile status.

### Known Dynamic Timeout Profiles

| profile | reason |
|---|---|
| `dofbot` | warmup_step timed out after load/articulation/play and degraded the host |
| `lite6` | dynamic profile-only probe timed out and degraded the host |
| `lite6_gripper` | isolated dynamic profile-only probe timed out during warmup_step and degraded the host |
| `openarm_bimanual` | isolated dynamic profile-only probe timed out during warmup_step and degraded the host |
| `openarm_unimanual` | dynamic profile-only probe timed out and degraded the host |
| `so101_new_calib` | dynamic profile-only probe timed out and degraded the host |
| `uf850` | isolated dynamic profile-only probe timed out during warmup_step and degraded the host |
| `ur3` | dynamic IK-only probe timed out and degraded the host |
| `ur5` | dynamic IK-only probe timed out and degraded the host |
| `ur20` | dynamic profile-only probe timed out and degraded the host |
| `xarm6` | isolated dynamic profile-only probe timed out during warmup_step and degraded the host |
| `xarm7` | isolated dynamic profile-only probe timed out during warmup_step and degraded the host |

### Known Pick/Place Blocker Profiles

| profile | reason |
|---|---|
| `franka_panda` | profile-selected playback repeatability proof failed on cycle 2: the cache-fix rerun avoided the prior ParallelGripper NoneType crash but failed with insufficient lift for durable proof |
| `factory_franka` | direct Franka-family playback trials reached no durable lift/place proof, and a deeper combined-Z offset trial degraded simulation/status/log calls |

## Full Catalog Coverage

This table is the profile-by-profile coverage ledger for
`builtin_robot_arm_profiles()`. `tests/unit/test_doc_references.py` now guards
that every built-in profile appears exactly once here and that each row's
`status` and `family` match the code catalog. The guard does not validate
pick/place behavior; it prevents the matrix from silently omitting profiles,
drifting from the catalog, or claiming pick/place validation in the table's
final column for profiles that are not catalog `validated_pick_place`.

| profile | status | family | live MCP evidence on 2026-06-15 | pick/place validation |
|---|---|---|---|---|
| `franka_panda` | `candidate_pick_place` | `franka` | fresh probe smoke and historical batch evidence: load/gripper/IK/EE ok; safe-nudge partial progress accepted; 2026-06-16 repeatability proof attempts failed cycle 2, first with a ParallelGripper `NoneType` crash and then, after the cache fix avoided that crash, with insufficient lift; see `docs/artifacts/robot-pickplace/franka-panda-pickplace-nonproof-2026-06-16.md` | not validated |
| `franka_fr3` | `validated_pick_place` | `franka` | fresh smoke and validated batch: load/gripper/IK/EE ok; safe-nudge partial progress accepted | durable FR3 proof exists |
| `factory_franka` | `candidate_pick_place` | `franka` | fresh smoke and candidate Franka batch: load/gripper/IK/EE ok; safe-nudge partial progress accepted; later pick/place proof attempt fit preflight passed but cycle 1 status and cleanup stop both timed out after about `91.7s`; bounded follow-up recorded the first playback status timeout in about `1.0s`, but follow-up stop still degraded after about `91.8s`; live selector-gate smoke now returns unsupported by default without creating the robot prim; direct EE reach telemetry showed the hand reaching within about `0.0959m` of the pick point while the cube remained unlifted/unplaced; explicit timing later reached event `2` and `0.0574m` EE-to-pick before exposing a nested-action telemetry parser bug; post-fix rerun advanced through event `8` without that parser failure and got EE-to-target to about `0.0399m`; aperture telemetry reached event `8` at step `815`, observed gripper aperture from about `0.000167m` to `0.080008m` with a minimum object-width margin about `-0.0449m`; the latest grasp-geometry sweep tried baseline, explicit high/low picks, +/-2cm EE offsets, and the `[0,1,0,0]` ScriptNode orientation hint, with Variant D reaching the closest EE-to-target distance about `0.028165m`, but every variant still reported `max_lift_delta=0.0` and no lift/place evidence; post-patch idle status now live-proves exact `diagnostics.requested_pick_strategy` telemetry after restart; follow-up contact-window smoke live-proves the new EE-to-object/closed-gripper diagnostic fields and populated them in a 120-frame bounded sample now classified as `closed_gripper_width_window_xy_aligned_outside_bbox_sphere`; a later restart recheck live-proves the full `contact_window` object after the validation API patch, again classifying the bounded sample as XY-aligned but outside the object bbox sphere; the object-motion recheck shows closed-gripper XY motion about `0.01145m` but lift delta stayed negative (`-0.002725m`) and below the `0.03m` lift threshold; the Z-separation recheck classifies the closed-gripper window as vertically outside the object half-height (`axis_hint="z_offset_outside_object_height"`, min absolute Z gap about `0.05206m`, margin about `0.03206m`) while ending `placing`, `done=false`, `lifted=false`, and `placed=false`; a follow-up simple Z-offset trial with `-0.032m` and `-0.052m` EE offsets stayed host-healthy but made the closed-gripper window XY-misaligned and still ended without `done/lifted/placed` proof; the latest signed-delta smoke live-proves directional EE-to-object vectors during the closed-gripper window, including min-distance/min-XY delta about `[-0.168,-0.336,0.863]`, but still reports `closed_gripper_width_window_not_xy_aligned`, `axis_hint=xy_offset_outside_object_width`, `done=false`, `lifted=false`, and `placed=false`; the latest approach-window smoke live-proves all-time approach classification separately from closed-gripper contact, with `approach_window_xy_aligned_outside_bbox_sphere`, `axis_hint=z_offset_outside_object_height`, min XY distance about `0.00790m`, min abs Z gap about `0.03393m`, but the comparison `contact_window` still reports `closed_gripper_width_window_far_from_object` and the run ended `done=false`, `lifted=false`, `placed=false`; the combined XY/Z offsets improved geometry but still failed cleanly, and the deeper `-0.1283m` combined-Z follow-up degraded the host before status/progress fields could be read; all contact-window, approach-window, and offset runs still ended without durable lift/place evidence | not validated |
| `kawasaki_rs007l` | `candidate_pick_place` | `kawasaki` | fresh individual smoke plus post-hardening, EE-alias, seed-index, patched-ladder, and sibling-batch smokes: load/joints/gripper/safe-nudge ok; EE pose resolved through `onrobot_rg2_base_link` for requested `tool0` with `attempted_frames=["tool0"]`; seed-index smoke reached Lula solve without seed-dimension failure; direct target sweep proved the relaxed orientation target with `solution_count=6`; fresh current-code probes now record the default target as handled no-convergence and succeed on `kawasaki_relaxed_orientation` with `end_effector_frame=gripper_center`, `solution_count=6` | not validated |
| `kawasaki_rs007n` | `candidate_pick_place` | `kawasaki` | post-hardening, EE-alias, and current-code sibling batches: load/joints/gripper/safe-nudge ok; EE pose resolved through `onrobot_rg2_base_link` for requested `tool0` with `attempted_frames=["tool0"]`; fresh current-code IK now records the default target as handled no-convergence and succeeds on `kawasaki_relaxed_orientation` with `solution_count=6` | not validated |
| `kawasaki_rs013n` | `candidate_pick_place` | `kawasaki` | post-hardening, EE-alias, and current-code sibling batches plus a supplemental single reprobe: load/joints/gripper/safe-nudge ok; EE pose resolved through `onrobot_rg2_base_link` for requested `tool0` with `attempted_frames=["tool0"]`; fresh current-code IK now records the default target as handled no-convergence and succeeds on `kawasaki_relaxed_orientation` with `solution_count=6` | not validated |
| `kawasaki_rs025n` | `candidate_pick_place` | `kawasaki` | post-hardening, EE-alias, and current-code sibling batches: load/joints/gripper/safe-nudge ok; EE pose resolved through `onrobot_rg2_base_link` for requested `tool0` with `attempted_frames=["tool0"]`; fresh current-code IK now records the default target as handled no-convergence and succeeds on `kawasaki_relaxed_orientation` with `solution_count=6` | not validated |
| `kawasaki_rs080n` | `candidate_pick_place` | `kawasaki` | post-hardening, EE-alias, current-code sibling batch, direct target sweep, and post-patch probe: load/joints/gripper/safe-nudge ok; EE pose resolved through `onrobot_rg2_base_link` for requested `tool0` with `attempted_frames=["tool0"]`; direct sweep proved `[0.7,0.0,0.5,0.0,0.0,1.0,0.0]` succeeds with `solution_count=6`; fresh patched MCP probe now records default and generic relaxed targets as handled no-converge attempts, then succeeds on `kawasaki_rs080n_relaxed_forward` with `solution_count=6` | not validated |
| `ridgeback_franka` | `candidate_pick_place` | `mobile_manipulator` | fresh-selector single probe: load/joints/gripper/IK/EE ok; safe nudge chose `panda_joint1` instead of mobile-base dummy joints | not validated |
| `ur10` | `candidate_pick_place` | `ur` | post-hardening smoke and tight candidate batch: load/joints/safe-nudge/IK/EE ok; gripper skipped unsupported; `stage_reset_stop ok=true`; fresh EE-alias candidate batch kept `overall_ok=true`, IK used `ee_link`, and EE pose resolved `ee_link` for requested `tool0` with `attempted_frames=["tool0"]` | not validated |
| `ur10e` | `candidate_pick_place` | `ur` | post-hardening tight candidate batch: load/joints/safe-nudge/IK/EE ok; gripper skipped unsupported; `stage_reset_stop ok=true`; fresh EE-alias candidate batch kept `overall_ok=true`, IK used `tool0`, and EE pose resolved `ee_link` for requested `tool0` with `attempted_frames=["tool0"]` | not validated |
| `cobotta_pro_1300` | `ik_only` | `denso` | fresh patched Denso batch: load/joints/safe-nudge ok; gripper skipped unsupported; IK succeeded on `default` with `solution_count=6`; EE pose resolved requested `onrobot_rg6_base_link` with `attempted_frames=["onrobot_rg6_base_link"]`; `mcp_controllability=dynamic_joint_control` | not validated |
| `cobotta_pro_900` | `ik_only` | `denso` | fresh patched Denso batch: load/joints/safe-nudge ok; gripper skipped unsupported; default IK target failed cleanly, `relaxed_orientation` succeeded with `solution_count=6`; EE pose resolved requested `onrobot_rg6_base_link` with `attempted_frames=["onrobot_rg6_base_link"]`; `mcp_controllability=dynamic_joint_control` | not validated |
| `fanuc_crx10ia_l` | `ik_only` | `fanuc` | post-hardening single probe: load/joints/safe-nudge/IK/EE ok; gripper skipped unsupported | not validated |
| `flexiv_rizon4` | `ik_only` | `flexiv` | post-hardening single probe: load/joints/safe-nudge/IK ok; gripper skipped unsupported; EE pose skipped unsupported | not validated |
| `kuka_kr210_l150` | `ik_only` | `kuka` | fresh instance-2 patched probe: `overall_ok=true`, `mcp_controllability=dynamic_joint_control`; load/joint_config/joint_read/safe-nudge/IK/EE-pose/cleanup ok; gripper skipped unsupported; selected `kuka_forward_high_identity` through `tool0` with `solution_count=6` after `default` and `relaxed_orientation` failed cleanly with `ROBOT_SET_EE_TARGET_ERROR`; direct target sweep previously live-proved `[1.5,0.0,1.2,1.0,0.0,0.0,0.0]` as the Kuka fallback target | not validated |
| `ridgeback_ur5` | `ik_only` | `mobile_manipulator` | fresh mobile UR EE-frame and seed-index smokes: load/joints/safe-nudge ok; safe nudge chose `ur_arm_shoulder_pan_joint` instead of mobile-base dummy joints; gripper skipped unsupported; latest IK succeeded for `tool0` with `solution_count=6`; EE pose resolved `ur_arm_wrist_3_link` for requested `tool0` with `attempted_frames=["tool0"]`; `mcp_controllability=dynamic_joint_control` | not validated |
| `techman_tm12` | `ik_only` | `techman` | post-hardening single probe: load/joints/safe-nudge/IK/EE ok; gripper skipped unsupported | not validated |
| `ur16e` | `ik_only` | `ur` | post-hardening single probe: load/joints/safe-nudge/IK ok; gripper skipped unsupported; fresh EE-alias IK-only batch kept `overall_ok=true`, IK used `tool0`, and EE pose resolved `wrist_3_link` for requested `tool0` with `attempted_frames=["tool0"]` | not validated |
| `ur3` | `ik_only` | `ur` | post-hardening dynamic single probe timed out; cleanup stop and cleanup also timed out; host degraded afterward; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; static-policy batch smoke and fresh EE-alias IK-only batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with 6-DOF static metadata and `overall_ok=false`; this is not controllability proof | not validated |
| `ur3e` | `ik_only` | `ur` | post-hardening single probe: load/joints/safe-nudge/IK ok; gripper skipped unsupported; static-policy and fresh EE-alias batches kept it on the dynamic path with `overall_ok=true`, no `dynamic_probe_policy`, safe nudge on `shoulder_pan_joint`, IK success for `tool0`, and EE pose resolved for requested `tool0` through concrete USD prim `wrist_3_link` with `attempted_frames=["tool0"]` | not validated |
| `ur5` | `ik_only` | `ur` | post-hardening dynamic single probe timed out; cleanup stop and cleanup also timed out; host degraded afterward; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh EE-alias IK-only batch and fresh single-profile guarded probe both routed it to a static-only known-hazard row with 6-DOF static metadata; this is not controllability proof | not validated |
| `ur5e` | `ik_only` | `ur` | post-hardening single probe: load/joints/safe-nudge/IK ok; gripper skipped unsupported; fresh EE-alias IK-only batch kept `overall_ok=true`, IK used `tool0`, and EE pose resolved `wrist_3_link` for requested `tool0` with `attempted_frames=["tool0"]` | not validated |
| `kinova_gen3` | `profile_only` | `kinova` | post-hardening profile-only batch: load/joints/safe-nudge ok; gripper skipped unsupported; IK skipped no robot description; EE pose skipped unsupported | not validated |
| `kinova_j2n6s300` | `profile_only` | `kinova` | post-hardening profile-only batch: load/joints/safe-nudge ok; gripper skipped unsupported; IK skipped no robot description; EE pose skipped unsupported | not validated |
| `kinova_j2n7s300` | `profile_only` | `kinova` | post-hardening profile-only batch: load/joints/safe-nudge ok; gripper skipped unsupported; IK skipped no robot description; EE pose skipped unsupported | not validated |
| `openarm_bimanual` | `profile_only` | `openarm` | post-hardening profile-only batch returned `ROBOT_PROBE_BATCH_ABORTED` after `openarm_unimanual` unhealthy timeout cleanup; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh isolated dynamic probe loaded/detected articulation and played simulation, then `warmup_step` timed out after `20.0s` with `ROBOT_PROBE_WARMUP_STEP_TIMEOUT`, no joint/safe-nudge/gripper/IK/EE-pose evidence, stop/cleanup deferred, follow-up status degraded to `SIMULATION_STATUS_ERROR` after about `75.4s`, WARN capture failed with `EXTENSION_LOGS_ERROR`, and lifecycle cleanup cleared port `[redacted]`; fresh current-code static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with no warmup attempt | not validated |
| `openarm_unimanual` | `profile_only` | `openarm` | post-hardening dynamic profile-only batch timed out; cleanup stop and cleanup also timed out; host degraded afterward; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh current-code static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with no warmup attempt | not validated |
| `sawyer` | `profile_only` | `rethink` | post-hardening profile-only batch: load/joints/safe-nudge ok; gripper skipped unsupported; IK skipped no robot description; EE pose skipped unsupported | not validated |
| `so100` | `profile_only` | `robotstudio` | post-hardening profile-only batch: load/joints/safe-nudge ok; gripper skipped unsupported; IK skipped no robot description; EE pose skipped unsupported; fresh current-code RobotStudio static-policy batch kept it on the dynamic path and healthy while routing neighboring `so101_new_calib` static | not validated |
| `so101_new_calib` | `profile_only` | `robotstudio` | post-hardening dynamic profile-only batch timed out; cleanup stop and cleanup also timed out; host degraded afterward; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh current-code RobotStudio static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with no warmup attempt | not validated |
| `lite6` | `profile_only` | `ufactory` | post-hardening dynamic profile-only batch timed out; cleanup stop and cleanup also timed out; host degraded afterward; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh current-code UFactory static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with static metadata and no warmup attempt | not validated |
| `lite6_gripper` | `profile_only` | `ufactory` | post-hardening profile-only batch returned `ROBOT_PROBE_BATCH_ABORTED` after `lite6` unhealthy timeout cleanup; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh isolated dynamic probe loaded/detected articulation and played simulation, then `warmup_step` timed out after `20.0s` with `ROBOT_PROBE_WARMUP_STEP_TIMEOUT`, no joint/safe-nudge/gripper/IK/EE evidence, stop/cleanup deferred, follow-up status degraded after about `53.3s`, WARN capture failed because REST no longer accepted requests, and owned port `[redacted]` was cleared by scoped cleanup; fresh current-code UFactory static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with static metadata and no warmup attempt | not validated |
| `uf850` | `profile_only` | `ufactory` | post-hardening profile-only batch returned `ROBOT_PROBE_BATCH_ABORTED` after `lite6` unhealthy timeout cleanup; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh isolated dynamic probe loaded/detected articulation and played simulation, then `warmup_step` timed out after `20.0s` with `ROBOT_PROBE_WARMUP_STEP_TIMEOUT`, no joint/safe-nudge/gripper/IK/EE evidence, stop/cleanup deferred, follow-up status degraded after about `85.3s`, WARN capture failed because REST no longer accepted requests, `kit_app_stop` reported already not running, and owned port `[redacted]` was clear after scoped cleanup; fresh current-code UFactory static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with static metadata and no warmup attempt | not validated |
| `xarm6` | `profile_only` | `ufactory` | post-hardening profile-only batch returned `ROBOT_PROBE_BATCH_ABORTED` after `lite6` unhealthy timeout cleanup; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh isolated dynamic probe loaded/detected articulation and played simulation, then `warmup_step` timed out after `20.0s` with `ROBOT_PROBE_WARMUP_STEP_TIMEOUT`, no joint/safe-nudge evidence, stop/cleanup deferred, follow-up status degraded to `SIMULATION_STATUS_ERROR` after about `91.6s`, and WARN capture returned `EXTENSION_LOGS_ERROR` after about `91.8s`; fresh current-code UFactory static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with static metadata and no warmup attempt | not validated |
| `xarm7` | `profile_only` | `ufactory` | post-hardening profile-only batch returned `ROBOT_PROBE_BATCH_ABORTED` after `lite6` unhealthy timeout cleanup; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh isolated dynamic probe loaded/detected articulation and played simulation, then `warmup_step` timed out after `20.0s` with `ROBOT_PROBE_WARMUP_STEP_TIMEOUT`, no joint/safe-nudge evidence, stop/cleanup deferred, and follow-up status degraded to `SIMULATION_STATUS_ERROR` after about `91.8s`; WARN capture was not collected because the worker was stopped after status returned; fresh current-code UFactory static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with static metadata and no warmup attempt | not validated |
| `unitree_z1` | `profile_only` | `unitree` | fresh phase-aware worker single probe: load/joints/safe-nudge ok; gripper skipped no built-in; IK skipped no robot description; EE pose skipped unsupported; earlier timeout row superseded | not validated |
| `ur20` | `profile_only` | `ur` | post-hardening dynamic profile-only batch timed out; cleanup stop and cleanup also timed out; host degraded afterward; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh current-code profile-only UR static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with no warmup attempt | not validated |
| `ur30` | `profile_only` | `ur` | post-hardening profile-only batch returned `ROBOT_PROBE_BATCH_ABORTED` after `ur20` unhealthy timeout cleanup; later direct static-only rerun loaded, detected articulation, skipped dynamic checks, cleaned up, and kept the host responsive; fresh isolated dynamic probe returned `overall_ok=true`, `mcp_controllability=dynamic_joint_control`, loaded/detected articulation, played and warmed simulation, read joints, safely nudged `shoulder_pan_joint`, restored/settled, skipped gripper as no built-in candidate, skipped IK as no robot description, recorded EE pose unsupported, cleaned up, kept final status responsive, and captured only non-fatal WARNs with no ERROR/FATAL lines; fresh current-code profile-only UR static-policy batch kept it on the dynamic path and healthy while routing neighboring `ur20` static | not validated |
| `dofbot` | `profile_only` | `yahboom` | dynamic probe timed out at `warmup_step` after reset/load/articulation/play and degraded the host; later `dynamic_checks=false` rerun live-proved load/articulation-only evidence, skipped all physics-dependent checks, cleaned up, and kept the host responsive; fresh current-code Yahboom static-policy batch routed it to `ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD` with no warmup attempt | not validated |
| `nex10` | `profile_only` | `yaskawa` | post-hardening profile-only batch: load/joints/safe-nudge/EE pose ok; gripper skipped unsupported; IK skipped no robot description | not validated |

## Adapter Priorities

1. Franka family:
   - Only `franka_fr3` currently has durable pick/place proof.
   - `franka_panda` remains MCP-controllable at probe level, but the
     2026-06-16 repeatability attempts failed cycle 2; it is now
     `candidate_pick_place` with known blocker diagnostics until a future
     proof artifact shows durable `done/lifted/placed=true` playback without
     kinematic carry.
   - `factory_franka` now has fresh load/gripper/IK/EE/safe-nudge probe
     success, but the live pick/place proof attempt timed out during cycle 1
     after fit preflight passed. A bounded follow-up now records the playback
     status timeout in about `1.0s`, while the next timeline stop still
     degrades for about `91.8s`.
  - The default profile selector now blocks `factory_franka` playback as
    unsupported before load/install REST calls, so routine callers do not hit
    the known host-degrading path. A fresh live smoke verified this by
    returning unsupported in about `222ms` and leaving the stage unchanged.
  - Follow-up module hardening makes that unsupported path machine-readable:
    known-but-unvalidated profiles now report
    `playback_route=blocked_unvalidated_profile`, `adapter_ready=false`,
    `required_support_status=validated_pick_place`,
    `validated_pick_place_requires=durable_live_pick_place_proof`, and
    `probe_success_is_pick_place_validation=false`, plus family/gripper
    context. Unknown names report `playback_route=unknown_profile`. This is
    triage metadata only, not pick/place validation.
  - Fresh no-Kit response-shape smoke from `workspaces/isaac/instance-1`
    proved the current MCP import was fresh (`source_newer_than_import=false`,
    no stale modules), did not start Kit (`process_list_kit_instances=[]`),
    and returned the expected unsupported diagnostics for both
    `factory_franka` and `not_a_builtin_arm`.
  - Fresh direct proof-path diagnostics now show FactoryFranka reaches
    controller event `1` and then fails bounded `max_steps=240` without lift or
    placement while host health remains responsive. A fresh rerun with
    joint/action telemetry shows event `1` does emit action joint positions and
    produces substantial joint readback movement, yet the cube remains
    unlifted and unplaced. The latest end-effector reach rerun shows the hand
    gets within about `0.0959m` of the pick point while still failing to lift,
    and explicit timing got within about `0.0574m` before exposing a nested
    action telemetry parser bug. The parser is now hardened and a post-fix live
    rerun reached event `8` without that failure and got EE-to-target down to
    about `0.0399m`, but still reported `lifted=false` and `placed=false`.
    The aperture telemetry rerun shows current gripper aperture ranging from
    about `0.000167m` to `0.080008m` with a minimum object-width margin about
    `-0.0449m`, while object lift remained `0.0`. A fresh grasp-geometry
    sweep then tried explicit high/low pick points, +/-2cm EE offsets, and the
    prior FR3 ScriptNode orientation hint `[0,1,0,0]`; the best target
    distance was the -2cm offset at about `0.028165m`, but every variant still
    had `max_lift_delta=0.0` and no lift/place proof. The next useful adapter
    work is grasp/contact and object-motion isolation before any validation
    claim.
  - The requested-strategy telemetry surface is now live-proven after a
    validation extension restart, so future FactoryFranka proof attempts can
    compare exact pick geometry, target, EE offset/orientation, events_dt, and
    max-step settings.
  - Current extension diagnostics now compute
    `diagnostic_end_effector_offset_delta_m` plus a source field for both the
    approach and closed-gripper contact windows. Unit coverage verifies no
    correction is emitted when the EE is already inside the object envelope and
    a signed Z correction is emitted for the observed vertically-outside contact
    cases. This is next-attempt guidance only; it is not live pick/place proof.
  - Follow-up diagnostics now also compute bounded next-offset recommendation
    fields for both approach/contact windows:
    `diagnostic_end_effector_offset_base_m`,
    `diagnostic_end_effector_offset_applied_delta_m`,
    `diagnostic_end_effector_offset_next_m`,
    `diagnostic_end_effector_offset_delta_limited`, and
    `diagnostic_end_effector_offset_delta_limit_m`. Unit coverage verifies a
    small Z correction passes through unchanged and a far Z correction is
    capped to the `0.05m` per-trial diagnostic step limit. Follow-up static
    hardening rejects non-finite base/delta values so the recommendation
    payload does not emit invalid next offsets.
  - Fresh instance-2 FR3 idle status-surface proof after the validation
    extension restart verified both `approach_window` and `contact_window`
    expose `diagnostic_end_effector_offset_delta_m` and
    `diagnostic_end_effector_offset_delta_source`; all four values were `null`
    at idle, final simulation health stayed responsive, and no playback cycle
    ran. This proves field presence only, not pick/place behavior.
  - A later fresh instance-2 smoke proved the full seven-field recommendation
    surface live: FR3 idle values stayed null/false with `limit_m=0.05`, while
    an optional direct FactoryFranka 30-frame bounded sample populated raw
    negative Z deltas and capped both approach/contact `next_m` suggestions to
    `[0,0,-0.05]`. The FactoryFranka sample still failed at `max_steps=180`
    without lift/place evidence, so it remains diagnostic guidance only.
  - The exact `[0,0,-0.05]` next-offset trial improved FactoryFranka proximity
    and reached `placing`/controller event `6` before failing at
    `max_steps=600`, but it still had `lifted=false`, `placed=false`, and
    `max_lift_delta=0.0`. Final diagnostics now suggest deeper Z offsets around
    `-0.064m` from the approach window and `-0.099m` from the contact window;
    this is adapter-geometry guidance only.
  - The follow-up `-0.064m`/`-0.099m` comparison reached `placing` and
    controller event `6` for both offsets, then failed cleanly at
    `max_steps=600`. The `-0.099m` run improved final distance to about
    `0.6634m`, target EE proximity to about `0.0814m`, and produced only tiny
    object lift (`0.00257m`), while diagnostics shifted toward combined
    XY/contact adjustment plus a deeper Z recommendation. Next adapter work
    should test combined XYZ/timing/contact changes; no promotion is justified.
  - The combined XY/Z follow-up tested the `-0.099m` contact-XY recommendation
    and then the same XY with deeper `-0.1129m` Z. Both variants still failed
    at `max_steps=600` with no lift/place validation, but the deeper combined
    run improved target EE proximity to about `0.0665m` and changed the contact
    classifier to XY-aligned-but-Z-outside. Next work should focus on deeper Z
    contact timing or gripper/object interaction, not promotion.
  - The next deeper combined-Z trial at about `-0.1283m` installed cleanly but
    degraded the live host on the first bounded playback step: step, demo
    status, stop, final status, and WARN capture all hit timeout/error
    boundaries. Treat this as a stability blocker and not as useful
    pick/place evidence; deeper Z alone is no longer a safe promotion path.
2. UR family:
   - `ur10`, `ur10e`, `ur16e`, `ur3e`, `ur5e`, and profile-only `ur30` are
     MCP-controllable at probe level in the post-hardening reruns, with
     unsupported grippers recorded cleanly.
   - The EE-frame candidate plus validation_api alias path is now live-proven
     across the healthy dynamic UR rows: `ur10` resolved EE pose through
     `ee_link`, `ur10e` resolved through `ee_link`, and `ur16e`/`ur3e`/`ur5e`
     resolved through `wrist_3_link` for requested `tool0`.
     Post-patch profile metadata now also includes `wrist_3_link` for UR-family
     arms, so MCP probes can try the concrete live-proven USD frame after
     `tool0`/`ee_link` before falling back to implicit aliases.
    - `ur3`, `ur5`, and profile-only `ur20` still time out in dynamic probes and
      can degrade the live host even after bounded cleanup.
    - The opt-in `static_only_for_known_dynamic_timeouts=true` routing now has
      live proof for both a mixed IK-only UR batch and the single-profile `ur5`
      tool path: `ur3` and `ur5` were preserved as static-only hazard evidence
      while `ur3e`, `ur5e`, and `ur16e` still ran dynamically. Use this for
      broad matrix refreshes or narrow static triage, not for joint-control or
      pick/place claims on the static-only rows.
    - Design a non-gripper pick/place adapter only after the UR timeout path is
      understood; do not validate UR pick/place from probe evidence alone.
   - The historical live abort path includes profile-only `ur30`, but the later
     isolated dynamic probe supersedes that row for `ur30` controllability.
3. Kawasaki family:
   - All five candidate Kawasaki profiles have fresh load/joint/gripper and
     safe-nudge proof, with unsupported or failed IK recorded cleanly rather
     than failing the probe.
    - The validation_api alias path now live-resolves EE pose for all five
      candidate Kawasaki profiles through `onrobot_rg2_base_link` for requested
      `tool0`, with host health staying responsive through the batch.
      Post-patch profile metadata also lists `onrobot_rg2_base_link` first, so
      MCP probes try the live-proven RG2 frame before relying on generic EE
      aliases.
   - The Lula seed/DOF adapter reaches the solver, and a direct target sweep
     proved a reachable RS007L target using relaxed orientation
     `[0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0]` with `solution_count=6`.
     Fresh current-code `robot_probe_arm_profile` proof now records the
     default target as handled no-convergence and succeeds on the relaxed
     orientation target for `kawasaki_rs007l`; the latest current-code
     sibling batch extends that proof to `kawasaki_rs007n`,
     `kawasaki_rs013n`, and `kawasaki_rs025n`. A direct RS080N sweep then
     found `[0.7, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0]`, and a fresh post-patch MCP
     probe now selects `kawasaki_rs080n_relaxed_forward` with
     `solution_count=6`.
   - The next adapter work is either a family controller/gripper strategy or
     an explicitly joint-space pick/place playback path before any validation
     claim.
4. IK-only families:
   - Fanuc and Techman have the cleanest current probe surface because load,
     safe nudge, IK, and EE pose all succeeded.
    - Denso profiles now have live IK target proof at probe level
      (`cobotta_pro_900` via `relaxed_orientation`, `cobotta_pro_1300` via
      `default`) and post-patch EE-pose proof through
      `onrobot_rg6_base_link`; gripper and pick/place remain unvalidated.
   - Flexiv remains MCP-controllable at probe level with unsupported EE-pose
      evidence. Kuka now has fresh current-code probe proof selecting
      `kuka_forward_high_identity` after the generic targets fail cleanly, while
      gripper/pick-place remain unsupported/unvalidated.
   - Keep the support-status taxonomy under review instead of promoting from
     `ik_only` labels alone.
   - Treat unsupported gripper as expected unless a gripper profile exists.
5. Mobile manipulators:
   - `ridgeback_franka` is now MCP-controllable at probe level after the
     mobile-base safe-nudge selector fix: it skipped dummy base joints and
     nudged `panda_joint1`; gripper, IK, and EE pose also passed.
   - `ridgeback_ur5` is also MCP-controllable at probe level after the selector
     fix: it skipped dummy base joints and nudged `ur_arm_shoulder_pan_joint`.
     A fresh mobile UR EE-frame smoke resolves EE pose through
     `ur_arm_wrist_3_link` for requested `tool0`, and the later seed-index
     smoke produced a live six-DOF IK solution for `tool0`.
   - Do not infer pick/place validation for Ridgeback from probe success.
6. Profile-only families:
   - Clean probe-controllable profile-only candidates: Kinova profiles,
     `sawyer`, `so100`, `unitree_z1`, `ur30`, and `nex10`.
    - Dynamic timeout teardown targets remain: `openarm_unimanual`,
      `openarm_bimanual`, `so101_new_calib`, `lite6`, `lite6_gripper`, `uf850`,
      `ur20`, `xarm6`, `xarm7`, and `dofbot`. `dofbot`,
      `openarm_bimanual`, `lite6_gripper`, and `uf850` have live
      phase-operation
      evidence showing `warmup_step` is the bounded operation that times out
      after reset/load/articulation/play, with downstream robot checks omitted
      and cleanup recorded as deferred.
   - Direct static-only `dynamic_checks=false` reruns now prove safe
     load/articulation classification for the previous timeout and batch-aborted
     rows (`openarm_*`, `so101_new_calib`, UFactory/xArm, `ur3`, `ur5`, `ur20`,
     and the historical `ur30` row) while keeping the host responsive. This
     removes the missing load/articulation evidence gap, but not the dynamic
     controllability gap for rows without later isolated dynamic proof.
    - `openarm_bimanual` now has isolated dynamic blocker evidence at
      `warmup_step`, followed by a degraded `simulation_get_status` call around
      `75.4s`; request-scoped WARN capture failed with `EXTENSION_LOGS_ERROR`
      because REST was no longer accepting requests. `xarm6` now has matching
      isolated dynamic blocker evidence at
      `warmup_step`, followed by a degraded `simulation_get_status` call around
      `91.6s`; request-scoped WARN capture also failed after about `91.8s`
      with `EXTENSION_LOGS_ERROR`. `lite6_gripper` now has matching isolated
      dynamic blocker evidence at `warmup_step`, followed by a degraded
      `simulation_get_status` call around `53.3s`; request-scoped WARN capture
      failed because REST was no longer accepting requests, and scoped cleanup
      cleared owned port `[redacted]`. `uf850` now has matching isolated dynamic
      blocker evidence at `warmup_step`, followed by a degraded
      `simulation_get_status` call around `85.3s`; request-scoped WARN capture
      failed because REST was no longer accepting requests, `kit_app_stop`
      reported already not running, and scoped cleanup showed owned port `[redacted]`
      clear. `xarm7` now also has isolated dynamic blocker evidence at
      `warmup_step`, followed by a degraded `simulation_get_status` call around
      `91.8s`; WARN capture was not collected because the worker was stopped
      after status returned.
    - There is no remaining UFactory inherited-batch-abort-only gap after the
      `uf850` isolated probe, and fresh static-policy batches now live-prove
      that known hazards in UFactory, OpenArm, RobotStudio, Yahboom, and
      profile-only UR can be preserved as static rows during broad refreshes
      while healthy neighbors such as `so100` and `ur30` still run dynamically.
      Next profile-only work should run isolated dynamic probes only when
      lifecycle recovery cost is acceptable. For broad refreshes, use
      `static_only_for_known_dynamic_timeouts=true` to preserve the known-hazard
      rows as explicit static-only evidence while continuing to probe
      neighboring profiles dynamically.
   - Do not attempt pick/place promotion until a motion-policy or playback
     strategy exists and direct live pick/place proof is captured.

## WARN/ERROR Summary

- Current-code worker: first-class `extension_capture_logs` became
  unresponsive after the candidate UR batch, returning `EXTENSION_LOGS_ERROR`
  after about `91.6s`.
- Current-code worker: follow-up `simulation_get_status` also timed out after
  about `91.8s`.
- Current-code worker: Windows saw Kit PID `[redacted]` as non-responding; local log
  grep found crashreporter warnings and dump zip
  a local Kit crash dump zip under the user-local Omniverse data directory,
  but no explicit `[Error]`, `[Fatal]`, traceback, or exception lines.
- Post-hardening instance-1 worker: after restart and tight UR probes, WARN
  capture returned 8 warnings: USD anonymous-stage/reference-count diagnostic
  warnings, UR schema relationship warnings, and one PhysX warning for
  `/World/MCPProbe/ur10e/joints/ee_joint` disjointed body transforms. ERROR
  count was 0.
- Post-hardening instance-1 worker: after Kawasaki and non-UR IK-only expansion,
  WARN capture returned 78 warnings and ERROR count was 0. Warnings were mostly
  USD reference-count diagnostics, PhysX negative mass/inertia warnings on
  several assets, one articulation velocity-iteration warning, carb perf
  warnings, and RTX Hydra corrupted primvar warnings for `techman_tm12` visuals.
- Post-hardening instance-1 worker: after `ur3` timed out, the follow-up status
  call took about `91.8s` and returned `SIMULATION_STATUS_ERROR`; no final log
  capture was attempted from that unhealthy state.
- Post-hardening instance-1 worker: repeated timeout passes for
  `openarm_unimanual`, `so101_new_calib`, `lite6`, `ur20`, `dofbot`, and `ur5`
  showed the same unhealthy cleanup signature: capped cleanup errors followed
  by post-probe `simulation_get_status` around `91.6s` to `91.8s` with
  `SIMULATION_STATUS_ERROR`.
- Post-hardening instance-1 worker: `unitree_z1` timed out historically, but
  cleanup stayed healthy and post-status returned in about `15ms`; the fresh
  phase-aware instance-2 worker later reran `unitree_z1` successfully.
- Post-hardening instance-1 worker: the final `ur5e` single-profile pass stayed
  responsive; final status returned in about `7ms`, WARN count was 4, and ERROR
  count was 0. Warnings were USD diagnostics plus a UR5e schema relationship
  warning.
- Post-hardening instance-1 worker: the corrective `ridgeback_franka` probe
  stayed responsive; final status returned in about `15ms`, WARN count was 1,
  and ERROR count was 0.
- Fresh mobile-selector worker: first `ridgeback_franka` run timed out at
  `25s` before safe-nudge evidence and degraded instance-2; after an owned
  restart, the `60s` rerun completed in about `9.0s`, final status returned in
  about `18ms`, WARN count was 1, and no ERROR capture was requested separately
  after the WARN capture closed the window.
- Fresh mobile-selector worker: `ridgeback_ur5` completed in about `3.0s`,
  final status returned in about `16ms`, WARN count was 2, and no ERROR capture
  was requested separately after the WARN capture closed the window.
- Fresh mobile UR EE-frame worker: `ridgeback_ur5` completed in about `4.47s`
  after restarting only owned instance-1 port `[redacted]`; pre/final status checks
  returned in about `31ms`/`25ms`, and WARN/ERROR capture was skipped because
  the probe and host-health checks stayed clean.
- Fresh validation_api Lula seed-index worker: `kawasaki_rs007l` and
  `ridgeback_ur5` completed in about `4.7s` and `3.1s` after restarting only
  owned instance-1 port `[redacted]`; pre/final status checks returned in about
  `477ms`/`14ms`, and WARN/ERROR capture was skipped because both probes
  returned normally and host health stayed responsive.
- Fresh Kawasaki IK target sweep worker: case A no-converged as a handled
  `ROBOT_SET_EE_TARGET_ERROR`, case B succeeded with `solution_count=6`,
  `stage_new` cleaned the probe stage, and final status returned in about
  `23ms`; WARN/ERROR capture was skipped because expected no-convergence was
  handled and host health stayed responsive. The immediate follow-up
  patched-probe smoke was intentionally not run because `mcp_runtime_info`
  showed stale `robot_module` imports; a later fresh-runtime worker proved the
  patched probe ladder.
- Fresh phase-aware worker: `unitree_z1` completed in about `10.0s`, final
  status returned in about `19ms`, WARN count was 5, and ERROR count was 0.
  Warnings were USD diagnostics plus Unitree Z1 schema relationship warnings.
- Fresh phase-aware worker: `dofbot` timed out in about `31.0s`; cleanup stop
  and cleanup both hit their `3s` caps, and the final status call returned
  `SIMULATION_STATUS_ERROR` after about `91.7s`, so WARN/ERROR log capture was
  intentionally skipped. A lifecycle cleanup turn then restarted the
  unambiguously owned instance-2 process on port `[redacted]` to PID `[redacted]`; final
  status returned in `728ms`.
- Fresh phase-operation worker: `dofbot` returned the new
  `ROBOT_PROBE_WARMUP_STEP_TIMEOUT` row in about `23.3s`, with
  `timeout_kind=phase_operation` and no downstream robot checks. Cleanup stop
  and cleanup still hit their `3s` caps, and the final status call returned
  `SIMULATION_STATUS_ERROR` after about `91.7s`; WARN/ERROR capture was
  intentionally skipped. Lifecycle cleanup restarted the unambiguously owned
  instance-2 process on port `[redacted]` from PID `[redacted]` to PID `[redacted]`; final
  status returned in `25ms`.
- Fresh deferred-cleanup worker: `dofbot` returned the deferred cleanup row in
  about `17.3s`, with `ROBOT_PROBE_SIMULATION_STOP_DEFERRED`,
  `ROBOT_PROBE_CLEANUP_DEFERRED`, and no downstream robot checks. The follow-up
  status still returned `SIMULATION_STATUS_ERROR` after about `91.8s`; WARN/ERROR
  capture was intentionally skipped because responsiveness had failed. Lifecycle
  cleanup restarted the unambiguously owned instance-2 process on port `[redacted]`
  from PID `[redacted]` to PID `[redacted]`; final status returned in `584ms`.
- Fresh static-only hazard-triage worker: `dofbot` with
  `dynamic_checks=false` completed in about `3.1s`; final status returned in
  `15ms`, WARN count was `3`, and ERROR count was `1`. The log summary was one
  USD stage reference-count warning, one dofbot material binding warning, and
  one `omni.ui.python` invalid null prim callback error from a
  property/camera/robot-poser UI rebuild path.
- Fresh FactoryFranka pick/place proof attempt worker: install and fit
  preflight succeeded, but the first playback-cycle status poll returned an MCP
  error after about `91.7s`; follow-up `simulation_stop` also returned
  `SIMULATION_CONTROL_ERROR` after about `91.7s`. WARN capture, ERROR capture,
  and final pre-cleanup `simulation_get_status` each timed out after about
  `91.7s`, so WARN/ERROR counts are unavailable. Lifecycle cleanup
  unambiguously restarted owned port `[redacted]` from PID `[redacted]` to PID `[redacted]`;
  post-restart `simulation_get_status` returned in about `20ms`.
- Parent hardening after that proof attempt added
  `ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT` for bounded playback status
  polling. This improves future evidence collection but does not change the
  failed FactoryFranka proof result above.
- Parent follow-up after the bounded diagnostic added cached
  `diagnostics.playback_progress` to playback status responses. This improves
  future FactoryFranka stall triage by surfacing controller event progress and
  sampled object motion, but it is static/unit-tested diagnostics hardening and
  does not change the failed proof result above.
- Fresh live diagnostics-surface smoke then restarted only owned instance-2 for
  the `validation_api` change and verified that immediate FR3 playback-demo
  status returns `diagnostics.playback_progress` in `17ms` with both
  approach/contact `diagnostic_end_effector_offset_delta_m` and
  `diagnostic_end_effector_offset_delta_source` keys present as `null`; final
  host health stayed responsive. No playback cycle ran, so this remains
  diagnostics evidence only.
- Fresh next-offset diagnostics-surface smoke then restarted only owned
  instance-2 from PID `[redacted]` to PID `[redacted]` for the validation extension
  change while leaving external PID `[redacted]` untouched. FR3 idle status returned
  in `17ms` and exposed all seven recommendation keys in both approach/contact
  windows with null delta/base/applied/next/source values,
  `diagnostic_end_effector_offset_delta_limited=false`, and
  `diagnostic_end_effector_offset_delta_limit_m=0.05`. The optional direct
  FactoryFranka 30-frame bounded sample populated capped Z recommendations
  (`next_m=[0,0,-0.05]` for both approach/contact windows) but failed at
  `max_steps=180`; final status stayed responsive, WARN+ capture returned 6
  WARN entries and no ERROR entries, and no validation is claimed.
- Fresh exact-offset FactoryFranka trial then restarted only owned instance-2
  from PID `[redacted]` to PID `[redacted]` for the finite-value validation API patch
  while again leaving external PID `[redacted]` untouched. The direct low-level
  FactoryFranka run used `end_effector_offset=[0,0,-0.05]`; it reached
  `placing`, `controller_event=6`, and returned bounded status in `38ms` after
  the first 260-frame burst, then failed cleanly at `max_steps=600` after the
  second burst. Final health stayed responsive, WARN+ capture returned 4 WARN
  entries and no ERROR entries, and the run remains non-promoting adapter
  geometry evidence.
- Fresh deeper-offset FactoryFranka comparison reused owned instance-2 PID `[redacted]` without restart. The `-0.064m` and `-0.099m` direct low-level runs
  both reached `placing`/event `6`, both failed cleanly at `max_steps=600`, and
  final stop/status/log capture stayed responsive. WARN+ capture returned 2
  WARN entries and no ERROR entries; no validation or promotion is claimed.
- Fresh combined XY/Z FactoryFranka comparison reused owned instance-2 PID `[redacted]` without restart. The contact-XY-plus-`-0.099m` and
  contact-XY-plus-`-0.1129m` direct low-level runs both reached
  `placing`/event `6`, both failed cleanly at `max_steps=600`, and final
  stop/status/log capture stayed responsive. WARN+ capture returned 2 WARN
  entries and no ERROR entries; no validation or promotion is claimed.
- Fresh deeper combined-Z FactoryFranka Trial E reused owned instance-2 PID `[redacted]` without restart, installed with
  `end_effector_offset=[0.0126288105,0.0075458046,-0.1283269972]`, and then
  degraded the host: first `simulation_step(frames=260)` failed after about
  `91.7s`, demo status timed out at `3s`, cleanup stop/final status/WARN
  capture each hit the long timeout/error boundary, and the process remained
  alive on port `[redacted]`. Scoped recovery then found the old PID already gone and
  started fresh owned PID `[redacted]` with status responsive in about `23ms`. No
  validation or promotion is claimed.
- Bounded playback-status smoke worker: pre-install bounded status returned
  quickly with the expected no-demo-installed module error; the FR3 bounded
  smoke completed with four fast status polls and final status responsiveness
  in `37ms`. WARN capture found three PhysX warnings tied to FR3 mass/inertia
  and articulation velocity iterations; no ERROR/FATAL entries appeared in the
  captured WARN+ window.
- Bounded FactoryFranka diagnostic worker: pre-restart WARN/ERROR capture was
  skipped after the REST path had already degraded on a `91.8s`
  `simulation_stop`; post-restart WARN capture returned `0` entries.
- Static-only blocked-profile triage worker: no WARN/ERROR capture was needed
  because all twelve direct `dynamic_checks=false` probes completed without
  timeout, cleanup failure, or host slowdown; final status returned in `15ms`.
- Static USD metadata worker `[worker-id-redacted]`:
  the first `dofbot` static-only run exposed zero static DOFs, then the
  suffix-matching patch plus stale MCP import exposed a sparse-USD `None`
  parsing error; the same stale-client run proved `franka_panda` static
  metadata with `dof_count=10`. Its WARN/ERROR capture path failed after about
  `91.7s` with `EXTENSION_LOGS_ERROR`.
- Fresh MCP-import static metadata worker
  `[worker-id-redacted]`: `dofbot` static metadata succeeded
  on Kit PID `[redacted]`, port `[redacted]`, with pre/post status responses around
  `18ms`/`14ms`, `static_only=true`, `order_reliable=false`, and
  `dof_count=13`. This remains static USD metadata only, not dynamic
  controllability or pick/place proof.
- Fresh validation_api EE-pose alias worker
  `[worker-id-redacted]`: UR3e and Kawasaki RS007L probes
  returned normally after restarting owned Kit port `[redacted]` from PID `[redacted]` to
  PID `[redacted]`; pre/post/final status checks stayed responsive around
  `17ms`/`15ms`/`16ms`. No WARN/ERROR capture was needed for this smoke because
  the host stayed healthy.
- Fresh validation_api EE-pose alias worker
  `[worker-id-redacted]`: UR3e and Kawasaki RS007L probes
  returned normally on fresh Kit PID `[redacted]`, port `[redacted]`; pre/post/final
  status checks stayed responsive around `29ms`/`17ms`/`21ms`. The same worker
  then ran candidate UR, IK-only UR with static hazard routing, and candidate
  Kawasaki sibling batches; health stayed responsive around
  `23ms`/`15ms`/`19ms`/`20ms`. No WARN/ERROR capture was needed because there
  were no unexpected probe failures, timeouts, or host-health degradation.
- Fresh FactoryFranka approach-window diagnostics worker
  `[worker-id-redacted]`: after the expected terminal
  playback failure at `600` ticks, `simulation_stop` and final
  `simulation_get_status` were responsive, and WARN+ capture returned `0`
  entries.
- Parent follow-up added machine-readable
  `robot_install_pick_place_playback_demo` unsupported diagnostics:
  `diagnostics.known_pick_place_blocker` and
  `diagnostics.known_pick_place_blocker_reason`. FactoryFranka now reports
  the durable deeper combined-Z host-degradation blocker at the profile
  selector call site, while ordinary unvalidated candidates and unknown
  profiles report no known blocker. This is static/module guidance hardening
  only, not live pick/place proof or promotion.
- Parent follow-up also added probe-row pick/place boundary fields:
  `probe_proves_pick_place`, `pick_place_validation_status`, and
  `pick_place_validation_reason`, plus batch
  `pick_place_validation_status_counts` and
  `pick_place_validation_status_profiles`. Probe rows now explicitly serialize
  that capability probes do not prove pick/place, while batch summaries list
  the profile names in each validation-boundary bucket. This distinguishes
  catalog-validated profiles from known playback blockers and ordinary
  unvalidated profiles. This is schema/guidance hardening only, not live
  pick/place proof or promotion.
- Parent follow-up then added profile maps for every batch controllability and
  capability class: `mcp_controllability_profiles` and
  `probe_capability_level_name_profiles`. These maps avoid broad-matrix claims
  that rely on counts plus inference; each evidence class now lists the profile
  names it contains.
- Fresh instance-1 worker `[worker-id-redacted]` then exposed
  those maps in a live fresh MCP host and populated them in a one-profile
  `franka_panda` batch. `mcp_runtime_info` returned `process_id=[redacted]`,
  `tool_count=143`, `source_newer_than_import=false`,
  `restart_required_for_latest_mcp_code=false`, and
  `stale_source_modules=[]`; `robot_probe_batch_result_fields` included
  `mcp_controllability_profiles` and `probe_capability_level_name_profiles`.
  The batch row returned `mcp_controllability_profiles={"dynamic_joint_control":
  ["franka_panda"]}` and
  `probe_capability_level_name_profiles={"ik_or_ee_telemetry":
  ["franka_panda"]}` with final simulation health responsive in about `21ms`.
  This is profile-map result-shape/probe evidence only, not new pick/place proof
  or promotion.
- Workspace-local instance-2 runtime-shape worker
  `[worker-id-redacted]` then verified the existing
  `[mcp-entry-redacted]` host without starting Kit. `mcp_runtime_info` returned
  `process_id=[redacted]`, `tool_count=143`, but
  `source_newer_than_import=true` and
  `restart_required_for_latest_mcp_code=true`; stale modules included
  `module_tools`, `robot_module`, `robot_arm_profiles`, `types.robot`, and
  `mcp.prompts`. The live host did not expose
  `probe_proves_pick_place`, `pick_place_validation_status`,
  `pick_place_validation_reason`, `pick_place_validation_status_counts`, or
  `pick_place_validation_status_profiles`. This is a stale-MCP import blocker
  for live validation of the new result shape; restart or use a fresh
  workspace-local MCP host before claiming live exposure. No Kit start, process
  listing, simulation status call, or robot probe ran in that check.
- Workspace-local instance-1 runtime-shape worker
  `[worker-id-redacted]` then loaded a fresh
  `[mcp-entry-redacted]` host without starting Kit and proved live exposure of the
  new result shape: `mcp_runtime_info` returned `process_id=[redacted]`,
  `tool_count=143`, `source_newer_than_import=false`,
  `restart_required_for_latest_mcp_code=false`, `stale_source_modules=[]`,
  `robot_probe_result_has_pick_place_validation_boundary=true`, and
  `robot_probe_batch_result_has_summary=true`. The runtime
  `robot_probe_result_fields` included `probe_proves_pick_place`,
  `pick_place_validation_status`, and `pick_place_validation_reason`; the
  runtime `robot_probe_batch_result_fields` included
  `pick_place_validation_status_counts` and
  `pick_place_validation_status_profiles`. No Kit start, process listing,
  simulation status call, or robot probe ran in that check, so this is
  MCP import/result-shape proof only, not MCP controllability or pick/place
  validation.
- A follow-up attempt to run a bounded `franka_panda` batch on the same
  instance-1 worker stopped at the freshness gate, as intended, after the
  parent prompt guidance changed: `mcp_runtime_info` still showed the new result
  fields present, but reported `source_newer_than_import=true`,
  `restart_required_for_latest_mcp_code=true`, and
  `stale_source_modules=["omniverse_kit_mcp.mcp.prompts"]`. The worker did not
  call `process_list_kit_instances`, `kit_app_start`, `simulation_get_status`,
  or any robot probe. This confirms the stale-MCP blocker rule is enforced
  before live probe claims.
- Fresh instance-1 worker `[worker-id-redacted]` then loaded
  then-current code and ran one bounded live batch for the pre-demotion
  `status_filter=["validated_pick_place"]`, `family_filter=["franka"]`, and
  `limit=1` selector. `mcp_runtime_info` returned `process_id=[redacted]`,
  `tool_count=143`, `source_newer_than_import=false`,
  `restart_required_for_latest_mcp_code=false`, and
  `stale_source_modules=[]`; the required single-row and batch boundary fields
  were present. The run started owned Kit port `[redacted]` as PID `[redacted]`, left the
  non-owned port `[redacted]` PID `[redacted]` untouched, and returned one historical
  `franka_panda` row with `overall_ok=true`,
  `mcp_controllability=dynamic_joint_control`, `probe_proves_pick_place=false`,
  and `pick_place_validation_status=catalog_validated_pick_place`. That result
  shape is superseded by the 2026-06-16 non-proof artifact; current code reports
  `franka_panda` as `known_pick_place_blocker` and leaves only `franka_fr3` in
  the catalog `validated_pick_place` set. The historical batch summaries
  included `pick_place_validation_status_counts={"catalog_validated_pick_place":
  1}` and `pick_place_validation_status_profiles={"catalog_validated_pick_place":
  ["franka_panda"]}` with no timed-out, blocked, hard-failure, or
  lifecycle-recovery profiles; final simulation status was responsive in about
  `8ms`. This is live result-shape/probe evidence only, not pick/place proof or
  promotion.
- Historical workers: FR3 and Kawasaki runs showed PhysX invalid
  inertia/negative mass warnings on helper bodies; UR runs showed schema
  relationship missing-joint warnings.

## Promotion Result

No profile is newly promoted by the latest FactoryFranka attempt, the bounded
FactoryFranka diagnostic, the playback-progress diagnostics hardening, the
playback joint/action telemetry hardening and rerun, the playback
end-effector reach telemetry hardening and rerun, the explicit timing
diagnostic, the nested-action parser hardening and post-fix timing rerun, the
gripper aperture telemetry hardening and rerun, the approach-window telemetry
hardening and live smoke, the playback-progress diagnostics-surface smoke, the
fresh direct FactoryFranka playback-progress diagnostic, the bounded
next-offset diagnostics-surface smoke, the exact `-0.05m` FactoryFranka
offset trial, the `-0.064m`/`-0.099m` FactoryFranka offset comparison, the
combined XY/Z FactoryFranka offset comparison, the deeper combined-Z
FactoryFranka Trial E host-degradation check, the bounded playback-status
smoke, the unsupported playback blocker diagnostics hardening, the probe-row
pick/place boundary schema hardening, the EE-pose alias telemetry smokes and
sibling batches, the mobile UR EE-frame smoke, the validation_api Lula
seed-index smoke, or the Kawasaki IK target sweep and fresh parent
target-ladder proof plus current-code Kawasaki sibling IK ladder batch. The
RS080N direct IK target sweep and post-patch probe are also non-promoting probe
evidence. The only durable live pick/place proof referenced here is the
existing FR3 proof artifact. All other profiles remain probe-only evidence
until live pick/place playback proves grasp, lift, and place behavior
profile-by-profile.
