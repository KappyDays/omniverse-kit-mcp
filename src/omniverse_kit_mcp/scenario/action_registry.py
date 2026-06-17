"""Action registry — maps (module, action) to typed request object constructors.

Fixes C-1: runner was passing **kwargs directly to module methods that expect
typed request/assertion objects. This registry builds the correct typed object
from the YAML args dict.
"""

from __future__ import annotations

from typing import Any

from omniverse_kit_mcp.types.character import (
    CharacterLoadCrowdRequest,
    CharacterLoadRequest,
    CharacterNavigateRequest,
    CharacterPlayAnimationRequest,
    CharacterPlayAnimationVariantRequest,
    CharacterSetPositionRequest,
    CharacterStopAnimationRequest,
)
from omniverse_kit_mcp.types.common import ModuleName
from omniverse_kit_mcp.types.extension import (
    ExtensionResetRequest,
    ExtensionTriggerRequest,
)
from omniverse_kit_mcp.types.lakehouse import (
    LakehouseDatasetRef,
    LakehouseQueryRequest,
)
from omniverse_kit_mcp.types.robot import (
    JointPositionsSetRequest,
    RobotDrivePhysicsRequest,
    RobotFrankaPickPlaceRequest,
    RobotGripperControlRequest,
    RobotLoadRequest,
    RobotNavigatePathRequest,
    RobotNavigateRequest,
    RobotSetEETargetRequest,
)
from omniverse_kit_mcp.types.stage import (
    PrimExistenceAssertion,
    PropertyAssertion,
    StageCaptureFilter,
    UsdPropertyValue,
)
from omniverse_kit_mcp.types.navigation import (
    NavigationSetVisualizationRequest,
    NavPathQueryRequest,
    SampleWalkablePointsRequest,
)
from omniverse_kit_mcp.types.sensor import (
    SensorAttachContactRequest,
    SensorAttachImuRequest,
    SensorAttachRtxCameraRequest,
    SensorAttachRtxDepthCameraRequest,
    SensorAttachRtxLidarRequest,
    SensorSetAnnotatorRequest,
    SensorSetVisualizationRequest,
)
from omniverse_kit_mcp.types.content import (
    ContentBrowseRequest,
    ContentPreviewRequest,
    ContentResolveRequest,
)
from omniverse_kit_mcp.types.omnigraph import (
    OmnigraphConnectRequest,
    OmnigraphCreateNodeRequest,
    OmnigraphCreateRos2PublisherRequest,
    OmnigraphCreateScriptControllerRequest,
    OmnigraphExecuteRequest,
)
from omniverse_kit_mcp.types.replicator import (
    ReplicatorCreateWriterRequest,
    ReplicatorRegisterRandomizerRequest,
    ReplicatorTriggerOnceRequest,
    ReplicatorTriggerOnTimeRequest,
)
from omniverse_kit_mcp.types.simulation import (
    SimulationSetTimeRequest,
    SimulationStepRequest,
)
from omniverse_kit_mcp.types.physics import (
    PhysicsApplyColliderRequest,
    PhysicsApplyMaterialRequest,
    PhysicsApplyRigidBodyRequest,
    PhysicsCreateJointRequest,
    PhysicsSetSceneRequest,
    PhysicsVisualizeRequest,
)
from omniverse_kit_mcp.types.lighting import (
    LightingCreateDiskRequest,
    LightingCreateDistantRequest,
    LightingCreateDomeRequest,
    LightingCreateRectRequest,
    LightingCreateSphereRequest,
    LightingSetExposureRequest,
)
from omniverse_kit_mcp.types.material import (
    MaterialAssignMdlRequest,
    MaterialGetBoundRequest,
    MaterialListMdlRequest,
)
from omniverse_kit_mcp.types.viewport import (
    SSIMComparisonRequest,
    ViewportCaptureRequest,
    ViewportCreateRequest,
    ViewportDestroyRequest,
    ViewportSetFovRequest,
    ViewportSetRenderModeRequest,
    ViewportSetRenderQualityRequest,
    ViewportToggleOverlayRequest,
)
from omniverse_kit_mcp.types.window import WindowCaptureRequest


def build_request(module: ModuleName, action: str, args: dict[str, Any]) -> Any | None:
    """Build a typed request object from module/action/args.

    Returns None if no mapping exists (fallback to **kwargs).
    """
    key = (module, action)
    builder = _REGISTRY.get(key)
    if builder is None:
        return None
    return builder(args)


# --- Builder functions ---


def _build_capture_filter(args: dict[str, Any]) -> StageCaptureFilter:
    return StageCaptureFilter(
        include_prim_patterns=tuple(args.get("include_prim_patterns", ["*"])),
        exclude_prim_patterns=tuple(args.get("exclude_prim_patterns", [])),
        include_properties=args.get("include_properties", True),
        include_metadata=args.get("include_metadata", True),
        max_prim_count=args.get("max_prim_count", 10_000),
    )


def _build_prim_existence_assertion(args: dict[str, Any]) -> PrimExistenceAssertion:
    return PrimExistenceAssertion(
        prim_path=args["prim_path"],
        should_exist=args.get("should_exist", True),
        expected_type_name=args.get("expected_type_name"),
        expected_active=args.get("expected_active"),
    )


def _build_property_assertion(args: dict[str, Any]) -> PropertyAssertion:
    expected = None
    if "expected_value" in args:
        expected = UsdPropertyValue(
            type_name=args.get("expected_type_name", "unknown"),
            value=args["expected_value"],
        )
    return PropertyAssertion(
        prim_path=args["prim_path"],
        property_name=args["property_name"],
        property_kind=args.get("property_kind", args.get("property_type", "attribute")),
        comparator=args.get("comparator", "equals"),
        expected=expected,
        tolerance=args.get("tolerance"),
    )


def _build_viewport_capture(args: dict[str, Any]) -> ViewportCaptureRequest:
    return ViewportCaptureRequest(
        viewport_name=args.get("viewport_name", "Viewport"),
        camera_prim_path=args.get("camera_prim_path"),
        renderer=args.get("renderer", "rtx"),
        width=args.get("width", 1280),
        height=args.get("height", 720),
        samples_per_pixel=args.get("samples_per_pixel", 64),
        settle_frames=args.get("settle_frames", 5),
        output_format=args.get("output_format", "png"),
        transparent_background=args.get("transparent_background", False),
    )


def _build_external_asset_search(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": args["query"],
        "providers": args.get("providers"),
        "limit": args.get("limit", 10),
    }


def _build_external_asset_download(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": args["provider"],
        "asset_id": args["asset_id"],
        "format_preference": args.get("format_preference"),
    }


def _build_external_asset_convert(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_path": args["manifest_path"],
        "output_format": args.get("output_format", "usd"),
        "timeout_s": args.get("timeout_s", 180.0),
    }


def _build_ssim_request(args: dict[str, Any]) -> SSIMComparisonRequest:
    crop = args.get("crop")
    return SSIMComparisonRequest(
        baseline_artifact_path=args["baseline_artifact_path"],
        candidate_artifact_path=args["candidate_artifact_path"],
        min_ssim=args.get("min_ssim", 0.99),
        crop=tuple(crop) if crop and len(crop) == 4 else None,
    )


def _build_lakehouse_query(args: dict[str, Any]) -> LakehouseQueryRequest:
    target = None
    target_raw = args.get("target")
    if isinstance(target_raw, dict):
        target = LakehouseDatasetRef(
            namespace=target_raw["namespace"],
            dataset=target_raw["dataset"],
            table=target_raw.get("table"),
            version=target_raw.get("version"),
        )
    return LakehouseQueryRequest(
        sql=args.get("sql"),
        target=target,
        filters=args.get("filters", {}),
        limit=args.get("limit", 1000),
    )


def _build_extension_trigger(args: dict[str, Any]) -> ExtensionTriggerRequest:
    return ExtensionTriggerRequest(
        operation=args["operation"],
        payload=args.get("payload", {}),
        wait_for_idle=args.get("wait_for_idle", True),
        idle_timeout_s=args.get("idle_timeout_s", 30.0),
        poll_interval_s=args.get("poll_interval_s", 0.5),
    )


def _build_extension_reset(args: dict[str, Any]) -> ExtensionResetRequest:
    return ExtensionResetRequest(
        reset_stage_changes=args.get("reset_stage_changes", False),
        reset_internal_state=args.get("reset_internal_state", True),
        clear_caches=args.get("clear_caches", True),
        reload_config=args.get("reload_config", False),
    )


def _build_stage_load_usd(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "usd_url": args["usd_url"],
        "prim_path": args["prim_path"],
        "position": args.get("position"),
        "rotation": args.get("rotation"),
    }


def _build_stage_set_property(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "prim_path": args["prim_path"],
        "property_name": args["property_name"],
        "value": args["value"],
        "type_hint": args.get("type_hint"),
    }


def _build_stage_create_prim(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "prim_path": args["prim_path"],
        "prim_type": args.get("prim_type", "Xform"),
        "position": args.get("position"),
    }


def _build_stage_delete_prim(args: dict[str, Any]) -> str:
    return args["prim_path"]


def _build_diff_snapshots(args: dict[str, Any]) -> dict[str, Any]:
    """Package diff_snapshots args — the runner resolves step IDs to snapshots
    via ScenarioContext (context-aware action)."""
    if "before_step_id" not in args or "after_step_id" not in args:
        raise KeyError(
            "stage.diff_snapshots requires 'before_step_id' and 'after_step_id' "
            "referring to prior capture_snapshot step IDs"
        )
    return {
        "before_step_id": args["before_step_id"],
        "after_step_id": args["after_step_id"],
        "min_changes": args.get("min_changes"),
        "max_changes": args.get("max_changes"),
    }


def _build_robot_load(args: dict[str, Any]) -> RobotLoadRequest:
    return RobotLoadRequest(
        usd_url=args["usd_url"],
        prim_path=args["prim_path"],
        position=tuple(args["position"]) if args.get("position") else None,  # type: ignore[arg-type]
        rotation=tuple(args["rotation"]) if args.get("rotation") else None,  # type: ignore[arg-type]
    )


def _build_robot_navigate(args: dict[str, Any]) -> RobotNavigateRequest:
    target = args["target"]
    if len(target) != 3:
        raise ValueError("robot.navigate_to target must be [x, y, z]")
    return RobotNavigateRequest(
        prim_path=args["prim_path"],
        target=(float(target[0]), float(target[1]), float(target[2])),
        duration_s=float(args.get("duration_s", 1.0)),
    )


def _build_set_joint_positions(args: dict[str, Any]) -> JointPositionsSetRequest:
    return JointPositionsSetRequest(
        prim_path=args["prim_path"],
        positions=tuple(float(p) for p in args["positions"]),
    )


def _build_character_load(args: dict[str, Any]) -> CharacterLoadRequest:
    return CharacterLoadRequest(
        usd_url=args["usd_url"],
        prim_path=args.get("prim_path"),
        position=tuple(args["position"]) if args.get("position") else None,  # type: ignore[arg-type]
        yaw=float(args.get("yaw", 0.0)),
    )


def _build_character_play_animation(args: dict[str, Any]) -> CharacterPlayAnimationRequest:
    target = args.get("target_position")
    return CharacterPlayAnimationRequest(
        prim_path=args["prim_path"],
        animation_name=args["animation_name"],
        speed=float(args.get("speed", 1.0)),
        target_position=tuple(target) if target else None,  # type: ignore[arg-type]
    )


def _build_character_set_position(args: dict[str, Any]) -> CharacterSetPositionRequest:
    position = args["position"]
    if len(position) != 3:
        raise ValueError("character.set_position requires position=[x, y, z]")
    orientation = args.get("orientation")
    if orientation is not None and len(orientation) != 4:
        raise ValueError("character.set_position orientation must be [qw, qx, qy, qz]")
    return CharacterSetPositionRequest(
        prim_path=args["prim_path"],
        position=(float(position[0]), float(position[1]), float(position[2])),
        orientation=tuple(float(v) for v in orientation) if orientation else None,  # type: ignore[arg-type]
    )


def _build_character_stop_animation(args: dict[str, Any]) -> CharacterStopAnimationRequest:
    return CharacterStopAnimationRequest(prim_path=args["prim_path"])


def _build_character_navigate(args: dict[str, Any]) -> CharacterNavigateRequest:
    target = args["target"]
    if len(target) != 3:
        raise ValueError("character.navigate_to target must be [x, y, z]")
    return CharacterNavigateRequest(
        prim_path=args["prim_path"],
        target=(float(target[0]), float(target[1]), float(target[2])),
        speed=float(args.get("speed", 1.0)),
    )


def _build_window_capture(args: dict[str, Any]) -> WindowCaptureRequest:
    return WindowCaptureRequest(
        mode=args.get("mode", "kit"),
        hwnd=args.get("hwnd"),
        settle_frames=int(args.get("settle_frames", 5)),
        output_format=args.get("output_format", "png"),
        bring_to_front=bool(args.get("bring_to_front", False)),
        use_client_rect=bool(args.get("use_client_rect", False)),
        wait_stable=bool(args.get("wait_stable", False)),
        stable_interval_s=float(args.get("stable_interval_s", 2.0)),
        stable_consecutive=int(args.get("stable_consecutive", 2)),
        stable_max_wait_s=float(args.get("stable_max_wait_s", 45.0)),
        stable_diff_threshold=float(args.get("stable_diff_threshold", 0.01)),
    )


def _build_nav_query_path(args: dict[str, Any]) -> NavPathQueryRequest:
    start = args["start"]
    end = args["end"]
    if len(start) != 3 or len(end) != 3:
        raise ValueError("navigation.query_path start / end must be [x,y,z]")
    return NavPathQueryRequest(
        start=(float(start[0]), float(start[1]), float(start[2])),
        end=(float(end[0]), float(end[1]), float(end[2])),
        agent_radius=float(args.get("agent_radius", 0.25)),
        agent_height=float(args.get("agent_height", 1.8)),
        straighten=bool(args.get("straighten", True)),
    )


def _build_nav_set_visualization(
    args: dict[str, Any],
) -> NavigationSetVisualizationRequest:
    mode = args["mode"]
    if mode not in ("walkable", "obstacles", "off"):
        raise ValueError(
            "navigation.set_visualization mode must be "
            "'walkable' | 'obstacles' | 'off'"
        )
    return NavigationSetVisualizationRequest(mode=mode)


def _build_sensor_attach_rtx_camera(
    args: dict[str, Any],
) -> SensorAttachRtxCameraRequest:
    offset = args["mount_offset"]
    rotation = args["mount_rotation"]
    if len(offset) != 3 or len(rotation) != 3:
        raise ValueError(
            "sensor.attach_rtx_camera mount_offset / mount_rotation must be [x,y,z]"
        )
    resolution = args.get("resolution", [1280, 720])
    if len(resolution) != 2:
        raise ValueError("sensor.attach_rtx_camera resolution must be [w,h]")
    return SensorAttachRtxCameraRequest(
        robot_prim=args["robot_prim"],
        mount_offset=(float(offset[0]), float(offset[1]), float(offset[2])),
        mount_rotation=(float(rotation[0]), float(rotation[1]), float(rotation[2])),
        resolution=(int(resolution[0]), int(resolution[1])),
        sensor_name=str(args.get("sensor_name", "RtxCamera")),
    )


def _build_sensor_attach_rtx_lidar(
    args: dict[str, Any],
) -> SensorAttachRtxLidarRequest:
    offset = args["mount_offset"]
    rotation = args["mount_rotation"]
    if len(offset) != 3 or len(rotation) != 3:
        raise ValueError(
            "sensor.attach_rtx_lidar mount_offset / mount_rotation must be [x,y,z]"
        )
    return SensorAttachRtxLidarRequest(
        robot_prim=args["robot_prim"],
        mount_offset=(float(offset[0]), float(offset[1]), float(offset[2])),
        mount_rotation=(float(rotation[0]), float(rotation[1]), float(rotation[2])),
        config_preset=str(args.get("config_preset", "Example_Rotary")),
        sensor_name=str(args.get("sensor_name", "RtxLidar")),
    )


def _build_sensor_attach_rtx_depth_camera(
    args: dict[str, Any],
) -> SensorAttachRtxDepthCameraRequest:
    offset = args["mount_offset"]
    rotation = args["mount_rotation"]
    if len(offset) != 3 or len(rotation) != 3:
        raise ValueError(
            "sensor.attach_rtx_depth_camera mount_offset / mount_rotation must be [x,y,z]"
        )
    resolution = args.get("resolution", [1280, 720])
    if len(resolution) != 2:
        raise ValueError("sensor.attach_rtx_depth_camera resolution must be [w,h]")
    return SensorAttachRtxDepthCameraRequest(
        robot_prim=args["robot_prim"],
        mount_offset=(float(offset[0]), float(offset[1]), float(offset[2])),
        mount_rotation=(float(rotation[0]), float(rotation[1]), float(rotation[2])),
        resolution=(int(resolution[0]), int(resolution[1])),
        sensor_name=str(args.get("sensor_name", "RtxDepthCamera")),
    )


def _build_sensor_set_visualization(
    args: dict[str, Any],
) -> SensorSetVisualizationRequest:
    mode = args.get("mode", "on")
    if mode not in ("on", "off"):
        raise ValueError("sensor.set_visualization mode must be 'on' | 'off'")
    return SensorSetVisualizationRequest(
        sensor_prim=args["sensor_prim"],
        mode=mode,
    )


def _build_viewport_create(args: dict[str, Any]) -> ViewportCreateRequest:
    return ViewportCreateRequest(
        viewport_name=args["viewport_name"],
        camera_path=args.get("camera_path"),
        width=int(args.get("width", 1280)),
        height=int(args.get("height", 720)),
        docked=bool(args.get("docked", False)),
    )


def _build_viewport_destroy(args: dict[str, Any]) -> ViewportDestroyRequest:
    return ViewportDestroyRequest(viewport_name=args["viewport_name"])


# --- Phase F: Physics / Lighting / Material / Render -----------------------


def _build_physics_apply_rigid_body(
    args: dict[str, Any],
) -> PhysicsApplyRigidBodyRequest:
    return PhysicsApplyRigidBodyRequest(
        prim_path=args["prim_path"],
        mass=float(args.get("mass", 1.0)),
        dynamic=bool(args.get("dynamic", True)),
    )


def _build_physics_apply_collider(
    args: dict[str, Any],
) -> PhysicsApplyColliderRequest:
    approximation = args.get("approximation", "convexHull")
    if approximation not in (
        "convexHull", "triangleMesh", "sdf", "box", "sphere", "none",
    ):
        raise ValueError(
            "physics.apply_collider approximation must be convexHull|triangleMesh|sdf|box|sphere|none"
        )
    return PhysicsApplyColliderRequest(
        prim_path=args["prim_path"],
        approximation=approximation,
    )


def _build_physics_apply_material(
    args: dict[str, Any],
) -> PhysicsApplyMaterialRequest:
    return PhysicsApplyMaterialRequest(
        prim_path=args["prim_path"],
        friction=float(args.get("friction", 0.5)),
        restitution=float(args.get("restitution", 0.0)),
        density=float(args.get("density", 1000.0)),
        material_name=args.get("material_name"),
    )


def _build_physics_create_joint(
    args: dict[str, Any],
) -> PhysicsCreateJointRequest:
    joint_type = args["joint_type"]
    if joint_type not in ("Fixed", "Revolute", "Prismatic", "Spherical"):
        raise ValueError(
            "physics.create_joint joint_type must be Fixed|Revolute|Prismatic|Spherical"
        )
    anchor = args.get("anchor") or [0.0, 0.0, 0.0]
    axis = args.get("axis") or [0.0, 0.0, 1.0]
    if len(anchor) != 3 or len(axis) != 3:
        raise ValueError("physics.create_joint anchor / axis must be [x,y,z]")
    return PhysicsCreateJointRequest(
        joint_type=joint_type,
        body_a=args["body_a"],
        body_b=args["body_b"],
        anchor=(float(anchor[0]), float(anchor[1]), float(anchor[2])),
        axis=(float(axis[0]), float(axis[1]), float(axis[2])),
        joint_prim_path=args.get("joint_prim_path"),
    )


def _build_physics_set_scene(args: dict[str, Any]) -> PhysicsSetSceneRequest:
    gravity = args.get("gravity") or [0.0, 0.0, -9.81]
    if len(gravity) != 3:
        raise ValueError("physics.set_scene gravity must be [gx,gy,gz]")
    return PhysicsSetSceneRequest(
        gravity=(float(gravity[0]), float(gravity[1]), float(gravity[2])),
        timestep=float(args.get("timestep", 1.0 / 60.0)),
        solver_iter_pos=int(args.get("solver_iter_pos", 4)),
        solver_iter_vel=int(args.get("solver_iter_vel", 1)),
        scene_prim_path=args.get("scene_prim_path", "/World/PhysicsScene"),
    )


def _build_physics_visualize(args: dict[str, Any]) -> PhysicsVisualizeRequest:
    mode = args["mode"]
    if mode not in ("collision", "joint", "mass", "off"):
        raise ValueError(
            "physics.visualize mode must be collision|joint|mass|off"
        )
    return PhysicsVisualizeRequest(mode=mode)


def _build_lighting_create_dome(args: dict[str, Any]) -> LightingCreateDomeRequest:
    return LightingCreateDomeRequest(
        prim_path=args["prim_path"],
        intensity=float(args.get("intensity", 1000.0)),
        texture=args.get("texture"),
    )


def _build_lighting_create_distant(
    args: dict[str, Any],
) -> LightingCreateDistantRequest:
    return LightingCreateDistantRequest(
        prim_path=args["prim_path"],
        intensity=float(args.get("intensity", 1000.0)),
        angle_deg=float(args.get("angle_deg", 0.53)),
    )


def _build_lighting_create_disk(args: dict[str, Any]) -> LightingCreateDiskRequest:
    return LightingCreateDiskRequest(
        prim_path=args["prim_path"],
        intensity=float(args.get("intensity", 1000.0)),
        radius=float(args.get("radius", 1.0)),
    )


def _build_lighting_create_rect(args: dict[str, Any]) -> LightingCreateRectRequest:
    return LightingCreateRectRequest(
        prim_path=args["prim_path"],
        intensity=float(args.get("intensity", 1000.0)),
        width=float(args.get("width", 1.0)),
        height=float(args.get("height", 1.0)),
    )


def _build_lighting_create_sphere(
    args: dict[str, Any],
) -> LightingCreateSphereRequest:
    return LightingCreateSphereRequest(
        prim_path=args["prim_path"],
        intensity=float(args.get("intensity", 1000.0)),
        radius=float(args.get("radius", 1.0)),
    )


def _build_lighting_set_exposure(
    args: dict[str, Any],
) -> LightingSetExposureRequest:
    return LightingSetExposureRequest(exposure=float(args["exposure"]))


def _build_material_list_mdl(args: dict[str, Any]) -> MaterialListMdlRequest:
    return MaterialListMdlRequest(library=str(args.get("library", "default")))


def _build_material_assign_mdl(args: dict[str, Any]) -> MaterialAssignMdlRequest:
    return MaterialAssignMdlRequest(
        prim_path=args["prim_path"],
        mdl_url=args["mdl_url"],
        material_name=args["material_name"],
    )


def _build_material_get_bound(args: dict[str, Any]) -> MaterialGetBoundRequest:
    return MaterialGetBoundRequest(prim_path=args["prim_path"])


def _build_viewport_set_render_mode(
    args: dict[str, Any],
) -> ViewportSetRenderModeRequest:
    mode = args.get("mode", "RealTime")
    if mode not in ("RealTime", "PathTracing"):
        raise ValueError("viewport.set_render_mode mode must be RealTime|PathTracing")
    return ViewportSetRenderModeRequest(
        viewport_name=str(args.get("viewport_name", "Viewport")),
        mode=mode,
    )


def _build_viewport_set_render_quality(
    args: dict[str, Any],
) -> ViewportSetRenderQualityRequest:
    denoiser = args.get("denoiser", "auto")
    if denoiser not in ("auto", "DLSS", "NRD", "off"):
        raise ValueError(
            "viewport.set_render_quality denoiser must be auto|DLSS|NRD|off"
        )
    return ViewportSetRenderQualityRequest(
        samples=int(args.get("samples", 1)),
        denoiser=denoiser,
    )


def _build_viewport_toggle_overlay(
    args: dict[str, Any],
) -> ViewportToggleOverlayRequest:
    overlay = args["overlay"]
    if overlay not in ("gridlines", "axis", "stats"):
        raise ValueError(
            "viewport.toggle_overlay overlay must be gridlines|axis|stats"
        )
    return ViewportToggleOverlayRequest(
        viewport_name=str(args.get("viewport_name", "Viewport")),
        overlay=overlay,
        visible=bool(args.get("visible", True)),
    )


def _build_viewport_set_fov(args: dict[str, Any]) -> ViewportSetFovRequest:
    return ViewportSetFovRequest(
        viewport_name=str(args.get("viewport_name", "Viewport")),
        fov_deg=float(args["fov_deg"]),
    )


# --- Phase G builders ---


def _build_robot_navigate_path(args: dict[str, Any]) -> RobotNavigatePathRequest:
    waypoints = args.get("waypoints") or args.get("points")
    if not waypoints or len(waypoints) < 2:
        raise ValueError(
            "robot.navigate_path requires waypoints=[[x,y,z], ...] with >= 2 entries"
        )
    for i, p in enumerate(waypoints):
        if len(p) != 3:
            raise ValueError(f"waypoint[{i}] must be [x, y, z]")
    return RobotNavigatePathRequest(
        prim_path=args["prim_path"],
        waypoints=tuple(
            (float(p[0]), float(p[1]), float(p[2])) for p in waypoints
        ),
        duration_s=float(args.get("duration_s", 5.0)),
    )


# --- Phase J builders (NavMesh Playground) ---


def _build_navigation_sample_walkable(args: dict[str, Any]) -> SampleWalkablePointsRequest:
    bmin = args.get("bounds_min")
    bmax = args.get("bounds_max")
    if (bmin is None) != (bmax is None):
        raise ValueError("bounds_min and bounds_max must both be set or both null")
    return SampleWalkablePointsRequest(
        count=int(args["count"]),
        bounds_min=tuple(float(v) for v in bmin) if bmin else None,  # type: ignore[arg-type]
        bounds_max=tuple(float(v) for v in bmax) if bmax else None,  # type: ignore[arg-type]
        seed=int(args["seed"]) if "seed" in args and args["seed"] is not None else None,
    )


def _build_robot_drive_physics(args: dict[str, Any]) -> RobotDrivePhysicsRequest:
    waypoints = args.get("waypoints")
    if not waypoints or len(waypoints) < 2:
        raise ValueError(
            "robot.drive_physics requires waypoints=[[x,y,z], ...] with >= 2 entries"
        )
    for i, p in enumerate(waypoints):
        if len(p) != 3:
            raise ValueError(f"waypoint[{i}] must be [x, y, z]")
    return RobotDrivePhysicsRequest(
        prim_path=args["prim_path"],
        waypoints=tuple(
            (float(p[0]), float(p[1]), float(p[2])) for p in waypoints
        ),
        max_linear=float(args.get("max_linear", 1.0)),
        max_angular=float(args.get("max_angular", 1.2)),
        wheel_radius=float(args.get("wheel_radius", 0.14)),
        wheel_base=float(args.get("wheel_base", 0.413)),
        arrival_tolerance=float(args.get("arrival_tolerance", 0.3)),
        timeout_s=float(args.get("timeout_s", 60.0)),
        lookahead=float(args.get("lookahead", 0.8)),
    )


def _build_robot_gripper_control(args: dict[str, Any]) -> RobotGripperControlRequest:
    action = args.get("action", "open")
    if action not in ("open", "close", "set"):
        raise ValueError("robot.gripper_control action must be open|close|set")
    target = args.get("target")
    if action == "set" and target is None:
        raise ValueError("robot.gripper_control action='set' requires target")
    return RobotGripperControlRequest(
        prim_path=args["prim_path"],
        action=action,
        target=float(target) if target is not None else None,
    )


def _build_robot_set_ee_target(args: dict[str, Any]) -> RobotSetEETargetRequest:
    pose = args.get("target_pose")
    if not pose or len(pose) != 7:
        raise ValueError(
            "robot.set_ee_target target_pose must be [x,y,z,qw,qx,qy,qz]"
        )
    return RobotSetEETargetRequest(
        prim_path=args["prim_path"],
        target_pose=tuple(float(v) for v in pose),  # type: ignore[arg-type]
        robot_description=str(args.get("robot_description", "Franka")),
        end_effector_frame=args.get("end_effector_frame"),
    )


def _build_robot_run_franka_pick_place(
    args: dict[str, Any],
) -> RobotFrankaPickPlaceRequest:
    target = args.get("target_position")
    if not target or len(target) != 3:
        raise ValueError("robot.run_franka_pick_place target_position must be [x,y,z]")
    offset = args.get("end_effector_offset")
    if offset is not None and len(offset) != 3:
        raise ValueError("robot.run_franka_pick_place end_effector_offset must be [x,y,z]")
    picking = args.get("picking_position")
    if picking is not None and len(picking) != 3:
        raise ValueError("robot.run_franka_pick_place picking_position must be [x,y,z]")
    orientation = args.get("end_effector_orientation")
    if orientation is not None and len(orientation) != 4:
        raise ValueError(
            "robot.run_franka_pick_place end_effector_orientation must be [qw,qx,qy,qz]"
        )
    events_dt = args.get("events_dt")
    return RobotFrankaPickPlaceRequest(
        robot_prim_path=args["robot_prim_path"],
        object_prim_path=args["object_prim_path"],
        target_position=tuple(float(v) for v in target),  # type: ignore[arg-type]
        robot_description=str(args.get("robot_description", "Franka")),
        picking_position=(
            tuple(float(v) for v in picking)
            if picking is not None
            else None
        ),  # type: ignore[arg-type]
        end_effector_initial_height=(
            float(args["end_effector_initial_height"])
            if args.get("end_effector_initial_height") is not None
            else None
        ),
        end_effector_offset=(
            tuple(float(v) for v in offset)
            if offset is not None
            else None
        ),  # type: ignore[arg-type]
        end_effector_orientation=(
            tuple(float(v) for v in orientation)
            if orientation is not None
            else None
        ),  # type: ignore[arg-type]
        events_dt=tuple(float(v) for v in events_dt) if events_dt else None,
        max_steps=int(args.get("max_steps", 1800)),
        position_tolerance=float(args.get("position_tolerance", 0.05)),
        lift_height_tolerance=float(args.get("lift_height_tolerance", 0.03)),
    )


def _build_character_play_animation_variant(
    args: dict[str, Any],
) -> CharacterPlayAnimationVariantRequest:
    variant = args.get("variant")
    if not variant:
        raise ValueError("character.play_animation_variant requires variant")
    target = args.get("target_position")
    if target is not None and len(target) != 3:
        raise ValueError("target_position must be [x,y,z]")
    return CharacterPlayAnimationVariantRequest(
        prim_path=args["prim_path"],
        variant=str(variant),
        speed=float(args.get("speed", 1.0)),
        target_position=(
            tuple(float(v) for v in target) if target else None  # type: ignore[arg-type]
        ),
        dispatch_mode=str(args.get("dispatch_mode", "auto")),
    )


def _build_character_load_crowd(args: dict[str, Any]) -> CharacterLoadCrowdRequest:
    count = int(args["count"])
    if count < 1:
        raise ValueError("character.load_crowd count must be >= 1")
    layout = args.get("layout", "grid")
    if layout not in ("grid", "line", "random"):
        raise ValueError("layout must be grid|line|random")
    center = args.get("center") or [0.0, 0.0, 0.0]
    if len(center) != 3:
        raise ValueError("center must be [x,y,z]")
    return CharacterLoadCrowdRequest(
        count=count,
        layout=layout,
        spacing=float(args.get("spacing", 2.0)),
        base_name=str(args.get("base_name", "Crowd")),
        center=(float(center[0]), float(center[1]), float(center[2])),
        usd_url=args.get("usd_url"),
    )


def _build_sensor_attach_contact(
    args: dict[str, Any],
) -> SensorAttachContactRequest:
    translation = args.get("translation") or [0.0, 0.0, 0.0]
    if len(translation) != 3:
        raise ValueError("sensor.attach_contact translation must be [x,y,z]")
    return SensorAttachContactRequest(
        prim_path=args["prim_path"],
        sensor_name=str(args.get("sensor_name", "ContactSensor")),
        frequency=int(args.get("frequency", 60)),
        translation=(float(translation[0]), float(translation[1]), float(translation[2])),
        radius=float(args.get("radius", -1.0)),
    )


def _build_sensor_attach_imu(args: dict[str, Any]) -> SensorAttachImuRequest:
    offset = args.get("mount_offset") or [0.0, 0.0, 0.0]
    orientation = args.get("mount_orientation") or [1.0, 0.0, 0.0, 0.0]
    if len(offset) != 3:
        raise ValueError("sensor.attach_imu mount_offset must be [x,y,z]")
    if len(orientation) != 4:
        raise ValueError("sensor.attach_imu mount_orientation must be [qw,qx,qy,qz]")
    return SensorAttachImuRequest(
        prim_path=args["prim_path"],
        sensor_name=str(args.get("sensor_name", "IMUSensor")),
        frequency=int(args.get("frequency", 200)),
        mount_offset=(float(offset[0]), float(offset[1]), float(offset[2])),
        mount_orientation=(
            float(orientation[0]), float(orientation[1]),
            float(orientation[2]), float(orientation[3]),
        ),
    )


def _build_sensor_set_annotator(
    args: dict[str, Any],
) -> SensorSetAnnotatorRequest:
    annotators = args.get("annotators") or []
    if not annotators:
        raise ValueError("sensor.set_annotator annotators list must be non-empty")
    resolution = args.get("resolution") or [1280, 720]
    if len(resolution) != 2:
        raise ValueError("sensor.set_annotator resolution must be [w,h]")
    return SensorSetAnnotatorRequest(
        sensor_prim=args["sensor_prim"],
        annotators=tuple(str(a) for a in annotators),
        resolution=(int(resolution[0]), int(resolution[1])),
    )


def _build_simulation_step(args: dict[str, Any]) -> SimulationStepRequest:
    frames = int(args.get("frames", 1))
    if frames < 1:
        raise ValueError("simulation.step frames must be >= 1")
    return SimulationStepRequest(frames=frames)


# --- Phase H builders ---


def _build_replicator_create_writer(
    args: dict[str, Any],
) -> ReplicatorCreateWriterRequest:
    writer_type = args.get("writer_type", "BasicWriter")
    if writer_type not in ("BasicWriter", "KittiWriter", "CocoWriter"):
        raise ValueError(
            "replicator.create_writer writer_type must be "
            "BasicWriter|KittiWriter|CocoWriter"
        )
    if not args.get("output_dir"):
        raise ValueError("replicator.create_writer requires output_dir")
    return ReplicatorCreateWriterRequest(
        writer_type=writer_type,  # type: ignore[arg-type]
        output_dir=str(args["output_dir"]),
        rgb=bool(args.get("rgb", True)),
        depth=bool(args.get("depth", False)),
        semantic_segmentation=bool(args.get("semantic_segmentation", False)),
    )


def _build_replicator_register_randomizer(
    args: dict[str, Any],
) -> ReplicatorRegisterRandomizerRequest:
    rand_type = args.get("type")
    if rand_type not in ("position", "rotation", "lighting"):
        raise ValueError(
            "replicator.register_randomizer type must be "
            "position|rotation|lighting"
        )
    if not args.get("target"):
        raise ValueError("replicator.register_randomizer requires target")
    return ReplicatorRegisterRandomizerRequest(
        type=rand_type,  # type: ignore[arg-type]
        target=str(args["target"]),
        config=dict(args.get("config") or {}),
    )


def _build_replicator_trigger_once(
    args: dict[str, Any],
) -> ReplicatorTriggerOnceRequest:
    num_frames = int(args.get("num_frames", 1))
    if num_frames < 1:
        raise ValueError("replicator.trigger_once num_frames must be >= 1")
    return ReplicatorTriggerOnceRequest(num_frames=num_frames)


def _build_replicator_trigger_on_time(
    args: dict[str, Any],
) -> ReplicatorTriggerOnTimeRequest:
    interval_s = float(args["interval_s"])
    if interval_s <= 0:
        raise ValueError("replicator.trigger_on_time interval_s must be > 0")
    return ReplicatorTriggerOnTimeRequest(interval_s=interval_s)


def _build_omnigraph_create_node(
    args: dict[str, Any],
) -> OmnigraphCreateNodeRequest:
    if not args.get("graph_path") or not args.get("node_type"):
        raise ValueError(
            "omnigraph.create_node requires graph_path and node_type"
        )
    return OmnigraphCreateNodeRequest(
        graph_path=str(args["graph_path"]),
        node_type=str(args["node_type"]),
        node_name=args.get("node_name"),
    )


def _build_omnigraph_connect(args: dict[str, Any]) -> OmnigraphConnectRequest:
    if not args.get("src_attr") or not args.get("dst_attr"):
        raise ValueError("omnigraph.connect requires src_attr and dst_attr")
    return OmnigraphConnectRequest(
        src_attr=str(args["src_attr"]),
        dst_attr=str(args["dst_attr"]),
    )


def _build_omnigraph_execute(args: dict[str, Any]) -> OmnigraphExecuteRequest:
    if not args.get("graph_path"):
        raise ValueError("omnigraph.execute requires graph_path")
    return OmnigraphExecuteRequest(graph_path=str(args["graph_path"]))


def _build_omnigraph_create_ros2_publisher(
    args: dict[str, Any],
) -> OmnigraphCreateRos2PublisherRequest:
    for field_name in ("graph_path", "topic", "source_prim"):
        if not args.get(field_name):
            raise ValueError(
                f"omnigraph.create_ros2_publisher requires {field_name}"
            )
    return OmnigraphCreateRos2PublisherRequest(
        graph_path=str(args["graph_path"]),
        topic=str(args["topic"]),
        source_prim=str(args["source_prim"]),
        msg_type=str(args.get("msg_type", "sensor_msgs/msg/Image")),
    )


def _build_omnigraph_create_script_controller(
    args: dict[str, Any],
) -> OmnigraphCreateScriptControllerRequest:
    for field_name in ("graph_path", "script_path"):
        if not args.get(field_name):
            raise ValueError(
                f"omnigraph.create_script_controller requires {field_name}"
            )
    return OmnigraphCreateScriptControllerRequest(
        graph_path=str(args["graph_path"]),
        script_path=str(args["script_path"]),
        node_name=str(args.get("node_name", "ScriptNode")),
        tick_node_name=str(args.get("tick_node_name", "OnPlaybackTick")),
        evaluator=str(args.get("evaluator", "execution")),
        reset_state=bool(args.get("reset_state", True)),
    )


def _build_content_browse(args: dict[str, Any]) -> ContentBrowseRequest:
    if not args.get("url"):
        raise ValueError("content.browse requires url")
    return ContentBrowseRequest(
        url=str(args["url"]),
        recursive=bool(args.get("recursive", False)),
        max_depth=int(args.get("max_depth", 2)),
        max_entries=int(args.get("max_entries", 500)),
    )


def _build_content_preview(args: dict[str, Any]) -> ContentPreviewRequest:
    if not args.get("url"):
        raise ValueError("content.preview requires url")
    return ContentPreviewRequest(url=str(args["url"]))


def _build_content_resolve(args: dict[str, Any]) -> ContentResolveRequest:
    if not args.get("url"):
        raise ValueError("content.resolve requires url")
    return ContentResolveRequest(url=str(args["url"]))


def _build_simulation_set_time(args: dict[str, Any]) -> SimulationSetTimeRequest:
    target = float(args["time_seconds"])
    if target < 0:
        raise ValueError("simulation.set_time time_seconds must be >= 0")
    return SimulationSetTimeRequest(time_seconds=target)


def _build_job_status(args: dict[str, Any]) -> dict[str, Any]:
    """Package job.status args — runner resolves job_id from prior step's
    RobotNavigateResult via ScenarioContext (context-aware action)."""
    if "job_id" not in args and "navigate_step_id" not in args:
        raise KeyError(
            "job.status requires either 'job_id' (literal) or "
            "'navigate_step_id' (prior robot.navigate_to step id)"
        )
    return {
        "job_id": args.get("job_id"),
        "navigate_step_id": args.get("navigate_step_id"),
        "expected_status": args.get("expected_status"),
        "poll_interval_s": float(args.get("poll_interval_s", 0.5)),
        "max_polls": int(args.get("max_polls", 60)),
    }


_REGISTRY: dict[tuple[ModuleName, str], Any] = {
    # READ / ASSERT
    (ModuleName.STAGE, "capture_snapshot"): _build_capture_filter,
    (ModuleName.STAGE, "assert_prim_exists"): _build_prim_existence_assertion,
    (ModuleName.STAGE, "assert_property"): _build_property_assertion,
    (ModuleName.STAGE, "diff_snapshots"): _build_diff_snapshots,
    (ModuleName.VIEWPORT, "capture"): _build_viewport_capture,
    (ModuleName.VIEWPORT, "compare_ssim"): _build_ssim_request,
    (ModuleName.LAKEHOUSE, "query"): _build_lakehouse_query,
    (ModuleName.EXTENSION, "trigger"): _build_extension_trigger,
    (ModuleName.EXTENSION, "reset"): _build_extension_reset,
    (ModuleName.ASSET, "external_search"): _build_external_asset_search,
    (ModuleName.ASSET, "external_download"): _build_external_asset_download,
    (ModuleName.ASSET, "external_convert"): _build_external_asset_convert,
    # WRITE — Stage mutations are implemented on SimulationModule
    (ModuleName.SIMULATION, "stage_load_usd"): _build_stage_load_usd,
    (ModuleName.SIMULATION, "stage_set_property"): _build_stage_set_property,
    (ModuleName.SIMULATION, "stage_create_prim"): _build_stage_create_prim,
    (ModuleName.SIMULATION, "stage_delete_prim"): _build_stage_delete_prim,
    # Robot (Phase B) — get_joint_positions uses **kwargs fallback (single str arg)
    (ModuleName.ROBOT, "load"): _build_robot_load,
    (ModuleName.ROBOT, "set_joint_positions"): _build_set_joint_positions,
    (ModuleName.ROBOT, "navigate_to"): _build_robot_navigate,
    # Job (Phase B) — context-aware polling + cancel
    (ModuleName.JOB, "status"): _build_job_status,
    # Character (Phase C) — get_state uses **kwargs fallback (single str arg, matches robot.get_joint_positions)
    (ModuleName.CHARACTER, "load"): _build_character_load,
    (ModuleName.CHARACTER, "play_animation"): _build_character_play_animation,
    (ModuleName.CHARACTER, "set_position"): _build_character_set_position,
    (ModuleName.CHARACTER, "stop_animation"): _build_character_stop_animation,
    (ModuleName.CHARACTER, "navigate_to"): _build_character_navigate,
    # Window (Phase E) — list_windows / list_ui_windows / list_menu_items / trigger_menu / show_ui_window
    # all use **kwargs fallback (simple str / bool params)
    (ModuleName.WINDOW, "capture"): _build_window_capture,
    # Navigation (Phase E) — bake / add_exclude_volume use **kwargs fallback; query_path is typed
    (ModuleName.NAVIGATION, "query_path"): _build_nav_query_path,
    (ModuleName.NAVIGATION, "set_visualization"): _build_nav_set_visualization,
    (ModuleName.NAVIGATION, "sample_walkable_points"): _build_navigation_sample_walkable,
    # Sensor (Phase E) — RTX Camera / Lidar / Depth Camera attach + viz toggle
    (ModuleName.SENSOR, "attach_rtx_camera"): _build_sensor_attach_rtx_camera,
    (ModuleName.SENSOR, "attach_rtx_lidar"): _build_sensor_attach_rtx_lidar,
    (ModuleName.SENSOR, "attach_rtx_depth_camera"): _build_sensor_attach_rtx_depth_camera,
    (ModuleName.SENSOR, "set_visualization"): _build_sensor_set_visualization,
    # Viewport multi (Phase E) — create / destroy
    (ModuleName.VIEWPORT, "create"): _build_viewport_create,
    (ModuleName.VIEWPORT, "destroy"): _build_viewport_destroy,
    # Phase F — Physics / Lighting / Material / Render extension
    (ModuleName.PHYSICS, "apply_rigid_body"): _build_physics_apply_rigid_body,
    (ModuleName.PHYSICS, "apply_collider"): _build_physics_apply_collider,
    (ModuleName.PHYSICS, "apply_material"): _build_physics_apply_material,
    (ModuleName.PHYSICS, "create_joint"): _build_physics_create_joint,
    (ModuleName.PHYSICS, "set_scene"): _build_physics_set_scene,
    (ModuleName.PHYSICS, "visualize"): _build_physics_visualize,
    (ModuleName.LIGHTING, "create_dome"): _build_lighting_create_dome,
    (ModuleName.LIGHTING, "create_distant"): _build_lighting_create_distant,
    (ModuleName.LIGHTING, "create_disk"): _build_lighting_create_disk,
    (ModuleName.LIGHTING, "create_rect"): _build_lighting_create_rect,
    (ModuleName.LIGHTING, "create_sphere"): _build_lighting_create_sphere,
    (ModuleName.LIGHTING, "set_exposure"): _build_lighting_set_exposure,
    (ModuleName.MATERIAL, "list_mdl"): _build_material_list_mdl,
    (ModuleName.MATERIAL, "assign_mdl"): _build_material_assign_mdl,
    (ModuleName.MATERIAL, "get_bound"): _build_material_get_bound,
    (ModuleName.VIEWPORT, "set_render_mode"): _build_viewport_set_render_mode,
    (ModuleName.VIEWPORT, "set_render_quality"): _build_viewport_set_render_quality,
    (ModuleName.VIEWPORT, "toggle_overlay"): _build_viewport_toggle_overlay,
    (ModuleName.VIEWPORT, "set_fov"): _build_viewport_set_fov,
    # Phase G — Robot / Character / Sensor / Simulation extensions
    (ModuleName.ROBOT, "navigate_path"): _build_robot_navigate_path,
    (ModuleName.ROBOT, "gripper_control"): _build_robot_gripper_control,
    (ModuleName.ROBOT, "set_ee_target"): _build_robot_set_ee_target,
    (ModuleName.ROBOT, "run_franka_pick_place"): _build_robot_run_franka_pick_place,
    (ModuleName.ROBOT, "drive_physics"): _build_robot_drive_physics,
    (ModuleName.CHARACTER, "play_animation_variant"): _build_character_play_animation_variant,
    (ModuleName.CHARACTER, "load_crowd"): _build_character_load_crowd,
    (ModuleName.SENSOR, "attach_contact"): _build_sensor_attach_contact,
    (ModuleName.SENSOR, "attach_imu"): _build_sensor_attach_imu,
    (ModuleName.SENSOR, "set_annotator"): _build_sensor_set_annotator,
    (ModuleName.SIMULATION, "step"): _build_simulation_step,
    (ModuleName.SIMULATION, "set_time"): _build_simulation_set_time,
    # Phase H — Replicator / OmniGraph / Content
    (ModuleName.REPLICATOR, "create_writer"): _build_replicator_create_writer,
    (ModuleName.REPLICATOR, "register_randomizer"): _build_replicator_register_randomizer,
    (ModuleName.REPLICATOR, "trigger_once"): _build_replicator_trigger_once,
    (ModuleName.REPLICATOR, "trigger_on_time"): _build_replicator_trigger_on_time,
    (ModuleName.OMNIGRAPH, "create_node"): _build_omnigraph_create_node,
    (ModuleName.OMNIGRAPH, "connect"): _build_omnigraph_connect,
    (ModuleName.OMNIGRAPH, "execute"): _build_omnigraph_execute,
    (ModuleName.OMNIGRAPH, "create_ros2_publisher"): _build_omnigraph_create_ros2_publisher,
    (ModuleName.OMNIGRAPH, "create_script_controller"): _build_omnigraph_create_script_controller,
    (ModuleName.CONTENT, "browse"): _build_content_browse,
    (ModuleName.CONTENT, "preview"): _build_content_preview,
    (ModuleName.CONTENT, "resolve"): _build_content_resolve,
}


CONTEXT_AWARE_ACTIONS: set[tuple[ModuleName, str]] = {
    (ModuleName.STAGE, "diff_snapshots"),
    (ModuleName.JOB, "status"),
}
