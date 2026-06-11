"""Sensor module — RTX Camera / Lidar / Depth Camera attachment + Debug Draw toggle (Phase E)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.sensor import (
    SensorAttachContactRequest,
    SensorAttachContactResult,
    SensorAttachImuRequest,
    SensorAttachImuResult,
    SensorAttachRtxCameraRequest,
    SensorAttachRtxCameraResult,
    SensorAttachRtxDepthCameraRequest,
    SensorAttachRtxDepthCameraResult,
    SensorAttachRtxLidarRequest,
    SensorAttachRtxLidarResult,
    SensorLidarGetPointCloudRequest,
    SensorLidarGetPointCloudResult,
    SensorSetAnnotatorRequest,
    SensorSetAnnotatorResult,
    SensorSetVisualizationRequest,
    SensorSetVisualizationResult,
)

logger = logging.getLogger(__name__)


class SensorModule:
    """RTX Camera / Lidar / Depth Camera attachment + visualization toggle (Phase E).

    Each attach_* method parents a new sensor prim beneath *robot_prim* at the
    given mount_offset/mount_rotation. `set_visualization` toggles the Debug
    Draw overlay for a previously-attached sensor (Lidar point cloud, Camera
    frustum, Depth grayscale preview).
    """

    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def attach_rtx_camera(
        self, meta: OperationMeta, request: SensorAttachRtxCameraRequest,
    ) -> ModuleResult[SensorAttachRtxCameraResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_attach_rtx_camera({
                "robot_prim": request.robot_prim,
                "mount_offset": list(request.mount_offset),
                "mount_rotation": list(request.mount_rotation),
                "resolution": list(request.resolution),
                "sensor_name": request.sensor_name,
            })
            resolution_raw = raw.get("resolution") or list(request.resolution)
            return ok_result(
                SensorAttachRtxCameraResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim_path=str(raw.get("sensor_prim_path", "")),
                    parent_prim=str(raw.get("parent_prim", request.robot_prim)),
                    sensor_type=str(raw.get("sensor_type", "rtx_camera")),
                    resolution=(int(resolution_raw[0]), int(resolution_raw[1])),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_ATTACH_RTX_CAMERA_ERROR",
            )

    async def attach_rtx_lidar(
        self, meta: OperationMeta, request: SensorAttachRtxLidarRequest,
    ) -> ModuleResult[SensorAttachRtxLidarResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_attach_rtx_lidar({
                "robot_prim": request.robot_prim,
                "mount_offset": list(request.mount_offset),
                "mount_rotation": list(request.mount_rotation),
                "config_preset": request.config_preset,
                "sensor_name": request.sensor_name,
            })
            return ok_result(
                SensorAttachRtxLidarResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim_path=str(raw.get("sensor_prim_path", "")),
                    parent_prim=str(raw.get("parent_prim", request.robot_prim)),
                    sensor_type=str(raw.get("sensor_type", "rtx_lidar")),
                    config_preset=str(raw.get("config_preset", request.config_preset)),
                    annotator=raw.get("annotator"),
                    backend=str(raw.get("backend", "")),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_ATTACH_RTX_LIDAR_ERROR",
            )

    async def attach_rtx_depth_camera(
        self, meta: OperationMeta, request: SensorAttachRtxDepthCameraRequest,
    ) -> ModuleResult[SensorAttachRtxDepthCameraResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_attach_rtx_depth_camera({
                "robot_prim": request.robot_prim,
                "mount_offset": list(request.mount_offset),
                "mount_rotation": list(request.mount_rotation),
                "resolution": list(request.resolution),
                "sensor_name": request.sensor_name,
            })
            resolution_raw = raw.get("resolution") or list(request.resolution)
            return ok_result(
                SensorAttachRtxDepthCameraResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim_path=str(raw.get("sensor_prim_path", "")),
                    parent_prim=str(raw.get("parent_prim", request.robot_prim)),
                    sensor_type=str(raw.get("sensor_type", "rtx_depth_camera")),
                    resolution=(int(resolution_raw[0]), int(resolution_raw[1])),
                    annotator=raw.get("annotator"),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_ATTACH_RTX_DEPTH_CAMERA_ERROR",
            )

    async def attach_contact(
        self, meta: OperationMeta, request: SensorAttachContactRequest,
    ) -> ModuleResult[SensorAttachContactResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_attach_contact({
                "prim_path": request.prim_path,
                "sensor_name": request.sensor_name,
                "frequency": request.frequency,
                "translation": list(request.translation),
                "radius": request.radius,
            })
            translation_raw = raw.get("translation", list(request.translation))
            return ok_result(
                SensorAttachContactResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim_path=str(raw.get("sensor_prim_path", "")),
                    parent_prim=str(raw.get("parent_prim", request.prim_path)),
                    sensor_type=str(raw.get("sensor_type", "contact")),
                    frequency=int(raw.get("frequency", request.frequency)),
                    translation=tuple(float(t) for t in translation_raw),  # type: ignore[arg-type]
                    radius=float(raw.get("radius", request.radius)),
                    backend=str(raw.get("backend", "")),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_ATTACH_CONTACT_ERROR",
            )

    async def attach_imu(
        self, meta: OperationMeta, request: SensorAttachImuRequest,
    ) -> ModuleResult[SensorAttachImuResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_attach_imu({
                "prim_path": request.prim_path,
                "sensor_name": request.sensor_name,
                "frequency": request.frequency,
                "mount_offset": list(request.mount_offset),
                "mount_orientation": list(request.mount_orientation),
            })
            offset_raw = raw.get("mount_offset", list(request.mount_offset))
            orient_raw = raw.get("mount_orientation", list(request.mount_orientation))
            return ok_result(
                SensorAttachImuResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim_path=str(raw.get("sensor_prim_path", "")),
                    parent_prim=str(raw.get("parent_prim", request.prim_path)),
                    sensor_type=str(raw.get("sensor_type", "imu")),
                    frequency=int(raw.get("frequency", request.frequency)),
                    mount_offset=tuple(float(t) for t in offset_raw),  # type: ignore[arg-type]
                    mount_orientation=tuple(float(q) for q in orient_raw),  # type: ignore[arg-type]
                    backend=str(raw.get("backend", "")),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_ATTACH_IMU_ERROR",
            )

    async def set_annotator(
        self, meta: OperationMeta, request: SensorSetAnnotatorRequest,
    ) -> ModuleResult[SensorSetAnnotatorResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_set_annotator({
                "sensor_prim": request.sensor_prim,
                "annotators": list(request.annotators),
                "resolution": list(request.resolution),
            })
            resolution_raw = raw.get("resolution", list(request.resolution))
            skipped = raw.get("skipped") or {}
            skipped_tuple = tuple(str(k) for k in skipped.keys()) if isinstance(
                skipped, dict
            ) else tuple(str(v) for v in skipped)
            return ok_result(
                SensorSetAnnotatorResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim=str(raw.get("sensor_prim", request.sensor_prim)),
                    annotators=tuple(str(a) for a in raw.get("annotators", ())),
                    skipped=skipped_tuple,
                    resolution=(int(resolution_raw[0]), int(resolution_raw[1])),
                    backend=str(raw.get("backend", "")),
                    render_product=raw.get("render_product"),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_SET_ANNOTATOR_ERROR",
            )

    async def lidar_get_point_cloud(
        self, meta: OperationMeta, request: SensorLidarGetPointCloudRequest,
    ) -> ModuleResult[SensorLidarGetPointCloudResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_lidar_get_point_cloud({
                "sensor_prim": request.sensor_prim,
                "max_points": request.max_points,
                "frames_to_wait": request.frames_to_wait,
            })
            points_raw = raw.get("points") or []
            points_tuple = tuple(
                (float(p[0]), float(p[1]), float(p[2])) for p in points_raw
            )
            intensities_raw = raw.get("intensities") or []
            return ok_result(
                SensorLidarGetPointCloudResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim=str(raw.get("sensor_prim", request.sensor_prim)),
                    annotator=str(raw.get("annotator", "")),
                    backend=str(raw.get("backend", "")),
                    num_points=int(raw.get("num_points", len(points_tuple))),
                    points=points_tuple,
                    intensities=tuple(float(i) for i in intensities_raw),
                    truncated=bool(raw.get("truncated", False)),
                    frames_waited=int(raw.get("frames_waited", request.frames_to_wait)),
                    raw_keys=tuple(str(k) for k in raw.get("raw_keys") or ()),
                    warning=raw.get("warning"),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_LIDAR_GET_POINT_CLOUD_ERROR",
            )

    async def set_visualization(
        self, meta: OperationMeta, request: SensorSetVisualizationRequest,
    ) -> ModuleResult[SensorSetVisualizationResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.sensor_set_visualization({
                "sensor_prim": request.sensor_prim,
                "mode": request.mode,
            })
            return ok_result(
                SensorSetVisualizationResult(
                    ok=bool(raw.get("ok", True)),
                    sensor_prim=str(raw.get("sensor_prim", request.sensor_prim)),
                    mode=str(raw.get("mode", request.mode)),
                    sensor_type=raw.get("sensor_type"),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="SENSOR_SET_VISUALIZATION_ERROR",
            )
