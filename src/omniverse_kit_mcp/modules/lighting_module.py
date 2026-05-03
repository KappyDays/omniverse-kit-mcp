"""Lighting module — UsdLux Dome/Distant/Disk/Rect/Sphere + exposure (Phase F)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.lighting import (
    LightingCreateDiskRequest,
    LightingCreateDistantRequest,
    LightingCreateDomeRequest,
    LightingCreateRectRequest,
    LightingCreateResult,
    LightingCreateSphereRequest,
    LightingSetExposureRequest,
    LightingSetExposureResult,
)

logger = logging.getLogger(__name__)


class LightingModule:
    """Create UsdLux lights + toggle RTX tonemap exposure."""

    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def create_dome(
        self, meta: OperationMeta, request: LightingCreateDomeRequest,
    ) -> ModuleResult[LightingCreateResult]:
        return await self._create(
            endpoint="dome",
            request_dict={
                "prim_path": request.prim_path,
                "intensity": request.intensity,
                "texture": request.texture,
            },
            expected_type="DomeLight",
            expected_path=request.prim_path,
            expected_intensity=request.intensity,
        )

    async def create_distant(
        self, meta: OperationMeta, request: LightingCreateDistantRequest,
    ) -> ModuleResult[LightingCreateResult]:
        return await self._create(
            endpoint="distant",
            request_dict={
                "prim_path": request.prim_path,
                "intensity": request.intensity,
                "angle_deg": request.angle_deg,
            },
            expected_type="DistantLight",
            expected_path=request.prim_path,
            expected_intensity=request.intensity,
        )

    async def create_disk(
        self, meta: OperationMeta, request: LightingCreateDiskRequest,
    ) -> ModuleResult[LightingCreateResult]:
        return await self._create(
            endpoint="disk",
            request_dict={
                "prim_path": request.prim_path,
                "intensity": request.intensity,
                "radius": request.radius,
            },
            expected_type="DiskLight",
            expected_path=request.prim_path,
            expected_intensity=request.intensity,
        )

    async def create_rect(
        self, meta: OperationMeta, request: LightingCreateRectRequest,
    ) -> ModuleResult[LightingCreateResult]:
        return await self._create(
            endpoint="rect",
            request_dict={
                "prim_path": request.prim_path,
                "intensity": request.intensity,
                "width": request.width,
                "height": request.height,
            },
            expected_type="RectLight",
            expected_path=request.prim_path,
            expected_intensity=request.intensity,
        )

    async def create_sphere(
        self, meta: OperationMeta, request: LightingCreateSphereRequest,
    ) -> ModuleResult[LightingCreateResult]:
        return await self._create(
            endpoint="sphere",
            request_dict={
                "prim_path": request.prim_path,
                "intensity": request.intensity,
                "radius": request.radius,
            },
            expected_type="SphereLight",
            expected_path=request.prim_path,
            expected_intensity=request.intensity,
        )

    async def set_exposure(
        self, meta: OperationMeta, request: LightingSetExposureRequest,
    ) -> ModuleResult[LightingSetExposureResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.lighting_set_exposure(
                {"exposure": request.exposure},
            )
            return ok_result(
                LightingSetExposureResult(
                    ok=bool(raw.get("ok", True)),
                    exposure=float(raw.get("exposure", request.exposure)),
                    setting_path=str(
                        raw.get("setting_path", "/rtx/post/tonemap/exposure"),
                    ),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="LIGHTING_SET_EXPOSURE_ERROR",
            )

    async def _create(
        self,
        *,
        endpoint: str,
        request_dict: dict,
        expected_type: str,
        expected_path: str,
        expected_intensity: float,
    ) -> ModuleResult[LightingCreateResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.lighting_create(endpoint, request_dict)
            extra_raw = raw.get("extra") or {}
            return ok_result(
                LightingCreateResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=str(raw.get("prim_path", expected_path)),
                    light_type=str(raw.get("light_type", expected_type)),
                    intensity=float(raw.get("intensity", expected_intensity)),
                    extra=dict(extra_raw),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc),
                started_ms=started,
                error_code=f"LIGHTING_CREATE_{expected_type.upper()}_ERROR",
            )
