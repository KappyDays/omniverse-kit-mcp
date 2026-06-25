"""Types for robot control (Phase B)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class RobotLoadRequest:
    usd_url: str
    prim_path: str
    position: tuple[float, float, float] | None = None
    rotation: tuple[float, float, float] | None = None


@dataclass(slots=True, frozen=True)
class RobotLoadResult:
    ok: bool
    prim_path: str
    usd_url: str
    type_name: str
    has_articulation: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class JointPositions:
    prim_path: str
    positions: tuple[float, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class JointConfig:
    """Drive config + limits + max velocity per articulation DOF.

    Symmetric readback for ``set_joint_positions`` — exposes drive
    stiffness/damping/max_force, position lower/upper limits, and max
    joint velocities. ``source`` reports which backend filled the arrays.
    Runtime sources such as ``dof_properties`` and ``usd_drive_api`` follow
    SingleArticulation DOF order. Static USD discovery sources are diagnostic
    only and must not be treated as write-order proof.
    """

    prim_path: str
    source: str
    dof_count: int
    dof_names: tuple[str, ...]
    joint_types: tuple[str, ...]
    stiffness: tuple[float, ...]
    damping: tuple[float, ...]
    max_force: tuple[float, ...]
    lower_limits: tuple[float, ...]
    upper_limits: tuple[float, ...]
    max_velocity: tuple[float, ...]
    static_only: bool = False
    order_reliable: bool = True
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class JointPositionsSetRequest:
    prim_path: str
    positions: tuple[float, ...]


@dataclass(slots=True, frozen=True)
class JointPositionsSetResult:
    prim_path: str
    positions_count: int
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RobotNavigateRequest:
    prim_path: str
    target: tuple[float, float, float]
    duration_s: float = 1.0


@dataclass(slots=True, frozen=True)
class RobotNavigateResult:
    job_id: str
    prim_path: str
    target: tuple[float, float, float]
    diagnostics: dict[str, Any] = field(default_factory=dict)


# --- Phase G ---


@dataclass(slots=True, frozen=True)
class RobotNavigatePathRequest:
    prim_path: str
    waypoints: tuple[tuple[float, float, float], ...]
    duration_s: float = 5.0


@dataclass(slots=True, frozen=True)
class RobotNavigatePathResult:
    job_id: str
    prim_path: str
    num_waypoints: int
    duration_s: float
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RobotGripperControlRequest:
    prim_path: str
    action: str  # Literal["open","close","set"]
    target: float | None = None


@dataclass(slots=True, frozen=True)
class RobotGripperControlResult:
    prim_path: str
    action: str
    target_value: float
    gripper_joint_names: tuple[str, ...]
    gripper_joint_indices: tuple[int, ...]
    dof_count: int
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RobotSetEETargetRequest:
    prim_path: str
    target_pose: tuple[float, float, float, float, float, float, float]
    robot_description: str = "Franka"
    end_effector_frame: str | None = None


@dataclass(slots=True, frozen=True)
class RobotSetEETargetResult:
    prim_path: str
    target_pose: tuple[float, float, float, float, float, float, float]
    robot_description: str
    end_effector_frame: str
    lula_import_path: str
    ik_success: bool
    solution: tuple[float, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RobotArmProfile:
    profile_name: str
    display_name: str
    vendor: str
    family: str
    asset_url: str
    robot_description: str | None
    robot_description_aliases: tuple[str, ...]
    gripper_kind: str
    built_in_gripper: bool
    controller_strategy: str
    support_status: str
    support_reason: str
    evidence: tuple[str, ...]
    max_grasp_width_m: float | None = None
    fit_clearance_m: float = 0.005
    end_effector_frame_candidates: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class RobotArmProfilesResult:
    count: int
    validated_pick_place_profiles: tuple[str, ...]
    candidate_pick_place_profiles: tuple[str, ...]
    motion_policy_profiles: tuple[str, ...]
    profile_only_profiles: tuple[str, ...]
    known_dynamic_timeout_profiles: tuple[str, ...]
    known_dynamic_timeout_profile_reasons: dict[str, str]
    dynamic_probe_recommended_profiles: tuple[str, ...]
    static_only_probe_recommended_profiles: tuple[str, ...]
    recommended_probe_mode_by_profile: dict[str, str]
    recommended_probe_mode_reasons: dict[str, str]
    known_pick_place_blocker_profiles: tuple[str, ...]
    known_pick_place_blocker_profile_reasons: dict[str, str]
    profiles: tuple[RobotArmProfile, ...]


@dataclass(slots=True, frozen=True)
class RobotProbeCheck:
    ok: bool
    skipped: bool
    error_code: str | None
    message: str
    evidence: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RobotArmProfileProbeRequest:
    profile_name: str
    prim_path: str | None = None
    reset_stage: bool = True
    safe_nudge: bool = True
    cleanup: bool = True
    dynamic_checks: bool = True
    static_only_for_known_dynamic_timeouts: bool = False
    timeout_s: float | None = 90.0


@dataclass(slots=True, frozen=True)
class RobotArmProfileProbeResult:
    profile_name: str
    display_name: str
    family: str
    asset_url: str
    prim_path: str
    support_status: str
    controller_strategy: str
    recommended_next_status: str
    overall_ok: bool
    mcp_controllability: str
    mcp_controllability_reason: str
    probe_capability_level: int
    probe_capability_level_name: str
    probe_capability_level_reason: str
    probe_proves_pick_place: bool
    pick_place_validation_status: str
    pick_place_validation_reason: str
    checks: dict[str, RobotProbeCheck]


@dataclass(slots=True, frozen=True)
class RobotArmProfilesProbeRequest:
    profile_names: tuple[str, ...] | None = None
    status_filter: tuple[str, ...] | None = None
    family_filter: tuple[str, ...] | None = None
    limit: int | None = None
    reset_stage_per_profile: bool = True
    safe_nudge: bool = True
    cleanup: bool = True
    dynamic_checks: bool = True
    static_only_for_known_dynamic_timeouts: bool = False
    per_profile_timeout_s: float | None = 90.0
    batch_timeout_s: float | None = 105.0


@dataclass(slots=True, frozen=True)
class RobotArmProfilesProbeResult:
    count: int
    requested_count: int
    profile_names: tuple[str, ...] | None
    status_filter: tuple[str, ...] | None
    family_filter: tuple[str, ...] | None
    mcp_controllability_counts: dict[str, int]
    mcp_controllability_profiles: dict[str, tuple[str, ...]]
    probe_capability_level_name_counts: dict[str, int]
    probe_capability_level_name_profiles: dict[str, tuple[str, ...]]
    pick_place_validation_status_counts: dict[str, int]
    pick_place_validation_status_profiles: dict[str, tuple[str, ...]]
    unsupported_capability_counts: dict[str, int]
    timed_out_profiles: tuple[str, ...]
    batch_timeout_profiles: tuple[str, ...]
    batch_aborted_profiles: tuple[str, ...]
    blocked_profiles: tuple[str, ...]
    hard_failure_profiles: tuple[str, ...]
    lifecycle_recovery_profiles: tuple[str, ...]
    unsupported_capability_profiles: tuple[str, ...]
    ik_target_failure_profiles: tuple[str, ...]
    static_metadata_profiles: tuple[str, ...]
    known_dynamic_timeout_routed_profiles: tuple[str, ...]
    dynamic_joint_control_profiles: tuple[str, ...]
    results: tuple[RobotArmProfileProbeResult, ...]


@dataclass(slots=True, frozen=True)
class RobotEEPose:
    prim_path: str
    end_effector_frame: str
    position: tuple[float, float, float]
    orientation: tuple[float, float, float, float]
    source: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RobotFrankaPickPlaceRequest:
    """Run Isaac Sim's official Franka PickPlaceController on an existing object."""

    robot_prim_path: str
    object_prim_path: str
    target_position: tuple[float, float, float]
    robot_description: str = "Franka"
    picking_position: tuple[float, float, float] | None = None
    end_effector_initial_height: float | None = None
    end_effector_offset: tuple[float, float, float] | None = None
    end_effector_orientation: tuple[float, float, float, float] | None = None
    events_dt: tuple[float, ...] | None = None
    max_steps: int = 1800
    position_tolerance: float = 0.05
    lift_height_tolerance: float = 0.03


@dataclass(slots=True, frozen=True)
class RobotFrankaPickPlaceResult:
    ok: bool
    robot_prim_path: str
    object_prim_path: str
    target_position: tuple[float, float, float]
    controller: str
    gripper: str
    uses_kinematic_carry: bool
    steps: int
    done: bool
    placed: bool
    lifted: bool
    initial_object_position: tuple[float, float, float]
    final_object_position: tuple[float, float, float]
    final_distance: float
    max_lift_delta: float
    object_bbox_size: tuple[float, float, float]
    picking_position: tuple[float, float, float]
    picking_position_source: str
    end_effector_initial_height: float
    end_effector_initial_height_source: str
    end_effector_orientation: tuple[float, float, float, float] | None
    diagnostics: dict[str, Any]
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class RobotFrankaPickPlaceDemoRequest:
    """Install a GUI Play replayable Franka pick/place demo controller."""

    robot_prim_path: str = "/World/Franka"
    object_prim_path: str = "/World/PickCube"
    target_position: tuple[float, float, float] = (0.45, -0.35, 0.02575)
    object_initial_position: tuple[float, float, float] = (0.3, 0.35, 0.02575)
    object_size: float = 0.04
    object_asset_url: str | None = None
    grid_asset_url: str | None = None
    max_grasp_width_m: float | None = 0.08
    fit_clearance_m: float = 0.005
    robot_description: str = "Franka"
    picking_position: tuple[float, float, float] | None = None
    end_effector_initial_height: float | None = None
    end_effector_offset: tuple[float, float, float] | None = None
    end_effector_orientation: tuple[float, float, float, float] | None = None
    events_dt: tuple[float, ...] | None = None
    max_steps: int = 1800
    position_tolerance: float = 0.05
    lift_height_tolerance: float = 0.03
    create_demo_scene: bool = True
    reset_on_play: bool = True


@dataclass(slots=True, frozen=True)
class RobotPickPlaceDemoRequest:
    """Install a profile-selected pick/place playback demo."""

    profile_name: str = "franka_fr3"
    robot_prim_path: str = "/World/Franka"
    object_prim_path: str = "/World/PickCube"
    target_position: tuple[float, float, float] = (0.45, -0.35, 0.02575)
    object_initial_position: tuple[float, float, float] = (0.3, 0.35, 0.02575)
    object_size: float = 0.04
    object_asset_url: str | None = None
    grid_asset_url: str | None = None
    picking_position: tuple[float, float, float] | None = None
    end_effector_initial_height: float | None = None
    end_effector_offset: tuple[float, float, float] | None = None
    end_effector_orientation: tuple[float, float, float, float] | None = None
    events_dt: tuple[float, ...] | None = None
    max_steps: int = 1800
    position_tolerance: float = 0.05
    lift_height_tolerance: float = 0.03
    create_demo_scene: bool = True
    reset_on_play: bool = True


@dataclass(slots=True, frozen=True)
class RobotFrankaPickPlaceDemoStatus:
    ok: bool
    status: str
    robot_prim_path: str
    object_prim_path: str
    target_position: tuple[float, float, float]
    uses_kinematic_carry: bool
    steps: int
    controller_event: int
    done: bool
    placed: bool
    lifted: bool
    initial_object_position: tuple[float, float, float]
    final_object_position: tuple[float, float, float]
    final_distance: float
    max_lift_delta: float
    object_bbox_center: tuple[float, float, float]
    object_bbox_size: tuple[float, float, float]
    object_fit_ok: bool
    object_fit_reason: str | None
    object_fit_axis: str | None
    object_fit_limit_m: float | None
    object_fit_measured_m: float | None
    picking_position: tuple[float, float, float]
    end_effector_initial_height: float
    diagnostics: dict[str, Any]
    profile_name: str | None = None
    support_status: str | None = None
    support_reason: str | None = None
    controller_strategy: str | None = None
    last_error: str | None = None


# --- Phase J (NavMesh Playground) ---


@dataclass(slots=True, frozen=True)
class RobotDrivePhysicsRequest:
    prim_path: str
    waypoints: tuple[tuple[float, float, float], ...]
    max_linear: float = 1.0
    max_angular: float = 1.2
    wheel_radius: float = 0.14
    wheel_base: float = 0.413
    arrival_tolerance: float = 0.3
    timeout_s: float = 60.0
    lookahead: float = 0.8


@dataclass(slots=True, frozen=True)
class RobotDrivePhysicsResult:
    ok: bool
    job_id: str
    prim_path: str
