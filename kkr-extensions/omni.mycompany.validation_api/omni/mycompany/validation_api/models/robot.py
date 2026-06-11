"""Pydantic models for Robot REST endpoints (Phase B + G)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RobotLoadRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usd_url: str = Field(description="USD asset URL (local path or omniverse://)")
    prim_path: str = Field(description="Stage path where the robot is placed")
    position: list[float] | None = Field(
        default=None, description="[x, y, z] world position"
    )
    rotation: list[float] | None = Field(
        default=None, description="[rx, ry, rz] Euler degrees (XYZ order)"
    )


class RobotLoadResponseModel(BaseModel):
    ok: bool = True
    prim_path: str
    usd_url: str
    type_name: str
    has_articulation: bool = False


class RobotSetJointPositionsRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    positions: list[float] = Field(description="Joint positions (radians or metres)")


class RobotJointPositionsResponseModel(BaseModel):
    ok: bool = True
    prim_path: str
    positions: list[float]


class RobotSetJointPositionsResponseModel(BaseModel):
    ok: bool = True
    prim_path: str
    positions_count: int


class RobotNavigateRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    target: list[float] = Field(
        description="[x, y, z] world-space target for the robot base"
    )
    duration_s: float = Field(
        default=1.0, ge=0.0, description="Navigation duration (linear interpolation)"
    )


class RobotNavigateResponseModel(BaseModel):
    ok: bool = True
    job_id: str
    prim_path: str
    target: list[float]


class RobotNavigatePathRequestModel(BaseModel):
    """Follow a multi-waypoint path (e.g. NavMesh result) via linear interp."""

    model_config = ConfigDict(extra="forbid")

    prim_path: str
    points: list[list[float]] = Field(
        description="Waypoints in world space; each entry is [x, y, z]. Minimum 2 points."
    )
    duration_s: float = Field(default=5.0, gt=0.0, description="Total traversal time.")


class NavigationQueryPathRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: list[float] = Field(description="[x, y, z] start world position")
    end: list[float] = Field(description="[x, y, z] end world position")
    agent_radius: float = Field(default=0.0, ge=0.0)
    agent_height: float = Field(default=0.0, ge=0.0)
    straighten: bool = True


class RobotGripperControlRequestModel(BaseModel):
    """Open/close/set gripper joints on an articulation (Phase G).

    The Extension auto-detects gripper joints by searching DOF names for
    ``finger`` or ``gripper`` substrings. Works with Franka / UR-like
    grippers. For ``action="set"`` the caller specifies an explicit
    *target*; ``open`` / ``close`` read the joint limits (falls back to
    Franka defaults ``0.04`` / ``0.0``).
    """

    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Articulation prim path")
    action: Literal["open", "close", "set"] = Field(
        description="Gripper command — open/close use joint limits, set uses target"
    )
    target: float | None = Field(
        default=None,
        description="Required when action='set'; target position for all gripper joints",
    )


class DrivePhysicsRequestModel(BaseModel):
    """Drive a wheel-based articulation along ``waypoints`` using
    DifferentialController + Pure Pursuit (spec §8.2). Physics-based —
    writes joint_velocities into PhysX articulation. Requires
    ``omni.timeline.is_playing()`` (R2). Returns a Job; poll ``/jobs/{id}``.
    """

    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Wheel-based articulation prim path")
    waypoints: list[list[float]] = Field(
        description="World-space [x,y,z] path (≥2 points). Use NavMesh query_path output.",
        min_length=2,
    )
    max_linear: float = Field(default=1.0, gt=0, description="m/s")
    max_angular: float = Field(default=1.2, gt=0, description="rad/s")
    wheel_radius: float = Field(default=0.14, gt=0, description="m (Nova Carter default)")
    wheel_base: float = Field(default=0.413, gt=0, description="m (Nova Carter default)")
    arrival_tolerance: float = Field(default=0.3, gt=0, description="m")
    timeout_s: float = Field(default=60.0, gt=0)
    lookahead: float = Field(default=0.8, gt=0, description="Pure Pursuit lookahead distance (m)")


class DrivePhysicsResponseModel(BaseModel):
    ok: bool = True
    job_id: str
    prim_path: str


class RobotSetEETargetRequestModel(BaseModel):
    """Inverse-kinematics — compute joint positions to reach an end-effector pose (Phase G).

    Uses ``isaacsim.robot_motion.motion_generation.lula`` IK solver. The
    Franka config ships with Isaac Sim; generic articulations without a
    Lula config cannot be solved (Extension returns HTTP 400).
    """

    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Articulation prim path")
    target_pose: list[float] = Field(
        description="[x, y, z, qw, qx, qy, qz] end-effector target",
        min_length=7, max_length=7,
    )
    robot_description: str = Field(
        default="Franka",
        description="Lula robot description preset — Franka|UR10|Leatherback (Franka supported)",
    )
    end_effector_frame: str | None = Field(
        default=None,
        description="URDF frame name for end-effector (default per robot_description)",
    )


class RobotFrankaPickPlaceRequestModel(BaseModel):
    """Run the official Isaac Sim Franka PickPlaceController on an existing object."""

    model_config = ConfigDict(extra="forbid")

    robot_prim_path: str = Field(description="Existing Franka articulation root prim path")
    object_prim_path: str = Field(description="Existing rigid object prim to pick/place")
    target_position: list[float] = Field(
        description="[x, y, z] world-space placing position for the object center",
        min_length=3,
        max_length=3,
    )
    robot_description: str = Field(
        default="Franka",
        description="Official motion-policy robot preset. This endpoint currently supports Franka.",
    )
    picking_position: list[float] | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description=(
            "Optional [x, y, z] world-space object grasp center. Defaults to live bbox center."
        ),
    )
    end_effector_initial_height: float | None = Field(
        default=None,
        gt=0.0,
        description="Controller hover height; defaults to Isaac Sim official controller default.",
    )
    end_effector_offset: list[float] | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description="[x, y, z] offset applied to the end-effector target.",
    )
    end_effector_orientation: list[float] | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        description=(
            "Optional [qw, qx, qy, qz] end-effector orientation passed to the official controller."
        ),
    )
    events_dt: list[float] | None = Field(
        default=None,
        min_length=10,
        max_length=10,
        description="Optional 10 phase dt values for the official PickPlaceController.",
    )
    max_steps: int = Field(default=1800, gt=0, le=20000)
    position_tolerance: float = Field(default=0.05, gt=0.0)
    lift_height_tolerance: float = Field(default=0.03, ge=0.0)


class RobotFrankaPickPlaceResponseModel(BaseModel):
    ok: bool
    robot_prim_path: str
    object_prim_path: str
    target_position: list[float]
    controller: str
    gripper: str
    uses_kinematic_carry: bool = False
    steps: int
    done: bool
    placed: bool
    lifted: bool
    initial_object_position: list[float]
    final_object_position: list[float]
    final_distance: float
    max_lift_delta: float
    object_bbox_size: list[float]
    picking_position: list[float]
    picking_position_source: str
    end_effector_initial_height: float
    end_effector_initial_height_source: str
    end_effector_orientation: list[float] | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class RobotFrankaPickPlaceDemoInstallRequestModel(BaseModel):
    """Install a playback-tick Franka pick/place demo for GUI Play replay."""

    model_config = ConfigDict(extra="forbid")

    robot_prim_path: str = Field(default="/World/Franka")
    object_prim_path: str = Field(default="/World/PickCube")
    target_position: list[float] = Field(
        default=[0.45, -0.35, 0.02575],
        min_length=3,
        max_length=3,
        description="[x, y, z] object center goal position",
    )
    object_initial_position: list[float] = Field(
        default=[0.3, 0.35, 0.02575],
        min_length=3,
        max_length=3,
        description="[x, y, z] object center reset position",
    )
    object_size: float = Field(default=0.0515, gt=0.0)
    robot_description: str = Field(default="Franka")
    picking_position: list[float] | None = Field(default=None, min_length=3, max_length=3)
    end_effector_initial_height: float | None = Field(default=None, gt=0.0)
    end_effector_offset: list[float] | None = Field(default=None, min_length=3, max_length=3)
    end_effector_orientation: list[float] | None = Field(default=None, min_length=4, max_length=4)
    events_dt: list[float] | None = Field(default=None, min_length=10, max_length=10)
    max_steps: int = Field(default=1800, gt=0, le=20000)
    position_tolerance: float = Field(default=0.05, gt=0.0)
    lift_height_tolerance: float = Field(default=0.03, ge=0.0)
    create_demo_scene: bool = Field(default=True)
    reset_on_play: bool = Field(default=True)
