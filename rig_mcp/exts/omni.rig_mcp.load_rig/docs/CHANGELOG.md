# CHANGELOG — omni.rig_mcp.load_rig

## [0.1.0] - 2026-05-26

- Initial scaffold (headless-verified). 2-DOF lift rig (prismatic lift joint + revolute tilt joint, both
  with UsdPhysics DriveAPI) + real pallet+box payload (MassAPI) on a ground collider, authored via usd-core.
  Pure kinematics (lift/tilt schedule) + measure (contact/effort series reduction).
- Headless: physics scene + joints + drives + mass + payload references + idempotency + units pass. Live
  (PhysX drive motion, contact-force + joint-effort readout, stability) verified in a workspaces/isaac
  session — see mcp-upgrade/make_progress/rig_make.md. Rig geometry R1 note in that file.
