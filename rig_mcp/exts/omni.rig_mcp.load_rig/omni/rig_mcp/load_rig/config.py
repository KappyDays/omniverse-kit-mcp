"""Pure constants for the mechanical lift rig (NO omni / pxr imports).

Payload is a real Isaac Sim 5.1 asset (R1); the lift rig is an authored 2-DOF
mechanism — see mcp-upgrade/make_progress/rig_make.md R1 NOTE.
"""
from __future__ import annotations

ISAAC = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac"

PAYLOAD_PALLET_URL = f"{ISAAC}/Props/Pallet/pallet.usd"
PAYLOAD_BOX_URL = f"{ISAAC}/Props/KLT_Bin/small_KLT.usd"

WORLD = "/World"
PHYSICS_SCENE = "/World/PhysicsScene"
GROUND = "/World/Ground"
RIG_ROOT = "/World/Rig"
PAYLOAD_ROOT = "/World/Payload"
# Lighting — the rig is bare authored geometry (no env reference carrying lights),
# so without these the RTX viewport renders all-black (live-observed 2026-05-28).
DOME_LIGHT = "/World/DomeLight"
KEY_LIGHT = "/World/KeyLight"
DOME_INTENSITY = 1000.0
KEY_INTENSITY = 3000.0

BASE = "/World/Rig/Base"
COLUMN = "/World/Rig/Column"
CARRIAGE = "/World/Rig/Carriage"
FORK = "/World/Rig/Fork"
LIFT_JOINT = "/World/Rig/LiftJoint"
TILT_JOINT = "/World/Rig/TiltJoint"
PALLET = "/World/Payload/Pallet"
BOX = "/World/Payload/Box"

# Geometry (meters): (sx, sy, sz) half-not — full sizes via Cube size*scale below.
BASE_SIZE = (1.6, 1.6, 0.2)
COLUMN_SIZE = (0.3, 0.3, 3.0)
CARRIAGE_SIZE = (0.4, 1.0, 0.3)
FORK_SIZE = (1.4, 0.9, 0.1)
GROUND_SIZE = (20.0, 20.0, 0.1)

# Layout anchors
COLUMN_Z = 1.6          # column center height
CARRIAGE_X = 0.35       # carriage offset from column (toward fork)
CARRIAGE_Z0 = 0.4       # carriage rest height
FORK_X = 1.0            # fork extends in +X from carriage

# Drive — heavily damped so the lift is smooth: with low damping (e.g. 4000/400)
# the carriage snaps up ~1.5 m in <0.5 s (~4 m/s) and LAUNCHES the unconstrained
# pallet+box off the fork (live-observed 2026-05-28: payload flew to z=3.2). High
# damping (450/1200) keeps the payload seated on the fork throughout the lift.
LIFT_HEIGHT = 1.5       # prismatic target (m)
LIFT_LOWER = 0.0
LIFT_UPPER = 2.0
LIFT_STIFFNESS = 450.0
LIFT_DAMPING = 1200.0
LIFT_MAX_FORCE = 1.0e6
TILT_ANGLE = 8.0        # revolute target (deg)
TILT_STIFFNESS = 800.0
TILT_DAMPING = 80.0

# Masses (kg)
CARRIAGE_MASS = 25.0
FORK_MASS = 15.0
PALLET_MASS = 8.0
BOX_MASS = 12.0

GRAVITY = 9.81
