# CHANGELOG — omni.fleet_mcp.choreography

## [0.1.0] - 2026-05-26

- Initial scaffold (headless-verified). Grid env + 3 Carter v1 robots at a triangle formation +
  leader-waypoint markers authored via usd-core. Pure path_planner (formations / per-robot waypoints /
  timing) + graph_spec (declarative ActionGraph). IExt authors the OmniGraph skeleton live.
- Headless: USD authoring + idempotency + units pass. Live (OmniGraph waypoint-follow wiring, articulation
  drive, sim_time formation change) verified in a workspaces/isaac session — see
  mcp-upgrade/make_progress/fleet_make.md.
