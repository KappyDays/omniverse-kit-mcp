# Franka Panda Pick/Place Non-Proof - 2026-06-16

## Scope

- Profile: `franka_panda`
- Decision: do not treat this profile as `validated_pick_place` from this evidence.
- Boundary: this artifact records failed durable proof attempts for Panda only. It
  does not demote or validate any other profile.

## Attempt 1

- Worker: `[worker-id-redacted]`
- Workspace: `workspaces/isaac/instance-1`
- MCP entry: `[mcp-entry-redacted]`
- Owned Kit: port `[redacted]`, restarted from PID `[redacted]` to PID `[redacted]`
- Non-owned Kit: port `[redacted]`, PID `[redacted]`, untouched
- Install:
  `robot_install_pick_place_playback_demo(profile_name="franka_panda",
  robot_prim_path="/World/FrankaPandaProof",
  object_prim_path="/World/PandaProofCube", object_size=0.04,
  max_steps=1800, position_tolerance=0.05,
  lift_height_tolerance=0.03, create_demo_scene=true, reset_on_play=true)`
- Preflight: `object_fit_ok=true`; bbox approximately `0.040 x 0.040 x
  0.040m`; fit limit/measured `0.075 / 0.0399999991`; `uses_kinematic_carry=false`.

| cycle | result |
|---|---|
| 1 | success: `done=true`, `lifted=true`, `placed=true`, `steps=917`, `controller_event=10`, `final_distance=0.0057740599`, `max_lift_delta=0.2799406164` |
| 2 | failure: `done=false`, `lifted=false`, `placed=false`, `steps=326`, `controller_event=3`, `final_distance=0.7158910532`, `max_lift_delta=0.0`, `last_error="'NoneType' object is not subscriptable"` |
| 3 | not run because cycle 2 failed |

Failure logs captured a `ParallelGripper` path error during
`PickPlaceController.forward`. Final host health remained responsive/stopped.

## Attempt 2

- Purpose: test the first reset/playback wrapper-refresh patch.
- Owned Kit restarted from PID `[redacted]` to PID `[redacted]`; non-owned port `[redacted]`
  remained untouched.
- Install path:
  `/World/FrankaPandaProofRerun` / `/World/PandaProofCubeRerun`.
- Preflight again passed with `object_fit_ok=true` and `uses_kinematic_carry=false`.

| cycle | result |
|---|---|
| 1 | success: `done=true`, `lifted=true`, `placed=true`, `steps=917`, `controller_event=10`, `final_distance=0.0057740599`, `max_lift_delta=0.2799406164` |
| 2 | failure: `done=false`, `lifted=false`, `placed=false`, `steps=326`, `controller_event=3`, `final_distance=0.7158910532`, `max_lift_delta=0.0`, `last_error="'NoneType' object is not subscriptable"` |
| 3 | not run because cycle 2 failed |

This disproved the wrapper-refresh-only patch as durable proof.

## Attempt 3

- Purpose: test the later last-known joint-position cache patch.
- Owned Kit restarted from PID `[redacted]` to PID `[redacted]`; non-owned port `[redacted]`
  remained untouched.
- Install path:
  `/World/FrankaPandaProofCacheFix` / `/World/PandaProofCubeCacheFix`.
- Preflight: `object_fit_ok=true`; bbox approximately `0.040 x 0.040 x
  0.040m`; fit limit/measured `0.075 / 0.0399999991`; `uses_kinematic_carry=false`.

| cycle | result |
|---|---|
| 1 | success: `done=true`, `lifted=true`, `placed=true`, `steps=917`, `controller_event=10`, `final_distance=0.0057740599`, `max_lift_delta=0.2799406164` |
| 2 | failure: `error_code=ROBOT_FRANKA_PICK_PLACE_DEMO_FAILED`, `done=true`, `lifted=false`, `placed=false`, `steps=917`, `controller_event=10`, `final_distance=0.5961540434`, `max_lift_delta=0.0132921748`, `last_error="Object was not lifted by the gripper (max_lift_delta=0.0133m < 0.0300m)"` |
| 3 | not run because cycle 2 failed |

WARN/ERROR capture after attempt 3 contained no old `NoneType` /
`ParallelGripper` exception. This suggests the cache patch avoided that specific
crash, but the profile still failed durable pick/place proof because cycle 2 did
not meet lift validation.

## Conclusion

`franka_panda` has live MCP probe controllability and can run a first playback
cycle, but the current profile-selected playback path did not pass durable
three-cycle pick/place proof on 2026-06-16. Keep it out of
`validated_pick_place` until a future profile-specific live artifact proves
repeatable grasp, lift, and place behavior without kinematic carry.
