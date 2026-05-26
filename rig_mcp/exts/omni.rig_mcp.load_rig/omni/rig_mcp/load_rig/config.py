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

# Drive
LIFT_HEIGHT = 1.5       # prismatic target (m)
LIFT_LOWER = 0.0
LIFT_UPPER = 2.0
LIFT_STIFFNESS = 4000.0
LIFT_DAMPING = 400.0
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
