# Franka FR3 Pick/Place Live Proof — 2026-06-15

## Summary

- Profile: `franka_fr3`
- Support decision: promote to `validated_pick_place`
- Workspace: `workspaces/isaac/instance-1`
- Kit REST port: `8111`
- Worker thread: `[worker-id-redacted]`
- Robot prim: `/World/FR3`
- Playback adapter: Franka-family official PickPlaceController/RMPflow/ParallelGripper path

## Evidence

- `robot_install_pick_place_playback_demo(profile_name="franka_fr3")` installed successfully at `/World/FR3`.
- The FR3 profile asset loaded from the built-in Franka FR3 USD before playback installation.
- Immediate fit preflight passed: `object_fit_ok=true`.
- Object bbox was about `0.040 x 0.040 x 0.040 m`.
- Grasp fit limit was `0.075 m`; measured object fit was about `0.040 m`.
- Stop -> Play cycles 1-3 all reached `done/lifted/placed=true`.
- `uses_kinematic_carry=false`.
- Final object-to-target distance was about `0.010 m`.
- Viewport artifact: local temp capture under `%TEMP%/validation_api_captures/`.
- Console summary: WARN only PhysX mass/inertia/TGS notices on FR3; ERROR count `0`.

## Promotion Boundary

This proof applies only to the Franka FR3 profile using the Franka-family playback adapter. It does not promote `factory_franka`, `ridgeback_franka`, UR profiles, Kawasaki profiles, or any other arm family.
