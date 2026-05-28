"""Pure constants for the fleet choreography (NO omni / pxr imports).

Real Isaac Sim 5.1 assets (R1) resolved during RECON — see
mcp-upgrade/make_progress/fleet_make.md.
"""
from __future__ import annotations

ISAAC = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac"

ENVIRONMENT_URL = f"{ISAAC}/Environments/Grid/default_environment.usd"
ROBOT_URL = f"{ISAAC}/Robots/NVIDIA/Carter/carter_v1.usd"

WORLD = "/World"
ENV_PRIM = "/World/Environment"
FLEET_ROOT = "/World/Fleet"
WAYPOINTS_ROOT = "/World/Waypoints"
GRAPH_PATH = "/World/FleetGraph"

ROBOT_NAMES = ("Carter_0", "Carter_1", "Carter_2")

# Formation = per-robot (dx, dy) offset from the leader centroid. Robot 0 is the leader.
FORMATIONS = {
    "triangle": ((0.0, 0.0), (-1.5, -1.5), (-1.5, 1.5)),
    "line": ((0.0, 0.0), (0.0, -1.5), (0.0, 1.5)),
}

# Leader centroid waypoint path (x, y); one leg per consecutive pair.
LEADER_WAYPOINTS = ((0.0, 0.0), (4.0, 0.0), (8.0, 2.0), (12.0, 0.0))
WAYPOINT_DURATION = 6.0  # seconds per leg (cumulative timing)
FORMATION_CHANGE_TIME = 12.0  # sim_time at which triangle -> line

# Carter v1 differential-drive params (approximate — confirm on the loaded asset).
WHEEL_RADIUS = 0.24
WHEEL_BASE = 0.41

# Ground clearance for the robot start pose. carter_v1's prim origin sits ~0.25 m
# ABOVE its wheel contact, so placing the parent at z=0 sinks the wheels through
# the GroundPlane collider -> PhysX penetration jitter -> no traction (live-observed
# 2026-05-28: reached=false, ~2 m travel). Lifting to z=0.30 rests the wheels on the
# ground (settles via gravity) -> clean contact -> drive reaches waypoints.
ROBOT_START_Z = 0.30

# Pure Pursuit / DifferentialController params for the inline drive loop
# (extension.py:_drive_fleet — mirrors robot_drive_physics but per-tick in-process).
DRIVE_MAX_LINEAR = 1.0    # m/s wheel velocity cap
DRIVE_MAX_ANGULAR = 1.2   # rad/s turn rate cap
DRIVE_ARRIVAL_TOL = 1.5   # m — generous corridor: at max_linear ~1 m/s with the
                          # free-running fast physics, carter overshoots a tight 0.35m
                          # tolerance and then oscillates (live-observed: 180° spin).
DRIVE_LOOKAHEAD = 0.8     # m (currently unused; reserved for full Pure Pursuit)
DRIVE_MAX_TICKS = 900     # ~15 s wall + sim ticks before timeout

MARKER_RADIUS = 0.2
