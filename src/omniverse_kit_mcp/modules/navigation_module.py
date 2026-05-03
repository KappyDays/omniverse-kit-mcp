"""NavMesh / navigation MCP module."""

from __future__ import annotations

import logging
import time
from typing import Any

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.navigation import (
    NavExcludeVolumeResult,
    NavigationSetVisualizationRequest,
    NavigationSetVisualizationResult,
    NavMeshBakeResult,
    NavPathQueryRequest,
    NavPathResult,
    SampleWalkablePointsRequest,
    SampleWalkablePointsResult,
)

logger = logging.getLogger(__name__)


class NavigationModule:
    """NavMesh bake + path query + exclude-volume helper."""

    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def bake(
        self, meta: OperationMeta,
        volume_scale: float = 40.0, timeout_s: float = 300.0,
    ) -> ModuleResult[NavMeshBakeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.navigation_bake(
                volume_scale=volume_scale, timeout_s=timeout_s,
            )
            result = NavMeshBakeResult(
                ok=bool(raw.get("ok", True)),
                agent_max_radius=raw.get("agent_max_radius"),
                area_count=raw.get("area_count"),
                mesh_signature=raw.get("mesh_signature"),
                volume_prim_path=raw.get("volume_prim_path"),
                volume_created=bool(raw.get("volume_created", False)),
                volume_scale=float(raw.get("volume_scale", volume_scale)),
                detail={k: v for k, v in raw.items() if k not in {
                    "ok", "agent_max_radius", "area_count", "mesh_signature",
                    "volume_prim_path", "volume_created", "volume_scale",
                }},
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="NAVIGATION_BAKE_ERROR",
            )

    async def query_path(
        self, meta: OperationMeta, request: NavPathQueryRequest,
    ) -> ModuleResult[NavPathResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.navigation_query_path(request.to_dict())
            points_raw = raw.get("points") or []
            points = tuple(
                (float(p[0]), float(p[1]), float(p[2]))
                for p in points_raw
                if isinstance(p, (list, tuple)) and len(p) >= 3
            )
            result = NavPathResult(
                ok=bool(raw.get("ok", True)),
                points=points,
                length=float(raw.get("length") or 0.0),
                straight=bool(raw.get("straight", request.straighten)),
                auto_baked=bool(raw.get("auto_baked", False)),
                agent_radius=float(raw.get("agent_radius", request.agent_radius)),
                agent_height=float(raw.get("agent_height", request.agent_height)),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="NAVIGATION_QUERY_PATH_ERROR",
            )

    async def add_exclude_volume(
        self, meta: OperationMeta,
        prim_path: str | None = None, padding: float = 0.1,
    ) -> ModuleResult[NavExcludeVolumeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.navigation_add_exclude_volume(
                prim_path=prim_path, padding=padding,
            )
            bbox_min = raw.get("bbox_min") or [0.0, 0.0, 0.0]
            bbox_max = raw.get("bbox_max") or [0.0, 0.0, 0.0]
            result = NavExcludeVolumeResult(
                ok=bool(raw.get("ok", True)),
                volume_prim_path=str(raw.get("volume_prim_path", "")),
                bbox_min=(float(bbox_min[0]), float(bbox_min[1]), float(bbox_min[2])),
                bbox_max=(float(bbox_max[0]), float(bbox_max[1]), float(bbox_max[2])),
                padding=float(raw.get("padding", padding)),
                source_prim_path=raw.get("source_prim_path"),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="NAVIGATION_EXCLUDE_ERROR",
            )

    async def set_visualization(
        self, meta: OperationMeta, request: NavigationSetVisualizationRequest,
    ) -> ModuleResult[NavigationSetVisualizationResult]:
        """Toggle NavMesh walkable-area / obstacle overlay in the viewport (Phase E).

        mode='walkable' shows the baked NavMesh surface, mode='obstacles' shows
        the NavMesh exclude/obstacle regions, mode='off' hides all overlays.
        Backend defaults to `carb_settings` (toggles the
        `/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh` key);
        the Extension may fall back to DebugDraw API or prim visibility if the
        setting is not honored — response.backend reports which path won.
        """
        started = int(time.time() * 1000)
        try:
            raw = await self._client.navigation_set_visualization({
                "mode": request.mode,
            })
            result = NavigationSetVisualizationResult(
                ok=bool(raw.get("ok", True)),
                mode=str(raw.get("mode", request.mode)),
                backend=str(raw.get("backend", "carb_settings")),
                setting_path=raw.get("setting_path"),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="NAVIGATION_SET_VISUALIZATION_ERROR",
            )

    async def sample_walkable_points(
        self, meta: OperationMeta, request: SampleWalkablePointsRequest,
    ) -> ModuleResult[SampleWalkablePointsResult]:
        """Sample N random walkable points on the baked NavMesh (spec §8.1).

        Algorithm prefers area-weighted barycentric over the triangle list;
        falls back to bbox-rejection (random point + reachability check) when
        triangle iteration API is absent on this Kit build (response.method
        reports which path was taken). Requires prior navigation_bake.
        """
        started = int(time.time() * 1000)
        try:
            raw = await self._client.navigation_sample_walkable_points(request.to_dict())
            if not raw.get("ok", False):
                return error_result(
                    raw.get("reason", "sample_walkable_points failed"),
                    started_ms=started,
                    error_code="NAVIGATION_SAMPLE_ERROR",
                )
            pts = tuple(
                (float(p[0]), float(p[1]), float(p[2]))
                for p in (raw.get("points") or [])
            )
            result = SampleWalkablePointsResult(
                ok=True,
                points=pts,
                triangle_count=int(raw.get("triangle_count", 0)),
                total_area_m2=float(raw.get("total_area_m2", 0.0)),
                seed=raw.get("seed"),
                method=str(raw.get("method", "area_weighted")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc, error_code="NAVIGATION_SAMPLE_ERROR",
            )
