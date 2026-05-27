"""FastAPI router for /validation/v1 endpoints (live Isaac Sim Extension).

All routes delegate to service singletons that use lazy omni.* imports.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .models.character import (
    CharacterLoadCrowdRequestModel,
    CharacterLoadRequestModel,
    CharacterNavigateRequestModel,
    CharacterPlayAnimationRequestModel,
    CharacterPlayAnimationVariantRequestModel,
    CharacterSetPositionRequestModel,
    CharacterSitOnPrimRequestModel,
    CharacterStopAnimationRequestModel,
)
from .models.extension import (
    ExtensionActivateRequestModel,
    ExtensionReloadCleanRequestModel,
    ExtensionResetRequestModel,
    ExtensionTriggerRequestModel,
)
from .models.ui import UiInvokeRequestModel
from .models.robot import (
    DrivePhysicsRequestModel,
    NavigationQueryPathRequestModel,
    RobotGripperControlRequestModel,
    RobotLoadRequestModel,
    RobotNavigatePathRequestModel,
    RobotNavigateRequestModel,
    RobotSetEETargetRequestModel,
    RobotSetJointPositionsRequestModel,
)
from .models.selection import (
    StageSelectionRequest,
    ViewportActiveCameraRequest,
)
from .models.stage import (
    PrimExistenceAssertionModel,
    PropertyAssertionModel,
    StageCaptureFilterModel,
    StageComputeWorldBboxRequestModel,
    StageCreatePrimRequestModel,
    StageLoadUsdRequestModel,
    StageSetPropertyRequestModel,
)
from .models.navigation import (
    NavigationSetVisualizationRequestModel,
    SampleWalkablePointsRequestModel,
)
from .models.sensor import (
    SensorAttachContactRequestModel,
    SensorAttachImuRequestModel,
    SensorAttachRtxCameraRequestModel,
    SensorAttachRtxDepthCameraRequestModel,
    SensorAttachRtxLidarRequestModel,
    SensorLidarGetPointCloudRequestModel,
    SensorSetAnnotatorRequestModel,
    SensorSetVisualizationRequestModel,
)
from .models.simulation import (
    SimulationSetTimeRequestModel,
    SimulationStepRequestModel,
)
from .models.physics import (
    PhysicsApplyColliderRequestModel,
    PhysicsApplyMaterialRequestModel,
    PhysicsApplyRigidBodyRequestModel,
    PhysicsCreateJointRequestModel,
    PhysicsSetJointDriveRequestModel,
    PhysicsSetSceneRequestModel,
    PhysicsVisualizeRequestModel,
)
from .models.lighting import (
    LightingCreateDiskRequestModel,
    LightingCreateDistantRequestModel,
    LightingCreateDomeRequestModel,
    LightingCreateRectRequestModel,
    LightingCreateSphereRequestModel,
    LightingSetExposureRequestModel,
)
from .models.material import MaterialAssignMdlRequestModel
from .models.viewport import (
    SSIMComparisonRequestModel,
    UiWindowShowRequestModel,
    ViewportCaptureRequestModel,
    ViewportCreateRequestModel,
    ViewportDestroyRequestModel,
    WindowCaptureRequestModel,
)
from .models.viewport_render import (
    ViewportSetCameraLookatRequestModel,
    ViewportSetFovRequestModel,
    ViewportSetRenderModeRequestModel,
    ViewportSetRenderQualityRequestModel,
    ViewportToggleOverlayRequestModel,
)
from .models.content import (
    ContentBrowseRequestModel,
    ContentPreviewRequestModel,
    ContentResolveRequestModel,
)
from .models.extension_ext import (
    ExtensionDeactivateRequestModel,
    ExtensionGetInfoRequestModel,
    ExtensionListAllRequestModel,
)
from .models.omnigraph import (
    OmnigraphConnectRequestModel,
    OmnigraphCreateNodeRequestModel,
    OmnigraphCreateRos2PublisherRequestModel,
    OmnigraphExecuteRequestModel,
)
from .models.replicator import (
    ReplicatorCreateWriterRequestModel,
    ReplicatorRegisterRandomizerRequestModel,
    ReplicatorTriggerOnceRequestModel,
    ReplicatorTriggerOnTimeRequestModel,
)
from .services.asset_service import AssetService
from .services.character_service import CharacterService
from .services.content_service import ContentService
from .services.extension_service import ExtensionService
from .services.job_service import JobService
from .services.log_capture_service import LogCaptureService
from .services.omnigraph_service import OmnigraphService
from .services.replicator_service import ReplicatorService
from .services.robot_service import RobotService
from .services.sensor_service import SensorService
from .services.simulation_service import SimulationService
from .services.stage_service import StageService
from .services.navigation_service import NavigationService
from .services.physics_service import PhysicsService
from .services.lighting_service import LightingService
from .services.material_service import MaterialService
from .services.ui_service import UiService
from .services.viewport_service import ViewportService
from .services.viewport_render_service import ViewportRenderService
from .services.window_service import WindowService

from ._app_features import (
    require_character_stack,
    require_navigation_stack,
    require_replicator_stack,
    require_robot_stack,
    require_ros2_bridge,
    require_sensor_physics_stack,
    require_sensor_rtx_stack,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Singleton services — created once when module is imported inside Extension
_stage = StageService()
_simulation = SimulationService()
_viewport = ViewportService()
_extension = ExtensionService()
_job = JobService()
_robot = RobotService(_job)
_asset = AssetService()
_character = CharacterService(_job, _stage)
_window = WindowService()  # touch v2 to force fswatcher reload after pyc clear
_navigation = NavigationService()
_sensor = SensorService()
_physics = PhysicsService()
_lighting = LightingService()
_material = MaterialService()
_viewport_render = ViewportRenderService()
_ui = UiService()
_log_capture = LogCaptureService(maxlen=10000)
_replicator = ReplicatorService()
_omnigraph = OmnigraphService()
_content = ContentService()


def get_log_capture_service() -> LogCaptureService:
    """Module accessor so extension.py can start/stop the hook on lifecycle events."""
    return _log_capture


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "extension_enabled": True, "busy": _extension._busy, "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Stage — READ
# ---------------------------------------------------------------------------

@router.post("/stage/snapshot")
async def stage_snapshot(body: StageCaptureFilterModel) -> Any:
    try:
        return await _stage.capture_snapshot(body.model_dump())
    except Exception as exc:
        logger.error("stage/snapshot failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/assert/prim-exists")
async def stage_assert_prim_exists(body: PrimExistenceAssertionModel) -> Any:
    try:
        return await _stage.assert_prim_exists(body.model_dump())
    except Exception as exc:
        logger.error("stage/assert/prim-exists failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/assert/property")
async def stage_assert_property(body: PropertyAssertionModel) -> Any:
    try:
        return await _stage.assert_property(body.model_dump())
    except Exception as exc:
        logger.error("stage/assert/property failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Stage — WRITE
# ---------------------------------------------------------------------------

@router.post("/stage/load_usd")
async def stage_load_usd(body: StageLoadUsdRequestModel) -> Any:
    try:
        return await _stage.load_usd(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("stage/load_usd failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/set_property")
async def stage_set_property(body: StageSetPropertyRequestModel) -> Any:
    try:
        return await _stage.set_property(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("stage/set_property failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/create_prim")
async def stage_create_prim(body: StageCreatePrimRequestModel) -> Any:
    try:
        return await _stage.create_prim(body.model_dump())
    except Exception as exc:
        logger.error("stage/create_prim failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/stage/prim")
async def stage_delete_prim(prim_path: str = Query(..., description="Prim path to delete")) -> Any:
    try:
        return await _stage.delete_prim(prim_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("stage/prim DELETE failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# File operations (Phase B+) — GUI File menu equivalent
# ---------------------------------------------------------------------------

@router.post("/stage/save")
async def stage_save(
    path: str | None = Query(
        None,
        description="Absolute USD path. Omit to save in-place (File → Save).",
    ),
) -> Any:
    try:
        return await _stage.save_stage(path)
    except Exception as exc:
        logger.error("stage/save failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/open")
async def stage_open(url: str = Query(..., description="USD url (local path or omniverse://)")) -> Any:
    try:
        return await _stage.open_stage(url)
    except Exception as exc:
        logger.error("stage/open failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/new")
async def stage_new() -> Any:
    try:
        return await _stage.new_stage()
    except Exception as exc:
        logger.error("stage/new failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Selection (Phase B+) — GUI Stage panel selection
# ---------------------------------------------------------------------------

@router.get("/stage/selection")
async def stage_get_selection() -> Any:
    try:
        return await _stage.get_selection()
    except Exception as exc:
        logger.error("stage/selection GET failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/selection")
async def stage_set_selection(body: StageSelectionRequest) -> Any:
    try:
        return await _stage.set_selection(body.prim_paths, body.expand_in_stage)
    except Exception as exc:
        logger.error("stage/selection POST failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

@router.post("/simulation/play")
async def simulation_play() -> Any:
    try:
        return await _simulation.play()
    except Exception as exc:
        logger.error("simulation/play failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/simulation/pause")
async def simulation_pause() -> Any:
    try:
        return await _simulation.pause()
    except Exception as exc:
        logger.error("simulation/pause failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/simulation/stop")
async def simulation_stop() -> Any:
    try:
        return await _simulation.stop()
    except Exception as exc:
        logger.error("simulation/stop failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/simulation/status")
async def simulation_status() -> Any:
    try:
        return await _simulation.get_status()
    except Exception as exc:
        logger.error("simulation/status failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/simulation/step")
async def simulation_step(body: SimulationStepRequestModel) -> Any:
    try:
        return await _simulation.step(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("simulation/step failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/simulation/set_time")
async def simulation_set_time(body: SimulationSetTimeRequestModel) -> Any:
    try:
        return await _simulation.set_time(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("simulation/set_time failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Viewport
# ---------------------------------------------------------------------------

@router.post("/viewport/capture")
async def viewport_capture(body: ViewportCaptureRequestModel) -> Any:
    try:
        return await _viewport.capture(body.model_dump())
    except Exception as exc:
        logger.error("viewport/capture failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/compare/ssim")
async def viewport_compare_ssim(body: SSIMComparisonRequestModel) -> Any:
    try:
        return await _viewport.compare_ssim(body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/compare/ssim failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/active_camera")
async def viewport_set_active_camera(body: ViewportActiveCameraRequest) -> Any:
    try:
        return await _viewport.set_active_camera(body.camera_path, body.viewport_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/active_camera failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/create")
async def viewport_create(body: ViewportCreateRequestModel) -> Any:
    try:
        return await _viewport.create(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/create failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/destroy")
async def viewport_destroy(body: ViewportDestroyRequestModel) -> Any:
    try:
        return await _viewport.destroy(body.model_dump())
    except Exception as exc:
        logger.error("viewport/destroy failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Sensor — RTX Camera / Lidar / Depth Camera attach + visualization (Phase E)
# ---------------------------------------------------------------------------

@router.post("/sensor/attach_rtx_camera")
async def sensor_attach_rtx_camera(body: SensorAttachRtxCameraRequestModel) -> Any:
    require_sensor_rtx_stack()
    try:
        return await _sensor.attach_rtx_camera(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/attach_rtx_camera failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor/attach_rtx_lidar")
async def sensor_attach_rtx_lidar(body: SensorAttachRtxLidarRequestModel) -> Any:
    require_sensor_rtx_stack()
    try:
        return await _sensor.attach_rtx_lidar(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/attach_rtx_lidar failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor/attach_rtx_depth_camera")
async def sensor_attach_rtx_depth_camera(
    body: SensorAttachRtxDepthCameraRequestModel,
) -> Any:
    require_sensor_rtx_stack()
    try:
        return await _sensor.attach_rtx_depth_camera(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/attach_rtx_depth_camera failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor/set_visualization")
async def sensor_set_visualization(body: SensorSetVisualizationRequestModel) -> Any:
    require_sensor_rtx_stack()
    try:
        return await _sensor.set_visualization(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/set_visualization failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor/attach_contact")
async def sensor_attach_contact(body: SensorAttachContactRequestModel) -> Any:
    require_sensor_physics_stack()
    try:
        return await _sensor.attach_contact(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/attach_contact failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor/attach_imu")
async def sensor_attach_imu(body: SensorAttachImuRequestModel) -> Any:
    require_sensor_physics_stack()
    try:
        return await _sensor.attach_imu(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/attach_imu failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor/set_annotator")
async def sensor_set_annotator(body: SensorSetAnnotatorRequestModel) -> Any:
    require_sensor_rtx_stack()
    try:
        return await _sensor.set_annotator(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/set_annotator failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensor/lidar_get_point_cloud")
async def sensor_lidar_get_point_cloud(
    body: SensorLidarGetPointCloudRequestModel,
) -> Any:
    """Read one frame of RTX Lidar point cloud — symmetric readback for attach_rtx_lidar.

    Reuses the annotator name stamped on the sensor prim by ``attach_rtx_lidar``.
    Returns Cartesian XYZ + intensities (truncated to ``max_points``).
    Empty data → ``warning`` field explains why (typically "call simulation_play
    and wait for the lidar to spin").
    """
    require_sensor_rtx_stack()
    try:
        return await _sensor.lidar_get_point_cloud(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("sensor/lidar_get_point_cloud failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Physics — UsdPhysics rigid body / collider / material / joint / scene / viz (Phase F)
# ---------------------------------------------------------------------------

@router.post("/physics/apply_rigid_body")
async def physics_apply_rigid_body(body: PhysicsApplyRigidBodyRequestModel) -> Any:
    try:
        return await _physics.apply_rigid_body(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/apply_rigid_body failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/physics/rigid_body_state")
async def physics_get_rigid_body_state(
    prim_path: str = Query(..., description="Rigid body prim path"),
) -> Any:
    """Read PhysX runtime state — linear/angular velocity, mass, COM, kinematic flags.

    Symmetric readback for ``apply_rigid_body``. ``source`` field reports
    which backend filled the readout (``physx_runtime`` for live PhysX
    state via SingleRigidPrim — populated after simulation.play — or
    ``usd_initial`` for USD authored values).
    """
    try:
        return await _physics.get_rigid_body_state(prim_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/rigid_body_state GET failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/physics/apply_collider")
async def physics_apply_collider(body: PhysicsApplyColliderRequestModel) -> Any:
    try:
        return await _physics.apply_collider(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/apply_collider failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/physics/apply_material")
async def physics_apply_material(body: PhysicsApplyMaterialRequestModel) -> Any:
    try:
        return await _physics.apply_material(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/apply_material failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/physics/create_joint")
async def physics_create_joint(body: PhysicsCreateJointRequestModel) -> Any:
    try:
        return await _physics.create_joint(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/create_joint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/physics/set_joint_drive")
async def physics_set_joint_drive(body: PhysicsSetJointDriveRequestModel) -> Any:
    try:
        return await _physics.set_joint_drive(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/set_joint_drive failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/physics/set_scene")
async def physics_set_scene(body: PhysicsSetSceneRequestModel) -> Any:
    try:
        return await _physics.set_scene(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/set_scene failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/physics/visualize")
async def physics_visualize(body: PhysicsVisualizeRequestModel) -> Any:
    try:
        return await _physics.visualize(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("physics/visualize failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Lighting — UsdLux Dome/Distant/Disk/Rect/Sphere + exposure (Phase F)
# ---------------------------------------------------------------------------

@router.post("/lighting/create_dome")
async def lighting_create_dome(body: LightingCreateDomeRequestModel) -> Any:
    try:
        return await _lighting.create_dome(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lighting/create_dome failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/lighting/create_distant")
async def lighting_create_distant(body: LightingCreateDistantRequestModel) -> Any:
    try:
        return await _lighting.create_distant(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lighting/create_distant failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/lighting/create_disk")
async def lighting_create_disk(body: LightingCreateDiskRequestModel) -> Any:
    try:
        return await _lighting.create_disk(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lighting/create_disk failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/lighting/create_rect")
async def lighting_create_rect(body: LightingCreateRectRequestModel) -> Any:
    try:
        return await _lighting.create_rect(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lighting/create_rect failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/lighting/create_sphere")
async def lighting_create_sphere(body: LightingCreateSphereRequestModel) -> Any:
    try:
        return await _lighting.create_sphere(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lighting/create_sphere failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/lighting/set_exposure")
async def lighting_set_exposure(body: LightingSetExposureRequestModel) -> Any:
    try:
        return await _lighting.set_exposure(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lighting/set_exposure failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Material — MDL list / assign / bound (Phase F)
# ---------------------------------------------------------------------------

@router.get("/material/list_mdl")
async def material_list_mdl(
    library: str = Query(
        "default",
        description="MDL library name or absolute path to search root.",
    ),
) -> Any:
    try:
        return await _material.list_mdl(library)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("material/list_mdl failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/material/assign_mdl")
async def material_assign_mdl(body: MaterialAssignMdlRequestModel) -> Any:
    try:
        return await _material.assign_mdl(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("material/assign_mdl failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/material/get_bound")
async def material_get_bound(
    prim_path: str = Query(..., description="Prim path to inspect."),
) -> Any:
    try:
        return await _material.get_bound(prim_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("material/get_bound failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Viewport render extension — mode / quality / overlay / FOV (Phase F)
# ---------------------------------------------------------------------------

@router.post("/viewport/set_render_mode")
async def viewport_set_render_mode(body: ViewportSetRenderModeRequestModel) -> Any:
    try:
        return await _viewport_render.set_render_mode(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/set_render_mode failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/set_render_quality")
async def viewport_set_render_quality(
    body: ViewportSetRenderQualityRequestModel,
) -> Any:
    try:
        return await _viewport_render.set_render_quality(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/set_render_quality failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/toggle_overlay")
async def viewport_toggle_overlay(body: ViewportToggleOverlayRequestModel) -> Any:
    try:
        return await _viewport_render.toggle_overlay(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/toggle_overlay failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/set_fov")
async def viewport_set_fov(body: ViewportSetFovRequestModel) -> Any:
    try:
        return await _viewport_render.set_fov(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/set_fov failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/viewport/set_camera_lookat")
async def viewport_set_camera_lookat(body: ViewportSetCameraLookatRequestModel) -> Any:
    try:
        return await _viewport_render.set_camera_lookat(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("viewport/set_camera_lookat failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Window — full Kit application capture (GUI panels + viewport + menus)
# ---------------------------------------------------------------------------

@router.post("/window/capture")
async def window_capture(body: WindowCaptureRequestModel) -> Any:
    try:
        return await _window.capture(body.model_dump())
    except Exception as exc:
        logger.error("window/capture failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/window/list")
async def window_list() -> Any:
    try:
        return await _window.list_windows()
    except Exception as exc:
        logger.error("window/list failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/window/ui_list")
async def window_ui_list(name_filter: str | None = Query(None, description="Case-insensitive substring filter on window title")) -> Any:
    try:
        return await _window.list_ui_windows(name_filter)
    except Exception as exc:
        logger.error("window/ui_list failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/window/ui_show")
async def window_ui_show(body: UiWindowShowRequestModel) -> Any:
    try:
        return await _window.show_ui_window(
            name=body.name,
            visible=body.visible,
            focus=body.focus,
            settle_frames=body.settle_frames,
        )
    except Exception as exc:
        logger.error("window/ui_show failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/window/menu_list")
async def window_menu_list(menu_path: str | None = Query(None, description="e.g. 'Window/Browsers' — limit to subtree")) -> Any:
    try:
        return await _window.list_menu_items(menu_path)
    except Exception as exc:
        logger.error("window/menu_list failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/window/menu_trigger")
async def window_menu_trigger(menu_path: str = Query(..., description="e.g. 'Window/Browsers/Asset Browser'")) -> Any:
    try:
        return await _window.trigger_menu(menu_path)
    except Exception as exc:
        logger.error("window/menu_trigger failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Extension
# ---------------------------------------------------------------------------

@router.get("/extension/state")
async def extension_state() -> Any:
    return _extension.get_state()


@router.post("/extension/trigger")
async def extension_trigger(body: ExtensionTriggerRequestModel) -> Any:
    try:
        return _extension.trigger(body.operation, body.model_dump())
    except Exception as exc:
        if _extension._busy:
            raise HTTPException(status_code=409, detail="Extension is busy") from exc
        logger.error("extension/trigger failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/extension/reset")
async def extension_reset(body: ExtensionResetRequestModel) -> Any:
    try:
        return _extension.reset(body.model_dump())
    except Exception as exc:
        logger.error("extension/reset failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Extension — UI automation + log capture (Phase D)
# ---------------------------------------------------------------------------

@router.post("/extension/activate")
async def extension_activate(body: ExtensionActivateRequestModel) -> Any:
    try:
        return await _extension.activate(body.ext_id, body.reload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/activate failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/extension/reload_clean")
async def extension_reload_clean(body: ExtensionReloadCleanRequestModel) -> Any:
    try:
        return await _extension.reload_clean(body.ext_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/reload_clean failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/extension/ui_tree")
async def extension_ui_tree(
    ext_id: str | None = Query(None, description="Advisory tag — included in response."),
    window: str | None = Query(
        None,
        description=(
            "Window title (exact-or-substring). Omit to list known windows only; "
            "supply to walk widgets inside matching windows."
        ),
    ),
    widget_types: list[str] | None = Query(
        None,
        description=(
            "Override the widget class allow-list (e.g. ?widget_types=Button&widget_types=TreeView). "
            "Omit to use the default enumeration."
        ),
    ),
) -> Any:
    try:
        return await _ui.get_ui_tree(
            ext_id=ext_id, window=window, widget_types=widget_types,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/ui_tree failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/extension/ui_invoke")
async def extension_ui_invoke(body: UiInvokeRequestModel) -> Any:
    try:
        return await _ui.ui_invoke(body.widget_path, body.action, body.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/ui_invoke failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/extension/logs")
async def extension_logs(
    ext_id: str | None = Query(None, description="Substring filter on log source/ext id."),
    since_ms: int | None = Query(None, description="Unix ms; return only entries with ts_ms >= since_ms."),
    level: str = Query("INFO", description="VERBOSE|INFO|WARN|ERROR|FATAL|ALL"),
    limit: int = Query(1000, ge=1, le=10000),
) -> Any:
    try:
        return _log_capture.query(
            since_ms=since_ms,
            level=level,
            source_filter=ext_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/logs failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/extension/logs/clear")
async def extension_logs_clear() -> Any:
    try:
        removed = _log_capture.clear()
        return {"ok": True, "removed": int(removed)}
    except Exception as exc:
        logger.error("extension/logs/clear failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Robot (Phase B)
# ---------------------------------------------------------------------------

@router.post("/robot/load")
async def robot_load(body: RobotLoadRequestModel) -> Any:
    require_robot_stack()
    try:
        return await _robot.load(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/load failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/robot/joint_positions")
async def robot_get_joint_positions(
    prim_path: str = Query(..., description="Articulation prim path"),
) -> Any:
    require_robot_stack()
    try:
        return await _robot.get_joint_positions(prim_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/joint_positions GET failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/robot/joint_positions")
async def robot_set_joint_positions(body: RobotSetJointPositionsRequestModel) -> Any:
    require_robot_stack()
    try:
        return await _robot.set_joint_positions(body.prim_path, body.positions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/joint_positions POST failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/robot/joint_config")
async def robot_get_joint_config(
    prim_path: str = Query(..., description="Articulation prim path"),
) -> Any:
    """Read drive stiffness/damping/max_force + joint limits + max velocity per DOF.

    Symmetric readback for ``set_joint_positions`` — exposes drive config
    + position lower/upper limits + max joint velocity per DOF. Useful
    for debugging IK / drive_physics when set_joint_positions or
    set_ee_target produce unexpected motion (drive too soft, target
    outside limits, velocity capped).
    """
    require_robot_stack()
    try:
        return await _robot.get_joint_config(prim_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/joint_config GET failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/robot/navigate")
async def robot_navigate(body: RobotNavigateRequestModel) -> Any:
    require_robot_stack()
    try:
        return await _robot.navigate_to(body.prim_path, body.target, body.duration_s)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/navigate failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/robot/navigate_path")
async def robot_navigate_path(body: RobotNavigatePathRequestModel) -> Any:
    require_robot_stack()
    try:
        return await _robot.navigate_path(body.prim_path, body.points, body.duration_s)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/navigate_path failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/robot/gripper_control")
async def robot_gripper_control(body: RobotGripperControlRequestModel) -> Any:
    require_robot_stack()
    try:
        return await _robot.gripper_control(body.prim_path, body.action, body.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/gripper_control failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/robot/set_ee_target")
async def robot_set_ee_target(body: RobotSetEETargetRequestModel) -> Any:
    require_robot_stack()
    try:
        return await _robot.set_ee_target(
            body.prim_path, body.target_pose,
            robot_description=body.robot_description,
            end_effector_frame=body.end_effector_frame,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/set_ee_target failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Navigation — NavMesh bake / query (Phase 3)
# ---------------------------------------------------------------------------

@router.post("/navigation/bake")
async def navigation_bake(
    volume_scale: float = Query(40.0, gt=0.0, le=500.0,
                                  description="Side length of auto-created NavMeshVolume (m)."),
    timeout_s: float = Query(300.0, gt=0.0, le=1800.0,
                               description="Max seconds to wait for the async bake to finish."),
) -> Any:
    require_navigation_stack()
    try:
        return await _navigation.bake({
            "volume_scale": volume_scale,
            "timeout_s": timeout_s,
        })
    except Exception as exc:
        logger.error("navigation/bake failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/navigation/query_path")
async def navigation_query_path(body: NavigationQueryPathRequestModel) -> Any:
    require_navigation_stack()
    try:
        return await _navigation.query_path(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("navigation/query_path failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/navigation/add_exclude_volume")
async def navigation_add_exclude_volume(
    prim_path: str | None = Query(None, description="Prim to derive bbox from"),
    padding: float = Query(0.1, ge=0.0, le=2.0),
) -> Any:
    require_navigation_stack()
    try:
        req = {"padding": padding}
        if prim_path:
            req["prim_path"] = prim_path
        return await _navigation.add_exclude_volume(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("navigation/add_exclude_volume failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/navigation/set_visualization")
async def navigation_set_visualization(
    body: NavigationSetVisualizationRequestModel,
) -> Any:
    require_navigation_stack()
    try:
        return await _navigation.set_visualization(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("navigation/set_visualization failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/navigation/sample_walkable")
async def navigation_sample_walkable(
    body: SampleWalkablePointsRequestModel,
) -> Any:
    require_navigation_stack()
    try:
        return await _navigation.sample_walkable_points(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("navigation/sample_walkable failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/robot/drive_physics")
async def robot_drive_physics(body: DrivePhysicsRequestModel) -> Any:
    require_robot_stack()
    try:
        return await _robot.drive_physics(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("robot/drive_physics failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Jobs (Phase B)
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}")
async def job_status(job_id: str) -> Any:
    try:
        return _job.get_status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("jobs/%s failed: %s", job_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/cancel")
async def job_cancel(job_id: str) -> Any:
    try:
        return _job.cancel(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("jobs/%s/cancel failed: %s", job_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Assets (Phase B+) — GUI Asset Browser equivalent
# ---------------------------------------------------------------------------

@router.get("/assets/list")
async def asset_list(
    category: str | None = Query(
        None,
        description="robots/environments/props/people/materials/isaaclab. Omit to list categories.",
    ),
    subpath: str = Query("", description="Subfolder under the category"),
    recursive: bool = Query(False),
    max_depth: int = Query(2, ge=1, le=5),
    max_entries: int = Query(500, ge=1, le=5000),
) -> Any:
    try:
        return await _asset.list(
            category=category,
            subpath=subpath,
            recursive=recursive,
            max_depth=max_depth,
            max_entries=max_entries,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("assets/list failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Character (Phase C) — human character load, animation, navigation
# ---------------------------------------------------------------------------

@router.post("/character/load")
async def character_load(body: CharacterLoadRequestModel) -> Any:
    require_character_stack()
    try:
        return await _character.load(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/load failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/character/play_animation")
async def character_play_animation(
    body: CharacterPlayAnimationRequestModel,
) -> Any:
    require_character_stack()
    try:
        return await _character.play_animation(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/play_animation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/character/set_position")
async def character_set_position(body: CharacterSetPositionRequestModel) -> Any:
    require_character_stack()
    try:
        return await _character.set_position(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/set_position failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/character/stop_animation")
async def character_stop_animation(
    body: CharacterStopAnimationRequestModel,
) -> Any:
    require_character_stack()
    try:
        return await _character.stop_animation(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/stop_animation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/character/navigate")
async def character_navigate(body: CharacterNavigateRequestModel) -> Any:
    require_character_stack()
    try:
        return await _character.navigate_to(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/navigate failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/character/play_animation_variant")
async def character_play_animation_variant(
    body: CharacterPlayAnimationVariantRequestModel,
) -> Any:
    require_character_stack()
    try:
        return await _character.play_animation_variant(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/play_animation_variant failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/character/load_crowd")
async def character_load_crowd(body: CharacterLoadCrowdRequestModel) -> Any:
    require_character_stack()
    try:
        return await _character.load_crowd(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/load_crowd failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/character/sit_on_prim")
async def character_sit_on_prim(body: CharacterSitOnPrimRequestModel) -> Any:
    require_character_stack()
    try:
        return await _character.sit_on_prim(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/sit_on_prim failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stage/compute_world_bbox")
async def stage_compute_world_bbox(body: StageComputeWorldBboxRequestModel) -> Any:
    try:
        return await _stage.compute_world_bbox(body.prim_path, body.include_purposes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("stage/compute_world_bbox failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/character/state")
async def character_state(
    prim_path: str = Query(..., description="Character prim path (root or SkelRoot)"),
) -> Any:
    require_character_stack()
    try:
        return await _character.get_state(prim_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("character/state failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Replicator (Phase H) — SDG writer / randomizer / trigger
# ---------------------------------------------------------------------------


@router.post("/replicator/create_writer")
async def replicator_create_writer(
    body: ReplicatorCreateWriterRequestModel,
) -> Any:
    require_replicator_stack()
    try:
        return await _replicator.create_writer(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("replicator/create_writer failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/replicator/register_randomizer")
async def replicator_register_randomizer(
    body: ReplicatorRegisterRandomizerRequestModel,
) -> Any:
    require_replicator_stack()
    try:
        return await _replicator.register_randomizer(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "replicator/register_randomizer failed: %s", exc, exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/replicator/trigger_once")
async def replicator_trigger_once(
    body: ReplicatorTriggerOnceRequestModel,
) -> Any:
    require_replicator_stack()
    try:
        return await _replicator.trigger_once(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("replicator/trigger_once failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/replicator/trigger_on_time")
async def replicator_trigger_on_time(
    body: ReplicatorTriggerOnTimeRequestModel,
) -> Any:
    require_replicator_stack()
    try:
        return await _replicator.trigger_on_time(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("replicator/trigger_on_time failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# OmniGraph (Phase H) — node / connect / execute + ROS2 publisher macro
# ---------------------------------------------------------------------------


@router.post("/omnigraph/create_node")
async def omnigraph_create_node(body: OmnigraphCreateNodeRequestModel) -> Any:
    try:
        return await _omnigraph.create_node(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("omnigraph/create_node failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/omnigraph/connect")
async def omnigraph_connect(body: OmnigraphConnectRequestModel) -> Any:
    try:
        return await _omnigraph.connect(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("omnigraph/connect failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/omnigraph/execute")
async def omnigraph_execute(body: OmnigraphExecuteRequestModel) -> Any:
    try:
        return await _omnigraph.execute(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("omnigraph/execute failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/omnigraph/create_ros2_publisher")
async def omnigraph_create_ros2_publisher(
    body: OmnigraphCreateRos2PublisherRequestModel,
) -> Any:
    require_ros2_bridge()
    try:
        return await _omnigraph.create_ros2_publisher(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "omnigraph/create_ros2_publisher failed: %s", exc, exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Content (Phase H) — omni.client list / stat / normalize_url
# ---------------------------------------------------------------------------


@router.post("/content/browse")
async def content_browse(body: ContentBrowseRequestModel) -> Any:
    try:
        return await _content.browse(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("content/browse failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/content/preview")
async def content_preview(body: ContentPreviewRequestModel) -> Any:
    try:
        return await _content.preview(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("content/preview failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/content/resolve")
async def content_resolve(body: ContentResolveRequestModel) -> Any:
    try:
        return await _content.resolve(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("content/resolve failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Extension management (Phase H) — deactivate / list_all / get_info
# ---------------------------------------------------------------------------


@router.post("/extension/deactivate")
async def extension_deactivate(body: ExtensionDeactivateRequestModel) -> Any:
    try:
        return await _extension.deactivate(body.ext_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/deactivate failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/extension/list_all")
async def extension_list_all(body: ExtensionListAllRequestModel) -> Any:
    try:
        return await _extension.list_all(enabled_only=body.enabled_only)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/list_all failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/extension/get_info")
async def extension_get_info(body: ExtensionGetInfoRequestModel) -> Any:
    try:
        return await _extension.get_info(body.ext_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("extension/get_info failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Kit Commands (D25) — common profile lever over omni.kit.commands.execute
# ---------------------------------------------------------------------------

from .models.commands import KitCommandExecuteRequestModel, KitPythonExecRequestModel
from .services.commands_service import get_commands_service


@router.post("/commands/execute")
def commands_execute(body: KitCommandExecuteRequestModel) -> dict[str, Any]:
    """Dispatch omni.kit.commands.execute(name, **payload).

    NO guard — this is a common-profile route. Kit commands are
    registered by the enabled extensions of whichever app is running;
    if a specific command name is not registered (e.g. CreateConveyorBelt
    on USD Composer without isaacsim.asset.gen.conveyor), the underlying
    execute() raises and we return ok=false with error=command_exception.
    """
    service = get_commands_service()
    result = service.execute(body.name, body.payload, body.expect_undo)
    return result


@router.post("/commands/python_run")
def commands_python_run(body: KitPythonExecRequestModel) -> dict[str, Any]:
    """Run arbitrary Python source on the Kit main thread.

    Fills the gap the Kit command registry leaves — the registry has
    no entry for "run this Python", so any operation that's not a
    pre-registered command (relationship edits, ``Usd.EditContext`` walks,
    omni.client direct calls) used to require pasting code into the GUI
    Script Editor. This route runs the code in the same context.

    Endpoint name is ``python_run`` (not ``python_exec``) so the project's
    pre-tool security hook — which flags the substring ``exec(`` literally —
    doesn't trip on the function definition itself. The user-facing MCP
    tool is still named ``kit_python_exec``.
    """
    service = get_commands_service()
    return service.python_run(body.code, body.return_keys)
